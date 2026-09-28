"""Upload videos to Bunny Stream; serve via Stream CDN."""
from __future__ import annotations

import requests
from django.conf import settings


class BunnyUploadError(Exception):
    pass


def _cfg():
    library_id = str(getattr(settings, "BUNNY_STREAM_LIBRARY_ID", "") or "").strip()
    api_key = (getattr(settings, "BUNNY_STREAM_API_KEY", "") or "").strip()
    cdn = (getattr(settings, "BUNNY_STREAM_CDN_HOSTNAME", "") or "").strip()
    if not library_id or not api_key or not cdn:
        raise BunnyUploadError(
            "Bunny Stream is not configured. Set BUNNY_STREAM_LIBRARY_ID, "
            "BUNNY_STREAM_API_KEY, and BUNNY_STREAM_CDN_HOSTNAME."
        )
    cdn = cdn.replace("https://", "").replace("http://", "").rstrip("/")
    return library_id, api_key, cdn


def _headers(api_key: str) -> dict:
    return {
        "AccessKey": api_key,
        "Accept": "application/json",
    }


def upload_video(file_obj, title: str = "AWAY video") -> tuple[str, str]:
    """Create Stream video + upload file. Returns (playback_url, thumbnail_url)."""
    library_id, api_key, cdn = _cfg()

    create_url = f"https://video.bunnycdn.com/library/{library_id}/videos"
    try:
        create = requests.post(
            create_url,
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={"title": (title or "AWAY video")[:120]},
            timeout=60,
        )
    except requests.RequestException as exc:
        raise BunnyUploadError(f"Network error creating video: {exc}") from exc

    if create.status_code not in (200, 201):
        raise BunnyUploadError(
            f"Bunny create video failed ({create.status_code}): {create.text[:300]}"
        )

    data = create.json() if create.content else {}
    guid = str(data.get("guid") or "")
    if not guid:
        raise BunnyUploadError("Bunny did not return a video GUID.")

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    body = file_obj.read()
    if not body:
        raise BunnyUploadError("Empty video file.")

    put_url = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}"
    try:
        put = requests.put(
            put_url,
            headers={
                **_headers(api_key),
                "Content-Type": "application/octet-stream",
            },
            data=body,
            timeout=600,
        )
    except requests.RequestException as exc:
        raise BunnyUploadError(f"Network error uploading video: {exc}") from exc

    if put.status_code not in (200, 201):
        raise BunnyUploadError(
            f"Bunny upload failed ({put.status_code}): {put.text[:300]}"
        )

    # MP4 after encode; original works early if library allows it
    playback = f"https://{cdn}/{guid}/play_720p.mp4"
    thumb = f"https://{cdn}/{guid}/thumbnail.jpg"
    return playback, thumb


def upload_image(file_obj) -> str:
    """Thumbnails: optional local-only fallback (Stream generates thumbs)."""
    raise BunnyUploadError("Use video file upload; Stream generates thumbnails.")
