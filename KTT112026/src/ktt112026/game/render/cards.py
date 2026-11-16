"""Character card + cultivate result as PNG (Pillow)."""
from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from ktt112026.game.content.realms import realm_display, stage_requirement
from ktt112026.game.models.player import (
    ROOT_QUALITY_LABEL,
    ROOT_SYSTEM_LABEL,
    STAT_LABELS,
)

if TYPE_CHECKING:
    from ktt112026.game.models.player import Player

# Palette — dark xianxia
BG = (16, 18, 28)
PANEL = (28, 32, 48)
GOLD = (212, 175, 95)
TEXT = (235, 232, 220)
MUTED = (150, 155, 170)
BAR_BG = (40, 44, 60)
BAR_FILL = (90, 160, 220)
ACCENT = (120, 90, 200)

def _theme_for(path: str = "", major: int = 1) -> dict:
    """Palette by Đạo Lộ + khung theo đại cảnh giới (GDD Thẻ 2)."""
    path = (path or "").lower()
    if path == "tien":
        # cyan → soft gold
        panel = (22, 40, 52)
        accent = (100, 200, 220)
        gold = (230, 200, 120)
        bar = (80, 180, 200)
        edge = (60, 140, 160)
    elif path == "ma":
        # crimson → violet
        panel = (42, 24, 40)
        accent = (200, 90, 120)
        gold = (220, 160, 100)
        bar = (180, 80, 110)
        edge = (140, 60, 100)
    else:
        panel = PANEL
        accent = ACCENT
        gold = GOLD
        bar = BAR_FILL
        edge = (70, 80, 100)
    # frame thickness by major realm
    frame = 2 + min(6, max(0, major - 1))
    return {
        "panel": panel,
        "accent": accent,
        "gold": gold,
        "bar": bar,
        "edge": edge,
        "frame": frame,
    }




def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, ratio: float, fill=BAR_FILL) -> None:
    ratio = max(0.0, min(1.0, ratio))
    draw.rounded_rectangle((x, y, x + w, y + h), radius=6, fill=BAR_BG)
    if ratio > 0:
        draw.rounded_rectangle((x, y, x + max(8, int(w * ratio)), y + h), radius=6, fill=fill)


def _radar(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    values: list[int],
    max_v: int = 100,
) -> None:
    import math

    n = len(values)
    pts = []
    for i, v in enumerate(values):
        ang = -math.pi / 2 + i * (2 * math.pi / n)
        r = radius * (max(0, min(max_v, v)) / max_v)
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    # grid
    for ring in (0.33, 0.66, 1.0):
        ring_pts = []
        for i in range(n):
            ang = -math.pi / 2 + i * (2 * math.pi / n)
            ring_pts.append((cx + radius * ring * math.cos(ang), cy + radius * ring * math.sin(ang)))
        draw.polygon(ring_pts, outline=(55, 60, 80))
    for i in range(n):
        ang = -math.pi / 2 + i * (2 * math.pi / n)
        draw.line((cx, cy, cx + radius * math.cos(ang), cy + radius * math.sin(ang)), fill=(55, 60, 80), width=1)
    draw.polygon(pts, fill=(90, 120, 200, 90) if False else None, outline=GOLD)
    for p in pts:
        draw.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=GOLD)


