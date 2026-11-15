"""Resolve a search term or video URL into a single audio track."""
from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from .models import Track

YTDL_OPTIONS: dict[str, Any] = {
    "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "noplaylist": True,
    "extract_flat": False,
    "socket_timeout": 15,
    "retries": 2,
    "extractor_retries": 2,
}


def validate_query(query: str) -> str:
    normalized = (query or "").strip()
    if not normalized:
        raise ValueError("Hãy nhập link hoặc tên bài hát.")
    if len(normalized) > 500:
        raise ValueError("Từ khóa tìm nhạc tối đa 500 ký tự.")
    parsed = urlparse(normalized)
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Chỉ hỗ trợ link HTTP hoặc HTTPS.")
    return normalized


def _extract(query: str) -> dict[str, Any]:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Chưa cài yt-dlp. Hãy cài dependencies từ requirements.txt.") from exc

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)
    except Exception as exc:
        raise RuntimeError(f"Không thể lấy nguồn nhạc: {exc}") from exc

    if not info:
        raise RuntimeError("Không lấy được thông tin nguồn nhạc.")
    if info.get("entries") is not None:
        entries = [entry for entry in (info.get("entries") or []) if entry]
        if not entries:
            raise RuntimeError("Không tìm thấy bài hát phù hợp.")
        info = entries[0]

    stream_url = info.get("url")
    if not stream_url:
        raise RuntimeError("Nguồn không cung cấp luồng audio.")
    webpage_url = info.get("webpage_url") or query
    parsed_webpage = urlparse(str(webpage_url))
    if parsed_webpage.scheme.lower() not in {"http", "https"}:
        webpage_url = query if query.startswith(("http://", "https://")) else ""
    duration = info.get("duration")
    try:
        duration_value = int(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_value = None
    return {
        "title": str(info.get("title") or "Không rõ tên")[:200],
        "stream_url": str(stream_url),
        "webpage_url": str(webpage_url),
        "duration": duration_value,
    }


async def resolve_track(query: str, requester_id: int) -> Track:
    normalized = validate_query(query)
    data = await asyncio.to_thread(_extract, normalized)
    return Track(
        title=data["title"],
        stream_url=data["stream_url"],
        webpage_url=data["webpage_url"],
        duration=data["duration"],
        requester_id=int(requester_id),
    )


async def refresh_stream_url(webpage_url: str) -> str:
    """Refresh an expiring CDN URL when a track has waited in a long queue."""
    if not webpage_url:
        raise ValueError("Không có URL gốc để làm mới luồng audio.")
    data = await asyncio.to_thread(_extract, validate_query(webpage_url))
    return data["stream_url"]
