"""Shop UI: image catalog + Discord buttons for interaction."""
from __future__ import annotations

import logging
from io import BytesIO

import discord

from ktt112026.game.services.shop_service import ShopService
from ktt112026.game.content.shop import CATEGORY_LABELS, SHOP, resolve_category
from ktt112026.game.render.cards import (
    render_shop_buy_result,
    render_shop_catalog,
    render_shop_menu,
)

logger = logging.getLogger("ktt.shop.view")

PAGE_SIZE = 6


def _png_file(png: bytes, name: str = "shop.png") -> discord.File:
    return discord.File(BytesIO(png), filename=name)


class ShopView(discord.ui.View):
    """Buttons under a shop image. Only the opener can press (ephemeral ownership)."""

    def __init__(
        self,
        *,
        shop: ShopService,
        owner_id: int,
        category: str | None = None,
        page: int = 0,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.shop = shop
        self.owner_id = owner_id
        self.category = category
        self.page = max(0, page)
        self._rebuild_children()

    def _rebuild_children(self) -> None:
        self.clear_items()
        # Category row
        for key, label in CATEGORY_LABELS.items():
            style = (
                discord.ButtonStyle.primary
                if self.category == key
                else discord.ButtonStyle.secondary
            )
            self.add_item(_CategoryButton(key, label, style, row=0))
        # Nav row when inside a category
        if self.category:
            items = self.shop.catalog(self.category, str(self.owner_id))
            pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
            self.page = min(self.page, pages - 1)
            self.add_item(_NavButton("prev", "◀ Trước", discord.ButtonStyle.secondary, disabled=self.page <= 0, row=1))
            self.add_item(_NavButton("home", "Menu", discord.ButtonStyle.secondary, row=1))
            self.add_item(
                _NavButton(
                    "next",
                    "Sau ▶",
                    discord.ButtonStyle.secondary,
                    disabled=self.page >= pages - 1,
                    row=1,
                )
            )

            start = self.page * PAGE_SIZE
            page_items = items[start : start + PAGE_SIZE]
            for it in page_items[:5]:
                self.add_item(_BuyButton(it["id"], it["name"][:16], int(it["price"])))

    def render_image(self) -> tuple[bytes, str]:
        if not self.category:
            return render_shop_menu(), "shop_menu.png"
        items = self.shop.catalog(self.category, str(self.owner_id))
        label = CATEGORY_LABELS.get(self.category, self.category)
        png = render_shop_catalog(
            category_label=label,
            items=items,
            page=self.page,
            page_size=PAGE_SIZE,
        )
        return png, f"shop_{self.category}.png"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Đây không phải cửa hàng của đạo hữu.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class _CategoryButton(discord.ui.Button["ShopView"]):
    def __init__(self, category: str, label: str, style: discord.ButtonStyle, row: int = 0) -> None:
        super().__init__(label=label, style=style, custom_id=f"shop:cat:{category}", row=row)
        self.category = category

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert isinstance(view, ShopView)
        view.category = self.category
        view.page = 0
        view._rebuild_children()
        png, name = view.render_image()
        await interaction.response.edit_message(attachments=[_png_file(png, name)], view=view)


class _NavButton(discord.ui.Button["ShopView"]):
    def __init__(
        self,
        action: str,
        label: str,
        style: discord.ButtonStyle,
        *,
        disabled: bool = False,
        row: int = 1,
    ) -> None:
        super().__init__(label=label, style=style, disabled=disabled, custom_id=f"shop:nav:{action}", row=row)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert isinstance(view, ShopView)
        if self.action == "home":
            view.category = None
            view.page = 0
        elif self.action == "prev":
            view.page = max(0, view.page - 1)
        elif self.action == "next":
            view.page += 1
        view._rebuild_children()
        png, name = view.render_image()
        await interaction.response.edit_message(attachments=[_png_file(png, name)], view=view)


class QuickBuyView(discord.ui.View):
    """Optional row of buy buttons for items on the current page."""

    def __init__(
        self,
        *,
        shop: ShopService,
        owner_id: int,
        items: list[dict],
        timeout: float = 120,
    ) -> None:
        super().__init__(timeout=timeout)
        self.shop = shop
        self.owner_id = owner_id
        for it in items[:5]:
            self.add_item(_BuyButton(it["id"], it["name"][:18], int(it["price"])))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Không phải giao dịch của đạo hữu.",
                ephemeral=True,
            )
            return False
        return True


class _BuyButton(discord.ui.Button["QuickBuyView"]):
    def __init__(self, item_id: str, label: str, price: int) -> None:
        super().__init__(
            label=f"{label} ({price})",
            style=discord.ButtonStyle.success,
            custom_id=f"shop:buy:{item_id}",
            row=2,
        )
        self.item_id = item_id

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert isinstance(view, QuickBuyView)
        try:
            result = view.shop.buy(str(interaction.user.id), self.item_id, 1)
        except ValueError as exc:
            png = render_shop_buy_result(ok=False, title="Không mua được", detail=str(exc))
            await interaction.response.send_message(file=_png_file(png, "mua_err.png"), ephemeral=True)
            return
        except Exception:
            logger.exception("quick buy failed")
            await interaction.response.send_message("Giao dịch thất bại.", ephemeral=True)
            return
        it = result["item"]
        detail = (
            f"{it['name']} x{result['qty']} | -{result['spent']:,} LS | "
            f"Còn {result['stones_left']:,} LS"
        )
        png = render_shop_buy_result(ok=True, title="Mua thành công", detail=detail)
        await interaction.response.send_message(file=_png_file(png, "mua_ok.png"), ephemeral=True)
