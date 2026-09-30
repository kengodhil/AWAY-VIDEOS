"""Upload / delete media on Backblaze B2 (S3-compatible API)."""
from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse, unquote

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings


class B2UploadError(Exception):
    pass


def _cfg():
    key_id = (getattr(settings, "B2_KEY_ID", "") or "").strip()
    app_key = (getattr(settings, "B2_APPLICATION_KEY", "") or "").strip()
    bucket = (getattr(settings, "B2_BUCKET_NAME", "") or "").strip()
    region = (getattr(settings, "B2_REGION", "") or "").strip()
    endpoint = (getattr(settings, "B2_ENDPOINT_URL", "") or "").strip()
    if not key_id or not app_key or not bucket:
        raise B2UploadError(
            "Backblaze B2 is not configured. Set B2_KEY_ID, B2_APPLICATION_KEY, "
            "and B2_BUCKET_NAME."
        )
    if not region and endpoint:
        # https://s3.us-west-004.backblazeb2.com → us-west-004
        host = endpoint.replace("https://", "").replace("http://", "").split("/")[0]
        parts = host.split(".")
        if len(parts) >= 2 and parts[0] == "s3":
            region = parts[1]
    if not region:
        region = "us-west-004"
    if not endpoint:
        endpoint = f"https://s3.{region}.backblazeb2.com"
    return key_id, app_key, bucket, region, endpoint.rstrip("/")


def _client():
    key_id, app_key, _bucket, region, endpoint = _cfg()
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=app_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def _public_url(key: str) -> str:
    base = (getattr(settings, "B2_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    if base:
        return f"{base}/{key}"

    _key_id, _app, bucket, region, endpoint = _cfg()
    # S3-compatible public URL (works when bucket is public)
    return f"https://{bucket}.s3.{region}.backblazeb2.com/{key}"


def _safe_name(name: str, fallback_ext: str) -> str:
    base = Path(name or "file").name
    ext = Path(base).suffix.lower() or fallback_ext
    if ext not in {".mp4", ".webm", ".mov", ".jpg", ".jpeg", ".png", ".webp"}:
        ext = fallback_ext
    return f"{uuid.uuid4().hex}{ext}"


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


def _upload(key: str, file_obj, content_type: str) -> str:
    _key_id, _app, bucket, _region, _endpoint = _cfg()
    client = _client()
    body, close_after = _file_body(file_obj)
    extra = {
        "ContentType": content_type or "application/octet-stream",
        "CacheControl": "public, max-age=31536000",
    }
    try:
        client.upload_fileobj(body, bucket, key, ExtraArgs=extra)
    except (ClientError, BotoCoreError) as exc:
        raise B2UploadError(f"B2 upload failed: {exc}") from exc
    finally:
        if close_after:
            try:
                body.close()
            except Exception:
                pass
    return _public_url(key)


def upload_video(file_obj, title: str = "") -> tuple[str, str]:
    name = _safe_name(getattr(file_obj, "name", "") or "video.mp4", ".mp4")
    key = f"videos/{name}"
    size = getattr(file_obj, "size", None)
    if size is not None and size < 1000:
        raise B2UploadError("Video file is too small or corrupt.")
    url = _upload(key, file_obj, _content_type(name, "video/mp4"))
    return url, ""


def upload_image(file_obj) -> str:
    name = _safe_name(getattr(file_obj, "name", "") or "thumb.jpg", ".jpg")
    key = f"thumbnails/{name}"
    return _upload(key, file_obj, _content_type(name, "image/jpeg"))


def delete_storage_object(url: str) -> None:
    if not url:
        return
    try:
        _key_id, _app, bucket, _region, _endpoint = _cfg()
    except B2UploadError:
        return

    path = urlparse(url).path.lstrip("/")
    # friendly URL: /file/bucket/key
    if path.startswith("file/"):
        parts = path.split("/", 2)
        if len(parts) == 3:
            path = parts[2]
    # virtual-host style may include bucket as first segment on some URLs
    if path.startswith(bucket + "/"):
        path = path[len(bucket) + 1 :]
    path = unquote(path)
    if not path:
        return
    try:
        _client().delete_object(Bucket=bucket, Key=path)
    except Exception:
        pass
