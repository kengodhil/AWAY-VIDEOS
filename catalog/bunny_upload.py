"""Upload media to Bunny.net Edge Storage; serve via CDN pull zone."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

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
            "Bunny is not configured. Set BUNNY_STORAGE_ZONE, BUNNY_STORAGE_API_KEY, "
            "and BUNNY_CDN_HOSTNAME on Render."
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


def _put(path: str, data: bytes, content_type: str) -> str:
    zone, key, cdn, host = _cfg()
    url = f"https://{host}/{zone}/{path.lstrip('/')}"
    try:
        resp = requests.put(
            url,
            data=data,
            headers={
                "AccessKey": key,
                "Content-Type": content_type or "application/octet-stream",
            },
            timeout=300,
        )
    except requests.RequestException as exc:
        raise BunnyUploadError(f"Network error talking to Bunny: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise BunnyUploadError(
            f"Bunny upload failed ({resp.status_code}): {resp.text[:300]}"
        )

    return f"https://{cdn}/{path.lstrip('/')}"


def upload_video(file_obj) -> str:
    name = _safe_name(getattr(file_obj, "name", "") or "video.mp4", ".mp4")
    path = f"away-videos/videos/{name}"
    data = file_obj.read()
    if not data:
        raise BunnyUploadError("Empty video file.")
    ctype = getattr(file_obj, "content_type", None) or "video/mp4"
    return _put(path, data, ctype)


def upload_image(file_obj) -> str:
    name = _safe_name(getattr(file_obj, "name", "") or "thumb.jpg", ".jpg")
    path = f"away-videos/thumbnails/{name}"
    data = file_obj.read()
    if not data:
        raise BunnyUploadError("Empty image file.")
    ctype = getattr(file_obj, "content_type", None) or "image/jpeg"
    return _put(path, data, ctype)
