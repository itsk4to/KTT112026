"""Environment-backed application settings. No secrets are stored in source."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


def _positive_int(env: Mapping[str, str], key: str, default: int, *, allow_zero: bool = False) -> int:
    raw = env.get(key, str(default)).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    minimum = 0 if allow_zero else 1
    return value if value >= minimum else default


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    command_prefix: str = "."
    voice_channel_id: int = 0
    voice_self_deaf: bool = True
    voice_keepalive_seconds: int = 45
    max_music_queue: int = 100
    max_tts_chars: int = 500
    log_level: str = "INFO"
    sync_commands_on_start: bool = True

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env
        prefix = source.get("KTT_COMMAND_PREFIX", ".").strip() or "."
        log_level = source.get("KTT_LOG_LEVEL", "INFO").strip().upper() or "INFO"
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            log_level = "INFO"
        return cls(
            discord_token=source.get("DISCORD_TOKEN", "").strip(),
            command_prefix=prefix,
            voice_channel_id=_positive_int(source, "KTT_VOICE_CHANNEL_ID", 0, allow_zero=True),
            voice_self_deaf=_bool(source, "KTT_VOICE_SELF_DEAF", True),
            voice_keepalive_seconds=_positive_int(source, "KTT_VOICE_KEEPALIVE_SECONDS", 45),
            max_music_queue=_positive_int(source, "KTT_MAX_MUSIC_QUEUE", 100),
            max_tts_chars=_positive_int(source, "KTT_MAX_TTS_CHARS", 500),
            log_level=log_level,
            sync_commands_on_start=_bool(source, "KTT_SYNC_COMMANDS_ON_START", True),
        )
