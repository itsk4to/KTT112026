"""Định dạng tiền / nội dung thông báo Shop Delta (thuần, dễ test)."""
from __future__ import annotations

import re

# Emoji tuỳ chỉnh theo server của shop (lấy từ mẫu đơn hàng).
EMO_ORDER = "<:order:1544918574106148895>"
EMO_SHOP = "<:shop:1480206827416191099>"
EMO_STATUS = "<a:X_online:1463063024012234834>"
EMO_PRODUCT = "<a:Boost1:1426859771406979202>"
EMO_STRIP = (
    "<:may:1460962883029700680><:may:1460960269474988045>"
    "<:may:1460960169566535681><:may:1460960103057326186>"
)

STATUS_TEXT = {
    "pending": "⌛ **Chờ**",
    "done": "✅ **Hoàn thành**",
    "cancelled": "❌ **Đã huỷ**",
}

WARRANTY_HOURS = 48


def _dots(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def parse_money(text: str) -> int:
    """'25k' / '25K' / '25.000' / '25000' / '1tr5' / '1,5tr' → số đồng. Lỗi → ValueError."""
    raw = (text or "").strip().lower().replace("₫", "").replace("vnđ", "").replace("vnd", "").replace("đ", "")
    raw = raw.replace(" ", "")
    if not raw:
        raise ValueError("Số tiền trống.")
    m = re.fullmatch(r"(\d+)tr(\d{1,2})?", raw)  # 1tr5 = 1.500.000
    if m:
        whole, frac = int(m.group(1)), m.group(2)
        return whole * 1_000_000 + (int(frac.ljust(2, "0")) * 10_000 if frac else 0)
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(k|tr|m)", raw)
    if m:
        num = float(m.group(1).replace(",", "."))
        mult = 1_000 if m.group(2) == "k" else 1_000_000
        return int(round(num * mult))
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):  # 25.000 / 1,500,000
        return int(re.sub(r"[.,]", "", raw))
    if raw.isdigit():
        return int(raw)
    raise ValueError("Số tiền không hợp lệ (ví dụ: 25k, 25000, 150.000).")


def format_money(amount: int) -> str:
    """25000 → '25K VNĐ (25.000 VNĐ)'."""
    amount = int(amount)
    full = f"{_dots(amount)} VNĐ"
    if amount >= 1000 and amount % 1000 == 0:
        return f"{_dots(amount // 1000)}K VNĐ ({full})"
    return full


def build_order_message(
    *, amount: int, channel_id: int | str, user_id: int | str,
    product: str, status: str, created_ts: int,
) -> str:
    """Mẫu thông báo ĐƠN HÀNG gửi vào kênh chỉ định."""
    return (
        f"## {EMO_ORDER} **ĐƠN HÀNG**\n"
        f"> **Số Tiền**: **``{format_money(amount) if amount > 0 else 'Chưa cập nhật'}``**\n"
        f"> **Ticket**: <#{channel_id}>\n"
        f"> **Khách hàng**: <@{user_id}>\n"
        f"{EMO_SHOP} **Thông tin đơn hàng**\n"
        f">>> **Sản Phẩm**: {EMO_PRODUCT}  {product}\n"
        f"{EMO_STATUS} **Trạng thái**: {STATUS_TEXT.get(status, STATUS_TEXT['pending'])}\n\n"
        f"{EMO_STRIP} ✦ <t:{int(created_ts)}:f>"
    )


def legit_template(staff_id: int | str, code: str) -> str:
    """Câu lệnh legit điền sẵn — khách chỉ việc copy."""
    return f"+1 legit <@{staff_id}> {code}"


def legit_template_block(staff_id: int | str, code: str) -> str:
    """Khối code (Discord có nút copy) chứa câu lệnh legit điền sẵn."""
    return f"```\n{legit_template(staff_id, code)}\n```"


SELLER_ID_DEFAULT = 875320426711117844  # người bán cố định trong mẫu +1 legit (đổi bằng /shopcfg nguoi_ban)


def normalize_code(code: str) -> str:
    """'dl-1' / 'DL-0001' / '1' / '0001' → 'DL-0001'. Giữ nguyên nếu không phải dạng số."""
    c = (code or "").strip().strip("`.,;:!").upper()
    m = re.fullmatch(r"(?:DL-?)?(\d{1,6})", c)
    return f"DL-{int(m.group(1)):04d}" if m else c


def legit_template(seller_id: int | str, code: str) -> str:
    """Dòng khách copy-paste vào kênh legit."""
    return f"+1 legit <@{seller_id}> {code}"


def done_thanks_text(*, code: str, product: str, user_id: int | str, seller_id: int | str,
                     legit_channel_id: int | str | None) -> str:
    where = f"<#{legit_channel_id}>" if legit_channel_id else "kênh legit"
    return (
        f"✅ **Đơn hàng `{code}` đã hoàn thành!**\n"
        f"Sản phẩm: {product}\n\n"
        f"Cảm ơn <@{user_id}> đã tin tưởng và ủng hộ **Shop Delta** 💙\n\n"
        f"🛡️ **Nhận bảo hành {WARRANTY_HOURS}h:** vào {where}, copy và gửi đúng mẫu bên dưới:\n"
        f"```\n{legit_template(seller_id, code)}\n```"
    )


def build_done_notice(*, code: str, channel_id: int | str, user_id: int | str, product: str, amount: int) -> str:
    """Thông báo 'xong đơn' gửi ra kênh đơn hàng (ngoài ticket)."""
    money = f"\n> **Số Tiền**: **``{format_money(amount)}``**" if amount > 0 else ""
    return (
        f"## ✅ **ĐƠN HÀNG HOÀN THÀNH**\n"
        f"> **Mã đơn**: `{code}`{money}\n"
        f"> **Ticket**: <#{channel_id}>\n"
        f"> **Khách hàng**: <@{user_id}>\n"
        f">>> **Sản Phẩm**: {EMO_PRODUCT}  {product}\n"
        f"Cảm ơn bạn đã ủng hộ **Shop Delta** 💙"
    )


LEGIT_RE = re.compile(r"^\s*\+1\s+legit\s+<@!?(\d+)>\s+(\S+)", re.IGNORECASE)


def parse_legit(content: str) -> tuple[int, str] | None:
    """'+1 legit <@id> MÃ' → (id_được_tag, 'DL-0001'). Không đúng cú pháp → None."""
    m = LEGIT_RE.match(content or "")
    if not m:
        return None
    return int(m.group(1)), normalize_code(m.group(2))
