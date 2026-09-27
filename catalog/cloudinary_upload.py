"""Upload media to Cloudinary CDN."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

from django.conf import settings


class CloudinaryUploadError(Exception):
    pass


def _ensure_configured():
    if not getattr(settings, "USE_CLOUDINARY", False):
        raise CloudinaryUploadError(
            "CLOUDINARY_URL is not set on the server. Add it in Render → Environment."
        )

    import cloudinary

    raw = (os.environ.get("CLOUDINARY_URL") or "").strip().strip("'\"")
    if not raw:
        raise CloudinaryUploadError("CLOUDINARY_URL is empty.")

    parsed = urlparse(raw)
    cloud_name = (parsed.hostname or "").strip()
    api_key = unquote(parsed.username or "")
    api_secret = unquote(parsed.password or "")
    if not (cloud_name and api_key and api_secret):
        raise CloudinaryUploadError(
            "CLOUDINARY_URL must look like: cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    return cloud_name


def upload_video(file_obj) -> str:
    """Upload video file; return secure CDN URL."""
    _ensure_configured()
    import cloudinary.uploader

    # Only simple signed options — eager_async caused Invalid Signature
    options = {
        "resource_type": "video",
        "folder": "away-videos/videos",
    }

    try:
        try:
            result = cloudinary.uploader.upload_large(
                file_obj,
                chunk_size=6 * 1024 * 1024,
                **options,
            )
        except Exception:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            result = cloudinary.uploader.upload(file_obj, **options)
    except Exception as exc:
        msg = str(exc)
        if "Invalid Signature" in msg or "Invalid signature" in msg:
            raise CloudinaryUploadError(
                "Invalid Signature: check CLOUDINARY_URL on Render. "
                "Copy the full API Environment variable from Cloudinary → API Keys "
                "(cloudinary://KEY:SECRET@cloud_name) with no extra spaces or quotes."
            ) from exc
        raise CloudinaryUploadError(msg) from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise CloudinaryUploadError("Cloudinary returned no URL. Check API keys.")
    return url


def upload_image(file_obj) -> str:
    """Upload image; return secure CDN URL."""
    _ensure_configured()
    import cloudinary.uploader

    try:
        result = cloudinary.uploader.upload(
            file_obj,
            resource_type="image",
            folder="away-videos/thumbnails",
        )
    except Exception as exc:
        msg = str(exc)
        if "Invalid Signature" in msg or "Invalid signature" in msg:
            raise CloudinaryUploadError(
                "Invalid Signature: re-copy CLOUDINARY_URL from Cloudinary dashboard."
            ) from exc
        raise CloudinaryUploadError(msg) from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise CloudinaryUploadError("Cloudinary returned no URL for image.")
    return url
