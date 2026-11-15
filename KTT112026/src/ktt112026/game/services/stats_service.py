"""Aggregate effective stats: base + gear + techniques."""
from __future__ import annotations

from typing import Any

from ktt112026.game.content.loader import catalog_by_id, load_congphap
from ktt112026.game.models.player import STAT_HARD_CAP, Player
from ktt112026.game.repo.players import PlayerRepository

CORE_STATS = ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van")


def _clamp_stat(v: int) -> int:
    return max(1, min(STAT_HARD_CAP, int(v)))


class StatsService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self._items = catalog_by_id()
        self._tech_by_id = {t["id"]: t for t in load_congphap()}

    def effective(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        base = p.stats.as_dict()
        bonus = {k: 0 for k in CORE_STATS}
        derived: dict[str, float] = {
            "atk": 0, "def": 0, "hp": 0,
            "atk_pct": 0, "def_pct": 0, "hp_pct": 0,
            "crit_pct": 0, "dodge_pct": 0, "lifesteal_pct": 0,
            "cultivate_pct": 0, "skill_damage_pct": 0,
        }

        def apply_map(src: dict[str, Any], mult: float = 1.0) -> None:
            for k, v in src.items():
                if k in bonus:
                    bonus[k] += int(v * mult)
                elif k in derived:
                    derived[k] += float(v) * mult

        for slot in (p.weapon1, p.weapon2, p.treasure, p.pet1, p.pet2, p.pet3):
            if not slot:
                continue
            item = self._items.get(slot)
            if not item:
                continue
            apply_map(item.get("bonuses") or {})
            apply_map(item.get("penalties") or {})

        for row in self.repo.list_techniques(user_id):
            tech = self._tech_by_id.get(row["technique_id"])
            if not tech:
                continue
            tier = max(1, min(5, int(row["tier"])))
            apply_map(tech.get("bonuses") or {}, mult=tier)
            apply_map(tech.get("penalties") or {}, mult=tier)

        final_stats = {k: _clamp_stat(base[k] + bonus[k]) for k in CORE_STATS}
        power = (
            final_stats["can_cot"]
            + final_stats["than_thuc"]
            + final_stats["than_phap"]
            + int(derived["atk"] / 10)
            + int(derived["def"] / 10)
            + p.major_realm * 20
            + p.minor_stage * 5
            + int(derived["atk_pct"] + derived["crit_pct"])
        )
        return {
            "player": p,
            "base": base,
            "bonus": bonus,
            "stats": final_stats,
            "derived": derived,
            "power": power,
            "cultivate_pct_total": derived["cultivate_pct"] + p.cultivate_bonus_pct,
        }
