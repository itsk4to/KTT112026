"""Discord application bootstrap; feature logic lives outside this module."""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from .config import Settings
from .features.voice.music.manager import MusicManager
from .features.voice.presence import VoicePresenceService
from .platform.discord_app.voice_commands import VoiceCommands

logger = logging.getLogger(__name__)


class KTTBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.voice_states = True
        # Required for the retained .tts prefix command. Enable Message Content Intent
        # in the Discord Developer Portal as well as here.
        intents.message_content = True
        super().__init__(command_prefix=settings.command_prefix, intents=intents, help_command=None)
        self.settings = settings
        self.music = MusicManager(max_queue=settings.max_music_queue)
        self.voice_presence = VoicePresenceService(
            self.music,
            settings.voice_channel_id,
            self_deaf=settings.voice_self_deaf,
            interval=settings.voice_keepalive_seconds,
        )
        self._commands_synced = False

    async def setup_hook(self) -> None:
        await self.add_cog(VoiceCommands(self.music, self.settings))
        if self.settings.sync_commands_on_start and not self._commands_synced:
            try:
                await self.tree.sync()
                self._commands_synced = True
                logger.info("Discord application commands synchronized")
            except Exception:
                logger.exception("Could not synchronize application commands")

    async def on_ready(self) -> None:
        logger.info("KTT112026 connected as %s", self.user)
        self.voice_presence.start(self)

    async def close(self) -> None:
        await self.voice_presence.stop()
        await self.music.close()
        await super().close()


def run(settings: Settings | None = None) -> None:
    active_settings = settings or Settings.from_env()
    if not active_settings.discord_token:
        raise SystemExit("Thiếu DISCORD_TOKEN trong biến môi trường.")
    logging.basicConfig(
        level=getattr(logging, active_settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = KTTBot(active_settings)
    bot.run(active_settings.discord_token, log_handler=None)
