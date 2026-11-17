"""Prefix game commands — image UI + button interactions."""
from __future__ import annotations

import logging
from io import BytesIO

import discord
from discord.ext import commands

from ktt112026.game.services.dokiep_service import DokiepService
from ktt112026.game.services.inventory_service import InventoryService
from ktt112026.game.services.item_use_service import ItemUseService
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.shop_service import ShopService
from ktt112026.game.services.alchemy_service import AlchemyService
from ktt112026.game.services.auction_service import AuctionService
from ktt112026.game.services.code_service import CodeService
from ktt112026.game.services.daily_service import DailyService
from ktt112026.game.services.quest_service import QuestService
from ktt112026.game.services.sect_service import SectService
from ktt112026.game.util.formatters import fmt_num, fmt_stones
from ktt112026.game.services.economy_service import EconomyService
from ktt112026.game.services.leaderboard_service import LeaderboardService
from ktt112026.game.services.partner_service import PartnerService
from ktt112026.game.services.exploration_service import ExplorationService
from ktt112026.game.services.gather_service import GatherService
from ktt112026.game.services.pet_service import PetService
from ktt112026.game.services.stats_service import StatsService
from ktt112026.game.services.technique_service import TechniqueService
from ktt112026.game.services.tower_service import TowerService
from ktt112026.game.content.shop import resolve_category
from ktt112026.game.render.cards import (
    render_partner_card,
    render_bag_card,
    render_create_card,
    render_cultivate_card,
    render_dokiep_card,
    render_profile_card,
    render_shop_buy_result,
    render_simple_result,
    render_tower_card,
)
from ktt112026.game.discord.dokiep_view import DokiepView
from ktt112026.game.discord.shop_view import ShopView
from ktt112026.game.discord.tower_view import TowerView

logger = logging.getLogger("ktt.game.commands")


