"""Hái dược — đặc quyền Tông Môn."""
from __future__ import annotations

import random
from datetime import date
from typing import Any

from ktt112026.game.content.loader import load_herbs
from ktt112026.game.repo.players import PlayerRepository

STAMINA_COST = 6
MAX_PER_DAY = 8
HERB_POOL = [
    ("linhthao", 40),
    ("thanhtrucdiep", 30),
    ("huyenlinhhoa", 18),
    ("loctamthao", 10),
    ("kimtinhthao", 2),
]


class GatherService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self.herbs = {h["id"]: h for h in load_herbs()}

    def gather(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if p.faction != "tongmon":
            raise ValueError("Chỉ đệ tử Tông Môn được vào Dược Viên (`.gianhap tongmon`).")
        today = date.today().isoformat()
        if p.last_gather_day != today:
            p.last_gather_day = today
            p.gather_count_today = 0
        if p.gather_count_today >= MAX_PER_DAY:
            raise ValueError(f"Hôm nay đã hái {MAX_PER_DAY} lần.")
        if p.stamina < STAMINA_COST:
            raise ValueError("Thể lực không đủ.")

        p.stamina -= STAMINA_COST
        p.gather_count_today += 1
        herb_id = self._roll()
        qty = 1 + (1 if self.rng.random() < 0.15 else 0)
        self.repo.inventory_add(user_id, herb_id, qty)
        self.repo.save(p)
        meta = self.herbs.get(herb_id, {"name": herb_id})
        return {
            "herb_id": herb_id,
            "name": meta.get("name", herb_id),
            "qty": qty,
            "left_today": MAX_PER_DAY - p.gather_count_today,
            "stamina": p.stamina,
        }

    def _roll(self) -> str:
        total = sum(w for _, w in HERB_POOL)
        r = self.rng.uniform(0, total)
        acc = 0.0
        for hid, w in HERB_POOL:
            acc += w
            if r <= acc:
                return hid
        return HERB_POOL[0][0]
