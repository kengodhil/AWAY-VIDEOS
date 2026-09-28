"""Upload videos to Bunny Stream; return playable CDN + thumbnail URLs."""
from __future__ import annotations

import time

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


def _get_video(library_id: str, api_key: str, guid: str) -> dict:
    url = f"https://video.bunnycdn.com/library/{library_id}/videos/{guid}"
    r = requests.get(url, headers=_headers(api_key), timeout=30)
    if r.status_code != 200:
        return {}
    try:
        return r.json() or {}
    except Exception:
        return {}


def _play_urls(library_id: str, api_key: str, cdn: str, guid: str) -> tuple[str, str]:
    """Resolve best playback + thumbnail URL after upload/encode."""
    # Prefer API play data when available
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
                # fallbackUrl is a prefix for MP4 renditions
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
    status = info.get("status")
    # 4 = finished encoding
    if status == 4 or info.get("hasMP4Fallback"):
        return (
            f"https://{cdn}/{guid}/play_720p.mp4",
            f"https://{cdn}/{guid}/thumbnail.jpg",
        )

    # Early play: original file (enable "Keep original" / early play in library)
    return (
        f"https://{cdn}/{guid}/original",
        f"https://{cdn}/{guid}/thumbnail.jpg",
    )


def upload_video(file_obj, title: str = "AWAY video") -> tuple[str, str]:
    """Create Stream video + upload bytes. Returns (playback_url, thumbnail_url)."""
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
    size = len(body)
    if size < 1000:
        raise BunnyUploadError("Video file is too small or corrupt.")

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

    # Wait for encode / original availability (status 4 = finished)
    for _ in range(24):
        info = _get_video(library_id, api_key, guid)
        st = info.get("status")
        progress = info.get("encodeProgress") or 0
        if st == 4 or progress >= 100:
            break
        if st in (5, 6):
            raise BunnyUploadError(
                f"Bunny processing failed (status={st}). Check file format (use MP4 H.264)."
            )
        time.sleep(5)

    play, thumb = _play_urls(library_id, api_key, cdn, guid)
    return play, thumb
