"""Upload / delete media on Bunny Edge Storage; serve via Pull Zone CDN."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings


class BunnyUploadError(Exception):
    pass


def _cfg():
    zone = (getattr(settings, "BUNNY_STORAGE_ZONE", "") or "").strip()
    key = (getattr(settings, "BUNNY_STORAGE_API_KEY", "") or "").strip()
    cdn = (getattr(settings, "BUNNY_CDN_HOSTNAME", "") or "").strip()
    host = (getattr(settings, "BUNNY_STORAGE_HOST", "") or "storage.bunnycdn.com").strip()
    if not zone or not key or not cdn:
        raise BunnyUploadError(
            "Bunny Storage is not configured. Set BUNNY_STORAGE_ZONE, "
            "BUNNY_STORAGE_API_KEY, and BUNNY_CDN_HOSTNAME."
        )
    cdn = cdn.replace("https://", "").replace("http://", "").rstrip("/")
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    return zone, key, cdn, host


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


def _put(path: str, file_obj, content_type: str) -> str:
    zone, key, cdn, host = _cfg()
    url = f"https://{host}/{zone}/{path.lstrip('/')}"
    body, close_after = _file_body(file_obj)
    try:
        resp = requests.put(
            url,
            data=body,
            headers={
                "AccessKey": key,
                "Content-Type": content_type or "application/octet-stream",
            },
            timeout=300,
        )
    except requests.RequestException as exc:
        raise BunnyUploadError(f"Network error talking to Bunny: {exc}") from exc
    finally:
        if close_after:
            try:
                body.close()
            except Exception:
                pass

    if resp.status_code not in (200, 201):
        raise BunnyUploadError(
            f"Bunny upload failed ({resp.status_code}): {resp.text[:300]}"
        )
    return f"https://{cdn}/{path.lstrip('/')}"


def upload_video(file_obj, title: str = "") -> tuple[str, str]:
    """Upload MP4 to Storage. Returns (cdn_url, empty_thumb). Instant play."""
    name = _safe_name(getattr(file_obj, "name", "") or "video.mp4", ".mp4")
    path = f"away-videos/videos/{name}"
    ctype = _content_type(name, "video/mp4")
    size = getattr(file_obj, "size", None)
    if size is not None and size < 1000:
        raise BunnyUploadError("Video file is too small or corrupt.")
    url = _put(path, file_obj, ctype)
    return url, ""


def upload_image(file_obj) -> str:
    name = _safe_name(getattr(file_obj, "name", "") or "thumb.jpg", ".jpg")
    path = f"away-videos/thumbnails/{name}"
    ctype = _content_type(name, "image/jpeg")
    return _put(path, file_obj, ctype)


def delete_storage_object(url: str) -> None:
    """Best-effort delete from Bunny Storage."""
    if not url:
        return
    try:
        zone, key, cdn, host = _cfg()
    except BunnyUploadError:
        return

    path = urlparse(url).path.lstrip("/")
    # CDN URL is https://cdn-host/path — path is storage path
    if not path:
        return
    api = f"https://{host}/{zone}/{path}"
    try:
        requests.delete(api, headers={"AccessKey": key}, timeout=30)
    except requests.RequestException:
        pass
