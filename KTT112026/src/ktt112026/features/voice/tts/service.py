"""TTS synthesis and queue integration; playback shares the guild audio queue."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ..music.models import TTSClip
from .voices import DEFAULT_VOICE, VOICE_LABELS


def validate_tts_text(text: str, max_chars: int = 500) -> str:
    value = (text or "").strip()
    if not value:
        raise ValueError("Nội dung TTS không được để trống.")
    if len(value) > max_chars:
        raise ValueError(f"TTS giới hạn {max_chars} ký tự mỗi lần đọc.")
    return value


async def synthesize(
    text: str,
    *,
    requester_id: int = 0,
    voice_name: str = DEFAULT_VOICE,
    max_chars: int = 500,
) -> TTSClip:
    normalized = validate_tts_text(text, max_chars)
    if voice_name not in VOICE_LABELS:
        raise ValueError("Giọng đọc chưa được hỗ trợ.")
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Chưa cài edge-tts. Hãy cài dependencies từ requirements.txt.") from exc

    descriptor, file_path = tempfile.mkstemp(suffix=".mp3", prefix="ktt112026-tts-")
    os.close(descriptor)
    try:
        communicate = edge_tts.Communicate(normalized, voice_name)
        await communicate.save(file_path)
        if not Path(file_path).is_file() or Path(file_path).stat().st_size == 0:
            raise RuntimeError("TTS không tạo được file âm thanh.")
    except Exception:
        Path(file_path).unlink(missing_ok=True)
        raise
    preview = " ".join(normalized.split())
    if len(preview) > 60:
        preview = preview[:57] + "..."
    return TTSClip(title=f"TTS: {preview}", file_path=file_path, requester_id=int(requester_id))


async def enqueue_speech(
    player,
    text: str,
    requester_id: int,
    *,
    voice_name: str = DEFAULT_VOICE,
    max_chars: int = 500,
) -> tuple[int, bool]:
    clip = await synthesize(
        text,
        requester_id=requester_id,
        voice_name=voice_name,
        max_chars=max_chars,
    )
    try:
        position = await player.enqueue_tts(clip)
        return position, player.current is clip
    except Exception:
        clip.cleanup()
        raise
