"""Shop Delta ticket system — panels, tickets, payments, price list."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from ktt112026.bot import KTTBot

logger = logging.getLogger("ktt.shop_delta")

# ==================== CẤU HÌNH SHOP DELTA ====================
STAFF_ROLE_ID = 0  # Thay bằng ID role staff
PANEL_CHANNEL_ID = 1575508677174231150
FEEDBACK_CHANNEL_ID = 1575508889791635477
ORDER_LOG_CHANNEL_ID = 1575508815946977342
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
            "• Không tính nhiệm vụ định mệnh\n"
            "• Không tính hợp đồng sưu tập\n"
            "• Nhiệm vụ định mệnh: **30.000₫**\n\n"
            f"Tạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng."
        ),
    },
    "xu_delta": {
        "label": "Cày xu Delta",
        "emoji": {"id": 1575531834647773204, "name": "emoji_76"},
        "title": "<:emoji_76:1575531834647773204> Cày xu Delta",
        "description": f"**Giá:** 2.000₫ / 1M xu\n\nTạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng.",
    },
    "harmonica": {
        "label": "Cày Kèn Harmonica",
        "emoji": {"id": 1575531792226844855, "name": "emoji_75"},
        "title": "<:emoji_75:1575531792226844855> Cày Kèn Harmonica",
        "description": f"**Giá:** 20.000₫\n\nTạo ticket ở <#{PANEL_CHANNEL_ID}> để mua hàng.",
    },
}


class ShopDeltaCog(commands.Cog):
    def __init__(self, bot: KTTBot) -> None:
        self.bot = bot

    def _is_staff(self, member: discord.Member) -> bool:
        if STAFF_ROLE_ID == 0:
            return member.guild_permissions.administrator
        return any(r.id == STAFF_ROLE_ID for r in member.roles)

    # ---------- Slash Commands ----------
    @app_commands.command(name="banggia", description="Gửi bảng giá Shop Delta")
    async def banggia(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff được dùng lệnh này.", ephemeral=True)
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
                label=data["label"],
                value=key,
                emoji=discord.PartialEmoji.from_dict(data["emoji"]),
            )
            for key, data in PRICE_LIST.items()
        ]
        select = discord.ui.Select(placeholder="Chọn sản phẩm", options=options, custom_id="select_product")
        view = discord.ui.View()
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="panel", description="Gửi panel tạo ticket Shop Delta")
    async def panel(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff được dùng lệnh này.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛒 Shop Delta - Ticket System",
            description=(
                "**❓ Hướng Dẫn Khi Mua Hàng:**\n"
                "• Bấm 1 trong 2 nút bên dưới theo nhu cầu của bạn\n"
                "• Lựa chọn sản phẩm trong kênh **BẢNG GIÁ**\n"
                "• Đọc kĩ **CHÍNH SÁCH** trước khi mua\n"
                "• Sau khi hoàn thành nhớ **LEGIT** cho shop\n\n"
                "**❗ Một Vài Lưu Ý:**\n"
                "• Không **SPAM** tạo ticket\n"
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
        if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff được dùng lệnh này.", ephemeral=True)
            return

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="BANK", emoji="🏦", style=discord.ButtonStyle.success, custom_id="pay_bank"))
        view.add_item(discord.ui.Button(label="THẺ CÀO", emoji="💳", style=discord.ButtonStyle.primary, custom_id="pay_card"))

        await interaction.response.send_message("**Chọn phương thức thanh toán:**", view=view)

    @app_commands.command(name="done", description="Xác nhận đơn hàng hoàn thành")
    @app_commands.describe(note="Ghi chú đơn hàng")
    async def done(self, interaction: discord.Interaction, note: str = "Đã hoàn thành") -> None:
        if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff được dùng lệnh này.", ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Shop Delta - Đơn hàng hoàn thành",
            description=note,
            color=0x57F287,
        )
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)
        await interaction.followup.send(f"Vui lòng vào <#{FEEDBACK_CHANNEL_ID}> và gõ lệnh để nhận bảo hành!")

        # Log channel
        if interaction.guild:
            log_ch = interaction.guild.get_channel(ORDER_LOG_CHANNEL_ID)
            if log_ch and isinstance(log_ch, discord.TextChannel):
                await log_ch.send(content=f"Đơn của {interaction.channel} đã hoàn thành.", embed=embed)

        # DM user (simple: first non-staff in channel overwrites is hard; skip for now or improve later)
        await interaction.followup.send("Đã gửi thông báo hoàn thành.", ephemeral=True)

    # ---------- Interactions ----------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id") if interaction.data else None
        if not custom_id:
            return

        # Select product
        if custom_id == "select_product" and interaction.data and "values" in interaction.data:
            value = interaction.data["values"][0]
            data = PRICE_LIST.get(value)
            if not data:
                await interaction.response.send_message("Sản phẩm không tồn tại.", ephemeral=True)
                return
            embed = discord.Embed(title=data["title"], description=data["description"], color=0x5865F2)
            embed.set_footer(text="Shop Delta • Bảng giá có thể thay đổi")
            embed.timestamp = discord.utils.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Open ticket buttons
        if custom_id in ("btn_mua_hang", "btn_ho_tro"):
            is_buy = custom_id == "btn_mua_hang"
            modal = discord.ui.Modal(title="Tạo Đơn Hàng" if is_buy else "Hỗ Trợ")
            modal.add_item(discord.ui.TextInput(label="Sản phẩm / Vấn đề", custom_id="product", required=True))
            modal.add_item(discord.ui.TextInput(label="Chi tiết", custom_id="detail", style=discord.TextStyle.paragraph, required=True))

            async def on_submit(inter: discord.Interaction) -> None:
                product = inter.data["components"][0]["components"][0]["value"]  # type: ignore
                detail = inter.data["components"][1]["components"][0]["value"]  # type: ignore
                await self._create_ticket(inter, product, detail, is_buy)

            modal.on_submit = on_submit  # type: ignore
            await interaction.response.send_modal(modal)
            return

        # Payment buttons
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
            modal = discord.ui.Modal(title="Nhập thông tin thẻ cào")
            modal.add_item(discord.ui.TextInput(label="Mã thẻ", custom_id="card_code", required=True))
            modal.add_item(discord.ui.TextInput(label="Số seri", custom_id="card_serial", required=True))
            modal.add_item(discord.ui.TextInput(label="Loại thẻ (Viettel/Mobi/Vina/Zing...)", custom_id="card_type", required=True))

            async def on_submit_card(inter: discord.Interaction) -> None:
                code = inter.data["components"][0]["components"][0]["value"]  # type: ignore
                serial = inter.data["components"][1]["components"][0]["value"]  # type: ignore
                ctype = inter.data["components"][2]["components"][0]["value"]  # type: ignore
                embed = discord.Embed(title="💳 Thông tin thẻ cào", color=0xFFA500)
                embed.add_field(name="Loại thẻ", value=ctype, inline=True)
                embed.add_field(name="Mã thẻ", value=f"`{code}`", inline=True)
                embed.add_field(name="Số seri", value=f"`{serial}`", inline=True)
                embed.set_footer(text=f"Gửi bởi {inter.user}")
                embed.timestamp = discord.utils.utcnow()
                content = f"<@&{STAFF_ROLE_ID}> Kiểm tra thẻ cào:" if STAFF_ROLE_ID else "Staff kiểm tra thẻ cào:"
                await inter.channel.send(content=content, embed=embed)  # type: ignore
                await inter.response.send_message("Đã gửi thông tin thẻ. Vui lòng chờ staff kiểm tra.", ephemeral=True)

            modal.on_submit = on_submit_card  # type: ignore
            await interaction.response.send_modal(modal)
            return

        # Close ticket
        if custom_id == "close_ticket":
            if not isinstance(interaction.user, discord.Member) or not self._is_staff(interaction.user):
                await interaction.response.send_message("Chỉ staff được đóng ticket.", ephemeral=True)
                return
            await interaction.response.send_message("Ticket sẽ đóng sau 5 giây...")
            await interaction.channel.delete(delay=5)  # type: ignore

    async def _create_ticket(self, interaction: discord.Interaction, product: str, detail: str, is_buy: bool) -> None:
        if not interaction.guild:
            return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        }
        if STAFF_ROLE_ID:
            role = interaction.guild.get_role(STAFF_ROLE_ID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, attach_files=True, read_message_history=True, manage_messages=True
                )

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
        )

        await channel.send(
            f"⚠️ **Thông báo:** Hiện không có staff online, vui lòng chờ staff online sẽ hỗ trợ bạn sớm nhất!\n\n"
            f"{interaction.user.mention}"
        )

        embed = discord.Embed(
            title="🛒 Shop Delta - Đơn hàng" if is_buy else "💬 Shop Delta - Hỗ trợ",
            color=0x00AE86,
        )
        embed.add_field(name="Sản phẩm / Vấn đề", value=product, inline=False)
        embed.add_field(name="Chi tiết", value=detail, inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Đóng Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket"))
        await channel.send(content="**Staff thao tác bên dưới:**", view=view)

        await interaction.response.send_message(f"Ticket đã tạo: {channel.mention}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShopDeltaCog(bot))  # type: ignore
