"""Optional 24/7 voice-channel presence with safe reconnect behavior."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .music.manager import MusicManager

logger = logging.getLogger(__name__)


class VoicePresenceService:
    def __init__(self, music: MusicManager, channel_id: int, *, self_deaf: bool = True, interval: int = 45) -> None:
        self.music = music
        self.channel_id = int(channel_id)
        self.self_deaf = bool(self_deaf)
        self.interval = max(10, int(interval))
        self._task: asyncio.Task | None = None

    def start(self, client: Any) -> asyncio.Task | None:
        if not self.channel_id:
            logger.info("KTT_VOICE_CHANNEL_ID is empty; 24/7 presence is disabled")
            return None
        if self._task is not None and not self._task.done():
            return self._task
        self._task = asyncio.create_task(self._run(client), name="ktt-voice-presence")
        return self._task

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def connect_once(self, client: Any) -> Any | None:
        if not self.channel_id:
            return None
        channel = client.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(self.channel_id)
            except Exception:
                logger.exception("Cannot fetch configured voice channel %s", self.channel_id)
                return None

        try:
            import discord
        except ImportError:
            logger.error("discord.py is not installed")
            return None
        if not isinstance(channel, discord.VoiceChannel):
            logger.error("KTT_VOICE_CHANNEL_ID=%s is not a standard voice channel", self.channel_id)
            return None

        guild = channel.guild
        existing = guild.voice_client
        player = self.music.get_existing(guild.id)
        if existing and existing.is_connected():
            if existing.channel and existing.channel.id == channel.id:
                if player:
                    player.adopt_voice_client(existing)
                return existing
            if self.music.is_music_active(guild.id):
                logger.info("Keep current voice channel: music is active in guild %s", guild.id)
                return existing
            try:
                await existing.move_to(channel)
                if player:
                    player.adopt_voice_client(existing)
                return existing
            except Exception:
                logger.exception("Could not move voice client; trying a clean reconnect")
                try:
                    await existing.disconnect(force=True)
                except Exception:
                    logger.debug("Disconnect after failed move also failed", exc_info=True)

        try:
            voice = await channel.connect(
                reconnect=True, self_deaf=self.self_deaf, self_mute=False
            )
            if player:
                player.adopt_voice_client(voice)
            logger.info("Connected to voice presence channel %s (%s)", channel.name, channel.id)
            return voice
        except Exception:
            logger.exception("Failed to connect to configured voice channel %s", self.channel_id)
            return None

    async def _run(self, client: Any) -> None:
        await client.wait_until_ready()
        while not client.is_closed():
            try:
                await self.connect_once(client)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Voice presence loop failed")
            await asyncio.sleep(self.interval)
