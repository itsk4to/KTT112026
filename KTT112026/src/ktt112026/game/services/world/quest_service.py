"""Nhiệm vụ ngày — track + nhận thưởng."""
from __future__ import annotations

from datetime import date
from typing import Any

from ktt112026.game.repo.players import PlayerRepository

# bit 0 = quest tu, 1 = explore, 2 = tower, 3 = all-clear bonus
QUESTS = (
    {"bit": 0, "id": "tu", "name": "Tu luyện", "need": 5, "field": "tu_count", "stones": 120, "desc": "`.tu` đủ 5 lần (batch cũng tính)"},
    {"bit": 1, "id": "shop", "name": "Mua sắm", "need": 1, "field": "explore_count", "stones": 150, "desc": "Mua đồ trong `.shop` 1 lần"},
    {"bit": 2, "id": "thap", "name": "Đăng tháp", "need": 1, "field": "tower_count", "stones": 180, "desc": "Chơi `.thap` 1 lần (bắt đầu run)"},
)
ALL_CLEAR_BIT = 3
ALL_CLEAR_STONES = 250


class QuestService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def _today(self) -> str:
        return date.today().isoformat()

    def _row(self, user_id: str) -> dict[str, int]:
        day = self._today()
        r = self.repo.db.fetchone(
            "SELECT * FROM daily_progress WHERE user_id=? AND day_key=?",
            (str(user_id), day),
        )
        if r:
            return {
                "tu_count": int(r["tu_count"]),
                "explore_count": int(r["explore_count"]),
                "tower_count": int(r["tower_count"]),
                "claimed_mask": int(r["claimed_mask"]),
            }
        self.repo.db.execute(
            "INSERT INTO daily_progress(user_id, day_key) VALUES(?,?)",
            (str(user_id), day),
        )
        self.repo.db.commit()
        return {"tu_count": 0, "explore_count": 0, "tower_count": 0, "claimed_mask": 0}

    def _save(self, user_id: str, row: dict[str, int]) -> None:
        self.repo.db.execute(
            """UPDATE daily_progress SET
                tu_count=?, explore_count=?, tower_count=?, claimed_mask=?
               WHERE user_id=? AND day_key=?""",
            (
                row["tu_count"], row["explore_count"], row["tower_count"], row["claimed_mask"],
                str(user_id), self._today(),
            ),
        )
        self.repo.db.commit()

    def bump(self, user_id: str, kind: str, amount: int = 1) -> None:
        if self.repo.get(str(user_id)) is None:
            return
        row = self._row(user_id)
        key = {"tu": "tu_count", "shop": "explore_count", "thap": "tower_count"}.get(kind)
        if not key:
            return
        row[key] = int(row[key]) + max(1, int(amount))
        self._save(user_id, row)

    def status(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        row = self._row(user_id)
        mask = row["claimed_mask"]
        items = []
        done_all = True
        for q in QUESTS:
            cur = int(row[q["field"]])
            need = int(q["need"])
            claimed = bool(mask & (1 << q["bit"]))
            complete = cur >= need
            if not complete:
                done_all = False
            items.append({
                **q,
                "current": min(cur, need),
                "complete": complete,
                "claimed": claimed,
                "claimable": complete and not claimed,
            })
        all_claimed = bool(mask & (1 << ALL_CLEAR_BIT))
        return {
            "day": self._today(),
            "quests": items,
            "all_complete": done_all,
            "all_claimable": done_all and not all_claimed,
            "all_claimed": all_claimed,
            "all_clear_stones": ALL_CLEAR_STONES,
            "player": p,
        }

    def claim(self, user_id: str, quest_id: str | None = None) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        row = self._row(user_id)
        mask = row["claimed_mask"]
        gained = 0
        names: list[str] = []

        def claim_one(q: dict) -> None:
            nonlocal mask, gained
            bit = 1 << q["bit"]
            if mask & bit:
                return
            if int(row[q["field"]]) < int(q["need"]):
                return
            mask |= bit
            gained += int(q["stones"])
            names.append(q["name"])

        if quest_id is None or quest_id in ("all", "het"):
            for q in QUESTS:
                claim_one(q)
            # all-clear
            if all(int(row[q["field"]]) >= int(q["need"]) for q in QUESTS):
                if not (mask & (1 << ALL_CLEAR_BIT)):
                    mask |= 1 << ALL_CLEAR_BIT
                    gained += ALL_CLEAR_STONES
                    names.append("Toàn thành")
        else:
            qid = quest_id.strip().lower()
            if qid in ("full", "toan", "bonus"):
                if not all(int(row[q["field"]]) >= int(q["need"]) for q in QUESTS):
                    raise ValueError("Chưa xong hết nhiệm vụ ngày.")
                if mask & (1 << ALL_CLEAR_BIT):
                    raise ValueError("Đã nhận thưởng toàn thành.")
                mask |= 1 << ALL_CLEAR_BIT
                gained += ALL_CLEAR_STONES
                names.append("Toàn thành")
            else:
                found = next((q for q in QUESTS if q["id"] == qid), None)
                if not found:
                    raise ValueError("Nhiệm vụ không tồn tại. `.nhiemvu` để xem.")
                if int(row[found["field"]]) < int(found["need"]):
                    raise ValueError(f"Chưa đủ tiến độ {found['name']}.")
                if mask & (1 << found["bit"]):
                    raise ValueError("Đã nhận thưởng nhiệm vụ này.")
                claim_one(found)

        if gained <= 0:
            raise ValueError("Không có phần thưởng để nhận. `.nhiemvu` xem tiến độ.")
        row["claimed_mask"] = mask
        self._save(user_id, row)
        p.spirit_stones += gained
        self.repo.save(p)
        return {"stones": gained, "names": names, "player": p, "status": self.status(user_id)}
