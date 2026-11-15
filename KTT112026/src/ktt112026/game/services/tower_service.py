"""Đăng Thiên Tháp — uses aggregated combat power."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.stats_service import StatsService

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


class TowerService:
    def __init__(
        self,
        repo: PlayerRepository,
        stats: StatsService | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repo = repo
        self.stats = stats or StatsService(repo)
        self.rng = rng or random.Random()
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
        difficulty = 35 + run.floor * 11
        chance = max(0.18, min(0.93, (power / max(1, difficulty)) * 0.6))
        if self.rng.random() > chance:
            run.alive = False
            run.bag_stones = 0
            run.bag_cultivation = 0
            run.risk = "Thất bại — mất túi thưởng đợt này."
            self._runs.pop(str(user_id), None)
            return run
        # economy: better stone/cult drip for same-realm shopping
        run.bag_stones += 40 * run.floor + p.major_realm * 25
        run.bag_cultivation += 25 * run.floor + p.stats.ngo_tinh
        if chance > 0.7:
            run.risk = "An toàn"
        elif chance > 0.45:
            run.risk = "Rủi ro"
        else:
            run.risk = "Rủi ro cao — sắp nguy"
        return run

    def _payout(self, user_id: str, run: TowerRun) -> None:
        p = self.repo.get(str(user_id))
        if not p:
            return
        p.spirit_stones += run.bag_stones
        need = stage_requirement(p.major_realm, p.minor_stage)
        p.cultivation = min(need, p.cultivation + run.bag_cultivation)
        self.repo.save(p)
