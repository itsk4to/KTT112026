"""Audio queue data structures independent of Discord transport."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Track:
    title: str
    stream_url: str
    webpage_url: str
    duration: int | None
    requester_id: int
    resolved_at: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class TTSClip:
    title: str
    file_path: str
    requester_id: int

    def cleanup(self) -> None:
        Path(self.file_path).unlink(missing_ok=True)


QueueItem = Track | TTSClip
