"""Bí cảnh — zones + random events."""
from __future__ import annotations

import random
import time
from typing import Any

from ktt112026.game.content.loader import load_herbs, load_zones
from ktt112026.game.content.realms import dual_requirement_label, stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player.stats_service import StatsService

COOLDOWN = 8.0

# weighted events
EVENTS = [
    ("calm", 40, "Hành trình êm đềm"),
    ("herb_cache", 18, "Phát hiện đám thảo dược"),
    ("stone_vein", 15, "Mạch linh thạch lộ thiên"),
    ("insight", 12, "Ngộ được đạo lý khi quan sát thiên địa"),
    ("ambush", 10, "Gặp tu sĩ/yêu thú phục kích"),
    ("ancient_box", 5, "Mở được cổ hũ bị phong ấn"),
    ("boss_lair", 0, "Gặp Thủ Hộ Bí Cảnh"),  # weight injected by zone
]


class ExplorationService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self.zones = {z["id"]: z for z in load_zones()}
        self.herbs = {h["id"]: h for h in load_herbs()}
        self.stats = StatsService(repo)

    def list_zones(self) -> list[dict]:
        out = []
        for z in load_zones():
            out.append({
                **z,
                "req_label": dual_requirement_label(int(z["major_min"]), int(z.get("stage_min", 0))),
            })
        return out

    def _pick_event(self) -> tuple[str, str]:
        total = sum(w for _, w, _ in EVENTS)
        roll = self.rng.uniform(0, total)
        acc = 0.0
        for eid, w, label in EVENTS:
            acc += w
            if roll <= acc:
                return eid, label
        return EVENTS[0][0], EVENTS[0][2]

    def explore(self, user_id: str, zone_id: str | None = None) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        now = time.time()
        if now - float(p.last_bicanh_at or 0) < COOLDOWN:
            left = COOLDOWN - (now - float(p.last_bicanh_at or 0))
            raise ValueError(f"Đang điều tức sau bí cảnh — còn {left:.1f}s.")

        if not zone_id:
            candidates = [
                z for z in load_zones()
                if p.major_realm > int(z["major_min"])
                or (p.major_realm == int(z["major_min"]) and p.minor_stage >= int(z.get("stage_min", 0)))
            ]
            if not candidates:
                raise ValueError("Chưa mở khu vực nào.")
            zone = candidates[-1]
        else:
            zone = self.zones.get(zone_id.strip().lower())
            if zone is None:
                ids = "/".join(z["id"] for z in load_zones())
                raise ValueError(f"Khu không tồn tại. `.bicanh` hoặc `.bicanh {ids}`")
            need_major = int(zone["major_min"])
            need_stage = int(zone.get("stage_min", 0))
            if p.major_realm < need_major or (
                p.major_realm == need_major and p.minor_stage < need_stage
            ):
                req = dual_requirement_label(need_major, need_stage)
                raise ValueError(f"Cảnh giới chưa đủ. Yêu cầu: {req}")

        cost = int(zone["stamina_cost"])
        if p.stamina < cost:
            raise ValueError("Thể lực không đủ.")
        p.stamina -= cost
        p.last_bicanh_at = now

        lo_s, hi_s = zone["reward_stones"]
        lo_c, hi_c = zone["reward_cultivation"]
        luck = p.stats.khi_van
        stones = int(self.rng.randint(lo_s, hi_s) * (1 + luck / 400))
        cult = int(self.rng.randint(lo_c, hi_c) * (1 + luck / 400))

        path_bonus = zone.get("path_bonus")
        if path_bonus and p.path == path_bonus:
            stones = int(stones * 1.15)
            cult = int(cult * 1.15)

        if p.faction == "tantu":
            stones = int(stones * 1.08)

        event_id, event_label = self._pick_event()
        # high zone: chance to force boss encounter
        if int(zone["major_min"]) >= 3 and self.rng.random() < 0.12:
            event_id, event_label = "boss_lair", "Gặp Thủ Hộ Bí Cảnh"
        event_notes: list[str] = [event_label]
        herbs_got: list[tuple[str, int]] = []
        power = int(self.stats.effective(user_id)["power"])

        if event_id == "herb_cache":
            pool = list(zone.get("herbs") or [])
            if pool:
                for _ in range(self.rng.randint(1, 3)):
                    hid = self.rng.choice(pool)
                    herbs_got.append((hid, 1))
                event_notes.append("Nhặt thêm thảo dược.")
        elif event_id == "stone_vein":
            bonus = int(stones * 0.5) + self.rng.randint(10, 40)
            stones += bonus
            event_notes.append(f"+{bonus} LS mạch đá.")
        elif event_id == "insight":
            bonus = int(cult * 0.4) + 20
            cult += bonus
            event_notes.append(f"+{bonus} Tu Vi ngộ đạo.")
        elif event_id == "ambush":
            # combat_power vs zone threat
            threat = 80 + int(zone["major_min"]) * 40 + int(zone.get("stage_min", 0)) * 15
            win_chance = min(0.92, max(0.25, 0.45 + (power - threat) / 400))
            if self.rng.random() <= win_chance:
                stones = int(stones * 1.35)
                cult = int(cult * 1.2)
                event_notes.append(f"Phá phục kích (LC {power} vs {threat}).")
            else:
                stones = int(stones * 0.4)
                cult = int(cult * 0.5)
                loss_sta = min(p.stamina, 5)
                p.stamina -= loss_sta
                event_notes.append(f"Bị thương — mất bớt phần thưởng và {loss_sta} TL.")
        elif event_id == "ancient_box":
            stones += self.rng.randint(50, 150) * int(zone["major_min"])
            if zone.get("herbs"):
                hid = self.rng.choice(list(zone["herbs"]))
                herbs_got.append((hid, self.rng.randint(1, 2)))
            event_notes.append("Cổ hũ: phần thưởng hiếm.")

        # base herb roll
        if self.rng.random() < float(zone.get("herb_chance", 0.2)):
            pool = list(zone.get("herbs") or [])
            if pool:
                herbs_got.append((self.rng.choice(pool), 1))

        need = stage_requirement(p.major_realm, p.minor_stage)
        room = max(0, need - p.cultivation)
        cult_applied = min(cult, room) if room > 0 else 0
        # if bar full, still give stones but note lock
        p.cultivation = min(need, p.cultivation + cult_applied)
        p.spirit_stones += stones

        for hid, qty in herbs_got:
            self.repo.inventory_add(user_id, hid, qty)

        self.repo.save(p)
        herb_summary = ", ".join(f"{h}x{q}" for h, q in herbs_got) if herbs_got else "—"
        locked = p.cultivation >= need
        return {
            "zone": zone,
            "stones": stones,
            "cultivation": cult_applied,
            "cult_raw": cult,
            "herbs": herbs_got,
            "herb_summary": herb_summary,
            "event": event_id,
            "event_notes": event_notes,
            "stamina": p.stamina,
            "locked": locked,
            "power": power,
            "player": p,
        }
