"""Linh thú — triệu hồi 5000 LS/lần, rate 4 bậc, chỉ số từ linhthu.json."""
from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from ktt112026.game.services._tx import atomic
from ktt112026.game.content.loader import load_linhthu
from ktt112026.game.repo.players import PlayerRepository

DATA = Path(__file__).resolve().parents[1] / "content" / "data" / "summon.json"


@lru_cache(maxsize=1)
def _summon_cfg() -> dict[str, Any]:
    with DATA.open(encoding="utf-8") as f:
        return json.load(f)


class PetService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self._pets = load_linhthu()
        self._by_id = {p["id"]: p for p in self._pets}
        self._by_tier: dict[str, list[dict]] = {}
        for p in self._pets:
            self._by_tier.setdefault(p.get("tier", "pham"), []).append(p)

    @property
    def cost_per_pull(self) -> int:
        return int(_summon_cfg().get("cost_per_pull", 5000))

    def rates(self) -> dict[str, float]:
        return dict(_summon_cfg().get("rates") or {})

    @atomic
    def summon(self, user_id: str, times: int = 1) -> dict[str, Any]:
        multi = int(_summon_cfg().get("multi_pull", 10))
        times = multi if int(times) >= multi else 1
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        cost = self.cost_per_pull * times
        if p.spirit_stones < cost:
            raise ValueError(f"Không đủ Linh Thạch (cần {cost:,} — {self.cost_per_pull:,} LS/lần).")
        p.spirit_stones -= cost
        got: list[dict] = []
        for _ in range(times):
            tier = self._roll_tier()
            pool = self._by_tier.get(tier) or self._by_tier.get("pham") or self._pets
            # Prefer pets player can use soon (major_min <= realm+1), else full tier pool
            eligible = [x for x in pool if int(x.get("major_min", 1)) <= p.major_realm + 1]
            if not eligible:
                eligible = list(pool)
            pet = self.rng.choice(eligible)
            self.repo.pet_add(user_id, pet["id"], 1)
            got.append(pet)
        self.repo.save(p)
        return {
            "cost": cost,
            "cost_each": self.cost_per_pull,
            "got": got,
            "stones_left": p.spirit_stones,
            "rates": self.rates(),
        }

    def _roll_tier(self) -> str:
        rates = self.rates()
        # Khí Vận lightly shifts weight toward higher tiers (soft)
        order = ["pham", "linh", "than", "hon_don"]
        weights = [float(rates.get(k, 0)) for k in order]
        total = sum(weights) or 1.0
        r = self.rng.uniform(0, total)
        acc = 0.0
        for key, w in zip(order, weights):
            acc += w
            if r <= acc:
                return key
        return "pham"

    def list_owned(self, user_id: str) -> list[dict]:
        out = []
        for row in self.repo.list_pets(user_id):
            meta = self._by_id.get(row["pet_id"], {})
            out.append({
                "pet_id": row["pet_id"],
                "quantity": row["quantity"],
                "name": meta.get("name", row["pet_id"]),
                "tier": meta.get("tier", "?"),
                "desc": meta.get("desc", ""),
            })
        return out

    @atomic
    def deploy(self, user_id: str, pet_id: str) -> str:
        pet_id = pet_id.strip().lower()
        if pet_id not in self._by_id:
            raise ValueError("Không có linh thú này.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if self.repo.pet_qty(user_id, pet_id) < 1:
            raise ValueError("Chưa sở hữu linh thú này.")
        slots = [p.pet1, p.pet2, p.pet3]
        if pet_id in slots:
            raise ValueError("Đã xuất chiến linh thú này.")
        for i, slot in enumerate(slots):
            if not slot:
                if i == 0:
                    p.pet1 = pet_id
                elif i == 1:
                    p.pet2 = pet_id
                else:
                    p.pet3 = pet_id
                self.repo.save(p)
                return self._by_id[pet_id]["name"]
        raise ValueError("Đã đủ 3 linh thú xuất chiến — `.thuve <ma>` để thu về.")

    @atomic
    def recall(self, user_id: str, pet_id: str) -> str:
        pet_id = pet_id.strip().lower()
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        name = self._by_id.get(pet_id, {}).get("name", pet_id)
        changed = False
        if p.pet1 == pet_id:
            p.pet1 = ""
            changed = True
        if p.pet2 == pet_id:
            p.pet2 = ""
            changed = True
        if p.pet3 == pet_id:
            p.pet3 = ""
            changed = True
        if not changed:
            raise ValueError("Linh thú này không đang xuất chiến.")
        self.repo.save(p)
        return name
