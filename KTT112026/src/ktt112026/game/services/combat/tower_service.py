"""Đăng Thiên Tháp — PvE floors via CombatService (PR2)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.combat.combat_service import CombatService, monster_for_tower_floor
from ktt112026.game.services.player.stats_service import StatsService

MAX_RUNS_PER_DAY = 5
STAMINA_COST = 12


@dataclass
class TowerRun:
    user_id: str
    floor: int = 0
    bag_stones: int = 0
    bag_cultivation: int = 0
    alive: bool = True
    risk: str = "An toàn"
    power: int = 0
    last_log: list[str] = field(default_factory=list)
    last_monster: str = ""


class TowerService:
    def __init__(
        self,
        repo: PlayerRepository,
        stats: StatsService | None = None,
        rng: random.Random | None = None,
        combat: CombatService | None = None,
    ) -> None:
        self.repo = repo
        self.stats = stats or StatsService(repo)
        self.rng = rng or random.Random()
        self.combat = combat or CombatService(repo, self.stats, self.rng)
        self._runs: dict[str, TowerRun] = {}

    def start(self, user_id: str) -> TowerRun:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        today = date.today().isoformat()
        if p.last_tower_day != today:
            p.last_tower_day = today
            p.tower_runs_today = 0
        if p.tower_runs_today >= MAX_RUNS_PER_DAY:
            raise ValueError(f"Hôm nay đã leo {MAX_RUNS_PER_DAY} lần.")
        if p.stamina < STAMINA_COST:
            raise ValueError("Không đủ thể lực.")
        p.stamina -= STAMINA_COST
        p.tower_runs_today += 1
        self.repo.save(p)
        run = TowerRun(user_id=str(user_id))
        self._runs[str(user_id)] = run
        return self.advance(user_id, continue_=True)

    def advance(self, user_id: str, *, continue_: bool) -> TowerRun:
        run = self._runs.get(str(user_id))
        if run is None or not run.alive:
            raise ValueError("Không có lượt tháp — gõ `.thap` để bắt đầu.")
        if not continue_:
            self._payout(user_id, run)
            self._runs.pop(str(user_id), None)
            run.risk = "Đã rút lui — nhận thưởng."
            return run
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")

        eff = self.stats.effective(user_id)
        power = int(eff["power"])
        run.power = power
        run.floor += 1
        monster = monster_for_tower_floor(run.floor, player_power=power)
        result = self.combat.resolve_pve(user_id, monster)
        run.last_log = list(result.get("log") or [])
        run.last_monster = monster.name

        if result["won"]:
            run.bag_stones += 15 + run.floor * 8 + self.rng.randint(0, 10)
            run.bag_cultivation += 8 + run.floor * 3
            hp_ratio = result["player_hp_left"] / max(1, self.combat.player_combat_stats(user_id)["hp"])
            if hp_ratio > 0.66:
                run.risk = f"Thắng {monster.name} — thế thượng phong"
            elif hp_ratio > 0.33:
                run.risk = f"Thắng {monster.name} — giao tranh gắt"
            else:
                run.risk = f"Thắng {monster.name} — thê thảm"
            return run

        # loss or draw = fall
        run.alive = False
        # consolation: partial bag kept at 50%
        run.bag_stones = int(run.bag_stones * 0.5)
        run.bag_cultivation = int(run.bag_cultivation * 0.5)
        self._payout(user_id, run)
        self._runs.pop(str(user_id), None)
        if result.get("drew"):
            run.risk = f"Hòa/khí lực kiệt trước {monster.name} — rơi tháp (nhận 50% túi)."
        else:
            run.risk = f"Bại trước {monster.name} — rơi tháp (nhận 50% túi)."
        return run

    def _payout(self, user_id: str, run: TowerRun) -> None:
        p = self.repo.get(str(user_id))
        if not p:
            return
        p.spirit_stones += run.bag_stones
        need = stage_requirement(p.major_realm, p.minor_stage)
        p.cultivation = min(need, p.cultivation + run.bag_cultivation)
        self.repo.save(p)