def render_profile_card(
    player: "Player",
    *,
    effective_stats: dict | None = None,
    power: int | None = None,
    gear_names: dict | None = None,
    pet_names: list[str] | None = None,
    partner_name: str | None = None,
    techniques: list[str] | None = None,
) -> bytes:
    """Full character card for .me — equipment, pets, radar, power."""
    W, H = 760, 560
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(26, bold=True)
    body_f = _font(17)
    small_f = _font(14)
    th = _theme_for(player.path, player.major_realm)
    # outer edge by realm
    draw.rounded_rectangle((8, 8, W - 8, H - 8), radius=20, outline=th["edge"], width=th["frame"])
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=18, fill=th["panel"])
    draw.rounded_rectangle((28, 28, 430, 96), radius=12, fill=(36, 40, 58))

    name = player.display_name[:22]
    realm = realm_display(player.major_realm, player.minor_stage, player.path)
    path_label = {"tien": "Tiên Đạo", "ma": "Ma Đạo"}.get(player.path, "Chưa chọn Đạo")
    faction_label = {"tongmon": "Tông Môn", "tantu": "Tán Tu"}.get(player.faction, "Chưa gia nhập")
    draw.text((42, 38), name, font=title_f, fill=th["gold"])
    path_lbl = "Tiên Đạo" if player.path == "tien" else ("Ma Đạo" if player.path == "ma" else "Chưa phân đạo")
    draw.text((42, 68), path_lbl, font=small_f, fill=th["accent"])
    draw.text((42, 70), f"{realm} · {path_label}", font=small_f, fill=TEXT)

    root = (
        f"Linh căn {ROOT_SYSTEM_LABEL.get(player.root_system, player.root_system)} · "
        f"{ROOT_QUALITY_LABEL.get(player.root_quality, player.root_quality)} · {faction_label}"
    )
    draw.text((28, 108), root, font=small_f, fill=MUTED)

    need = stage_requirement(player.major_realm, player.minor_stage)
    ratio = player.cultivation / need if need else 0
    draw.text((28, 136), f"Tu Vi  {player.cultivation:,} / {need:,}", font=body_f, fill=TEXT)
    _bar(draw, 28, 160, 380, 16, ratio)
    draw.text((28, 186), f"Linh Thạch  {player.spirit_stones:,}", font=body_f, fill=TEXT)
    draw.text((220, 186), f"TL {player.stamina}/{player.max_stamina}", font=body_f, fill=TEXT)
    _bar(draw, 28, 212, 380, 12, player.stamina / max(1, player.max_stamina), fill=(100, 180, 120))

    stats = effective_stats or player.stats.as_dict()
    base = player.stats.as_dict()
    y = 236
    draw.text((28, y), "Chỉ số (gốc → hiệu dụng)", font=small_f, fill=MUTED)
    y += 20
    for key in ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van"):
        label = STAT_LABELS[key]
        val = int(stats.get(key, base[key]))
        b = int(base[key])
        extra = val - b
        extra_s = f" ({extra:+d})" if extra else ""
        draw.text((28, y), f"{label}", font=small_f, fill=MUTED)
        draw.text((120, y), f"{val}{extra_s}", font=small_f, fill=TEXT)
        _bar(draw, 200, y + 2, 200, 12, min(1.0, val / 100.0), fill=ACCENT)
        y += 20

    if power is not None:
        draw.text((28, y + 4), f"Lực chiến ~ {power:,}", font=body_f, fill=GOLD)

    # Right: radar
    values = [int(stats.get(k, 50)) for k in ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van")]
    _radar(draw, 580, 180, 100, values, max_v=120)
    labels = ["Cốt", "Ngộ", "Thức", "Pháp", "Vận"]
    import math
    for i, lab in enumerate(labels):
        ang = -math.pi / 2 + i * (2 * math.pi / 5)
        lx = 580 + 118 * math.cos(ang)
        ly = 180 + 118 * math.sin(ang)
        draw.text((lx - 12, ly - 8), lab, font=small_f, fill=MUTED)

    # Gear panel
    gear = gear_names or {}
    draw.rounded_rectangle((450, 300, W - 28, H - 28), radius=12, fill=(36, 40, 58))
    draw.text((466, 312), "Trang bị & Linh thú", font=body_f, fill=GOLD)
    gy = 342
    for label, key in (("Vũ khí 1", "weapon1"), ("Vũ khí 2", "weapon2"), ("Pháp bảo", "treasure")):
        val = gear.get(key) or "—"
        draw.text((466, gy), f"{label}: {val[:22]}", font=small_f, fill=TEXT)
        gy += 20
    pets = pet_names or []
    draw.text((466, gy + 4), "Xuất chiến:", font=small_f, fill=MUTED)
    gy += 22
    if pets:
        for pn in pets[:3]:
            draw.text((466, gy), f"• {pn[:24]}", font=small_f, fill=TEXT)
            gy += 18
    else:
        draw.text((466, gy), "• (trống)", font=small_f, fill=MUTED)
        gy += 18

    if partner_name:
        draw.text((466, min(gy + 6, H - 50)), f"Đạo Lữ: {partner_name[:18]}", font=small_f, fill=GOLD)

    # bottom left techniques
    if techniques:
        draw.text((28, 500), "Công pháp: " + ", ".join(techniques[:4]), font=small_f, fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_cultivate_card(
    *,
    name: str,
    realm: str,
    gain: int,
    cultivation: int,
    need: int,
    stamina: int,
    max_stamina: int,
    advanced: bool,
) -> bytes:
    W, H = 520, 240
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(24, bold=True)
    body_f = _font(18)
    small_f = _font(15)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    title = "Tiểu Cảnh Giới đột phá!" if advanced else "Tu Luyện"
    draw.text((28, 28), title, font=title_f, fill=GOLD)
    draw.text((28, 64), f"{name} · {realm}", font=body_f, fill=TEXT)
    draw.text((28, 100), f"+{gain:,} Tu Vi", font=body_f, fill=(120, 200, 140))
    draw.text((28, 130), f"Tu Vi  {cultivation:,} / {need:,}", font=small_f, fill=MUTED)
    _bar(draw, 28, 154, 460, 16, cultivation / need if need else 0)
    draw.text((28, 185), f"Thể lực  {stamina}/{max_stamina}", font=small_f, fill=MUTED)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_create_card(player: "Player") -> bytes:
    return render_profile_card(player)


def render_shop_menu() -> bytes:
    """Category picker image."""
    W, H = 560, 380
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(26, bold=True)
    body_f = _font(18)
    small_f = _font(15)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    draw.text((32, 28), "Cửa Hàng Hệ Thống", font=title_f, fill=GOLD)
    draw.text((32, 70), "Chọn gian hàng:", font=body_f, fill=TEXT)
    cats = [
        (".shop vukhi", "Vũ Khí"),
        (".shop phapbao", "Pháp Bảo"),
        (".shop danduoc", "Đan Dược"),
        (".shop congphap", "Công Pháp"),
        (".shop linhthu", "Linh Thú"),
    ]
    y = 110
    for cmd, label in cats:
        draw.rounded_rectangle((32, y, W - 32, y + 40), radius=10, fill=(36, 40, 58))
        draw.text((48, y + 10), f"{label}", font=body_f, fill=TEXT)
        draw.text((280, y + 12), cmd, font=small_f, fill=MUTED)
        y += 48
    draw.text((32, H - 40), "Mua: .mua <ma_do> [so_luong]", font=small_f, fill=MUTED)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_shop_catalog(
    *,
    category_label: str,
    items: list[dict],
    page: int = 0,
    page_size: int = 6,
) -> bytes:
    """One shop category page as image."""
    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    slice_ = items[page * page_size : (page + 1) * page_size]

    W, H = 720, 120 + max(1, len(slice_)) * 52 + 36
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(24, bold=True)
    body_f = _font(16)
    small_f = _font(14)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    draw.text((28, 28), f"Shop · {category_label}", font=title_f, fill=GOLD)
    draw.text((28, 62), f"Trang {page + 1}/{pages} — .mua <ma_do> [sl]", font=small_f, fill=MUTED)

    y = 96
    for it in slice_:
        draw.rounded_rectangle((24, y, W - 24, y + 46), radius=8, fill=(36, 40, 58))
        path_tag = {"tien": "Tiên", "ma": "Ma", "any": "Chung"}.get(str(it.get("path")), "")
        draw.text((36, y + 6), f"{it['name']}", font=body_f, fill=TEXT)
        draw.text((320, y + 6), f"{int(it['price']):,} LS", font=body_f, fill=GOLD)
        draw.text((440, y + 6), f"[{it['id']}]", font=small_f, fill=MUTED)
        draw.text((36, y + 26), f"{path_tag} · Cấp {it.get('major_min', 1)} · {it.get('stats', '')}"[:78], font=small_f, fill=MUTED)
        y += 52

    if pages > 1:
        draw.text((28, H - 32), f"Trang sau: .shop <loai> {page + 2}" if page + 1 < pages else "Hết trang", font=small_f, fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_shop_buy_result(*, ok: bool, title: str, detail: str) -> bytes:
    W, H = 520, 180
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(22, bold=True)
    body_f = _font(16)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    color = (120, 200, 140) if ok else (220, 120, 120)
    draw.text((28, 36), title, font=title_f, fill=color)
    # wrap detail
    y = 80
    line = ""
    for word in detail.split():
        trial = (line + " " + word).strip()
        if len(trial) > 48:
            draw.text((28, y), line, font=body_f, fill=TEXT)
            y += 24
            line = word
        else:
            line = trial
    if line:
        draw.text((28, y), line, font=body_f, fill=TEXT)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_dokiep_card(
    *,
    round_no: int,
    shields: int,
    message: str,
    options: list[str] | None = None,
    finished: bool = False,
    success: bool = False,
    hints: list[str] | None = None,
) -> bytes:
    opts = options or []
    hint_lines = hints or []
    base_h = 340 if not finished else 220
    extra = 18 * min(4, len(hint_lines)) + max(0, len(opts) - 3) * 52
    H = min(520, base_h + extra)
    W = 640
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(24, bold=True)
    body_f = _font(16)
    small_f = _font(14)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    if finished:
        title = "Độ Kiếp Thành Công" if success else "Độ Kiếp Thất Bại"
        color = (120, 200, 140) if success else (220, 120, 120)
        draw.text((28, 36), title, font=title_f, fill=color)
        draw.text((28, 90), message[:90], font=body_f, fill=TEXT)
    else:
        draw.text((28, 28), f"Lôi Kiếp · Vòng {round_no}/5", font=title_f, fill=GOLD)
        draw.text((28, 64), f"Hộ Thể còn: {shields}", font=body_f, fill=TEXT)
        y = 92
        for h in hint_lines[:4]:
            draw.text((28, y), f"• {h[:70]}", font=small_f, fill=(180, 160, 100))
            y += 18
        draw.text((28, y), message[:70], font=small_f, fill=MUTED)
        y += 28
        labels = ["①", "②", "③"]
        for i, opt in enumerate(opts[:3]):
            draw.rounded_rectangle((24, y, W - 24, y + 44), radius=8, fill=(36, 40, 58))
            draw.text((36, y + 12), f"{labels[i]}  {opt[:52]}", font=small_f, fill=TEXT)
            y += 52
        draw.text((28, H - 36), "Bấm nút bên dưới — đáp án sai có thể đã bị loại", font=small_f, fill=MUTED)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_bag_card(items: list[dict], *, name: str) -> bytes:
    W = 640
    rows = max(1, len(items))
    H = min(520, 100 + rows * 36)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(22, bold=True)
    small_f = _font(14)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    draw.text((28, 28), f"Túi đồ · {name[:20]}", font=title_f, fill=GOLD)
    if not items:
        draw.text((28, 80), "Trống — vào .shop để mua.", font=small_f, fill=MUTED)
    y = 70
    for it in items[:12]:
        draw.text((28, y), f"x{it['quantity']}  {it['name']}  [{it['item_id']}]", font=small_f, fill=TEXT)
        y += 32
    if len(items) > 12:
        draw.text((28, y), f"... và {len(items)-12} món khác", font=small_f, fill=MUTED)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_tower_card(*, floor: int, risk: str, stones: int, cult: int, alive: bool, message: str) -> bytes:
    W, H = 560, 240
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_f = _font(22, bold=True)
    body_f = _font(16)
    small_f = _font(14)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=PANEL)
    draw.text((28, 28), f"Đăng Thiên Tháp · Tầng {floor}", font=title_f, fill=GOLD)
    draw.text((28, 70), f"Rủi ro: {risk}", font=body_f, fill=TEXT)
    draw.text((28, 100), f"Túi tạm: {stones:,} LS · {cult:,} Tu Vi", font=body_f, fill=MUTED)
    draw.text((28, 140), message[:70], font=small_f, fill=(120, 200, 140) if alive else (220, 120, 120))
    if alive:
        draw.text((28, 180), "Bấm Tiếp tục hoặc Rút lui", font=small_f, fill=MUTED)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_simple_result(*, title: str, detail: str, ok: bool = True) -> bytes:
    return render_shop_buy_result(ok=ok, title=title, detail=detail)


def render_partner_card(
    *,
    name: str,
    partner_name: str,
    days: int,
    hours: int,
    major: int,
    path: str,
    last_songtu: str,
) -> bytes:
    """Thẻ đạo lữ — tông màu hồng."""
    W, H = 640, 360
    bg = (28, 16, 24)
    panel = (56, 28, 48)
    pink = (255, 140, 180)
    soft = (255, 200, 220)
    text = (255, 240, 245)
    muted = (200, 160, 180)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    title_f = _font(26, bold=True)
    body_f = _font(17)
    small_f = _font(14)
    draw.rounded_rectangle((10, 10, W - 10, H - 10), radius=18, outline=pink, width=3)
    draw.rounded_rectangle((16, 16, W - 16, H - 16), radius=14, fill=panel)
    draw.text((36, 32), "Đạo Lữ", font=title_f, fill=pink)
    draw.text((36, 80), f"{name}  ♥  {partner_name}", font=body_f, fill=text)
    path_lbl = "Tiên Đạo" if path == "tien" else ("Ma Đạo" if path == "ma" else "—")
    draw.text((36, 120), f"Cùng tu: {days} ngày {hours} giờ", font=body_f, fill=soft)
    draw.text((36, 160), f"Cảnh đối phương: cấp {major} · {path_lbl}", font=small_f, fill=muted)
    draw.text((36, 200), f"Song tu gần nhất: {last_songtu}", font=small_f, fill=muted)
    draw.text((36, H - 48), "`.songtu` để cùng tu một lần mỗi ngày", font=small_f, fill=pink)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