class GameCommands(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        players: PlayerService,
        shop: ShopService,
        dokiep: DokiepService,
        tower: TowerService,
        inventory: InventoryService,
        items: ItemUseService,
        techniques: TechniqueService,
        stats: StatsService,
        pets: PetService,
        exploration: ExplorationService,
        gather: GatherService,
        alchemy: AlchemyService,
        economy: EconomyService,
        partners: PartnerService,
        leaderboard: LeaderboardService,
        auction: AuctionService,
        codes: CodeService,
        daily: DailyService,
        quests: QuestService,
        sects: SectService,
        world_events,
        pvp,
        missions,
        sect_tower,
    ) -> None:
        self.bot = bot
        self.players = players
        self.shop = shop
        self.dokiep = dokiep
        self.tower = tower
        self.inventory = inventory
        self.items = items
        self.techniques = techniques
        self.stats = stats
        self.pets = pets
        self.exploration = exploration
        self.gather = gather
        self.alchemy = alchemy
        self.economy = economy
        self.partners = partners
        self.leaderboard = leaderboard
        self.auction = auction
        self.codes = codes
        self.daily = daily
        self.quests = quests
        self.sects = sects
        self.world_events = world_events
        self.pvp = pvp
        self.missions = missions
        self.sect_tower = sect_tower

    async def _img(self, ctx: commands.Context, png: bytes, name: str = "card.png", view=None) -> None:
        file = discord.File(BytesIO(png), filename=name)
        await ctx.reply(file=file, view=view, mention_author=False)

    @commands.command(name="taothe")
    async def taothe(self, ctx: commands.Context) -> None:
        try:
            player = self.players.create(str(ctx.author.id), ctx.author.display_name)
        except ValueError as exc:
            await ctx.reply(str(exc), mention_author=False)
            return
        await self._img(ctx, render_create_card(player), "taothe.png")
        await ctx.reply(
            "Chào mừng đạo hữu. Gõ `.huongdan` để xem lộ trình · Bắt đầu bằng `.tu` hoặc `.tu 5`.",
            mention_author=False,
        )

    @commands.command(name="me", aliases=("the", "profile_me"))
    async def me(self, ctx: commands.Context) -> None:
        player = self.players.get(str(ctx.author.id))
        if player is None:
            await ctx.reply("Chưa có thể đạo. Gõ `.taothe`.", mention_author=False)
            return
        if player.display_name != ctx.author.display_name[:64]:
            player.display_name = ctx.author.display_name[:64]
            self.players.repo.save(player)
        from ktt112026.game.content.loader import catalog_by_id
        cat = catalog_by_id()
        gear = {
            "weapon1": cat.get(player.weapon1, {}).get("name") if player.weapon1 else None,
            "weapon2": cat.get(player.weapon2, {}).get("name") if player.weapon2 else None,
            "treasure": cat.get(player.treasure, {}).get("name") if player.treasure else None,
        }
        pets = []
        for pid in (player.pet1, player.pet2, player.pet3):
            if pid:
                pets.append(cat.get(pid, {}).get("name", pid))
        partner_name = None
        if player.partner_id:
            partner = self.players.get(player.partner_id)
            partner_name = partner.display_name if partner else player.partner_id
        techs = [f"{r['name']}T{r['tier']}" for r in self.techniques.list_learned(str(ctx.author.id))[:4]]
        try:
            eff = self.stats.effective(str(ctx.author.id))
            estats, power = eff["stats"], eff["power"]
        except Exception:
            estats, power = None, None
        png = render_profile_card(
            player,
            effective_stats=estats,
            power=power,
            gear_names=gear,
            pet_names=pets,
            partner_name=partner_name,
            techniques=techs,
        )
        await self._img(ctx, png, "me.png")

    @commands.command(name="tu", aliases=("tuluyen",))
    async def tu(self, ctx: commands.Context, times: str | None = None) -> None:
        # .tu | .tu 5 | .tu max
        arg: int | str = 1
        if times is not None:
            arg = times
        try:
            result = self.players.cultivate(str(ctx.author.id), arg)
        except ValueError as exc:
            await ctx.reply(str(exc), mention_author=False)
            return
        p = result["player"]
        self.quests.bump(str(ctx.author.id), "tu", int(result.get("ticks") or 1))
        # annotate batch on card via advanced flag text path
        advanced = bool(result.get("locked"))
        await self._img(
            ctx,
            render_cultivate_card(
                name=p.display_name, realm=result["realm"], gain=result["gain"],
                cultivation=result["cultivation"], need=result["need"],
                stamina=result["stamina"], max_stamina=result["max_stamina"],
                advanced=advanced,
            ),
            "tu.png",
        )
        if result.get("locked"):
            tip = "Tu Vi 100% — `.dp` đột phá tiểu cảnh" if p.minor_stage < 2 else "Hậu Kỳ 100% — `.dokiep`"
            await ctx.reply(f"🔒 {tip} | x{result['ticks']} lần · +{result['stones_gained']} LS", mention_author=False)
        elif result.get("ticks", 1) > 1:
            await ctx.reply(
                f"Đã tu **{result['ticks']}** lần · +{result['gain']:,} TV · +{result['stones_gained']} LS",
                mention_author=False,
            )

    @commands.command(name="dp", aliases=("dotpha",))
    async def dp(self, ctx: commands.Context) -> None:
        try:
            result = self.players.breakthrough_minor(str(ctx.author.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không đột phá được", detail=str(exc), ok=False))
            return
        ok = result["success"]
        detail = result["message"]
        if ok:
            detail += f" (tỷ lệ ~{result['rate']*100:.0f}%)"
        else:
            detail += f" · Còn {result['cultivation']:,}/{result['need']:,}"
        await self._img(
            ctx,
            render_simple_result(
                title="Đột phá tiểu cảnh" if ok else "Đột phá thất bại",
                detail=detail[:150],
                ok=ok,
            ),
        )


    @commands.command(name="code", aliases=("nhapcode", "giftcode"))
    async def redeem_code(self, ctx: commands.Context, code: str | None = None) -> None:
        if not code:
            await ctx.reply("`.code <ma>` — nhập giftcode", mention_author=False)
            return
        try:
            r = self.codes.redeem(str(ctx.author.id), code)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Mã không dùng được", detail=str(exc), ok=False))
            return
        parts = []
        if r["stones"]:
            parts.append(f"+{r['stones']:,} LS")
        if r["item_id"] and r["item_qty"]:
            parts.append(f"+{r['item_qty']} {r['item_id']}")
        detail = " · ".join(parts) + f" · Còn {r['stones_left']:,} LS"
        await self._img(ctx, render_simple_result(title=f"Đã nhập {r['code']}", detail=detail[:140]))



    @commands.command(name="nhiemvu", aliases=("quest", "nv"))
    async def nhiemvu(self, ctx: commands.Context) -> None:
        try:
            st = self.quests.status(str(ctx.author.id))
        except ValueError as exc:
            await ctx.reply(str(exc), mention_author=False)
            return
        lines = []
        for q in st["quests"]:
            flag = "✅" if q["claimed"] else ("🎁" if q["claimable"] else "⬜")
            lines.append(f"{flag} **{q['name']}** {q['current']}/{q['need']} (+{q['stones']} LS)")
        bonus = (
            "✅ Toàn thành" if st["all_claimed"]
            else ("🎁 Toàn thành sẵn sàng" if st["all_claimable"] else "⬜ Toàn thành (+%s LS)" % st["all_clear_stones"])
        )
        lines.append(bonus)
        lines.append("Nhận: `.nhannv` hoặc `.nhannv tu|bicanh|thap|full`")
        await ctx.reply("\n".join(lines), mention_author=False)

    @commands.command(name="nhannv", aliases=("claimquest",))
    async def nhannv(self, ctx: commands.Context, quest_id: str | None = None) -> None:
        try:
            r = self.quests.claim(str(ctx.author.id), quest_id)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Chưa nhận được", detail=str(exc), ok=False))
            return
        names = ", ".join(r["names"])
        await self._img(
            ctx,
            render_simple_result(title="Nhận nhiệm vụ", detail=f"{names} · +{r['stones']:,} LS"),
        )


    @commands.command(name="tongmon", aliases=("tong", "sect"))
    async def tongmon(self, ctx: commands.Context, action: str | None = None, arg: str | None = None) -> None:
        """
        `.tongmon` — danh sách
        `.tongmon vao|nhan|roi|moi|kick|chuc|gop|info|bxh|qua`
        """
        act = (action or "list").lower()

        def _target_id() -> str | None:
            if ctx.message.mentions:
                return str(ctx.message.mentions[0].id)
            if arg:
                raw = arg.strip().strip("<@!>")
                if raw.isdigit():
                    return raw
            return None

        if act in ("list", "ds", "xem"):
            rows = self.sects.list_sects()
            lines = ["**Tông Môn** — `.gianhap tongmon` rồi `vao <id>` · Lập tông: `.tongmon tao <tên>`"]
            for s in rows:
                path = s.get("path", "any")
                path_lbl = "Tiên" if path == "tien" else ("Ma" if path == "ma" else "Hỗn")
                tag = "NPC" if s.get("npc", True) else "PC"
                lines.append(
                    f"`{s['id']}` **{s['name']}** [{tag}] Lv.{s['level']} {path_lbl} · "
                    f"{s['members']}/{s['max_members']} · CH {fmt_num(s['contrib'])}"
                )
            lines.append(
                "Lệnh: `vao` · `tao` · `nhan` · `moi @` · `kick @` · `chuc @` · "
                "`gop` · `bxh` · `info` · `roi` — Quà top tuần tự động (đan/bảo khí)"
            )
            await ctx.reply("\n".join(lines), mention_author=False)
            return

        if act in ("vao", "join"):
            if not arg:
                await ctx.reply("`.tongmon vao <id>`", mention_author=False)
                return
            try:
                r = self.sects.join(str(ctx.author.id), arg)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Không vào được", detail=str(exc), ok=False))
                return
            role = "Tông Chủ" if r.get("role") == "leader" else "Đệ tử"
            await self._img(
                ctx,
                render_simple_result(
                    title="Gia nhập Tông Môn",
                    detail=f"{r['sect']['name']} · {role} · Cấp tông {r.get('level', 1)}",
                ),
            )
            return

        if act in ("nhan", "accept", "nhanloi"):
            try:
                r = self.sects.join_via_invite(str(ctx.author.id), arg)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Không nhận được", detail=str(exc), ok=False))
                return
            await self._img(
                ctx,
                render_simple_result(title="Đã nhận lời mời", detail=r["sect"]["name"][:80]),
            )
            return

        if act in ("roi", "leave"):
            try:
                r = self.sects.leave(str(ctx.author.id))
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Không rời được", detail=str(exc), ok=False))
                return
            await self._img(
                ctx,
                render_simple_result(title="Đã rời tông", detail=str(r["old"].get("name", ""))[:80]),
            )
            return

        if act in ("moi", "invite"):
            tid = _target_id()
            if not tid:
                await ctx.reply("`.tongmon moi @người_chơi`", mention_author=False)
                return
            try:
                r = self.sects.invite(str(ctx.author.id), tid)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Mời thất bại", detail=str(exc), ok=False))
                return
            await ctx.reply(
                f"Đã mời <@{tid}> vào **{r['sect']['name']}** "
                f"(còn {r['expires_hours']}h — đối phương: `.tongmon nhan`).",
                mention_author=False,
            )
            return

        if act in ("kick", "duoi"):
            tid = _target_id()
            if not tid:
                await ctx.reply("`.tongmon kick @người_chơi`", mention_author=False)
                return
            try:
                r = self.sects.kick(str(ctx.author.id), tid)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Kick thất bại", detail=str(exc), ok=False))
                return
            await ctx.reply(f"Đã mời rời tông: **{r['name']}**.", mention_author=False)
            return

        if act in ("chuc", "promote", "bonhiem"):
            tid = _target_id()
            role = "elder"
            # arg may be role if mention used
            if arg and not arg.startswith("<@"):
                role = arg
            # if two tokens: need parse from message
            parts = ctx.message.content.split()
            # .tongmon chuc @user elder
            for i, part in enumerate(parts):
                if part.lower() in ("elder", "member", "leader", "trưởng", "de_tu"):
                    role = {"trưởng": "elder", "de_tu": "member"}.get(part.lower(), part.lower())
            if not tid:
                await ctx.reply("`.tongmon chuc @user elder|member|leader`", mention_author=False)
                return
            try:
                r = self.sects.promote(str(ctx.author.id), tid, role)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Bổ nhiệm thất bại", detail=str(exc), ok=False))
                return
            await ctx.reply(f"**{r['name']}** → `{r['role']}`", mention_author=False)
            return

        if act in ("gop", "donate", "cung"):
            if not arg:
                await ctx.reply("`.tongmon gop <số_linh_thạch>`", mention_author=False)
                return
            try:
                r = self.sects.donate(str(ctx.author.id), int(arg))
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Cống hiến thất bại", detail=str(exc), ok=False))
                return
            self.missions.bump(str(ctx.author.id), "sect_contrib", int(r["contrib"]), absolute=True)
            await self._img(
                ctx,
                render_simple_result(
                    title="Cống hiến Tông Môn",
                    detail=(
                        f"-{fmt_num(r['amount'])} LS · CH {fmt_num(r['contrib'])} · "
                        f"Kho +{fmt_num(r['bank_add'])} · Cấp {r['level']}"
                        + (" · **Lên Tông Chủ!**" if r.get("promoted") else "")
                    ),
                ),
            )
            return

        if act in ("bxh", "rank", "xephang"):
            try:
                r = self.sects.ranking(str(ctx.author.id))
            except ValueError as exc:
                await ctx.reply(str(exc), mention_author=False)
                return
            lines = [
                f"**BXH {r['sect'].get('name', '')}** · Cấp {r['level']} · "
                f"{r['members']}/{r['max_members']} · CH {fmt_num(r['total'])}"
            ]
            medals = ["🥇", "🥈", "🥉"]
            for e in r["entries"]:
                med = medals[e["rank"] - 1] if e["rank"] <= 3 else f"`#{e['rank']}`"
                lines.append(f"{med} **{e['name']}** ({e['role']}) — {e['contrib_fmt']}")
            await ctx.reply("\n".join(lines), mention_author=False)
            return

        if act in ("info", "tt"):
            try:
                r = self.sects.info(str(ctx.author.id), arg)
            except ValueError as exc:
                await ctx.reply(str(exc), mention_author=False)
                return
            s = r["sect"]
            nxt = r.get("next_level_at")
            nxt_s = fmt_num(nxt) if nxt else "MAX"
            lines = [
                f"**{s['name']}** (`{s['id']}`) · Cấp **{r['level']}**",
                s.get("desc", ""),
                f"Tông Chủ: {r['leader_name']} · Thành viên {r['member_count']}/{r['max_members']}",
                f"Cống hiến: {fmt_num(r['contrib_total'])} · Kho: {fmt_num(r['bank'])} LS · Mốc cấp sau: {nxt_s}",
                "**Top cống hiến:**",
            ]
            for i, mrow in enumerate(r["members"][:5], 1):
                role = mrow.get("sect_role") or "member"
                rl = {"leader": "TC", "elder": "TL"}.get(role, "Đệ")
                lines.append(f"{i}. [{rl}] {mrow['display_name']} — {fmt_num(int(mrow['sect_contrib']))}")
            await ctx.reply("\n".join(lines), mention_author=False)
            return

        if act in ("tao", "create", "lap"):
            # .tongmon tao Tên Tông
            name = arg or ""
            parts = ctx.message.content.split(None, 2)
            if len(parts) >= 3:
                name = parts[2].strip()
            if not name:
                await ctx.reply(
                    f"`.tongmon tao <tên tông>` — phí 50k LS, cần cấp 3+, đã rời tông cũ.",
                    mention_author=False,
                )
                return
            try:
                r = self.sects.create_sect(str(ctx.author.id), name)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Không lập được tông", detail=str(exc), ok=False))
                return
            await self._img(
                ctx,
                render_simple_result(
                    title="Lập Tông Môn",
                    detail=f"{r['sect']['name']} (`{r['sect']['id']}`) · -{fmt_num(r['cost'])} LS · Bạn là Tông Chủ",
                ),
            )
            return

        await ctx.reply(
            "`.tongmon` · `vao` · `tao` · `nhan` · `moi @` · `kick @` · `chuc @` · "
            "`gop` · `bxh` · `info` · `roi`",
            mention_author=False,
        )


    @commands.command(name="daolu", aliases=("dao_lu", "partner"))
    async def daolu(self, ctx: commands.Context) -> None:
        p = self.players.get(str(ctx.author.id))
        if p is None:
            await ctx.reply("Chưa có thể đạo.", mention_author=False)
            return
        if not p.partner_id:
            await self._img(
                ctx,
                render_simple_result(title="Chưa có Đạo Lữ", detail="Dùng `.ketduyen @user` khi đủ duyên.", ok=False),
            )
            return
        partner = self.players.get(p.partner_id)
        if partner is None:
            await ctx.reply("Không tìm thấy đạo lữ (dữ liệu lệch).", mention_author=False)
            return
        import time
        joined = min(float(p.created_at or 0) or time.time(), float(partner.created_at or 0) or time.time())
        # Prefer last_songtu and partner link time from partner service if any
        delta = max(0, time.time() - joined)
        days = int(delta // 86400)
        hours = int((delta % 86400) // 3600)
        last = float(p.last_songtu_at or 0)
        if last <= 0:
            last_s = "Chưa song tu"
        else:
            ago = int(time.time() - last)
            last_s = f"{ago // 3600} giờ trước" if ago >= 3600 else f"{ago // 60} phút trước"
        png = render_partner_card(
            name=p.display_name,
            partner_name=partner.display_name,
            days=days,
            hours=hours,
            major=partner.major_realm,
            path=partner.path,
            last_songtu=last_s,
        )
        await self._img(ctx, png, "daolu.png")

    @commands.command(name="info", aliases=("xem", "xemthe", "nguoichoi"))
    async def info_other(self, ctx: commands.Context, user: str | None = None) -> None:
        """Xem thể đạo người khác: `.info @user`"""
        target = None
        if ctx.message.mentions:
            target = ctx.message.mentions[0]
        elif user:
            # raw id
            uid = user.strip().strip("<@!>")
            if uid.isdigit():
                target_id = uid
            else:
                await ctx.reply("Dùng `.info @tên` hoặc mention người chơi.", mention_author=False)
                return
            target = type("U", (), {"id": int(target_id), "display_name": uid})()
        else:
            await ctx.reply("`.info @user` để xem thể đạo người khác.", mention_author=False)
            return
        uid = str(target.id)
        p = self.players.get(uid)
        if p is None:
            await self._img(ctx, render_simple_result(title="Không có thể đạo", detail="Người này chưa `.taothe`.", ok=False))
            return
        try:
            eff = self.stats.effective(uid)
            power = int(eff["power"])
        except Exception:
            power = 0
            eff = None
        gear = {}
        pets = []
        # names optional
        png = render_profile_card(
            p,
            effective_stats=(eff or {}).get("stats"),
            power=power,
        )
        await self._img(ctx, png, "info.png")

    @commands.command(name="diemdanh", aliases=("daily", "checkin"))
    async def diemdanh(self, ctx: commands.Context) -> None:
        try:
            r = self.daily.claim(str(ctx.author.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Điểm danh", detail=str(exc), ok=False))
            return
        await self._img(
            ctx,
            render_simple_result(
                title=f"Điểm danh · chuỗi {r['streak']} ngày",
                detail=f"+{r['stones']:,} LS · +{r['stamina']} TL",
            ),
        )


    @commands.command(name="tim", aliases=("tra", "timdo", "lookup"))
    async def tim(self, ctx: commands.Context, *, query: str | None = None) -> None:
        """`.tim <id|tên|loại>` — tra cứu vật phẩm trong catalog."""
        if not query or not query.strip():
            await ctx.reply("`.tim <id hoặc tên>` ví dụ `.tim tukhidan` · `.tim kiếm`", mention_author=False)
            return
        from ktt112026.game.content.item_search import format_item_brief, search_items
        rows = search_items(query.strip(), limit=8)
        if not rows:
            await ctx.reply(f"Không thấy vật phẩm khớp `{query.strip()[:40]}`.", mention_author=False)
            return
        lines = [f"**Tra cứu:** `{query.strip()[:40]}` ({len(rows)} kết quả)"]
        for it in rows:
            lines.append(format_item_brief(it))
        await ctx.reply("\n".join(lines)[:1900], mention_author=False)


    @commands.command(name="sukien", aliases=("event", "worldevent"))
    async def sukien(self, ctx: commands.Context, action: str | None = None) -> None:
        """`.sukien` xem · `.sukien nhan` nhận thưởng ngày."""
        act = (action or "xem").lower()
        if act in ("nhan", "claim", "nhận"):
            try:
                r = self.world_events.claim(str(ctx.author.id))
                self.missions.bump(str(ctx.author.id), "sukien", 1)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Sự kiện", detail=str(exc), ok=False))
                return
            ev = r["event"]
            detail = f"{ev['name']}: +{r['stones']} LS"
            if r.get("cultivation"):
                detail += f" · +{r['cultivation']} tu vi"
            if r.get("stamina"):
                detail += f" · +{r['stamina']} TL"
            await self._img(ctx, render_simple_result(title="Nhận sự kiện thế giới", detail=detail[:150]))
            return
        cur = self.world_events.current()
        ev = cur["event"]
        await ctx.reply(
            f"**Sự kiện hôm nay** (`{cur['day']}`)\n"
            f"**{ev['name']}** — {ev['desc']}\n"
            f"Thưởng: {ev.get('stones', 0)} LS"
            + (f" · {ev.get('cultivation', 0)} tu vi" if ev.get("cultivation") else "")
            + "\nNhận: `.sukien nhan`",
            mention_author=False,
        )

    @commands.command(name="pvp", aliases=("thachdau", "duel"))
    async def pvp_cmd(self, ctx: commands.Context, action: str | None = None, arg: str | None = None) -> None:
        """`.pvp @user <cược>` · `.pvp chap` · `.pvp huy`"""
        act = (action or "").lower()
        def _target():
            if ctx.message.mentions:
                return str(ctx.message.mentions[0].id)
            if arg and arg.strip().strip("<@!>").isdigit():
                return arg.strip().strip("<@!>")
            return None

        if act in ("huy", "cancel"):
            try:
                r = self.pvp.cancel(str(ctx.author.id))
            except ValueError as exc:
                await ctx.reply(str(exc), mention_author=False)
                return
            await ctx.reply(f"Đã hủy thách — hoàn {r['wager']} LS cọc.", mention_author=False)
            return
        if act in ("chap", "accept", "nhan"):
            try:
                r = self.pvp.accept(str(ctx.author.id), arg)
            except ValueError as exc:
                await ctx.reply(str(exc), mention_author=False)
                return
            if r.get("draw"):
                await ctx.reply("PvP hòa — hoàn cọc hai bên.\n" + " | ".join((r.get("log") or [])[-2:]), mention_author=False)
                return
            await ctx.reply(
                f"PvP xong — **{r['winner_name']}** thắng +{r['pot']} LS.\n" + " | ".join((r.get("log") or [])[-2:]),
                mention_author=False,
            )
            return
        # challenge: .pvp @user 100 or .pvp 100 with mention
        tid = _target()
        # action might be mention if no subcommand
        wager_s = arg
        if tid is None and action and action.strip().strip("<@!>").isdigit():
            tid = action.strip().strip("<@!>")
        if ctx.message.mentions and not act.startswith("<@"):
            # .pvp @user 100 → action is mention garbled; parse content
            parts = ctx.message.content.split()
            # find number
            for part in parts[1:]:
                if part.isdigit():
                    wager_s = part
                    break
            tid = str(ctx.message.mentions[0].id)
        if not tid or not wager_s:
            await ctx.reply("`.pvp @user <cược>` · `.pvp chap` · `.pvp huy`", mention_author=False)
            return
        try:
            r = self.pvp.challenge(str(ctx.author.id), tid, int(wager_s))
        except ValueError as exc:
            await ctx.reply(str(exc), mention_author=False)
            return
        await ctx.reply(
            f"Đã thách <@{tid}> cược **{r['wager']}** LS (cọc đã giữ, hết hạn {r['expires_sec']}s).\n"
            f"Đối phương: `.pvp chap` · Bạn: `.pvp huy`",
            mention_author=False,
        )


    @commands.command(name="nvda", aliases=("nhiemvuda", "mission"))
    async def nvda(self, ctx: commands.Context, action: str | None = None, mid: str | None = None) -> None:
        """`.nvda` danh sách nhiệm vụ dài · `.nvda nhan [id]`"""
        act = (action or "list").lower()
        if act in ("nhan", "claim"):
            try:
                r = self.missions.claim(str(ctx.author.id), mid)
            except ValueError as exc:
                await ctx.reply(str(exc), mention_author=False)
                return
            await ctx.reply(
                f"Nhận nhiệm vụ dài: {', '.join(r['names'])} · +{r['stones']} LS",
                mention_author=False,
            )
            return
        st = self.missions.status(str(ctx.author.id))
        lines = ["**Nhiệm vụ dài hạn**"]
        for m in st["missions"]:
            lines.append(
                f"{m['flag']} `{m['id']}` **{m['name']}** {m['progress']}/{m['need']} — {m['desc']} (+{m['stones']} LS)"
            )
        lines.append("Nhận: `.nvda nhan` hoặc `.nvda nhan <id>`")
        await ctx.reply("\n".join(lines)[:1900], mention_author=False)

    @commands.command(name="tongthap", aliases=("secttower", "tthap"))
    async def tongthap(self, ctx: commands.Context) -> None:
        """Tông Tháp — chỉ đệ tử tông, đóng góp kho tông."""
        try:
            run = self.sect_tower.start(str(ctx.author.id))
            self.missions.bump(str(ctx.author.id), "thap", 1)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Tông Tháp", detail=str(exc), ok=False))
            return
        log = " | ".join(run.last_log[-2:]) if run.last_log else run.risk
        png = render_tower_card(
            floor=run.floor, risk=run.risk, stones=run.bag_stones,
            cult=run.bag_contrib, alive=run.alive, message=log[:180],
        )
        from ktt112026.game.discord.sect_tower_view import SectTowerView
        view = SectTowerView(self.sect_tower, ctx.author.id) if run.alive else None
        await self._img(ctx, png, "tongthap.png", view=view)


    @commands.command(name="muatl", aliases=("hoitl", "buystamina"))
    async def muatl(self, ctx: commands.Context, packs: int | None = 1) -> None:
        """`.muatl [số_gói]` — mua thể lực bằng Linh Thạch (tối đa 5 gói/ngày)."""
        try:
            r = self.players.buy_stamina(str(ctx.author.id), int(packs or 1))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không mua được thể lực", detail=str(exc), ok=False))
            return
        await self._img(
            ctx,
            render_simple_result(
                title="Mua thể lực",
                detail=(
                    f"+{r['gain']} TL · -{r['cost']:,} LS · "
                    f"{r['stamina']}/{r['max_stamina']} · còn {r['buys_left']} gói hôm nay"
                ),
            ),
        )

    @commands.command(name="help", aliases=("huongdan", "trogiup"))
    async def help_game(self, ctx: commands.Context) -> None:
        lines_help = [
            "**Kho:** `.tim`/`.tra` · **Tân thủ:** `.taothe` → `.tu` / `.tu 5` / `.tu max` → đầy thanh thì `.dp` (Hậu Kỳ thì `.dokiep`) → `.me` `.shop` `.thap` `.bicanh`",
            "**Đạo lộ:** `.chon tien|ma` · `.gianhap tongmon|tantu` · `.tongmon`",
            "**Đồ:** `.mua` `.dung <đan> [n]` `.hoc` `.tui` `.mac` · **Thú:** `.trieuhoi` `.mang`",
            "**Xã hội:** `.chuyen` `.ban` `.bxh` `.ketduyen` `.daolu` `.songtu` · **Mã:** `.code <mã>`",
            "**Ngày:** `.diemdanh` `.nhiemvu` `.nhannv` · **Xem người khác:** `.info @user` / `.xemthe @user`",
            "Thể lực hồi ngoại tuyến (~2 phút/điểm). Lệnh không phân biệt hoa/thường.",
        ]
        await ctx.reply("\n".join(lines_help), mention_author=False)

    @commands.command(name="chon")
    async def chon(self, ctx: commands.Context, path: str | None = None) -> None:
        if not path:
            await ctx.reply("`.chon tien` hoặc `.chon ma`", mention_author=False)
            return
        try:
            p = self.players.choose_path(str(ctx.author.id), path)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không chọn được", detail=str(exc), ok=False))
            return
        label = "Tiên Đạo" if p.path == "tien" else "Ma Đạo"
        await self._img(ctx, render_simple_result(title="Đã chọn Đạo Lộ", detail=f"{p.display_name} → {label}"))

    @commands.command(name="gianhap")
    async def gianhap(self, ctx: commands.Context, phe: str | None = None) -> None:
        if not phe:
            await ctx.reply("`.gianhap tongmon` hoặc `.gianhap tantu`", mention_author=False)
            return
        try:
            p = self.players.choose_faction(str(ctx.author.id), phe)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không gia nhập được", detail=str(exc), ok=False))
            return
        if p.faction == "tongmon":
            detail = "Đã chọn Tông Môn — `.tongmon` xem tông NPC rồi `.tongmon vao <id>`. Cống hiến đủ sẽ thành Tông Chủ."
        else:
            detail = "Đã chọn Tán Tu — tự do tu luyện, không vào tông NPC. Sau này vẫn có thể đổi hướng nếu thiết kế cho phép."
        await self._img(ctx, render_simple_result(title="Chọn thế lực", detail=detail[:150]))

    @commands.command(name="dokiep")
    async def dokiep(self, ctx: commands.Context) -> None:
        try:
            sess = self.dokiep.start(str(ctx.author.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Chưa Độ Kiếp được", detail=str(exc), ok=False))
            return
        prompt = sess.prompt()
        png = render_dokiep_card(
            round_no=prompt["round"], shields=prompt["shields"],
            message="Chọn một phương án hộ pháp.", options=prompt["options"],
            hints=prompt.get("hints") or [],
        )
        view = DokiepView(self.dokiep, ctx.author.id)
        await self._img(ctx, png, "dokiep.png", view=view)

    @commands.command(name="thap", aliases=("leothap",))
    async def thap(self, ctx: commands.Context) -> None:
        try:
            run = self.tower.start(str(ctx.author.id))
            self.quests.bump(str(ctx.author.id), "thap", 1)
            self.missions.bump(str(ctx.author.id), "thap", 1)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không leo tháp được", detail=str(exc), ok=False))
            return
        log = " | ".join(run.last_log[-2:]) if getattr(run, "last_log", None) else ""
        msg = (log + " — Tiếp tục hoặc Rút lui.") if log else "Tầng đầu — chọn Tiếp tục hoặc Rút lui."
        png = render_tower_card(
            floor=run.floor, risk=run.risk, stones=run.bag_stones,
            cult=run.bag_cultivation, alive=run.alive,
            message=msg[:180],
        )
        view = TowerView(self.tower, ctx.author.id) if run.alive else None
        await self._img(ctx, png, "thap.png", view=view)

    @commands.command(name="tui")
    async def tui(self, ctx: commands.Context, _muc: str | None = None) -> None:
        if self.players.get(str(ctx.author.id)) is None:
            await ctx.reply("Chưa có thể đạo.", mention_author=False)
            return
        items = self.inventory.list_items(str(ctx.author.id))
        await self._img(ctx, render_bag_card(items, name=ctx.author.display_name), "tui.png")

    @commands.command(name="mac")
    async def mac(self, ctx: commands.Context, item_id: str | None = None) -> None:
        if not item_id:
            await ctx.reply("`.mac <ma_do>`", mention_author=False)
            return
        try:
            name = self.inventory.equip(str(ctx.author.id), item_id)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không trang bị được", detail=str(exc), ok=False))
            return
        await self._img(ctx, render_simple_result(title="Đã trang bị", detail=name))

    @commands.command(name="dung")
    async def dung(self, ctx: commands.Context, item_id: str | None = None, qty: str | None = None) -> None:
        if not item_id:
            await ctx.reply("`.dung <mã_đan> [số_lượng]` — ví dụ `.dung linhdan 3`", mention_author=False)
            return
        n = 1
        if qty is not None:
            try:
                n = int(qty)
            except ValueError:
                await ctx.reply("Số lượng phải là số nguyên.", mention_author=False)
                return
        try:
            r = self.items.use(str(ctx.author.id), item_id, n)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không dùng được", detail=str(exc), ok=False))
            return
        detail = " · ".join(r.get("messages") or [])[:150]
        await self._img(ctx, render_simple_result(title=f"Dùng đan ×{r.get('qty', 1)}", detail=detail or "Xong"))


    @commands.command(name="hoc")
    async def hoc(self, ctx: commands.Context, technique_id: str | None = None) -> None:
        if not technique_id:
            await ctx.reply("`.hoc <ma_cong_phap>` — mua bí kíp trong shop rồi học.", mention_author=False)
            return
        try:
            result = self.techniques.learn(str(ctx.author.id), technique_id)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không học được", detail=str(exc), ok=False))
            return
        tech = result["technique"]
        detail = f"{tech['name']} · Tầng {result['tier']}/{result['max_tier']}"
        title = "Lĩnh ngộ công pháp" if result["first_learn"] else "Nâng tầng công pháp"
        await self._img(ctx, render_simple_result(title=title, detail=detail))

    @commands.command(name="congphap")
    async def congphap(self, ctx: commands.Context) -> None:
        rows = self.techniques.list_learned(str(ctx.author.id))
        if not rows:
            await self._img(ctx, render_simple_result(title="Công pháp", detail="Chưa học cuốn nào. .shop congphap → .hoc", ok=False))
            return
        detail = " | ".join(f"{r['name']} T{r['tier']}" for r in rows[:8])
        await self._img(ctx, render_simple_result(title="Công pháp đã học", detail=detail))

    @commands.command(name="lucchien", aliases=("power", "chienso"))
    async def lucchien(self, ctx: commands.Context) -> None:
        try:
            eff = self.stats.effective(str(ctx.author.id))
        except ValueError as exc:
            await ctx.reply(str(exc), mention_author=False)
            return
        s = eff["stats"]
        detail = (
            f"Lực chiến ~{eff['power']} | "
            f"Cốt {s['can_cot']} Ngộ {s['ngo_tinh']} Thức {s['than_thuc']} "
            f"Pháp {s['than_phap']} Vận {s['khi_van']}"
        )
        await self._img(ctx, render_simple_result(title="Chỉ số tổng", detail=detail))


    @commands.command(name="trieuhoi")
    async def trieuhoi(self, ctx: commands.Context, times: int = 1) -> None:
        try:
            result = self.pets.summon(str(ctx.author.id), times)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Triệu hồi thất bại", detail=str(exc), ok=False))
            return
        names = ", ".join(g["name"] for g in result["got"][:10])
        detail = f"-{result['cost']:,} LS ({result.get('cost_each', 5000):,}/lần) | {names} | Còn {result['stones_left']:,} LS"
        await self._img(ctx, render_simple_result(title="Triệu hồi Linh Thú", detail=detail[:140]))

    @commands.command(name="thu", aliases=("linhthu", "pet"))
    async def thu_list(self, ctx: commands.Context) -> None:
        rows = self.pets.list_owned(str(ctx.author.id))
        p = self.players.get(str(ctx.author.id))
        deployed = []
        if p:
            deployed = [x for x in (p.pet1, p.pet2, p.pet3) if x]
        if not rows:
            await self._img(ctx, render_simple_result(title="Linh thú", detail="Chưa có — .trieuhoi hoặc .trieuhoi 10", ok=False))
            return
        detail = " | ".join(f"{r['name']} x{r['quantity']}" for r in rows[:8])
        if deployed:
            detail = f"Xuất chiến: {', '.join(deployed)} · " + detail
        await self._img(ctx, render_simple_result(title="Kho Linh Thú", detail=detail[:140]))

    @commands.command(name="mang", aliases=("xuat",))
    async def mang(self, ctx: commands.Context, pet_id: str | None = None) -> None:
        if not pet_id:
            await ctx.reply("`.mang <ma_linh_thu>`", mention_author=False)
            return
        try:
            name = self.pets.deploy(str(ctx.author.id), pet_id)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không xuất chiến được", detail=str(exc), ok=False))
            return
        await self._img(ctx, render_simple_result(title="Xuất chiến", detail=name))

    @commands.command(name="thuve")
    async def thuve(self, ctx: commands.Context, pet_id: str | None = None) -> None:
        if not pet_id:
            await ctx.reply("`.thuve <ma_linh_thu>`", mention_author=False)
            return
        try:
            name = self.pets.recall(str(ctx.author.id), pet_id)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không thu được", detail=str(exc), ok=False))
            return
        await self._img(ctx, render_simple_result(title="Đã thu về", detail=name))

    @commands.command(name="bicanh")
    async def bicanh(self, ctx: commands.Context, zone_id: str | None = None) -> None:
        if zone_id is None:
            zones = self.exploration.list_zones()
            lines = [f"`{z['id']}` {z['name']} (C{z['major_min']}+) — {z.get('desc','')}" for z in zones[:8]]
            await ctx.reply("**Bí cảnh:** `.bicanh <id>`\n" + "\n".join(lines), mention_author=False)
            return
        try:
            r = self.exploration.explore(str(ctx.author.id), zone_id)
            self.quests.bump(str(ctx.author.id), "bicanh", 1)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không vào được", detail=str(exc), ok=False))
            return
        notes = " · ".join(r.get("event_notes") or [])
        detail = (
            f"{r['zone']['name']}: +{r['stones']:,} LS · +{r['cultivation']:,} TV · "
            f"thảo {r['herb_summary']} · {notes}"
        )[:150]
        await self._img(
            ctx,
            render_simple_result(title=f"Bí cảnh · {r.get('event','?')}", detail=detail),
        )
        if r.get("locked"):
            await ctx.reply("Tu Vi đầy — `.dp` hoặc `.dokiep`.", mention_author=False)


    @commands.command(name="haiduoc")
    async def haiduoc(self, ctx: commands.Context) -> None:
        try:
            result = self.gather.gather(str(ctx.author.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không hái được", detail=str(exc), ok=False))
            return
        detail = f"+{result['qty']} {result['name']} | Còn {result['left_today']} lượt hôm nay | TL {result['stamina']}"
        await self._img(ctx, render_simple_result(title="Dược Viên", detail=detail))

    @commands.command(name="congthuc")
    async def congthuc(self, ctx: commands.Context) -> None:
        rows = self.alchemy.list_recipes()
        detail = " · ".join(f"{r['id']}: {r['desc']}" for r in rows[:6])
        await self._img(ctx, render_simple_result(title="Công thức luyện đan", detail=detail[:150]))

    @commands.command(name="luyendan")
    async def luyendan(self, ctx: commands.Context, recipe_id: str | None = None) -> None:
        if not recipe_id:
            await ctx.reply("`.luyendan <id>` — xem `.congthuc`", mention_author=False)
            return
        try:
            result = self.alchemy.craft(str(ctx.author.id), recipe_id)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Luyện đan thất bại", detail=str(exc), ok=False))
            return
        if result["success"]:
            detail = f"Thành công {result['output_id']} x{result['qty']} (tỷ lệ ~{result['rate']*100:.0f}%)"
            await self._img(ctx, render_simple_result(title="Luyện đan", detail=detail))
        else:
            detail = f"Nổ đan — mất nguyên liệu (tỷ lệ ~{result['rate']*100:.0f}%)"
            await self._img(ctx, render_simple_result(title="Luyện đan xịt", detail=detail, ok=False))


    @commands.command(name="chuyen")
    async def chuyen(self, ctx: commands.Context, member: discord.Member | None = None, amount: int | None = None) -> None:
        if member is None or amount is None:
            await ctx.reply("`.chuyen @user <so_ls>`", mention_author=False)
            return
        try:
            r = self.economy.transfer(str(ctx.author.id), str(member.id), amount)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Chuyển thất bại", detail=str(exc), ok=False))
            return
        detail = f"→ {r['to_name']} +{r['amount']:,} LS | Bạn còn {r['from_left']:,} LS"
        await self._img(ctx, render_simple_result(title="Chuyển Linh Thạch", detail=detail))

    @commands.command(name="ban")
    async def ban_npc(self, ctx: commands.Context, item_id: str | None = None, qty: int = 1) -> None:
        if not item_id:
            await ctx.reply("`.ban <ma_do> [sl]` — bán cho NPC", mention_author=False)
            return
        try:
            r = self.economy.sell_npc(str(ctx.author.id), item_id, qty)
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Bán thất bại", detail=str(exc), ok=False))
            return
        detail = f"{r['name']} x{r['qty']} → +{r['total']:,} LS | Túi còn {r['stones']:,} LS"
        await self._img(ctx, render_simple_result(title="Bán NPC", detail=detail))

    @commands.command(name="bxh", aliases=("bangxephang", "top"))
    async def bxh(self, ctx: commands.Context, kind: str | None = None) -> None:
        """`.bxh` · `.bxh linhthach|canhgioi|tongmon|cunghien`"""
        data = self.leaderboard.top(kind or "lucchien", 10)
        if data["kind"] == "tongmon":
            from ktt112026.game.content.loader import load_sects
            names = {s["id"]: s["name"] for s in load_sects()}
            for e in data["entries"]:
                e["name"] = names.get(e["name"], e["name"])
        if not data["entries"]:
            await ctx.reply("Chưa có dữ liệu bảng xếp hạng.", mention_author=False)
            return
        lines = [f"**{data['title']}**"]
        medals = ["🥇", "🥈", "🥉"]
        for e in data["entries"]:
            med = medals[e["rank"] - 1] if e["rank"] <= 3 else f"`#{e['rank']}`"
            extra = f" · {e['realm']}" if e.get("realm") else ""
            lines.append(f"{med} **{e['name']}** — {e['score_fmt']} {data['score_label']}{extra}")
        lines.append("_Loại: lucchien · linhthach · canhgioi · tongmon · cunghien_")
        await ctx.reply("\n".join(lines), mention_author=False)


    @commands.command(name="ketduyen")
    async def ketduyen(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        if member is None:
            await ctx.reply("`.ketduyen @user`", mention_author=False)
            return
        try:
            r = self.partners.bind(str(ctx.author.id), str(member.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Kết duyên thất bại", detail=str(exc), ok=False))
            return
        await self._img(ctx, render_simple_result(title="Kết duyên Đạo Lữ", detail=f"Cùng {r['partner_name']}"))

    @commands.command(name="huyduyen")
    async def huyduyen(self, ctx: commands.Context) -> None:
        try:
            self.partners.unbind(str(ctx.author.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Không hủy được", detail=str(exc), ok=False))
            return
        await self._img(ctx, render_simple_result(title="Đã hủy duyên", detail="Hai bên không còn là Đạo Lữ"))

    @commands.command(name="songtu")
    async def songtu(self, ctx: commands.Context) -> None:
        try:
            r = self.partners.songtu(str(ctx.author.id))
        except ValueError as exc:
            await self._img(ctx, render_simple_result(title="Song tu thất bại", detail=str(exc), ok=False))
            return
        detail = (
            f"Cùng {r['partner_name']} | +{r['gain_self']:,} TV "
            f"(ĐL +{r['gain_partner']:,}) | +{r['bonus_pct']}% · 24h/lần"
        )
        await self._img(ctx, render_simple_result(title="Song Tu", detail=detail[:150]))


    @commands.command(name="daugia")
    async def daugia(self, ctx: commands.Context, action: str | None = None, *args: str) -> None:
        """
        .daugia — xem sàn
        .daugia dang <ma_do> <gia> [sl]
        .daugia mua <id>
        """
        act = (action or "list").lower()
        if act in ("list", "xem", "ds"):
            rows = self.auction.list_open(12)
            if not rows:
                await self._img(ctx, render_simple_result(title="Sàn Đấu Giá", detail="Trống — .daugia dang <ma> <gia>"))
                return
            detail = " · ".join(f"#{r['id']} {r['name']}x{r['quantity']}={r['price']:,}" for r in rows[:8])
            await self._img(ctx, render_simple_result(title="Sàn Đấu Giá", detail=detail[:150]))
            return
        if act in ("dang", "ban", "sell"):
            if len(args) < 2:
                await ctx.reply("`.daugia dang <ma_do> <gia> [sl]`", mention_author=False)
                return
            item_id = args[0]
            try:
                price = int(args[1])
                qty = int(args[2]) if len(args) > 2 else 1
            except ValueError:
                await ctx.reply("Giá/số lượng phải là số.", mention_author=False)
                return
            try:
                r = self.auction.create(str(ctx.author.id), item_id, price, qty)
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Đăng thất bại", detail=str(exc), ok=False))
                return
            await self._img(
                ctx,
                render_simple_result(
                    title="Đã đăng Sàn",
                    detail=f"#{r['id']} {r['name']} x{r['qty']} · {r['price']:,} LS · 48h",
                ),
            )
            return
        if act in ("mua", "buy"):
            if not args:
                await ctx.reply("`.daugia mua <id>`", mention_author=False)
                return
            try:
                r = self.auction.buy(str(ctx.author.id), int(args[0]))
            except ValueError as exc:
                await self._img(ctx, render_simple_result(title="Mua thất bại", detail=str(exc), ok=False))
                return
            await self._img(
                ctx,
                render_simple_result(
                    title="Mua thành công",
                    detail=f"{r['name']} x{r['qty']} · -{r['price']:,} LS (phí người bán {r['fee']:,})",
                ),
            )
            return
        await ctx.reply("`.daugia` | `.daugia dang <ma> <gia>` | `.daugia mua <id>`", mention_author=False)

    @commands.command(name="shop")
    async def shop(self, ctx: commands.Context, category: str | None = None, page: int = 1) -> None:
        cat = resolve_category(category) if category else None
        if category and cat is None:
            await self._img(
                ctx,
                render_shop_buy_result(ok=False, title="Sai gian hàng", detail="Dùng .shop hoặc bấm nút"),
            )
            return
        view = ShopView(shop=self.shop, owner_id=ctx.author.id, category=cat, page=max(0, int(page) - 1))
        png, name = view.render_image()
        await self._img(ctx, png, name, view=view)

    @commands.command(name="mua")
    async def mua(self, ctx: commands.Context, item_id: str | None = None, qty: int = 1) -> None:
        if not item_id:
            await self._img(
                ctx,
                render_shop_buy_result(ok=False, title="Thiếu mã đồ", detail=".mua <ma_do> [sl]"),
            )
            return
        try:
            result = self.shop.buy(str(ctx.author.id), item_id, qty)
        except ValueError as exc:
            await self._img(ctx, render_shop_buy_result(ok=False, title="Không mua được", detail=str(exc)))
            return
        it = result["item"]
        detail = f"{it['name']} x{result['qty']} | -{result['spent']:,} LS | Còn {result['stones_left']:,} LS"
        await self._img(ctx, render_shop_buy_result(ok=True, title="Mua thành công", detail=detail))


async def setup_game(
    bot: commands.Bot,
    players: PlayerService,
    shop: ShopService,
    dokiep: DokiepService,
    tower: TowerService,
    inventory: InventoryService,
    items: ItemUseService,
    techniques: TechniqueService,
    stats: StatsService,
    pets: PetService,
    exploration: ExplorationService,
    gather: GatherService,
    alchemy: AlchemyService,
    economy: EconomyService,
    partners: PartnerService,
    leaderboard: LeaderboardService,
    auction: AuctionService,
    codes: CodeService,
    daily: DailyService,
    quests: QuestService,
    sects: SectService,
    world_events,
    pvp,
    missions,
    sect_tower,
) -> None:
    await bot.add_cog(
        GameCommands(
            bot, players, shop, dokiep, tower, inventory, items, techniques, stats,
            pets, exploration, gather, alchemy, economy, partners, leaderboard, auction, codes, daily, quests, sects,
            world_events, pvp, missions, sect_tower,
        )
    )
