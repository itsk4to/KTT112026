"""Concurrency-safe, per-guild audio queue.

The voice client's ``after`` callback runs on Discord's audio thread. This player
captures the owning asyncio loop at connect time and always schedules work back
onto that loop with ``call_soon_threadsafe``.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from .models import QueueItem, TTSClip, Track

logger = logging.getLogger(__name__)

STREAM_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin"
STREAM_OPTIONS = "-vn"
FILE_OPTIONS = "-vn -nostdin"
PCM_OPTIONS = "-vn -ac 2 -ar 48000 -f s16le"


def make_audio_source(item: QueueItem, executable: str) -> Any:
    """Create an FFmpeg source lazily, after an item reaches the queue head."""
    import discord

    if isinstance(item, TTSClip):
        try:
            return discord.FFmpegOpusAudio(
                item.file_path, executable=executable, options=FILE_OPTIONS, bitrate=96
            )
        except Exception as opus_error:
            logger.warning("TTS Opus source failed; falling back to PCM: %s", opus_error)
            return discord.FFmpegPCMAudio(
                item.file_path, executable=executable, options=PCM_OPTIONS
            )

    try:
        return discord.FFmpegOpusAudio(
            item.stream_url,
            executable=executable,
            before_options=STREAM_BEFORE_OPTIONS,
            options=STREAM_OPTIONS,
            bitrate=128,
        )
    except Exception as opus_error:
        logger.warning("Opus source failed; falling back to PCM: %s", opus_error)
        return discord.FFmpegPCMAudio(
            item.stream_url,
            executable=executable,
            before_options=STREAM_BEFORE_OPTIONS,
            options=PCM_OPTIONS,
        )


class GuildMusicPlayer:
    def __init__(
        self,
        guild_id: int,
        *,
        max_queue: int = 100,
        source_factory: Callable[[QueueItem, str], Any] = make_audio_source,
    ) -> None:
        self.guild_id = int(guild_id)
        self.max_queue = max(1, int(max_queue))
        self.queue: deque[QueueItem] = deque()
        self.current: QueueItem | None = None
        self.voice: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._source_factory = source_factory
        self._transition_lock = asyncio.Lock()

    @property
    def is_active(self) -> bool:
        voice_active = bool(
            self.voice and (self.voice.is_playing() or self.voice.is_paused())
        )
        return bool(self.current or self.queue or voice_active)

    @property
    def current_track(self) -> Track | None:
        return self.current if isinstance(self.current, Track) else None

    async def connect(self, channel: Any) -> Any:
        self._loop = asyncio.get_running_loop()
        guild = channel.guild
        voice = getattr(guild, "voice_client", None)
        if voice and voice.is_connected():
            if voice.channel and voice.channel.id != channel.id:
                await voice.move_to(channel)
            # A 24/7 presence connection may be self-deafened; music needs audio enabled.
            try:
                await guild.change_voice_state(
                    channel=channel, self_deaf=False, self_mute=False
                )
            except Exception:
                logger.exception("Could not update bot deaf/mute state before playback")
            self.voice = voice
            await self._play_next()
            return voice

        self.voice = await channel.connect(
            reconnect=True, self_deaf=False, self_mute=False
        )
        await self._play_next()
        return self.voice

    def adopt_voice_client(self, voice: Any) -> None:
        """Register a voice client created by the 24/7 presence service."""
        self._loop = asyncio.get_running_loop()
        self.voice = voice
        if self.queue and not (voice.is_playing() or voice.is_paused()):
            asyncio.create_task(self._play_next())

    async def enqueue(self, track: Track) -> int:
        return await self._enqueue_item(track)

    async def enqueue_tts(self, clip: TTSClip) -> int:
        return await self._enqueue_item(clip)

    async def _enqueue_item(self, item: QueueItem) -> int:
        if len(self.queue) >= self.max_queue:
            if isinstance(item, TTSClip):
                item.cleanup()
            raise RuntimeError(f"Hàng chờ đã đạt giới hạn {self.max_queue} mục.")
        self.queue.append(item)
        position = len(self.queue)
        should_start = self.current is None and not (
            self.voice and (self.voice.is_playing() or self.voice.is_paused())
        )
        if should_start:
            await self._play_next()
        return position

    async def _play_next(self) -> None:
        async with self._transition_lock:
            while True:
                voice = self.voice
                if voice is None or not voice.is_connected():
                    return
                if voice.is_playing() or voice.is_paused():
                    return
                if not self.queue:
                    self.current = None
                    return

                item = self.queue.popleft()
                self.current = item
                try:
                    if isinstance(item, Track) and item.webpage_url and time.monotonic() - item.resolved_at > 120:
                        from .resolver import refresh_stream_url

                        fresh_url = await refresh_stream_url(item.webpage_url)
                        if self.current is not item:
                            continue
                        item = replace(item, stream_url=fresh_url, resolved_at=time.monotonic())
                        self.current = item
                    from ..audio.ffmpeg import get_ffmpeg_executable

                    source = self._source_factory(item, get_ffmpeg_executable())
                    try:
                        import discord
                    except ImportError:
                        discord = None
                    if discord is not None and isinstance(source, discord.PCMAudio):
                        source = discord.PCMVolumeTransformer(source, volume=1.0)
                    voice.play(
                        source,
                        after=lambda error, finished=item: self._after_audio(error, finished),
                    )
                    logger.info("Playing %s for guild %s", item.title, self.guild_id)
                    return
                except Exception:
                    logger.exception("Could not start audio item %s", item.title)
                    self._cleanup_item(item)
                    self.current = None
                    # Continue iteratively: a long run of bad sources cannot grow the call stack.

    def _after_audio(self, error: Exception | None, finished_item: QueueItem) -> None:
        """Audio-thread callback; never manipulate asyncio primitives here."""
        if error:
            logger.warning("Audio playback ended with error in guild %s: %s", self.guild_id, error)
        loop = self._loop
        if loop is None or loop.is_closed():
            self._cleanup_item(finished_item)
            return
        try:
            loop.call_soon_threadsafe(self._schedule_advance, finished_item)
        except RuntimeError:
            self._cleanup_item(finished_item)

    def _schedule_advance(self, finished_item: QueueItem) -> None:
        asyncio.create_task(self._advance_after_audio(finished_item))

    async def _advance_after_audio(self, finished_item: QueueItem) -> None:
        # Ignore late callbacks from audio that was stopped after a newer item started.
        if self.current is not finished_item:
            self._cleanup_item(finished_item)
            return
        self.current = None
        self._cleanup_item(finished_item)
        await self._play_next()

    @staticmethod
    def _cleanup_item(item: QueueItem | None) -> None:
        if isinstance(item, TTSClip):
            try:
                item.cleanup()
            except OSError:
                logger.exception("Could not clean temporary TTS file")

    async def skip(self) -> QueueItem | None:
        skipped = self.current
        if skipped is None and self.queue:
            skipped = self.queue.popleft()
            self._cleanup_item(skipped)
            await self._play_next()
            return skipped
        if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
            self.voice.stop()
            # The audio callback schedules the next item on the owning event loop.
        else:
            self.current = None
            self._cleanup_item(skipped)
            await self._play_next()
        return skipped

    async def stop(self) -> None:
        queued = list(self.queue)
        self.queue.clear()
        current = self.current
        self.current = None
        for item in queued:
            self._cleanup_item(item)
        self._cleanup_item(current)
        if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
            self.voice.stop()

    async def pause(self) -> bool:
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            return True
        return False

    async def resume(self) -> bool:
        if self.voice and self.voice.is_paused():
            self.voice.resume()
            return True
        return False

    async def leave(self) -> None:
        await self.stop()
        voice = self.voice
        self.voice = None
        if voice and voice.is_connected():
            await voice.disconnect(force=True)
        self._loop = None
