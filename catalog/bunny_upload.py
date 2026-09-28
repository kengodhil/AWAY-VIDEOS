"""Upload / delete videos on Bunny Stream (no blocking encode wait)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

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
    return {"AccessKey": api_key, "Accept": "application/json"}


def guid_from_url(url: str) -> str:
    if not url:
        return ""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if not parts:
        return ""
    candidate = parts[0]
    if re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        candidate,
    ):
        return candidate
    return ""


def delete_stream_video(guid_or_url: str) -> None:
    try:
        library_id, api_key, _cdn = _cfg()
    except BunnyUploadError:
        return

    guid = guid_or_url.strip()
    if "/" in guid or guid.startswith("http"):
        guid = guid_from_url(guid)
    if not guid:
        return

    url = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}"
    try:
        requests.delete(url, headers=_headers(api_key), timeout=30)
    except requests.RequestException:
        pass


def _file_stream(file_obj):
    """Prefer disk path to avoid loading whole video into RAM."""
    path = getattr(file_obj, "temporary_file_path", None)
    if callable(path):
        try:
            return open(path(), "rb")
        except Exception:
            pass
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    return file_obj


def upload_video(file_obj, title: str = "AWAY video") -> tuple[str, str]:
    """Create + upload to Bunny Stream. Returns URLs immediately (encode is async)."""
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
            f"Bunny create failed ({create.status_code}): {create.text[:300]}"
        )

    try:
        data = create.json() or {}
    except Exception:
        data = {}
    guid = str(data.get("guid") or "")
    if not guid:
        raise BunnyUploadError("Bunny did not return a video GUID.")

    size = getattr(file_obj, "size", None)
    if size is not None and size < 1000:
        raise BunnyUploadError("Video file is too small or corrupt.")

    put_url = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}"
    stream = _file_stream(file_obj)
    close_after = stream is not file_obj and hasattr(stream, "close")

    try:
        put = requests.put(
            put_url,
            headers={
                **_headers(api_key),
                "Content-Type": "application/octet-stream",
            },
            data=stream,
            timeout=300,
        )
    except requests.RequestException as exc:
        raise BunnyUploadError(f"Network error uploading video: {exc}") from exc
    finally:
        if close_after:
            try:
                stream.close()
            except Exception:
                pass

    if put.status_code not in (200, 201):
        raise BunnyUploadError(
            f"Bunny upload failed ({put.status_code}): {put.text[:300]}"
        )

    # Encode continues on Bunny; URLs work once processing finishes
    play = f"https://{cdn}/{guid}/play_720p.mp4"
    thumb = f"https://{cdn}/{guid}/thumbnail.jpg"
    return play, thumb
