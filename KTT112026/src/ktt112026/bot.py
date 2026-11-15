"""KTT112026 entry — wire voice + game."""
from __future__ import annotations

import logging
from pathlib import Path

from discord.ext import commands

from ktt112026.config import Settings
from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.discord.commands import setup_game
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.alchemy_service import AlchemyService
from ktt112026.game.services.economy_service import EconomyService
from ktt112026.game.services.leaderboard_service import LeaderboardService
from ktt112026.game.services.partner_service import PartnerService
from ktt112026.game.services.dokiep_service import DokiepService
from ktt112026.game.services.exploration_service import ExplorationService
from ktt112026.game.services.gather_service import GatherService
from ktt112026.game.services.inventory_service import InventoryService
from ktt112026.game.services.item_use_service import ItemUseService
from ktt112026.game.services.pet_service import PetService
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.shop_service import ShopService
from ktt112026.game.services.stats_service import StatsService
from ktt112026.game.services.technique_service import TechniqueService
from ktt112026.game.services.tower_service import TowerService
from ktt112026.voice.commands import VoiceCommands
from ktt112026.voice.music.manager import MusicManager
from ktt112026.voice.presence import VoicePresenceService

logger = logging.getLogger("ktt.bot")


class KTTBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = __import__("discord").Intents.default()
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
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(db_path)
        ensure_schema(self.db)
        repo = PlayerRepository(self.db)
        self.player_repo = repo
        self.players = PlayerService(repo)
        self.shop = ShopService(repo)
        self.stats = StatsService(repo)
        self.dokiep = DokiepService(repo)
        self.tower = TowerService(repo, self.stats)
        self.inventory = InventoryService(repo)
        self.items = ItemUseService(repo)
        self.techniques = TechniqueService(repo)
        self.pets = PetService(repo)
        self.exploration = ExplorationService(repo)
        self.gather = GatherService(repo)
        self.alchemy = AlchemyService(repo)
        self.economy = EconomyService(repo)
        self.partners = PartnerService(repo)
        self.leaderboard = LeaderboardService(repo)
        self._commands_synced = False

    async def setup_hook(self) -> None:
        await self.add_cog(VoiceCommands(self.music, self.settings))
        await setup_game(
            self,
            self.players,
            self.shop,
            self.dokiep,
            self.tower,
            self.inventory,
            self.items,
            self.techniques,
            self.stats,
            self.pets,
            self.exploration,
            self.gather,
            self.alchemy,
            self.economy,
            self.partners,
            self.leaderboard,
        )
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
        self.db.close()
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
