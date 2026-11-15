"""Pure game rules."""
from .breakthrough import (
    DOKIEP_FAIL_LOSS_PCT,
    DP_FAIL_LOSS_PCT,
    minor_breakthrough_chance,
    minor_needs_breakthrough,
    shield_charges,
    wrong_option_removal_chance,
)
from .cultivation import can_auto_advance_minor, clamp, cultivation_gain
from .stamina import REGEN_INTERVAL_SECONDS, regen, seconds_to_full

__all__ = [
    "clamp",
    "cultivation_gain",
    "can_auto_advance_minor",
    "shield_charges",
    "wrong_option_removal_chance",
    "minor_needs_breakthrough",
    "minor_breakthrough_chance",
    "DP_FAIL_LOSS_PCT",
    "DOKIEP_FAIL_LOSS_PCT",
    "regen",
    "seconds_to_full",
    "REGEN_INTERVAL_SECONDS",
]
