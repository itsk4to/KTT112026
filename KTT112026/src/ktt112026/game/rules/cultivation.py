"""Pure cultivation rules (GDD)."""
from __future__ import annotations

from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.models.player import ROOT_QUALITY_MULT


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def cultivation_gain(
    *,
    ngo_tinh: int,
    root_quality: str,
    major_realm: int,
) -> int:
    """One .tu tick — scales lightly with realm and Ngộ Tính + phẩm chất linh căn."""
    mult = ROOT_QUALITY_MULT.get(root_quality, 1.0)
    base = 25 + ngo_tinh * 0.4 + major_realm * 8
    return max(1, int(base * mult))


def can_auto_advance_minor(cultivation: int, major: int, minor: int) -> bool:
    """Within major realm, full bar advances Sơ→Trung→Hậu automatically."""
    if minor >= 2:
        return False
    return cultivation >= stage_requirement(major, minor)
