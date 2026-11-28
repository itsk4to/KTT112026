"""Danh mục sản phẩm Shop Delta + từ khoá để bot tự phân loại ticket."""
from __future__ import annotations

import re
import unicodedata

# key -> tên hiển thị, tên danh mục Discord, từ khoá (viết không dấu, thường)
CATEGORIES: dict[str, dict] = {
    "ket": {
        "label": "Két mùa 3x3",
        "discord_category": "🧰┃Két mùa 3x3",
        "slug": "ket",
        "keywords": ["ket", "ket mua", "ket 3x3", "3x3", "safe", "ket sat"],
    },
    "nhiemvu": {
        "label": "Nhiệm vụ định mệnh / sưu tập",
        "discord_category": "📜┃Nhiệm vụ",
        "slug": "nhiemvu",
        "keywords": [
            "dinh menh", "hop dong", "nhiem vu", "suu tap", "suu tam",
            "nha suu tap", "nha suu tam", "hop dong dinh menh",
        ],
    },
    "rank": {
        "label": "Cày rank",
        "discord_category": "🏆┃Cày rank",
        "slug": "rank",
        "keywords": [
            "rank", "cay rank", "kc", "kim cuong", "cao thu", "thach dau",
            "len rank", "keo rank",
        ],
    },
    "xu": {
        "label": "Cày xu Delta",
        "discord_category": "💰┃Cày xu",
        "slug": "xu",
        "keywords": ["xu", "cay xu", "trieu xu", "xu delta", "1m xu"],
    },
    "item": {
        "label": "Item Layali",
        "discord_category": "🎁┃Item Layali",
        "slug": "item",
        "keywords": [
            "ken", "harmonica", "ken harmonica", "ten lua", "layali",
            "item", "item layali", "vat pham",
        ],
    },
    "hotro": {
        "label": "Hỗ trợ",
        "discord_category": "👩‍💻┃Hỗ trợ",
        "slug": "hotro",
        "keywords": [],
    },
    "khac": {
        "label": "Khác",
        "discord_category": "📦┃Khác",
        "slug": "khac",
        "keywords": [],
    },
}

# Khoá bảng giá (PRICE_LIST / menu /banggia) -> danh mục
PRICE_KEY_TO_CATEGORY = {
    "cay_rank": "rank",
    "ket_mua": "ket",
    "xu_delta": "xu",
    "harmonica": "item",
}


def normalize(text: str) -> str:
    """Bỏ dấu, thường hoá, giữ chữ-số và khoảng trắng."""
    text = unicodedata.normalize("NFD", (text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def classify(text: str) -> list[str]:
    """Trả về các danh mục khớp từ khoá, theo thứ tự xuất hiện trong câu. Không khớp → ['khac']."""
    norm = f" {normalize(text)} "
    hits: list[tuple[int, str]] = []
    for key, cat in CATEGORIES.items():
        best = None
        for kw in cat["keywords"]:
            m = re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", norm)
            if m and (best is None or m.start() < best):
                best = m.start()
        if best is not None:
            hits.append((best, key))
    if not hits:
        return ["khac"]
    hits.sort()
    return [k for _, k in hits]


def primary_category(keys: list[str]) -> str:
    return keys[0] if keys else "khac"


def label_of(key: str) -> str:
    return CATEGORIES.get(key, CATEGORIES["khac"])["label"]
