"""Combat pure formulas (PR1) — adapted from KTT102026 V3.9.9 combat_rules.

No Discord, no DB, no item catalog. Callers supply numeric stats.
Compatible with V1.6.3 StatsService derived fields (atk/def/hp/crit/dodge).
"""
from __future__ import annotations

import random
from typing import Mapping


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def hit_chance(accuracy: float, evasion: float) -> float:
    """Bounded 35%–97%."""
    raw = 0.75 + (accuracy - evasion) * 0.004
    return clamp(raw, 0.35, 0.97)


def calculate_damage(
    attack: int,
    defense: int,
    *,
    power: float = 1.0,
    variance: float = 0.12,
    rng: random.Random | None = None,
) -> int:
    """Physical-style damage after defense mitigation."""
    rng = rng or random.Random()
    mitigated = max(1.0, float(attack) - float(defense) * 0.55)
    roll = 1.0 + rng.uniform(-variance, variance)
    return max(1, int(mitigated * power * roll))


def critical_hit(
    damage: int,
    crit_pct: float,
    *,
    crit_mult: float = 1.5,
    rng: random.Random | None = None,
) -> tuple[int, bool]:
    """Return (damage_after_crit, was_crit). crit_pct is 0–100 scale."""
    rng = rng or random.Random()
    rate = clamp(float(crit_pct) / 100.0, 0.0, 0.75)
    if rng.random() < rate:
        return max(1, int(damage * crit_mult)), True
    return max(1, int(damage)), False


def mastery_multiplier(mastery: int) -> float:
    """Skill mastery: +1% per point, cap +12%."""
    return 1.0 + min(0.12, max(0, int(mastery)) * 0.01)


def mastery_stage(mastery: int) -> str:
    m = max(0, int(mastery))
    if m >= 12:
        return "Viên mãn"
    if m >= 8:
        return "Đại thành"
    if m >= 4:
        return "Tiểu thành"
    return "Nhập môn"


def status_on_hit_chance(base: float = 0.14) -> float:
    return clamp(float(base), 0.0, 1.0)


def tick_dot(max_hp: int, potency: float) -> int:
    """DoT tick from max HP fraction."""
    return max(1, int(max(1, int(max_hp)) * max(0.0, float(potency))))


def apply_shield(damage: int, shield_factor: float) -> int:
    """Reduce damage by shield_factor (0–0.9)."""
    factor = clamp(float(shield_factor), 0.0, 0.9)
    return max(1, int(round(int(damage) * (1.0 - factor))))


def resolve_attack(
    *,
    attack: int,
    defense: int,
    accuracy: float,
    evasion: float,
    crit_pct: float = 0.0,
    skill_power: float = 1.0,
    mastery: int = 0,
    shield_factor: float = 0.0,
    rng: random.Random | None = None,
) -> dict[str, int | float | bool | str]:
    """One attack resolution for future combat_service (PR2+).

    accuracy/evasion: same unit as V3 (flat); can pass than_thuc / than_phap.
    """
    rng = rng or random.Random()
    chance = hit_chance(accuracy, evasion)
    if rng.random() > chance:
        return {
            "hit": False,
            "damage": 0,
            "crit": False,
            "hit_chance": chance,
            "mastery_stage": mastery_stage(mastery),
        }
    mult = mastery_multiplier(mastery) * float(skill_power)
    raw = calculate_damage(attack, defense, power=mult, rng=rng)
    dmg, was_crit = critical_hit(raw, crit_pct, rng=rng)
    dmg = apply_shield(dmg, shield_factor)
    return {
        "hit": True,
        "damage": dmg,
        "crit": was_crit,
        "hit_chance": chance,
        "mastery_stage": mastery_stage(mastery),
    }


def combat_power_from_effective(eff: Mapping[str, object]) -> int:
    """Optional bridge: prefer StatsService['power'] when present."""
    if "power" in eff and eff["power"] is not None:
        return max(1, int(eff["power"]))  # type: ignore[arg-type]
    stats = eff.get("stats") or {}
    derived = eff.get("derived") or {}
    if isinstance(stats, Mapping) and isinstance(derived, Mapping):
        return max(
            1,
            int(stats.get("can_cot", 0) or 0)
            + int(stats.get("than_thuc", 0) or 0)
            + int(stats.get("than_phap", 0) or 0)
            + int(float(derived.get("atk", 0) or 0) / 10)
            + int(float(derived.get("def", 0) or 0) / 10),
        )
    return 1
