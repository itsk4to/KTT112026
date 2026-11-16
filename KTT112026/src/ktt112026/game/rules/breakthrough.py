"""Độ Kiếp rules — shields, remove wrong answers."""
from __future__ import annotations

from .cultivation import clamp


def shield_charges(can_cot: int, base: int = 3) -> int:
    """Căn Cốt >= 70 → 4 Hộ Thể."""
    return 4 if can_cot >= 70 else base


def wrong_option_removal_chance(khi_van: int) -> float:
    """Khí Vận giúp loại đáp án sai (0..0.55)."""
    return clamp(khi_van / 180.0, 0.0, 0.55)


def pick_removed_wrong(correct: int, count: int, rng) -> list[int]:
    """Return up to `count` wrong option indices to hide (0..2 except correct)."""
    wrong = [i for i in range(3) if i != correct]
    rng.shuffle(wrong)
    return wrong[: max(0, min(count, len(wrong)))]
