"""Shop Delta — ticket tự phân loại, đơn hàng, thông báo hoàn thành, +1 legit & bảo hành 48h."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .catalog import CATEGORIES, classify, emojis_for, label_of
from .fmt import (
    SELLER_ID_DEFAULT,
    WARRANTY_HOURS,
    build_done_notice,
    build_order_message,
    done_thanks_text,
    format_money,
    legit_template,
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

    def seller_id(self) -> int:
        return self.svc.get_int("seller_id", SELLER_ID_DEFAULT)

    async def _text_channel(self, guild: discord.Guild | None, channel_id: int) -> discord.TextChannel | None:
        """Lấy kênh chữ; không có trong cache thì fetch từ API (tránh 'không gửi được' do cache)."""
        ch = guild.get_channel(channel_id) if guild else None
        if ch is None and channel_id:
            try:
                ch = await self.bot.fetch_channel(channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        return ch if isinstance(ch, discord.TextChannel) else None

    @staticmethod
    def _why(exc: Exception) -> str:
        if isinstance(exc, discord.Forbidden):
            return "bot thiếu quyền (View Channel / Send Messages / Embed Links)"
        return f"lỗi Discord: {str(exc)[:120]}"

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Không để lệnh treo 'đang suy nghĩ' khi có lỗi bất ngờ."""
        logger.exception("Shop Delta command error", exc_info=error)
        msg = "⚠️ Có lỗi khi xử lý lệnh, vui lòng thử lại hoặc báo admin."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

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
        nguoi_ban="Người bán được tag trong mẫu +1 legit",
    )
    @app_commands.default_permissions(administrator=True)
    async def shopcfg(
        self,
        interaction: discord.Interaction,
        kenh_don_hang: discord.TextChannel | None = None,
        kenh_legit: discord.TextChannel | None = None,
        role_staff: discord.Role | None = None,
        nguoi_ban: discord.User | None = None,
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
        if nguoi_ban:
            self.svc.set_setting("seller_id", str(nguoi_ban.id))
        role_id = self.staff_role_id()
        await interaction.response.send_message(
            "**Cấu hình Shop Delta**\n"
            f"• Kênh đơn hàng: <#{self.order_channel_id()}>\n"
            f"• Kênh legit: <#{self.legit_channel_id()}>\n"
            f"• Role staff: {f'<@&{role_id}>' if role_id else 'chưa đặt (chỉ admin)'}\n"
            f"• Người bán (mẫu legit): <@{self.seller_id()}>",
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
        order_ch = await self._text_channel(interaction.guild, self.order_channel_id())
        if order_ch is None:
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
            product=product, status=status, product_emoji=emojis_for(product),
            created_ts=int(ticket["order_at"] or now),
        )
        msg = None
        if ticket["order_message_id"]:  # gọi lại /donhang = sửa đơn cũ, không gửi trùng
            try:
                old_ch = await self._text_channel(interaction.guild, int(ticket["order_channel_id"]))
                msg = await old_ch.fetch_message(int(ticket["order_message_id"]))  # type: ignore[union-attr]
                await msg.edit(content=text, allowed_mentions=NO_MENTIONS)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError, ValueError):
                msg = None
        if msg is None:
            try:
                msg = await order_ch.send(text, allowed_mentions=NO_MENTIONS)
            except (discord.Forbidden, discord.HTTPException) as exc:
                await interaction.followup.send(
                    f"❌ Không gửi được vào {order_ch.mention}: {self._why(exc)}", ephemeral=True)
                return
            self.svc.set_order(ticket["id"], amount=amount, product=product,
                               channel_id=order_ch.id, message_id=msg.id, now=now)
        else:
            self.svc.set_order(ticket["id"], amount=amount, product=product,
                               channel_id=msg.channel.id, message_id=msg.id, keep_time=True)
        await interaction.followup.send(
            f"✅ Đã gửi đơn **{format_money(amount)}** → {msg.jump_url}", ephemeral=True
        )

    @app_commands.command(name="done", description="Xác nhận đơn hoàn thành, cảm ơn khách và gửi mẫu legit")
    @app_commands.describe(ghi_chu="Lời nhắn thêm gửi khách (không bắt buộc)")
    async def done(self, interaction: discord.Interaction, ghi_chu: str | None = None) -> None:
        """Có thể gõ lại /done để gửi lại các thông báo bị lỗi lần trước (đơn không bị đánh dấu hai lần)."""
        if not await self._staff_only(interaction):
            return
        channel_id = interaction.channel_id or 0
        before = self.svc.get_by_channel(channel_id)
        try:
            ticket = self.svc.complete(channel_id, interaction.user.id, allow_repeat=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        repeat = bool(before and before["status"] == "done")
        await interaction.response.defer(ephemeral=True)
        report: list[str] = ["🔁 Gửi lại thông báo cho đơn đã hoàn thành" if repeat else "✅ Đã đánh dấu đơn hoàn thành"]

        guild = interaction.guild
        product = ticket["order_product"] or ticket["product_text"]
        thanks = done_thanks_text(
            code=ticket["code"], product=product, user_id=ticket["user_id"],
            seller_id=self.seller_id(), legit_channel_id=self.legit_channel_id(),
        )
        if ghi_chu:
            thanks += f"\n\n💬 {ghi_chu}"
        embed = discord.Embed(title="✅ Shop Delta - Đơn hàng hoàn thành", description=thanks, color=0x57F287)
        embed.timestamp = discord.utils.utcnow()
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Copy mẫu legit", emoji="📋", style=discord.ButtonStyle.secondary,
                                        custom_id=f"legit_tpl:{ticket['code']}"))

        # 1) trong ticket
        try:
            await interaction.channel.send(  # type: ignore[union-attr]
                content=f"<@{ticket['user_id']}>", embed=embed, view=view,
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            report.append("✅ Đã gửi thông báo trong ticket")
        except (discord.Forbidden, discord.HTTPException) as exc:
            report.append(f"❌ Không gửi được trong ticket: {self._why(exc)}")

        # 2) gửi riêng (DM)
        try:
            user = self.bot.get_user(int(ticket["user_id"])) or await self.bot.fetch_user(int(ticket["user_id"]))
            await user.send(embed=embed, view=view)
            report.append("✅ Đã gửi DM cho khách")
        except (discord.Forbidden, discord.HTTPException):
            report.append("⚠️ Không DM được (khách tắt tin nhắn riêng) — thông báo trong ticket vẫn có")

        # 3) ngoài ticket: cập nhật trạng thái đơn + gửi thông báo xong đơn vào kênh đơn hàng
        order_ch = await self._text_channel(guild, self.order_channel_id())
        if order_ch is None:
            report.append("❌ Không thấy kênh đơn hàng — dùng `/shopcfg kenh_don_hang` rồi `/done` lại")
        else:
            order_msg = None
            if ticket["order_message_id"]:
                try:
                    och = await self._text_channel(guild, int(ticket["order_channel_id"])) or order_ch
                    order_msg = await och.fetch_message(int(ticket["order_message_id"]))
                    await order_msg.edit(
                        content=build_order_message(
                            amount=ticket["amount"], channel_id=ticket["channel_id"], user_id=ticket["user_id"],
                            product=product, status="done", product_emoji=emojis_for(product),
                            created_ts=int(ticket["order_at"] or time.time()),
                        ),
                        allowed_mentions=NO_MENTIONS,
                    )
                    report.append("✅ Đã đổi trạng thái đơn: ⌛ Chờ → ✅ Hoàn thành")
                except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
                    order_msg = None
                    report.append("⚠️ Không sửa được tin nhắn đơn cũ (đã bị xoá?) — gửi thông báo mới")
            notice = build_done_notice(
                code=ticket["code"], channel_id=ticket["channel_id"], user_id=ticket["user_id"],
                product=product, amount=ticket["amount"], product_emoji=emojis_for(product),
            )
            try:
                if order_msg is not None:
                    try:
                        await order_msg.reply(notice, mention_author=False, allowed_mentions=NO_MENTIONS)
                    except discord.HTTPException:
                        await order_ch.send(notice, allowed_mentions=NO_MENTIONS)
                else:
                    await order_ch.send(notice, allowed_mentions=NO_MENTIONS)
                report.append(f"✅ Đã gửi thông báo xong đơn vào {order_ch.mention}")
            except (discord.Forbidden, discord.HTTPException) as exc:
                report.append(f"❌ Không gửi được vào {order_ch.mention}: {self._why(exc)}")
        await interaction.followup.send("\n".join(report), ephemeral=True)

    @app_commands.command(name="huydon", description="Huỷ đơn trong ticket này (đổi trạng thái đơn → ❌ Đã huỷ)")
    async def huydon(self, interaction: discord.Interaction) -> None:
        if not await self._staff_only(interaction):
            return
        ticket = self.svc.get_by_channel(interaction.channel_id or 0)
        if ticket is None or not ticket["order_message_id"]:
            await interaction.response.send_message("Ticket này chưa có đơn nào trong kênh đơn hàng.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            och = await self._text_channel(interaction.guild, int(ticket["order_channel_id"]))
            msg = await och.fetch_message(int(ticket["order_message_id"]))  # type: ignore[union-attr]
            await msg.edit(
                content=build_order_message(
                    amount=ticket["amount"], channel_id=ticket["channel_id"], user_id=ticket["user_id"],
                    product=ticket["order_product"] or ticket["product_text"], status="cancelled",
                    product_emoji=emojis_for(ticket["order_product"] or ticket["product_text"]),
                    created_ts=int(ticket["order_at"] or time.time()),
                ),
                allowed_mentions=NO_MENTIONS,
            )
            await interaction.followup.send("❌ Đã đổi trạng thái đơn → Đã huỷ.", ephemeral=True)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError, ValueError) as exc:
            await interaction.followup.send(f"Không sửa được tin nhắn đơn: {self._why(exc)}", ephemeral=True)

    @app_commands.command(name="legitbang", description="Gửi bảng hướng dẫn +1 legit (mẫu copy sẵn) vào kênh legit")
    @app_commands.describe(kenh="Kênh gửi bảng (mặc định: kênh legit)")
    async def legitbang(self, interaction: discord.Interaction, kenh: discord.TextChannel | None = None) -> None:
        if not await self._staff_only(interaction):
            return
        target = kenh or await self._text_channel(interaction.guild, self.legit_channel_id())
        if target is None:
            await interaction.response.send_message("Chưa có kênh legit — dùng `/shopcfg kenh_legit`.", ephemeral=True)
            return
        seller = self.seller_id()
        embed = discord.Embed(
            title="🛡️ BẢNG +1 LEGIT — NHẬN BẢO HÀNH 48H",
            description="Mua xong hãy **+1 legit** để được bảo hành. Bấm giữ vào khung bên dưới để **copy mẫu**.",
            color=0x57F287,
        )
        embed.add_field(name="📋 Mẫu (copy rồi thay mã)", value=f"```\n{legit_template(seller, '<mã sp>')}\n```", inline=False)
        embed.add_field(name="📌 Ví dụ", value=f"```\n{legit_template(seller, 'DL-0001')}\n```", inline=False)
        embed.add_field(
            name="📖 Cách làm",
            value=(
                "1️⃣ Khi đơn xong, bot gửi bạn **mã sản phẩm** dạng `DL-xxxx` (trong ticket và tin nhắn riêng)\n"
                "2️⃣ Copy mẫu ở trên, thay `<mã sp>` bằng mã của bạn\n"
                "3️⃣ Gửi tin nhắn vào **kênh này** — bot sẽ tự kiểm tra"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛡️ Bảo hành",
            value=f"**{WARRANTY_HOURS} giờ** tính từ lúc legit thành công • Mỗi đơn legit **1 lần** • Phải dùng đúng mã đơn của bạn",
            inline=False,
        )
        await interaction.response.defer(ephemeral=True)
        try:
            msg = await target.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException) as exc:
            await interaction.followup.send(f"❌ Không gửi được vào {target.mention}: {self._why(exc)}", ephemeral=True)
            return
        try:
            await msg.pin()
        except (discord.Forbidden, discord.HTTPException):
            pass
        await interaction.followup.send(f"✅ Đã gửi bảng legit vào {target.mention}", ephemeral=True)

    @app_commands.command(name="baohanh", description="Kiểm tra bảo hành của một đơn")
    @app_commands.describe(ma="Mã đơn, VD: DL-0001")
    async def baohanh(self, interaction: discord.Interaction, ma: str) -> None:
        try:
            r = self.svc.warranty_status(ma)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        t = r["ticket"]
        is_staff = isinstance(interaction.user, discord.Member) and self._is_staff(interaction.user)
        if not is_staff and t["user_id"] != str(interaction.user.id):
            await interaction.response.send_message("Mã đơn này không phải của bạn.", ephemeral=True)
            return
        text = {
            "chua_legit": f"Đơn `{t['code']}` chưa legit. Gửi `{legit_template(self.seller_id(), t['code'])}` ở <#{self.legit_channel_id()}> để nhận bảo hành {WARRANTY_HOURS}h."
            if t["status"] == "done" else f"Đơn `{t['code']}` chưa hoàn thành.",
            "con_han": f"🛡️ Đơn `{t['code']}` **còn bảo hành** đến <t:{int(t['warranty_until'])}:f> (<t:{int(t['warranty_until'])}:R>).",
            "het_han": f"⌛ Đơn `{t['code']}` **đã hết bảo hành** từ <t:{int(t['warranty_until'])}:f>.",
        }[r["state"]]
        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=NO_MENTIONS)

    @app_commands.command(name="thongke", description="Thống kê đơn hàng Shop Delta")
    async def thongke(self, interaction: discord.Interaction) -> None:
        if not await self._staff_only(interaction):
            return
        st = self.svc.stats()
        def line(label: str, pair: tuple[int, int]) -> str:
            return f"• {label}: **{pair[0]}** đơn · {format_money(pair[1]) if pair[1] else '0 VNĐ'}"
        await interaction.response.send_message(
            "**📊 Thống kê Shop Delta**\n"
            + line("24 giờ qua", st["day"]) + "\n" + line("7 ngày qua", st["week"]) + "\n"
            + line("Tổng", st["all"]) + "\n"
            f"• Ticket đang mở: **{st['open']}**\n• Tổng +1 legit: **{st['legit']}**",
            ephemeral=True,
        )

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

        if custom_id.startswith("legit_tpl:"):
            t = self.svc.get_by_code(custom_id.split(":", 1)[1])
            if t is None or t["user_id"] != str(interaction.user.id):
                await interaction.response.send_message("Mã đơn này không phải của bạn.", ephemeral=True)
                return
            await interaction.response.send_message(
                f"📋 Copy dòng dưới rồi gửi vào <#{self.legit_channel_id()}>:\n"
                f"```\n{legit_template(self.seller_id(), t['code'])}\n```",
                ephemeral=True,
            )
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
                    f"Gửi đúng mẫu: `{legit_template(self.seller_id(), '<mã sp>')}` (mã như `DL-0001`).",
                    mention_author=False, delete_after=20, allowed_mentions=NO_MENTIONS,
                )
            return
        tagged_id, code = parsed
        try:
            result = self.svc.legit(message.author.id, tagged_id, code, seller_ids=(self.seller_id(),))
        except ValueError as exc:
            await message.reply(f"❌ {exc}", mention_author=False, delete_after=30, allowed_mentions=NO_MENTIONS)
            return
        t = result["ticket"]
        embed = discord.Embed(
            title="✅ Đã ghi nhận +1 legit",
            description=(
                f"Cảm ơn {message.author.mention} đã legit cho <@{tagged_id}>!\n\n"
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
