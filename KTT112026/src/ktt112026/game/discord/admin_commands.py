"""Slash admin: /admin tutien …"""
from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from ktt112026.game.services.code_service import CodeService
from ktt112026.game.services.player_service import PlayerService

logger = logging.getLogger("ktt.admin")
VERSION_FILE = Path(__file__).resolve().parents[4] / "VERSION.txt"


def _read_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


class TutienAdminGroup(app_commands.Group):
    def __init__(
        self,
        bot: commands.Bot,
        codes: CodeService,
        players: PlayerService,
        admin_ids: tuple[int, ...],
    ) -> None:
        super().__init__(name="tutien", description="Quản trị game Đạo Lộ Tu Tiên")
        self.bot = bot
        self.codes = codes
        self.players = players
        self.admin_ids = set(admin_ids)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        uid = interaction.user.id
        if uid in self.admin_ids:
            return True
        try:
            if await self.bot.is_owner(interaction.user):
                return True
        except Exception:
            pass
        # If KTT_ADMIN_IDS empty, allow guild administrators
        if not self.admin_ids:
            perms = getattr(interaction.user, "guild_permissions", None)
            if perms and perms.administrator:
                return True
        await interaction.response.send_message(
            "Không có quyền. Thêm Discord ID vào biến `KTT_ADMIN_IDS`.",
            ephemeral=True,
        )
        return False

    @app_commands.command(name="version", description="Xem phiên bản bot")
    async def version(self, interaction: discord.Interaction) -> None:
        ver = _read_version()
        db_path = getattr(getattr(self.bot, "settings", None), "database_path", "?")
        await interaction.response.send_message(
            f"**KTT112026** v`{ver}`\nDB: `{db_path}`",
            ephemeral=True,
        )

    @app_commands.command(name="give_stones", description="Tặng / trừ Linh Thạch")
    @app_commands.describe(user="Người nhận", amount="Số LS (âm = trừ)")
    async def give_stones(
        self, interaction: discord.Interaction, user: discord.User, amount: int
    ) -> None:
        try:
            r = self.codes.gift_stones(str(user.id), amount)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        sign = "+" if r["delta"] > 0 else ""
        await interaction.response.send_message(
            f"{r['name']}: {sign}{r['delta']:,} LS → còn **{r['stones']:,}** LS",
            ephemeral=True,
        )

    @app_commands.command(name="create_code", description="Tạo giftcode")
    @app_commands.describe(
        stones="Linh Thạch mỗi lần nhập",
        max_uses="Tổng lượt dùng",
        code="Mã (trống = random)",
        expires_days="Hết hạn sau N ngày (0 = không)",
        note="Ghi chú",
    )
    async def create_code(
        self,
        interaction: discord.Interaction,
        stones: int,
        max_uses: app_commands.Range[int, 1, 100000] = 1,
        code: str | None = None,
        expires_days: app_commands.Range[int, 0, 365] = 0,
        note: str = "",
    ) -> None:
        try:
            r = self.codes.create_code(
                code=code,
                stones=stones,
                max_uses=int(max_uses),
                expires_days=int(expires_days),
                note=note,
                created_by=str(interaction.user.id),
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        exp = f"<t:{r['expires_at']}:R>" if r["expires_at"] else "không hạn"
        await interaction.response.send_message(
            f"Mã **`{r['code']}`** · {r['stones']:,} LS · {r['max_uses']} lượt · HSD: {exp}\n"
            f"Nhập: `.code {r['code']}`",
            ephemeral=True,
        )

    @app_commands.command(name="list_codes", description="Liệt kê giftcode")
    async def list_codes(self, interaction: discord.Interaction) -> None:
        rows = self.codes.list_codes(15)
        if not rows:
            await interaction.response.send_message("Chưa có mã.", ephemeral=True)
            return
        lines = [
            f"`{r['code']}` · {int(r['reward_stones']):,} LS · {int(r['used_count'])}/{int(r['max_uses'])}"
            for r in rows
        ]
        await interaction.response.send_message("\n".join(lines)[:1800], ephemeral=True)

    @app_commands.command(name="delete_code", description="Xóa giftcode")
    async def delete_code(self, interaction: discord.Interaction, code: str) -> None:
        try:
            self.codes.delete_code(code)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(f"Đã xóa `{code.upper()}`.", ephemeral=True)

    @app_commands.command(name="lookup", description="Tra tài khoản game")
    async def lookup(self, interaction: discord.Interaction, user: discord.User) -> None:
        try:
            r = self.codes.lookup(str(user.id))
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"**{r['name']}** (`{r['user_id']}`)\n"
            f"C{r['major']}.{r['minor']} · {r['path'] or '—'} · {r['faction'] or '—'}\n"
            f"Tu Vi {r['cultivation']:,} · LS **{r['stones']:,}** · TL {r['stamina']}",
            ephemeral=True,
        )

    @app_commands.command(name="set_stones", description="Set cứng Linh Thạch")
    async def set_stones(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: app_commands.Range[int, 0, 10_000_000_000],
    ) -> None:
        p = self.players.get(str(user.id))
        if p is None:
            await interaction.response.send_message("Chưa có thể đạo.", ephemeral=True)
            return
        p.spirit_stones = int(amount)
        self.players.repo.save(p)
        await interaction.response.send_message(
            f"{p.display_name}: LS = **{p.spirit_stones:,}**",
            ephemeral=True,
        )


async def setup_admin(
    bot: commands.Bot,
    codes: CodeService,
    players: PlayerService,
    admin_ids: tuple[int, ...],
) -> None:
    if bot.tree.get_command("admin") is not None:
        bot.tree.remove_command("admin")
    root = app_commands.Group(name="admin", description="Quản trị bot")
    root.add_command(TutienAdminGroup(bot, codes, players, admin_ids))
    bot.tree.add_command(root)
    logger.info("Registered /admin tutien (admins=%s)", admin_ids or "owner/guild-admin fallback")
