"""KTT112026 entry — wire voice + game."""
from __future__ import annotations

import logging
from pathlib import Path

from discord.ext import commands

from ktt112026.config import Settings
from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.discord.admin_commands import setup_admin
from ktt112026.game.discord.commands import setup_game
from ktt112026.game.services.economy.code_service import CodeService
from ktt112026.game.services.world.daily_service import DailyService
from ktt112026.game.services.world.quest_service import QuestService
from ktt112026.game.services.social.sect_service import SectService
from ktt112026.game.services.world.world_event_service import WorldEventService
from ktt112026.game.services.combat.pvp_service import PvpService
from ktt112026.game.services.economy.bet_service import BetService
from ktt112026.game.services.economy.taixiu_service import TaiXiuService
from ktt112026.game.services.social.leader_service import LeaderService
from ktt112026.game.services.world.mission_service import MissionService
from ktt112026.game.services.combat.sect_tower_service import SectTowerService
from ktt112026.game.services.combat.combat_service import CombatService
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.world.alchemy_service import AlchemyService
from ktt112026.game.services.economy.auction_service import AuctionService
from ktt112026.game.services.economy.economy_service import EconomyService
from ktt112026.game.services.social.leaderboard_service import LeaderboardService
from ktt112026.game.services.social.partner_service import PartnerService
from ktt112026.game.services.player.dokiep_service import DokiepService
from ktt112026.game.services.world.gather_service import GatherService
from ktt112026.game.services.economy.inventory_service import InventoryService
from ktt112026.game.services.economy.item_use_service import ItemUseService
from ktt112026.game.services.world.pet_service import PetService
from ktt112026.game.services.player.player_service import PlayerService
from ktt112026.game.services.economy.shop_service import ShopService
from ktt112026.game.services.player.stats_service import StatsService
from ktt112026.game.services.player.technique_service import TechniqueService
from ktt112026.game.services.combat.tower_service import TowerService
from ktt112026.voice.commands import VoiceCommands
from ktt112026.voice.music.manager import MusicManager
from ktt112026.game.discord.shop_delta import setup as setup_shop_delta

logger = logging.getLogger("ktt.bot")


class KTTBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = __import__("discord").Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=settings.command_prefix, intents=intents, help_command=None, case_insensitive=True)
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
        logger.info("Player database: %s", db_path.resolve())
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
        self.gather = GatherService(repo)
        self.alchemy = AlchemyService(repo)
        self.auction = AuctionService(repo)
        self.economy = EconomyService(repo)
        self.partners = PartnerService(repo)
        self.leaderboard = LeaderboardService(repo)
        self.codes = CodeService(repo)
        self.daily = DailyService(repo)
        self.quests = QuestService(repo)
        self.sects = SectService(repo)
        self.combat = CombatService(repo, self.stats)
        self.world_events = WorldEventService(repo)
        self.pvp = PvpService(repo, self.stats, self.combat)
        self.bet = BetService(repo)
        self.taixiu = TaiXiuService(repo)
        self.leaders = LeaderService(repo)
        self.missions = MissionService(repo)
        self.sect_tower = SectTowerService(repo, self.stats, self.combat)
        self._commands_synced = False


    async def on_command_error(self, ctx, error):
        """Always reply on command errors so users see feedback."""
        import traceback
        logger.exception("Command error: %s", error)
        # Ignore unknown command / check failures that are intentional
        from discord.ext.commands import CommandNotFound, CheckFailure
        if isinstance(error, (CommandNotFound, CheckFailure)):
            return
        msg = str(error) or type(error).__name__
        try:
            await ctx.reply(f"Lỗi lệnh: {msg[:200]}", mention_author=False)
        except Exception:
            pass

    async def setup_hook(self) -> None:
        await self.add_cog(VoiceCommands(self.music, self.settings))
        await setup_admin(self, self.codes, self.players, self.settings.admin_ids)
        try:
            wr = self.sects.process_weekly_rewards()
            try:
                lr = self.leaders.process_weekly()
                if lr.get("paid"):
                    logger.info("Global leader weekly: %s", lr)
            except Exception:
                logger.exception("leader weekly")
            if wr.get("paid") and wr.get("winners"):
                logger.info("Sect weekly rewards: %s", wr)
        except Exception:
            logger.exception("sect weekly rewards")
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
            self.gather,
            self.alchemy,
            self.economy,
            self.partners,
            self.leaderboard,
            self.auction,
            self.codes,
            self.daily,
            self.quests,
            self.sects,
            self.world_events,
            self.pvp,
            self.bet,
            self.taixiu,
            self.leaders,
            self.missions,
            self.sect_tower,
        )
        await setup_shop_delta(self)
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
