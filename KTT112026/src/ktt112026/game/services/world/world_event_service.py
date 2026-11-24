"""World events nhẹ (PR5) — 1 event/ngày, claim 1 lần."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from ktt112026.game.repo.players import PlayerRepository

# Static catalog — no secret realm
EVENTS: list[dict[str, Any]] = [
    {
        "id": "linhkhi_trieu",
        "name": "Linh Khí triều",
        "desc": "Thiên địa tràn linh khí — nhận Linh Thạch và ít tu vi.",
        "stones": 120,
        "cultivation": 25,
    },
    {
        "id": "van_dao",
        "name": "Vân Dao ban phúc",
        "desc": "Đạo vận hanh thông — nhận Linh Thạch.",
        "stones": 180,
        "cultivation": 10,
    },
    {
        "id": "luyen_the",
        "name": "Luyện Thể thiên thời",
        "desc": "Phù hợp tắm linh tuyền — thể lực + Linh Thạch.",
        "stones": 80,
        "cultivation": 15,
        "stamina": 20,
    },
]


def _day_key() -> str:
    return date.today().isoformat()


def _event_for_day(day: str) -> dict[str, Any]:
    # stable rotate by day string
    idx = sum(ord(c) for c in day) % len(EVENTS)
    return dict(EVENTS[idx])


class WorldEventService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def current(self) -> dict[str, Any]:
        day = _day_key()
        ev = _event_for_day(day)
        return {"day": day, "event": ev}

    def claim(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. `.taothe` trước.")
        day = _day_key()
        ev = _event_for_day(day)
        eid = str(ev["id"])
        row = self.repo.db.fetchone(
            "SELECT 1 AS ok FROM world_event_claims WHERE day_key=? AND event_id=? AND user_id=?",
            (day, eid, str(user_id)),
        )
        if row:
            raise ValueError(f"Hôm nay đã nhận sự kiện **{ev['name']}** rồi.")
        stones = int(ev.get("stones") or 0)
        cult = int(ev.get("cultivation") or 0)
        sta = int(ev.get("stamina") or 0)
        p.spirit_stones += stones
        if cult:
            from ktt112026.game.content.realms import stage_requirement
            need = stage_requirement(p.major_realm, p.minor_stage)
            p.cultivation = min(need, p.cultivation + cult)
        if sta:
            p.stamina = min(p.max_stamina, p.stamina + sta)
        self.repo.save(p)
        self.repo.db.execute(
            "INSERT INTO world_event_claims(day_key, event_id, user_id, claimed_at) VALUES(?,?,?,?)",
            (day, eid, str(user_id), time.time()),
        )
        self.repo.db.commit()
        return {"event": ev, "stones": stones, "cultivation": cult, "stamina": sta, "player": p}
