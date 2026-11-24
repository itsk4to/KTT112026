"""Combat service (PR2) — PvE encounter resolution using combat_rules + StatsService.

No PvP, no Secret Realm. Stateless per call except RNG.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.rules import combat_rules as cr
from ktt112026.game.services.player.stats_service import StatsService


@dataclass(frozen=True)
class MonsterProfile:
    name: str
    attack: int
    defense: int
    hp: int
    accuracy: float
    evasion: float
    crit_pct: float = 5.0


def monster_for_tower_floor(floor: int, *, player_power: int = 50) -> MonsterProfile:
    """Scale a tower guardian to floor + rough player power."""
    f = max(1, int(floor))
    base = 20 + f * 8 + max(0, player_power) // 15
    return MonsterProfile(
        name=f"Thủ Vệ Tầng {f}",
        attack=base + f * 2,
        defense=max(5, base // 2),
        hp=base * 3 + f * 10,
        accuracy=40 + f * 1.5,
        evasion=20 + f,
        crit_pct=min(25.0, 3.0 + f * 0.4),
    )


class CombatService:
    def __init__(
        self,
        repo: PlayerRepository,
        stats: StatsService | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repo = repo
        self.stats = stats or StatsService(repo)
        self.rng = rng or random.Random()

    def player_combat_stats(self, user_id: str) -> dict[str, Any]:
        eff = self.stats.effective(str(user_id))
        st = eff["stats"]
        der = eff["derived"]
        # Map core stats → combat numbers
        atk = int(st["can_cot"] * 1.2 + st["than_thuc"] * 0.5 + der.get("atk", 0))
        defense = int(st["can_cot"] * 0.6 + st["than_phap"] * 0.4 + der.get("def", 0))
        hp = int(80 + st["can_cot"] * 2 + der.get("hp", 0) + eff["player"].major_realm * 15)
        accuracy = float(st["than_thuc"] + der.get("skill_damage_pct", 0))
        evasion = float(st["than_phap"] + der.get("dodge_pct", 0))
        crit_pct = float(der.get("crit_pct", 0)) + st["than_thuc"] * 0.05
        return {
            "eff": eff,
            "attack": max(1, atk),
            "defense": max(1, defense),
            "hp": max(1, int(hp * (1 + float(der.get("hp_pct", 0)) / 100.0))),
            "accuracy": accuracy,
            "evasion": evasion,
            "crit_pct": crit_pct,
            "power": int(eff["power"]),
        }

    def resolve_pve(
        self,
        user_id: str,
        monster: MonsterProfile,
        *,
        max_rounds: int = 12,
    ) -> dict[str, Any]:
        """Simple alternating swings until one side HP <= 0 or rounds exhausted."""
        pc = self.player_combat_stats(user_id)
        php = int(pc["hp"])
        mhp = int(monster.hp)
        log: list[str] = []
        rounds = 0
        while php > 0 and mhp > 0 and rounds < max_rounds:
            rounds += 1
            # Player swing
            pr = cr.resolve_attack(
                attack=int(pc["attack"]),
                defense=monster.defense,
                accuracy=float(pc["accuracy"]),
                evasion=monster.evasion,
                crit_pct=float(pc["crit_pct"]),
                skill_power=1.0,
                mastery=0,
                rng=self.rng,
            )
            if pr["hit"]:
                mhp -= int(pr["damage"])
                tag = " bạo kích" if pr["crit"] else ""
                log.append(f"R{rounds}: Bạn gây {pr['damage']}{tag} (còn {max(0, mhp)} HP địch)")
            else:
                log.append(f"R{rounds}: Bạn đánh trượt")
            if mhp <= 0:
                break
            # Monster swing
            mr = cr.resolve_attack(
                attack=monster.attack,
                defense=int(pc["defense"]),
                accuracy=monster.accuracy,
                evasion=float(pc["evasion"]),
                crit_pct=monster.crit_pct,
                rng=self.rng,
            )
            if mr["hit"]:
                php -= int(mr["damage"])
                tag = " bạo kích" if mr["crit"] else ""
                log.append(f"R{rounds}: {monster.name} gây {mr['damage']}{tag} (HP bạn {max(0, php)})")
            else:
                log.append(f"R{rounds}: {monster.name} đánh trượt")

        won = mhp <= 0 and php > 0
        drew = mhp > 0 and php > 0
        return {
            "won": won and not drew,
            "drew": drew,
            "player_hp_left": max(0, php),
            "monster_hp_left": max(0, mhp),
            "monster": monster,
            "rounds": rounds,
            "log": log[-6:],  # last swings only
            "power": pc["power"],
        }
