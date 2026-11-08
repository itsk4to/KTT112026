"""Registry of independent music players keyed by Discord guild ID."""
from __future__ import annotations

import logging

from .player import GuildMusicPlayer

logger = logging.getLogger(__name__)


class MusicManager:
    def __init__(self, *, max_queue: int = 100) -> None:
        self._players: dict[int, GuildMusicPlayer] = {}
        self._max_queue = max_queue

    def player(self, guild_id: int) -> GuildMusicPlayer:
        guild_id = int(guild_id)
        if guild_id not in self._players:
            self._players[guild_id] = GuildMusicPlayer(
                guild_id, max_queue=self._max_queue
            )
        return self._players[guild_id]

    def get_existing(self, guild_id: int) -> GuildMusicPlayer | None:
        return self._players.get(int(guild_id))

    def is_music_active(self, guild_id: int) -> bool:
        player = self.get_existing(guild_id)
        return bool(player and player.is_active)

    async def close(self) -> None:
        players = list(self._players.values())
        self._players.clear()
        for player in players:
            try:
                await player.leave()
            except Exception:
                logger.exception("Could not close voice player for guild %s", player.guild_id)
