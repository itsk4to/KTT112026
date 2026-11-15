"""Bí cảnh — 2 zone đầu theo GDD."""
from __future__ import annotations

import random
import time
from typing import Any

from ktt112026.game.content.loader import load_herbs, load_zones
from ktt112026.game.content.realms import dual_requirement_label, stage_requirement
from ktt112026.game.repo.players import PlayerRepository

COOLDOWN = 8.0


class ExplorationService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self.zones = {z["id"]: z for z in load_zones()}
        self.herbs = {h["id"]: h for h in load_herbs()}

    def list_zones(self) -> list[dict]:
        out = []
        for z in load_zones():
            out.append({
                **z,
                "req_label": dual_requirement_label(int(z["major_min"]), int(z.get("stage_min", 0))),
            })
        return out

    def explore(self, user_id: str, zone_id: str | None = None) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        now = time.time()
        if now - float(p.last_bicanh_at or 0) < COOLDOWN:
            raise ValueError(f"Đang điều tức sau bí cảnh — còn {COOLDOWN - (now - p.last_bicanh_at):.1f}s.")

        if not zone_id:
            # auto pick highest unlocked
            candidates = [z for z in load_zones() if p.major_realm >= int(z["major_min"])]
            if not candidates:
                raise ValueError("Chưa mở khu vực nào.")
            zone = candidates[-1]
        else:
            zone = self.zones.get(zone_id.strip().lower())
            if zone is None:
                raise ValueError("Khu không tồn tại. `.bicanh` hoặc `.bicanh linh_cuc|huyen_lam`.")
            if p.major_realm < int(zone["major_min"]):
                req = dual_requirement_label(int(zone["major_min"]), int(zone.get("stage_min", 0)))
                raise ValueError(f"Cảnh giới chưa đủ. Yêu cầu: {req}")

        cost = int(zone["stamina_cost"])
        if p.stamina < cost:
            raise ValueError("Thể lực không đủ.")
        p.stamina -= cost
        p.last_bicanh_at = now

        lo_s, hi_s = zone["reward_stones"]
        lo_c, hi_c = zone["reward_cultivation"]
        # khí vận mildly boosts
        luck = p.stats.khi_van
        stones = int(self.rng.randint(lo_s, hi_s) * (1 + luck / 400))
        cult = int(self.rng.randint(lo_c, hi_c) * (1 + luck / 400))
        # tantu bonus from GDD +30% khí vận feel -> +10% rewards
        if p.faction == "tantu":
            stones = int(stones * 1.1)
            cult = int(cult * 1.1)

        need = stage_requirement(p.major_realm, p.minor_stage)
        p.spirit_stones += stones
        gained_c = min(need - p.cultivation, cult) if p.cultivation < need else 0
        # allow cult even at full minor if not hau max - still cap
        p.cultivation = min(need, p.cultivation + cult)

        herb_got = None
        if self.rng.random() < float(zone.get("herb_chance", 0.3)):
            herb_id = self.rng.choice(list(zone.get("herbs") or ["linhthao"]))
            self.repo.inventory_add(user_id, herb_id, 1)
            herb_got = self.herbs.get(herb_id, {"id": herb_id, "name": herb_id})

        self.repo.save(p)
        return {
            "zone": zone,
            "stones": stones,
            "cultivation": cult,
            "herb": herb_got,
            "req_label": dual_requirement_label(int(zone["major_min"]), int(zone.get("stage_min", 0))),
            "stamina": p.stamina,
            "player": p,
        }
