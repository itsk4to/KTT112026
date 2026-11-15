"""FFmpeg discovery with system-install preference and imageio fallback."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)
_cached_executable: str | None = None


def get_ffmpeg_executable() -> str:
    global _cached_executable
    if _cached_executable and Path(_cached_executable).is_file():
        return _cached_executable

    system_path = shutil.which("ffmpeg")
    if system_path:
        _cached_executable = system_path
        logger.info("Using system FFmpeg: %s", system_path)
        return system_path

    try:
        import imageio_ffmpeg

        bundled_path = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled_path and Path(bundled_path).is_file():
            _cached_executable = bundled_path
            logger.info("Using imageio-ffmpeg binary: %s", bundled_path)
            return bundled_path
    except Exception:
        logger.exception("Could not locate bundled FFmpeg")

    raise RuntimeError(
        "Không tìm thấy FFmpeg. Hãy cài FFmpeg trên máy chạy bot hoặc cài package imageio-ffmpeg."
    )
