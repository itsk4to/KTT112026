"""6 đại cảnh giới × 3 tiểu kỳ — song song Tiên / Ma (GDD)."""
from __future__ import annotations

# major 1..6 -> (tien_name, ma_name)
MAJOR_NAMES: dict[int, tuple[str, str]] = {
    1: ("Luyện Khí", "Dẫn Khí"),
    2: ("Trúc Cơ", "Ngưng Huyết"),
    3: ("Kim Đan", "Ma Đan"),
    4: ("Nguyên Anh", "Ma Anh"),
    5: ("Hóa Thần", "Hóa Ma"),
    6: ("Đại Thừa", "Ma Tôn"),
}

MINOR_NAMES = ("Sơ Kỳ", "Trung Kỳ", "Hậu Kỳ")

# GDD thresholds: major -> (so, trung, hau) cultivation needed to fill that stage
THRESHOLDS: dict[int, tuple[int, int, int]] = {
    1: (1_000, 2_000, 3_500),
    2: (10_000, 20_000, 35_000),
    3: (100_000, 200_000, 350_000),
    4: (800_000, 1_500_000, 2_500_000),
    5: (6_000_000, 12_000_000, 20_000_000),
    6: (50_000_000, 100_000_000, 200_000_000),
}

STAMINA_BY_MAJOR = {1: 100, 2: 120, 3: 140, 4: 160, 5: 180, 6: 200}


def realm_display(major: int, minor: int, path: str = "") -> str:
    names = MAJOR_NAMES.get(major, ("?", "?"))
    if path == "ma":
        major_name = names[1]
    elif path == "tien":
        major_name = names[0]
    else:
        major_name = f"{names[0]}/{names[1]}"
    minor_name = MINOR_NAMES[max(0, min(2, minor))]
    return f"{major_name} · {minor_name}"


def stage_requirement(major: int, minor: int) -> int:
    row = THRESHOLDS.get(major, THRESHOLDS[1])
    return int(row[max(0, min(2, minor))])


def dual_requirement_label(major: int, minor: int) -> str:
    """Hiển thị điều kiện song song Tiên/Ma."""
    names = MAJOR_NAMES.get(major, ("?", "?"))
    minor_name = MINOR_NAMES[max(0, min(2, minor))]
    return f"{names[0]} {minor_name} / {names[1]} {minor_name}"
