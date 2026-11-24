"""Gacha case-open style image for linh thu."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont

TIER_COLOR = {
    "pham": (160, 160, 170),
    "linh": (80, 180, 120),
    "thien": (70, 140, 220),
    "hon": (180, 80, 220),
    "hon_don": (220, 160, 60),
}
TIER_NAME = {
    "pham": "Pham",
    "linh": "Linh",
    "thien": "Thien",
    "hon": "Hon",
    "hon_don": "Hon Don",
}


def _font(size: int, bold: bool = False):
    try:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def render_gacha_open(*, results: list[dict[str, Any]], cost: int, stones_left: int) -> bytes:
    W, H = 720, 280
    img = Image.new("RGB", (W, H), (18, 18, 24))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((16, 16, W - 16, H - 16), radius=18, fill=(28, 28, 36))
    draw.text((32, 28), "MO HOM LINH THU", font=_font(20, True), fill=(230, 210, 140))
    y = 70
    slot_w = 140
    for i, pet in enumerate(results[-5:]):
        x = 40 + i * (slot_w + 8)
        tier = str(pet.get("tier") or "pham")
        col = TIER_COLOR.get(tier, (160, 160, 170))
        draw.rounded_rectangle((x, y, x + slot_w, y + 120), radius=12, outline=col, width=3, fill=(40, 40, 50))
        name = str(pet.get("name") or "?")[:14]
        draw.text((x + 10, y + 40), name, font=_font(14, True), fill=(240, 240, 240))
        draw.text((x + 10, y + 70), TIER_NAME.get(tier, tier), font=_font(12), fill=col)
    if results:
        last = results[-1]
        tier = str(last.get("tier") or "pham")
        col = TIER_COLOR.get(tier, (200, 180, 80))
        draw.rounded_rectangle((W - 220, 60, W - 40, 200), radius=14, outline=col, width=4, fill=(30, 28, 40))
        draw.text((W - 200, 80), "NHAN DUOC", font=_font(12), fill=(180, 180, 180))
        draw.text((W - 200, 110), str(last.get("name") or "?")[:16], font=_font(16, True), fill=col)
        draw.text((W - 200, 140), TIER_NAME.get(tier, tier), font=_font(13), fill=col)
    draw.text((32, H - 50), f"-{cost:,} LS  ·  Con {stones_left:,} LS", font=_font(14), fill=(160, 200, 160))
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
