"""Đột phá & Độ Kiếp — công thức thuần (không Discord)."""
from __future__ import annotations

from .cultivation import clamp

# Mất bao nhiêu % mốc Tu Vi khi `.dp` thất bại / Độ Kiếp vỡ Hộ Thể.
DP_FAIL_LOSS_PCT = 10
DOKIEP_FAIL_LOSS_PCT = 20


def shield_charges(can_cot: int, base: int = 3) -> int:
    """Căn Cốt >= 70 → 4 Hộ Thể."""
    return 4 if can_cot >= 70 else base


def wrong_option_removal_chance(khi_van: int) -> float:
    """Khí Vận giúp loại đáp án sai (0..0.45)."""
    return clamp(khi_van / 200.0, 0.0, 0.45)


def minor_needs_breakthrough(major: int) -> bool:
    """Cấp 1: đầy Tu Vi tự lên tiểu cảnh. Từ Cấp 2: khóa `.tu` ở 100% và phải gõ `.dp`."""
    return major >= 2


def minor_breakthrough_chance(ngo_tinh: int, can_cot: int, bonus: float = 0.0) -> float:
    """Tỷ lệ `.dp` thành công theo Ngộ Tính + Căn Cốt (+ vật phẩm). 0.50 .. 0.95."""
    return clamp(0.55 + ngo_tinh * 0.002 + can_cot * 0.0015 + bonus, 0.50, 0.95)
