"""Shop Delta — ticket tự phân loại, đơn hàng, thông báo hoàn thành, +1 legit & bảo hành 48h."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .catalog import CATEGORIES, classify, label_of
from .fmt import (
    WARRANTY_HOURS,
    build_order_message,
    done_thanks_text,
    format_money,
    parse_legit,
    parse_money,
)
from .service import ShopTicketService

if TYPE_CHECKING:
    from ktt112026.bot import KTTBot

logger = logging.getLogger("ktt.shop_delta")

# ==================== CẤU HÌNH SHOP DELTA ====================
STAFF_ROLE_ID = 0  # Mặc định; nên đặt bằng /shopcfg role_staff
PANEL_CHANNEL_ID = 1575508677174231150
FEEDBACK_CHANNEL_ID = 1575508889791635477  # kênh +1 legit (đổi bằng /shopcfg kenh_legit)
ORDER_LOG_CHANNEL_ID = 1575508815946977342  # kênh thông báo ĐƠN HÀNG (đổi bằng /shopcfg kenh_don_hang)
BANK_IMAGE_URL = "https://i.ibb.co/zyyRVys/Messenger-creation-08-C6-DDB2-1-AF1-463-A-BE2-F-B8-B2-F7-B9-DC0-C.jpg"
# ============================================================

PRICE_LIST = {
    "cay_rank": {
        "label": "Cày Rank",
        "emoji": {"id": 1575531934593982535, "name": "emoji_78"},
        "title": "<:emoji_78:1575531934593982535> Cày Rank",
        "description": (
            "**Bảng giá cày rank:**\n\n"
            "• Từ Đồng <:emoji_78:1575531934593982535> → KC <:emoji_79:1575532052126629938>: **5.000₫**\n"
            "• KC <:emoji_79:1575532052126629938> → Cao thủ <:emoji_80:1575532121995477012>: **15.000₫**\n"
            "• Cao thủ <:emoji_80:1575532121995477012> → Thách đấu <:emoji_81:1575532198965158101>: **20.000₫**\n\n"
            f"Tạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng."
        ),
    },
    "ket_mua": {
        "label": "Két mùa 3x3",
        "emoji": {"id": 1575531871180431370, "name": "emoji_77"},
        "title": "<:emoji_77:1575531871180431370> Két mùa 3x3",
        "description": (
            "**Giá:** 150.000₫\n\n"
            "• Không tính nhiệm vụ định mệnh/sưu tập\n"
            "• Nhiệm vụ định mệnh: **30.000₫**\n"
            "• Nhiệm vụ nhà sưu tập: **15.000₫**\n\n"
            f"Tạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng."
        ),
    },
    "xu_delta": {
        "label": "Cày xu Delta",
        "emoji": {"id": 1575531834647773204, "name": "emoji_76"},
        "title": "<:emoji_76:1575531834647773204> Cày xu Delta",
        "description": f"**Giá:** 2.000₫ / 1M xu\n\nTạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng.",
    },
    # Giữ key "harmonica" để panel đã gửi trước đó trong Discord vẫn chọn được.
    "harmonica": {
        "label": "Item Layali (các vật phẩm)",
        "emoji": {"id": 1575531792226844855, "name": "emoji_75"},
        "title": "<:emoji_75:1575531792226844855> Item Layali (các vật phẩm)",
        "description": (
            "**Bảng giá Item Layali:**\n\n"
            "• Kèn Harmonica: **20.000₫**\n"
            "• Tên lửa: **40.000₫**\n"
            "• Cả 2 món đồ: **50.000₫**\n\n"
            f"Tạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng."
        ),
    },
}


NO_STAFF_NOTICE = (
    "⚠️ **Thông báo:** Hiện không có staff online, vui lòng chờ staff online sẽ hỗ trợ bạn sớm nhất"
)
NO_MENTIONS = discord.AllowedMentions.none()


class TicketModal(discord.ui.Modal):
    """Bước 1: khách nhập sản phẩm cần mua → bot tự phân loại theo từ khoá."""

    def __init__(self, cog: "ShopDeltaCog", kind: str) -> None:
        super().__init__(title="Tạo đơn hàng" if kind == "buy" else "Hỗ trợ", timeout=600)
        self.cog = cog
        self.kind = kind
        self.product = discord.ui.TextInput(
            label="Sản phẩm cần mua" if kind == "buy" else "Vấn đề cần hỗ trợ",
            placeholder="VD: két mùa 3x3, kèn harmonica, cày rank đồng → KC..." if kind == "buy" else "Mô tả ngắn",
            max_length=200,
            required=True,
        )
        self.detail = discord.ui.TextInput(
            label="Ghi chú thêm (không bắt buộc)",
            style=discord.TextStyle.paragraph,
            max_length=800,
            required=False,
        )
        self.add_item(self.product)
        self.add_item(self.detail)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.create_ticket(interaction, self.kind, self.product.value, self.detail.value)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.exception("Ticket modal error", exc_info=error)
        msg = "Có lỗi khi tạo ticket, vui lòng thử lại hoặc nhắn staff."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


class CardModal(discord.ui.Modal):
    def __init__(self, cog: "ShopDeltaCog") -> None:
        super().__init__(title="Nhập thông tin thẻ cào", timeout=600)
        self.cog = cog
        self.code = discord.ui.TextInput(label="Mã thẻ", required=True)
        self.serial = discord.ui.TextInput(label="Số seri", required=True)
        self.ctype = discord.ui.TextInput(label="Loại thẻ (Viettel/Mobi/Vina/Zing...)", required=True)
        for item in (self.code, self.serial, self.ctype):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="💳 Thông tin thẻ cào", color=0xFFA500)
        embed.add_field(name="Loại thẻ", value=self.ctype.value, inline=True)
        embed.add_field(name="Mã thẻ", value=f"`{self.code.value}`", inline=True)
        embed.add_field(name="Số seri", value=f"`{self.serial.value}`", inline=True)
        embed.set_footer(text=f"Gửi bởi {interaction.user}")
        embed.timestamp = discord.utils.utcnow()
        role_id = self.cog.staff_role_id()
        content = f"<@&{role_id}> Kiểm tra thẻ cào:" if role_id else "Staff kiểm tra thẻ cào:"
        await interaction.channel.send(content=content, embed=embed)  # type: ignore[union-attr]
        await interaction.response.send_message("Đã gửi thông tin thẻ. Vui lòng chờ staff kiểm tra.", ephemeral=True)


class ShopDeltaCog(commands.Cog):
    def __init__(self, bot: KTTBot) -> None:
        self.bot = bot
        self.svc = ShopTicketService(bot.db)

    # ---------- cấu hình / quyền ----------
    def staff_role_id(self) -> int:
        return self.svc.get_int("staff_role", STAFF_ROLE_ID)

    def order_channel_id(self) -> int:
        return self.svc.get_int("order_channel", ORDER_LOG_CHANNEL_ID)

    def legit_channel_id(self) -> int:
        return self.svc.get_int("legit_channel", FEEDBACK_CHANNEL_ID)

    def _is_staff(self, member: discord.Member) -> bool:
        role_id = self.staff_role_id()
        if role_id == 0:
            return member.guild_permissions.administrator
        return member.guild_permissions.administrator or any(r.id == role_id for r in member.roles)

    async def _staff_only(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff được dùng lệnh này.", ephemeral=True)
            return False
        return True

    # ---------- Slash commands ----------
    @app_commands.command(name="banggia", description="Gửi bảng giá Shop Delta")
    async def banggia(self, interaction: discord.Interaction) -> None:
        if not await self._staff_only(interaction):
            return
        embed = discord.Embed(
            title="BẢNG GIÁ SHOP DELTA",
            description=(
                "🛒 **Nhấn menu bên dưới theo nhu cầu của bạn**\n\n"
                "🔴 **Chú Ý:**\n"
                "• Card thì shop thu thêm 15%-20% vì chiết khấu\n\n"
                "✨ Cảm ơn bạn đã quan tâm đến sản phẩm của Shop Delta\n"
                f"Nếu muốn mua hàng hãy tạo ticket ở kênh <#{PANEL_CHANNEL_ID}>\n\n"
                "🔴 **Lưu ý:** Bảng giá không cố định, có thể thay đổi theo thời gian."
            ),
            color=0x2B2D31,
        )
        options = [
            discord.SelectOption(
                label=data["label"], value=key, emoji=discord.PartialEmoji.from_dict(data["emoji"])
            )
            for key, data in PRICE_LIST.items()
        ]
        select = discord.ui.Select(placeholder="Chọn sản phẩm", options=options, custom_id="select_product")
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="panel", description="Gửi panel tạo ticket Shop Delta")
    async def panel(self, interaction: discord.Interaction) -> None:
        if not await self._staff_only(interaction):
            return
        embed = discord.Embed(
            title="🛒 Shop Delta - Ticket System",
            description=(
                "**❓ Hướng Dẫn Khi Mua Hàng:**\n"
                "• Bấm **MUA HÀNG** và nhập sản phẩm cần mua — bot sẽ tự tạo ticket đúng danh mục\n"
                "• Xem giá trong kênh **BẢNG GIÁ**\n"
                "• Đọc kĩ **CHÍNH SÁCH** trước khi mua\n"
                "• Sau khi hoàn thành nhớ **LEGIT** để nhận bảo hành\n\n"
                "**❗ Một Vài Lưu Ý:**\n"
                "• Không **SPAM** tạo ticket (mỗi người 1 ticket đang mở)\n"
                "• Không tạo ticket khi chưa có nhu cầu"
            ),
            color=0x2B2D31,
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="MUA HÀNG", emoji="🛒", style=discord.ButtonStyle.primary, custom_id="btn_mua_hang"))
        view.add_item(discord.ui.Button(label="HỖ TRỢ", emoji="👩‍💻", style=discord.ButtonStyle.secondary, custom_id="btn_ho_tro"))
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="pay", description="Hiện nút thanh toán trong ticket")
    async def pay(self, interaction: discord.Interaction) -> None:
        if not await self._staff_only(interaction):
            return
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="BANK", emoji="🏦", style=discord.ButtonStyle.success, custom_id="pay_bank"))
        view.add_item(discord.ui.Button(label="THẺ CÀO", emoji="💳", style=discord.ButtonStyle.primary, custom_id="pay_card"))
        await interaction.response.send_message("**Chọn phương thức thanh toán:**", view=view)

    @app_commands.command(name="shopcfg", description="Cấu hình kênh/role Shop Delta (admin)")
    @app_commands.describe(
        kenh_don_hang="Kênh nhận thông báo ĐƠN HÀNG",
        kenh_legit="Kênh khách gõ +1 legit",
        role_staff="Role staff",
    )
    @app_commands.default_permissions(administrator=True)
    async def shopcfg(
        self,
        interaction: discord.Interaction,
        kenh_don_hang: discord.TextChannel | None = None,
        kenh_legit: discord.TextChannel | None = None,
        role_staff: discord.Role | None = None,
    ) -> None:
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Chỉ admin được cấu hình.", ephemeral=True)
            return
        if kenh_don_hang:
            self.svc.set_setting("order_channel", str(kenh_don_hang.id))
        if kenh_legit:
            self.svc.set_setting("legit_channel", str(kenh_legit.id))
        if role_staff:
            self.svc.set_setting("staff_role", str(role_staff.id))
        role_id = self.staff_role_id()
        await interaction.response.send_message(
            "**Cấu hình Shop Delta**\n"
            f"• Kênh đơn hàng: <#{self.order_channel_id()}>\n"
            f"• Kênh legit: <#{self.legit_channel_id()}>\n"
            f"• Role staff: {f'<@&{role_id}>' if role_id else 'chưa đặt (chỉ admin)'}",
            ephemeral=True,
            allowed_mentions=NO_MENTIONS,
        )

    @app_commands.command(name="donhang", description="Gửi thông báo ĐƠN HÀNG vào kênh đơn hàng")
    @app_commands.describe(
        so_tien="Số tiền, VD: 25k, 25000, 150.000",
        san_pham="Nội dung sản phẩm (mặc định lấy từ ticket)",
    )
    async def donhang(self, interaction: discord.Interaction, so_tien: str, san_pham: str | None = None) -> None:
        if not await self._staff_only(interaction):
            return
        ticket = self.svc.get_by_channel(interaction.channel_id or 0)
        if ticket is None:
            await interaction.response.send_message("Hãy dùng lệnh này trong kênh ticket.", ephemeral=True)
            return
        try:
            amount = parse_money(so_tien)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        if amount <= 0:
            await interaction.response.send_message("Số tiền phải lớn hơn 0.", ephemeral=True)
            return
        order_ch = interaction.guild.get_channel(self.order_channel_id()) if interaction.guild else None
        if not isinstance(order_ch, discord.TextChannel):
            await interaction.response.send_message(
                "Chưa có kênh đơn hàng hợp lệ — dùng `/shopcfg kenh_don_hang`.", ephemeral=True
            )
            return
        product = (san_pham or ticket["product_text"]).strip()
        await interaction.response.defer(ephemeral=True)
        status = "done" if ticket["status"] == "done" else "pending"
        now = int(time.time())
        text = build_order_message(
            amount=amount, channel_id=ticket["channel_id"], user_id=ticket["user_id"],
            product=product, status=status, created_ts=int(ticket["order_at"] or now),
        )
        msg = None
        if ticket["order_message_id"]:  # gọi lại /donhang = sửa đơn cũ, không gửi trùng
            try:
                old_ch = interaction.guild.get_channel(int(ticket["order_channel_id"]))  # type: ignore[union-attr]
                msg = await old_ch.fetch_message(int(ticket["order_message_id"]))  # type: ignore[union-attr]
                await msg.edit(content=text, allowed_mentions=NO_MENTIONS)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError, ValueError):
                msg = None
        if msg is None:
            msg = await order_ch.send(text, allowed_mentions=NO_MENTIONS)
            self.svc.set_order(ticket["id"], amount=amount, product=product,
                               channel_id=order_ch.id, message_id=msg.id, now=now)
        else:
            self.svc.set_order(ticket["id"], amount=amount, product=product,
                               channel_id=msg.channel.id, message_id=msg.id, keep_time=True)
        await interaction.followup.send(
            f"✅ Đã gửi đơn **{format_money(amount)}** → {msg.jump_url}", ephemeral=True
        )

    @app_commands.command(name="done", description="Xác nhận đơn hoàn thành, cảm ơn khách và hướng dẫn legit")
    @app_commands.describe(ghi_chu="Lời nhắn thêm gửi khách (không bắt buộc)")
    async def done(self, interaction: discord.Interaction, ghi_chu: str | None = None) -> None:
        if not await self._staff_only(interaction):
            return
        try:
            ticket = self.svc.complete(interaction.channel_id or 0, interaction.user.id)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        product = ticket["order_product"] or ticket["product_text"]
        thanks = done_thanks_text(
            code=ticket["code"], product=product, user_id=ticket["user_id"],
            staff_id=interaction.user.id, legit_channel_id=self.legit_channel_id(),
        )
        if ghi_chu:
            thanks += f"\n\n💬 {ghi_chu}"
        embed = discord.Embed(title="✅ Shop Delta - Đơn hàng hoàn thành", description=thanks, color=0x57F287)
        embed.timestamp = discord.utils.utcnow()

        # 1) thông báo trong ticket
        await interaction.channel.send(  # type: ignore[union-attr]
            content=f"<@{ticket['user_id']}>", embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        # 2) gửi riêng (DM) cho khách
        dm_ok = True
        try:
            user = self.bot.get_user(int(ticket["user_id"])) or await self.bot.fetch_user(int(ticket["user_id"]))
            await user.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            dm_ok = False
        # 3) cập nhật trạng thái đơn trong kênh đơn hàng: Chờ → Hoàn thành
        order_updated = False
        if ticket["order_message_id"] and interaction.guild:
            try:
                ch = interaction.guild.get_channel(int(ticket["order_channel_id"]))
                msg = await ch.fetch_message(int(ticket["order_message_id"]))  # type: ignore[union-attr]
                await msg.edit(
                    content=build_order_message(
                        amount=ticket["amount"], channel_id=ticket["channel_id"], user_id=ticket["user_id"],
                        product=product, status="done", created_ts=int(ticket["order_at"] or time.time()),
                    ),
                    allowed_mentions=NO_MENTIONS,
                )
                order_updated = True
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError, ValueError):
                pass
        notes = [
            "✅ Đã gửi thông báo trong ticket",
            "✅ Đã gửi DM cho khách" if dm_ok else "⚠️ Không DM được (khách tắt tin nhắn riêng)",
            "✅ Đã cập nhật trạng thái đơn" if order_updated else "ℹ️ Chưa có đơn trong kênh đơn hàng (dùng `/donhang`)",
        ]
        await interaction.followup.send("\n".join(notes), ephemeral=True)

    # ---------- Tạo ticket ----------
    async def _ensure_category(self, guild: discord.Guild, name: str) -> discord.CategoryChannel | None:
        for cat in guild.categories:
            if cat.name == name:
                return cat
        overwrites: dict = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        role = guild.get_role(self.staff_role_id()) if self.staff_role_id() else None
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True)
        try:
            return await guild.create_category(name, overwrites=overwrites)
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Không tạo được danh mục %s", name)
            return None

    async def create_ticket(self, interaction: discord.Interaction, kind: str, product_text: str, detail: str) -> None:
        guild = interaction.guild
        if guild is None:
            return
        await interaction.response.defer(ephemeral=True)
        # Chặn spam: mỗi người một ticket đang mở
        for old in self.svc.open_tickets(interaction.user.id):
            ch = guild.get_channel(int(old["channel_id"]))
            if ch is not None:
                await interaction.followup.send(f"Bạn đang có ticket chưa đóng: {ch.mention}", ephemeral=True)
                return
            self.svc.mark_closed(old["id"])  # kênh đã bị xoá tay

        cats = ["hotro"] if kind == "support" else classify(product_text)
        primary = cats[0]
        reserved = self.svc.reserve_ticket(
            guild_id=guild.id, user_id=interaction.user.id, kind=kind,
            categories=cats, product_text=product_text.strip(), detail=(detail or "").strip(),
        )
        try:
            channel = await self._make_channel(guild, interaction.user, primary, reserved["id"], reserved["code"], product_text)
        except (discord.Forbidden, discord.HTTPException) as exc:
            self.svc.discard(reserved["id"])
            logger.exception("Không tạo được kênh ticket", exc_info=exc)
            await interaction.followup.send(
                "Bot thiếu quyền **Manage Channels** hoặc server đã đầy kênh — hãy báo staff.", ephemeral=True
            )
            return
        self.svc.attach_channel(reserved["id"], channel.id)

        # Bước 3: thông báo tự động đầu ticket
        await channel.send(f"{NO_STAFF_NOTICE}\n\n{interaction.user.mention}",
                           allowed_mentions=discord.AllowedMentions(users=True))
        embed = discord.Embed(
            title="🛒 Shop Delta - Đơn hàng" if kind == "buy" else "💬 Shop Delta - Hỗ trợ",
            color=0x00AE86,
        )
        embed.add_field(name="Mã đơn", value=f"`{reserved['code']}`", inline=True)
        embed.add_field(name="Danh mục", value=", ".join(label_of(k) for k in cats), inline=True)
        embed.add_field(name="Sản phẩm / Vấn đề", value=product_text.strip()[:1000], inline=False)
        if detail and detail.strip():
            embed.add_field(name="Ghi chú", value=detail.strip()[:1000], inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Đóng Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket"))
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(f"Ticket đã tạo: {channel.mention}", ephemeral=True)

    async def _make_channel(self, guild: discord.Guild, user: discord.abc.User, primary: str,
                            tid: int, code: str, product_text: str) -> discord.TextChannel:
        cat_cfg = CATEGORIES.get(primary, CATEGORIES["khac"])
        overwrites: dict = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        }
        if guild.me is not None:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True, manage_messages=True, embed_links=True
            )
        role = guild.get_role(self.staff_role_id()) if self.staff_role_id() else None
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, attach_files=True, read_message_history=True, manage_messages=True
            )
        category = await self._ensure_category(guild, cat_cfg["discord_category"])
        name = f"{cat_cfg['slug']}-{tid:04d}"
        topic = f"{code} | user {user.id} | {product_text.strip()[:80]}"
        try:
            return await guild.create_text_channel(name=name, category=category, overwrites=overwrites, topic=topic)
        except discord.HTTPException:
            if category is None:
                raise
            # danh mục đầy (50 kênh) → tạo ở ngoài danh mục
            return await guild.create_text_channel(name=name, overwrites=overwrites, topic=topic)

    # ---------- Interactions (nút / menu) ----------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id") if interaction.data else None
        if not custom_id:
            return

        if custom_id == "select_product" and interaction.data and "values" in interaction.data:
            data = PRICE_LIST.get(interaction.data["values"][0])
            if not data:
                await interaction.response.send_message("Sản phẩm không tồn tại.", ephemeral=True)
                return
            embed = discord.Embed(title=data["title"], description=data["description"], color=0x5865F2)
            embed.set_footer(text="Shop Delta • Bảng giá có thể thay đổi")
            embed.timestamp = discord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if custom_id in ("btn_mua_hang", "btn_ho_tro"):
            await interaction.response.send_modal(TicketModal(self, "buy" if custom_id == "btn_mua_hang" else "support"))
            return

        if custom_id == "pay_bank":
            embed = discord.Embed(
                title="🏦 Thanh toán BANK",
                description="Vui lòng chuyển khoản theo thông tin bên dưới và gửi bill vào ticket.",
                color=0x00AE86,
            )
            embed.set_image(url=BANK_IMAGE_URL)
            embed.set_footer(text="Shop Delta")
            await interaction.response.send_message(embed=embed)
            return

        if custom_id == "pay_card":
            await interaction.response.send_modal(CardModal(self))
            return

        if custom_id == "close_ticket":
            if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
                await interaction.response.send_message("Chỉ staff được đóng ticket.", ephemeral=True)
                return
            ticket = self.svc.get_by_channel(interaction.channel_id or 0)
            if ticket:
                self.svc.mark_closed(ticket["id"])  # đơn đã 'done' giữ nguyên để còn check legit
            await interaction.response.send_message("Ticket sẽ đóng sau 5 giây...")
            await interaction.channel.delete(delay=5)  # type: ignore[union-attr]

    # ---------- +1 legit ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if message.channel.id != self.legit_channel_id():
            return
        text = message.content or ""
        parsed = parse_legit(text)
        if parsed is None:
            if text.strip().lower().startswith("+1"):
                await message.reply(
                    "Cú pháp: `+1 legit @người_bán <mã_đơn>` (mã đơn như `DL-0001`).",
                    mention_author=False, delete_after=20, allowed_mentions=NO_MENTIONS,
                )
            return
        staff_id, code = parsed
        try:
            result = self.svc.legit(message.author.id, staff_id, code)
        except ValueError as exc:
            await message.reply(f"❌ {exc}", mention_author=False, delete_after=30, allowed_mentions=NO_MENTIONS)
            return
        t = result["ticket"]
        embed = discord.Embed(
            title="✅ Đã ghi nhận +1 legit",
            description=(
                f"Cảm ơn {message.author.mention} đã legit cho <@{staff_id}>!\n\n"
                f"🛡️ Đơn **`{t['code']}`** được **bảo hành {WARRANTY_HOURS} giờ** "
                f"(đến <t:{int(result['warranty_until'])}:f>)."
            ),
            color=0x57F287,
        )
        embed.set_footer(text=f"Tổng legit của shop: {result['count']}")
        embed.timestamp = discord.utils.utcnow()
        try:
            await message.add_reaction("✅")
        except discord.HTTPException:
            pass
        await message.reply(embed=embed, mention_author=False, allowed_mentions=NO_MENTIONS)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShopDeltaCog(bot))  # type: ignore
