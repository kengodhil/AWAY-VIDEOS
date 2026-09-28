"""Upload / delete videos on Bunny Stream."""
from __future__ import annotations

import re
import time
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
    """Extract Stream video GUID from a CDN URL path."""
    if not url:
        return ""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if not parts:
        return ""
    # https://vz-xxx.b-cdn.net/{guid}/play_720p.mp4
    candidate = parts[0]
    if re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        candidate,
    ):
        return candidate
    return ""


def delete_stream_video(guid_or_url: str) -> None:
    """Delete a video from Bunny Stream library (best-effort)."""
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


def _get_video(library_id: str, api_key: str, guid: str) -> dict:
    url = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}"
    try:
        r = requests.get(url, headers=_headers(api_key), timeout=30)
    except requests.RequestException:
        return {}
    if r.status_code != 200:
        return {}
    try:
        return r.json() or {}
    except Exception:
        return {}


def _play_urls(library_id: str, api_key: str, cdn: str, guid: str) -> tuple[str, str]:
    play_api = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}/play"
    try:
        r = requests.get(play_api, headers=_headers(api_key), timeout=30)
        if r.status_code == 200:
            data = r.json() or {}
            thumb = (data.get("thumbnailUrl") or "").strip()
            original = (data.get("originalUrl") or "").strip()
            playlist = (data.get("videoPlaylistUrl") or "").strip()
            fallback = (data.get("fallbackUrl") or "").strip()

            play = original or ""
            if not play and fallback:
                play = fallback.rstrip("/") + "/play_720p.mp4"
            if not play and playlist:
                play = playlist
            if play:
                if not thumb:
                    thumb = f"https://{cdn}/{guid}/thumbnail.jpg"
                return play, thumb
    except requests.RequestException:
        pass

    info = _get_video(library_id, api_key, guid)
    if info.get("status") == 4 or info.get("hasMP4Fallback"):
        return (
            f"https://{cdn}/{guid}/play_720p.mp4",
            f"https://{cdn}/{guid}/thumbnail.jpg",
        )

    return (
        f"https://{cdn}/{guid}/original",
        f"https://{cdn}/{guid}/thumbnail.jpg",
    )


def upload_video(file_obj, title: str = "AWAY video") -> tuple[str, str]:
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

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    body = file_obj.read()
    if not body:
        raise BunnyUploadError("Empty video file.")
    if len(body) < 1000:
        raise BunnyUploadError("Video file is too small or corrupt.")

    put_url = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}"
    try:
        put = requests.put(
            put_url,
            headers={**_headers(api_key), "Content-Type": "application/octet-stream"},
            data=body,
            timeout=600,
        )
    except requests.RequestException as exc:
        raise BunnyUploadError(f"Network error uploading video: {exc}") from exc

    if put.status_code not in (200, 201):
        raise BunnyUploadError(
            f"Bunny upload failed ({put.status_code}): {put.text[:300]}"
        )

    for _ in range(24):
        info = _get_video(library_id, api_key, guid)
        st = info.get("status")
        progress = info.get("encodeProgress") or 0
        if st == 4 or progress >= 100:
            break
        if st in (5, 6):
            raise BunnyUploadError(
                f"Bunny processing failed (status={st}). Use MP4 H.264."
            )
        time.sleep(5)

    return _play_urls(library_id, api_key, cdn, guid)
