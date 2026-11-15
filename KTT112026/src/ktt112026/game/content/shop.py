"""System shop — built from JSON content data."""
from __future__ import annotations

from typing import Any

from ktt112026.game.content.loader import (
    catalog_by_id,
    load_congphap,
    load_danduoc,
    load_linhthu,
    load_phapbao,
    load_vukhi,
    shop_stats_line,
)

CATEGORY_LABELS = {
    "vukhi": "Vũ Khí",
    "phapbao": "Pháp Bảo",
    "danduoc": "Đan Dược",
    "congphap": "Công Pháp",
    "linhthu": "Linh Thú",
}

CATEGORY_ALIASES = {
    "vukhi": "vukhi", "vk": "vukhi", "weapon": "vukhi",
    "phapbao": "phapbao", "pb": "phapbao",
    "danduoc": "danduoc", "dan": "danduoc",
    "congphap": "congphap", "cp": "congphap",
    "linhthu": "linhthu", "pet": "linhthu", "thu": "linhthu",
}


def _to_shop_row(item: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "path": item.get("path", "any"),
        "major_min": int(item.get("major_min", 1)),
        "stage_min": int(item.get("stage_min", 0)),
        "price": int(item.get("price", 0)),
        "stats": shop_stats_line(item),
        "kind": kind,
        "raw": item,
    }


def _build_shop() -> dict[str, list[dict[str, Any]]]:
    return {
        "vukhi": [_to_shop_row(x, "vukhi") for x in load_vukhi()],
        "phapbao": [_to_shop_row(x, "phapbao") for x in load_phapbao()],
        "danduoc": [_to_shop_row(x, "danduoc") for x in load_danduoc()],
        "congphap": [_to_shop_row(x, "congphap") for x in load_congphap()],
        "linhthu": [_to_shop_row(x, "linhthu") for x in load_linhthu()],
    }


SHOP: dict[str, list[dict[str, Any]]] = _build_shop()
ITEM_INDEX: dict[str, dict[str, Any]] = catalog_by_id()


def resolve_category(raw: str | None) -> str | None:
    if not raw:
        return None
    return CATEGORY_ALIASES.get(raw.strip().lower())


def get_catalog(category: str) -> list[dict[str, Any]]:
    return list(SHOP.get(category, []))


def find_item(item_id: str) -> tuple[str, dict[str, Any]] | None:
    needle = item_id.strip().lower()
    for cat, items in SHOP.items():
        for it in items:
            if it["id"] == needle or it["name"].lower() == needle:
                return cat, it
    return None
