"""Nội dung `.help` — tách khỏi Discord/render để dễ sửa và test."""
from __future__ import annotations

import unicodedata

# key -> (tiêu đề, [alias], [(lệnh, mô tả)], mẹo cuối)
TOPICS: dict[str, dict] = {
    "tuluyen": {
        "title": "Tu luyện & đột phá",
        "aliases": ["tu", "dp", "dotpha", "thele", "thethuc", "tuvi", "taothe", "me", "hoithe", "tuluyen"],
        "rows": [
            (".taothe", "Tạo nhân vật: random Linh Căn và 5 chỉ số gốc."),
            (".me", "Xem thẻ nhân vật (chỉ số, trang bị, biểu đồ nhện)."),
            (".tu [n|max]", "Tu luyện. `.tu 5` hoặc `.tu max` gộp nhiều lượt (tối đa 20). Mỗi lượt tốn 2 Thể Lực."),
            (".dp", "Đột phá Tiểu Cảnh Giới từ Cấp 2 khi Tu Vi đầy 100%. Có tỷ lệ thành công, thất bại mất 10% mốc."),
            (".hoithe", "Mua +30 Thể Lực bằng Linh Thạch, tối đa 5 lần mỗi ngày."),
        ],
        "tip": "Cấp 1 tự lên tiểu cảnh. Thể Lực tự hồi 1 điểm / 3 phút, kể cả khi offline.",
    },
    "dokiep": {
        "title": "Độ Kiếp & đạo lộ",
        "aliases": ["kiep", "loikiep", "chon", "daolo", "gianhap", "thanhluc"],
        "rows": [
            (".chon tien|ma", "Chọn Tiên Đạo hoặc Ma Đạo (từ Trung Kỳ Cấp 1, không đổi được)."),
            (".gianhap tongmon|tantu", "Chọn thế lực khi đã qua Cấp 2."),
            (".dokiep", "Vượt 5 đợt Lôi Kiếp khi đạt Hậu Kỳ 100%. Mỗi vòng bấm nút 1 / 2 / 3, chỉ một đáp án đúng."),
        ],
        "tip": "Căn Cốt ≥ 70 có 4 Hộ Thể, Đạo Lữ +1. Khí Vận và Tị Lôi Đan loại bớt đáp án sai — dùng đan bằng `.dung` trước khi `.dokiep`.",
    },
    "do": {
        "title": "Đồ, công pháp & sức mạnh",
        "aliases": ["tui", "shop", "mua", "dung", "mac", "hoc", "congphap", "trangbi", "item", "lucchien"],
        "rows": [
            (".shop [mục] [trang]", "Cửa hàng hệ thống, lọc theo cảnh giới."),
            (".mua <ma_do> [sl]", "Mua vật phẩm."),
            (".tui", "Xem túi đồ."),
            (".dung <ma_do>", "Dùng đan dược (cộng Tu Vi, đổi chỉ số, hỗ trợ Độ Kiếp…)."),
            (".mac <ma_do>", "Mặc vũ khí / pháp bảo."),
            (".hoc <congphap>", "Học và nâng công pháp từ Tầng 1 đến 5."),
            (".congphap", "Danh sách công pháp đã học."),
            (".lucchien", "Xem chiến lực tổng."),
        ],
        "tip": "Chỉ số tổng = chỉ số gốc + trang bị đang mặc + công pháp × tầng lĩnh ngộ.",
    },
    "hoatdong": {
        "title": "Bí cảnh, hái dược & luyện đan",
        "aliases": ["bicanh", "haiduoc", "luyendan", "congthuc", "thap", "thaptien", "farm"],
        "rows": [
            (".bicanh [khu]", "Vào Bí Cảnh lấy Linh Thạch, Tu Vi, vật phẩm. `.bicanh list` xem khu và điều kiện Tiên/Ma."),
            (".haiduoc", "Hái dược liệu (giới hạn mỗi ngày)."),
            (".congthuc", "Xem công thức luyện đan."),
            (".luyendan <công_thức>", "Luyện đan. Ngộ Tính cao giảm tỷ lệ thất bại."),
            (".thap", "Leo Đăng Thiên Tháp: mỗi tầng chọn TIẾP TỤC hoặc RÚT LUI."),
        ],
        "tip": "Bí Cảnh tốn Thể Lực và có hồi chiêu. Tháp ẩn con số, hãy đọc cảnh báo rủi ro.",
    },
    "linhthu": {
        "title": "Linh thú",
        "aliases": ["thu", "trieuhoi", "pet", "mang", "thuve", "xuat"],
        "rows": [
            (".trieuhoi [lần]", "Triệu hồi Linh Thú bằng Linh Thạch."),
            (".thu", "Xem Linh Thú đang có."),
            (".mang <ma_thu>", "Cho Linh Thú xuất chiến (tối đa 3 con)."),
            (".thuve <ma_thu>", "Thu Linh Thú về."),
        ],
        "tip": "Thần Thức tăng uy lực Linh Thú.",
    },
    "kinhte": {
        "title": "Kinh tế & Sàn Đấu Giá",
        "aliases": ["daugia", "dg", "ban", "chuyen", "bxh", "linhthach", "ls", "tien"],
        "rows": [
            (".chuyen @user <sl>", "Chuyển Linh Thạch cho người chơi khác."),
            (".ban <ma_do> [sl]", "Bán đồ cho NPC."),
            (".daugia", "Xem các lô trên Sàn Đấu Giá."),
            (".daugia ban <ma_do> <sl> <giá>", "Đăng bán cả lô, giá cố định, phí 5%, hết hạn sau 24 giờ."),
            (".daugia mua|huy <id>", "Mua lô, hoặc hạ lô của mình (đồ về túi)."),
            (".daugia cua", "Xem lô của bạn."),
            (".bxh [tuvi|cancot|tien|tongmon]", "Bảng xếp hạng."),
        ],
        "tip": "Đồ ký gửi bị giữ trên sàn; lô hết hạn tự trả về túi.",
    },
    "daolu": {
        "title": "Đạo Lữ & Song Tu",
        "aliases": ["ketduyen", "huyduyen", "songtu", "tinhduyen"],
        "rows": [
            (".ketduyen @user", "Kết duyên Đạo Lữ (cả hai chưa có Đạo Lữ)."),
            (".huyduyen", "Hủy duyên."),
            (".songtu", "Song tu cùng Đạo Lữ: cả hai nhận Tu Vi, 24 giờ một lần."),
        ],
        "tip": "Đạo Lữ truyền công thêm 1 Hộ Thể khi Độ Kiếp.",
    },
}

ORDER = ["tuluyen", "dokiep", "do", "hoatdong", "linhthu", "kinhte", "daolu"]

QUICK_START = [
    ("1", ".taothe  →  tạo nhân vật"),
    ("2", ".tu max  →  tu luyện"),
    ("3", ".chon tien|ma  →  chọn đạo lộ"),
    ("4", ".dokiep  →  Độ Kiếp khi Hậu Kỳ 100%"),
]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.strip().lower().lstrip("."))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").replace("đ", "d")
    return "".join(c for c in text if c.isalnum())


_LOOKUP: dict[str, str] = {}
for _key, _t in TOPICS.items():
    _LOOKUP[_norm(_key)] = _key
    for _a in _t["aliases"]:
        _LOOKUP.setdefault(_norm(_a), _key)


def resolve_topic(query: str | None) -> str | None:
    """Tên chủ đề / alias / tên lệnh (có hoặc không dấu, có hoặc không dấu chấm) → key."""
    if not query:
        return None
    return _LOOKUP.get(_norm(query))


def overview_rows() -> list[tuple[str, str]]:
    return [(f".help {k}", TOPICS[k]["title"]) for k in ORDER]
