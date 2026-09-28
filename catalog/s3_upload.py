"""Upload / delete media on AWS S3 (instant MP4 playback)."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings


class S3UploadError(Exception):
    pass


def _cfg():
    key = (getattr(settings, "AWS_ACCESS_KEY_ID", "") or "").strip()
    secret = (getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or "").strip()
    bucket = (getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or "").strip()
    region = (getattr(settings, "AWS_S3_REGION_NAME", "") or "us-east-1").strip()
    if not key or not secret or not bucket:
        raise S3UploadError(
            "S3 is not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, "
            "and AWS_STORAGE_BUCKET_NAME."
        )
    return key, secret, bucket, region


def _client():
    key, secret, _bucket, region = _cfg()
    return boto3.client(
        "s3",
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=region,
    )


def _public_url(key: str) -> str:
    custom = (getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "") or "").strip()
    custom = custom.replace("https://", "").replace("http://", "").rstrip("/")
    if custom:
        return f"https://{custom}/{key}"

    _k, _s, bucket, region = _cfg()
    if region == "us-east-1":
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _safe_name(name: str, fallback_ext: str) -> str:
    base = Path(name or "file").name
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip(".-") or "file"
    if "." not in base:
        base = f"{base}{fallback_ext}"
    return f"{uuid.uuid4().hex[:12]}-{base}"


def _content_type(name: str, default: str) -> str:
    lower = (name or "").lower()
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".webm"):
        return "video/webm"
    if lower.endswith(".mov"):
        return "video/quicktime"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    return default


def _file_body(file_obj):
    path = getattr(file_obj, "temporary_file_path", None)
    if callable(path):
        try:
            return open(path(), "rb"), True
        except Exception:
            pass
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    return file_obj, False


def upload_video(file_obj, title: str = "") -> tuple[str, str]:
    """Upload video to S3. Returns (video_url, empty_thumb_placeholder)."""
    _key, _secret, bucket, _region = _cfg()
    client = _client()

    name = _safe_name(getattr(file_obj, "name", "") or "video.mp4", ".mp4")
    key = f"away-videos/videos/{name}"
    ctype = _content_type(name, "video/mp4")
    body, close_after = _file_body(file_obj)

    extra = {
        "ContentType": ctype,
        "CacheControl": "public, max-age=31536000",
    }
    # Public-read only if bucket still uses ACLs; ignore failure on ACL-disabled buckets
    try:
        extra["ACL"] = "public-read"
        client.upload_fileobj(body, bucket, key, ExtraArgs=extra)
    except ClientError as exc:
        code = (exc.response or {}).get("Error", {}).get("Code", "")
        if code in ("AccessControlListNotSupported", "InvalidRequest", "AccessDenied"):
            extra.pop("ACL", None)
            if close_after:
                body.close()
                body, close_after = _file_body(file_obj)
            try:
                client.upload_fileobj(body, bucket, key, ExtraArgs=extra)
            except (ClientError, BotoCoreError) as exc2:
                raise S3UploadError(f"S3 upload failed: {exc2}") from exc2
        else:
            raise S3UploadError(f"S3 upload failed: {exc}") from exc
    except BotoCoreError as exc:
        raise S3UploadError(f"S3 upload failed: {exc}") from exc
    finally:
        if close_after:
            try:
                body.close()
            except Exception:
                pass

    return _public_url(key), ""


def upload_image(file_obj) -> str:
    _key, _secret, bucket, _region = _cfg()
    client = _client()

    name = _safe_name(getattr(file_obj, "name", "") or "thumb.jpg", ".jpg")
    key = f"away-videos/thumbnails/{name}"
    ctype = _content_type(name, "image/jpeg")
    body, close_after = _file_body(file_obj)

    extra = {
        "ContentType": ctype,
        "CacheControl": "public, max-age=31536000",
    }
    try:
        extra["ACL"] = "public-read"
        client.upload_fileobj(body, bucket, key, ExtraArgs=extra)
    except ClientError as exc:
        code = (exc.response or {}).get("Error", {}).get("Code", "")
        if code in ("AccessControlListNotSupported", "InvalidRequest", "AccessDenied"):
            extra.pop("ACL", None)
            if close_after:
                body.close()
                body, close_after = _file_body(file_obj)
            try:
                client.upload_fileobj(body, bucket, key, ExtraArgs=extra)
            except (ClientError, BotoCoreError) as exc2:
                raise S3UploadError(f"S3 image upload failed: {exc2}") from exc2
        else:
            raise S3UploadError(f"S3 image upload failed: {exc}") from exc
    except BotoCoreError as exc:
        raise S3UploadError(f"S3 image upload failed: {exc}") from exc
    finally:
        if close_after:
            try:
                body.close()
            except Exception:
                pass

    return _public_url(key)


def delete_s3_object(url: str) -> None:
    if not url:
        return
    try:
        _key, _secret, bucket, _region = _cfg()
    except S3UploadError:
        return

    path = urlparse(url).path.lstrip("/")
    # Bucket-style URL: /bucket/key or path-style
    if path.startswith(bucket + "/"):
        path = path[len(bucket) + 1 :]
    if not path:
        return
    try:
        _client().delete_object(Bucket=bucket, Key=path)
    except Exception:
        pass
