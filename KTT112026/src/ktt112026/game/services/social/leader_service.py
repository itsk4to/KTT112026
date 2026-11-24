"""Hệ thống Leader toàn server — top lực chiến + quà tuần tự động."""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num

# Quà tuần top lực chiến
WEEKLY_REWARDS = [
    {"rank": 1, "stones": 5000, "item": "hoanglongdan", "qty": 10},
    {"rank": 2, "stones": 3000, "item": "tukhidan", "qty": 8},
    {"rank": 3, "stones": 1500, "item": "theluclon", "qty": 5},
]


def _week_key(d: date | None = None) -> str:
    d = d or date.today()
    # Monday as start
    mon = d - timedelta(days=d.weekday())
    return mon.isoformat()


class LeaderService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def top_power(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.repo.db.fetchall(
            """SELECT user_id, display_name,
                      (can_cot + than_thuc + than_phap + major_realm * 20 + minor_stage * 5) AS score,
                      major_realm, minor_stage, path, spirit_stones
               FROM players
               ORDER BY score DESC, spirit_stones DESC
               LIMIT ?""",
            (max(3, min(20, limit)),),
        )
        out = []
        for i, r in enumerate(rows, 1):
            out.append({
                "rank": i,
                "user_id": str(r["user_id"]),
                "name": str(r["display_name"]),
                "score": int(r["score"]),
                "score_fmt": fmt_num(int(r["score"])),
                "stones": int(r["spirit_stones"]),
            })
        return out

    def process_weekly(self) -> dict[str, Any]:
        """Award top 3 once per week. Call on bot start."""
        wk = _week_key()
        existing = self.repo.db.fetchone(
            "SELECT COUNT(*) AS c FROM leader_weekly WHERE week_key=?",
            (wk,),
        )
        if existing and int(existing["c"]) > 0:
            return {"paid": False, "week": wk, "reason": "already"}

        tops = self.top_power(3)
        winners = []
        for entry in tops:
            reward = next((r for r in WEEKLY_REWARDS if r["rank"] == entry["rank"]), None)
            if not reward:
                continue
            p = self.repo.get(entry["user_id"])
            if not p:
                continue
            p.spirit_stones += int(reward["stones"])
            self.repo.save(p)
            self.repo.inventory_add(entry["user_id"], reward["item"], int(reward["qty"]))
            self.repo.db.execute(
                "INSERT INTO leader_weekly(week_key, user_id, rank, stones, item_id, qty, created_at) VALUES(?,?,?,?,?,?,?)",
                (wk, entry["user_id"], entry["rank"], reward["stones"], reward["item"], reward["qty"], time.time()),
            )
            winners.append({**entry, "reward": reward})
        self.repo.db.commit()
        return {"paid": True, "week": wk, "winners": winners}
