"""Tông Tháp (PR8) — chỉ đệ tử tông; combat PvE; đóng góp nhẹ vào kho tông."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.combat_service import CombatService, monster_for_tower_floor
from ktt112026.game.services.stats_service import StatsService

MAX_RUNS = 3
STAMINA = 15
BANK_SHARE = 0.1  # 10% stones bag -> sect bank


@dataclass
class SectTowerRun:
    user_id: str
    floor: int = 0
    bag_stones: int = 0
    bag_contrib: int = 0
    alive: bool = True
    risk: str = "An toàn"
    power: int = 0
    last_log: list[str] = field(default_factory=list)
    last_monster: str = ""


class SectTowerService:
    def __init__(
        self,
        repo: PlayerRepository,
        stats: StatsService | None = None,
        combat: CombatService | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repo = repo
        self.stats = stats or StatsService(repo)
        self.combat = combat or CombatService(repo, self.stats)
        self.rng = rng or random.Random()
        self._runs: dict[str, SectTowerRun] = {}

    def _day(self) -> str:
        return date.today().isoformat()

    def _runs_today(self, user_id: str) -> int:
        r = self.repo.db.fetchone(
            "SELECT runs FROM sect_tower_runs WHERE user_id=? AND day_key=?",
            (str(user_id), self._day()),
        )
        return int(r["runs"]) if r else 0

    def _inc_runs(self, user_id: str, best_floor: int) -> None:
        day = self._day()
        r = self.repo.db.fetchone(
            "SELECT runs, best_floor FROM sect_tower_runs WHERE user_id=? AND day_key=?",
            (str(user_id), day),
        )
        if r:
            self.repo.db.execute(
                "UPDATE sect_tower_runs SET runs=?, best_floor=? WHERE user_id=? AND day_key=?",
                (int(r["runs"]) + 1, max(int(r["best_floor"]), best_floor), str(user_id), day),
            )
        else:
            self.repo.db.execute(
                "INSERT INTO sect_tower_runs(user_id, day_key, runs, best_floor) VALUES(?,?,?,?)",
                (str(user_id), day, 1, best_floor),
            )
        self.repo.db.commit()

    def start(self, user_id: str) -> SectTowerRun:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if not p.sect_id:
            raise ValueError("Cần vào tông môn trước (`.tongmon`).")
        if self._runs_today(user_id) >= MAX_RUNS:
            raise ValueError(f"Hôm nay đã đánh Tông Tháp {MAX_RUNS} lần.")
        if p.stamina < STAMINA:
            raise ValueError("Không đủ thể lực.")
        p.stamina -= STAMINA
        self.repo.save(p)
        self._inc_runs(user_id, 0)
        run = SectTowerRun(user_id=str(user_id))
        self._runs[str(user_id)] = run
        return self.advance(user_id, continue_=True)

    def advance(self, user_id: str, *, continue_: bool) -> SectTowerRun:
        run = self._runs.get(str(user_id))
        if run is None or not run.alive:
            raise ValueError("Không có lượt Tông Tháp — `.tongthap` để bắt đầu.")
        if not continue_:
            self._payout(user_id, run)
            self._runs.pop(str(user_id), None)
            run.risk = "Rút lui Tông Tháp — đã nộp kho / nhận thưởng."
            return run
        p = self.repo.get(str(user_id))
        if not p or not p.sect_id:
            raise ValueError("Cần ở trong tông.")
        power = int(self.stats.effective(user_id)["power"])
        run.power = power
        run.floor += 1
        mon = monster_for_tower_floor(run.floor + 2, player_power=power)  # slightly harder
        mon = type(mon)(
            name=f"Thủ Hộ Tông Tháp · {run.floor}",
            attack=mon.attack,
            defense=mon.defense,
            hp=mon.hp,
            accuracy=mon.accuracy,
            evasion=mon.evasion,
            crit_pct=mon.crit_pct,
        )
        result = self.combat.resolve_pve(user_id, mon)
        run.last_log = list(result.get("log") or [])
        run.last_monster = mon.name
        if result["won"]:
            gain = 20 + run.floor * 10 + self.rng.randint(0, 15)
            run.bag_stones += gain
            run.bag_contrib += max(1, int(gain * BANK_SHARE))
            run.risk = f"Thắng {mon.name}"
            return run
        run.alive = False
        run.bag_stones = int(run.bag_stones * 0.5)
        run.bag_contrib = int(run.bag_contrib * 0.5)
        self._payout(user_id, run)
        self._runs.pop(str(user_id), None)
        run.risk = f"Bại tại {mon.name} — nhận 50% túi / kho."
        return run

    def _payout(self, user_id: str, run: SectTowerRun) -> None:
        p = self.repo.get(str(user_id))
        if not p:
            return
        p.spirit_stones += run.bag_stones
        p.sect_contrib += run.bag_contrib
        self.repo.save(p)
        if p.sect_id and run.bag_contrib:
            row = self.repo.db.fetchone("SELECT sect_id FROM sect_state WHERE sect_id=?", (p.sect_id,))
            if row:
                self.repo.db.execute(
                    "UPDATE sect_state SET bank_stones = bank_stones + ? WHERE sect_id=?",
                    (run.bag_contrib, p.sect_id),
                )
            else:
                self.repo.db.execute(
                    "INSERT INTO sect_state(sect_id, level, bank_stones, leader_id, last_weekly_key) VALUES(?,?,?,?,?)",
                    (p.sect_id, 1, run.bag_contrib, "", ""),
                )
            self.repo.db.commit()
        # best floor
        day = self._day()
        r = self.repo.db.fetchone(
            "SELECT best_floor FROM sect_tower_runs WHERE user_id=? AND day_key=?",
            (str(user_id), day),
        )
        if r and run.floor > int(r["best_floor"]):
            self.repo.db.execute(
                "UPDATE sect_tower_runs SET best_floor=? WHERE user_id=? AND day_key=?",
                (run.floor, str(user_id), day),
            )
            self.repo.db.commit()
