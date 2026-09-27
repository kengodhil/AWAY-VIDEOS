"""Upload media to Cloudinary CDN (chunked for large videos)."""
from __future__ import annotations

from django.conf import settings


class CloudinaryUploadError(Exception):
    pass


def upload_video(file_obj) -> str:
    """Upload video file; return secure CDN URL."""
    if not getattr(settings, "USE_CLOUDINARY", False):
        raise CloudinaryUploadError("CLOUDINARY_URL is not configured on the server.")

    import cloudinary.uploader

    try:
        # upload_large supports files bigger than ~100MB via chunks
        result = cloudinary.uploader.upload_large(
            file_obj,
            resource_type="video",
            folder="away-videos/videos",
            chunk_size=6 * 1024 * 1024,
            eager_async=True,
        )
    except Exception as exc:
        raise CloudinaryUploadError(str(exc)) from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise CloudinaryUploadError("Cloudinary returned no URL. Check API keys.")
    return url


def upload_image(file_obj) -> str:
    """Upload image; return secure CDN URL."""
    if not getattr(settings, "USE_CLOUDINARY", False):
        raise CloudinaryUploadError("CLOUDINARY_URL is not configured on the server.")

    import cloudinary.uploader

    try:
        result = cloudinary.uploader.upload(
            file_obj,
            resource_type="image",
            folder="away-videos/thumbnails",
        )
    except Exception as exc:
        raise CloudinaryUploadError(str(exc)) from exc

    url = result.get("secure_url") or result.get("url")
    if not url:
        raise CloudinaryUploadError("Cloudinary returned no URL for image.")
    return url
