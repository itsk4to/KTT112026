"""Đạo lữ + song tu (1 lần / 24h)."""
from __future__ import annotations

import time

from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.repo.players import PlayerRepository

SONGTU_COOLDOWN = 24 * 3600
SONGTU_BONUS_PCT = 15
SONGTU_STAMINA = 5


class PartnerService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def bind(self, user_id: str, partner_id: str) -> dict:
        if str(user_id) == str(partner_id):
            raise ValueError("Không thể kết duyên với chính mình.")
        a = self.repo.get(str(user_id))
        b = self.repo.get(str(partner_id))
        if a is None:
            raise ValueError("Bạn chưa có thể đạo.")
        if b is None:
            raise ValueError("Đối phương chưa tạo thể đạo.")
        if a.partner_id:
            raise ValueError("Bạn đã có Đạo Lữ.")
        if b.partner_id:
            raise ValueError("Đối phương đã có Đạo Lữ.")
        a.partner_id = str(partner_id)
        b.partner_id = str(user_id)
        self.repo.save(a)
        self.repo.save(b)
        return {"partner_name": b.display_name, "partner_id": b.user_id}

    def unbind(self, user_id: str) -> dict:
        a = self.repo.get(str(user_id))
        if a is None:
            raise ValueError("Chưa có thể đạo.")
        if not a.partner_id:
            raise ValueError("Chưa kết duyên.")
        b = self.repo.get(a.partner_id)
        pid = a.partner_id
        a.partner_id = ""
        self.repo.save(a)
        if b and b.partner_id == str(user_id):
            b.partner_id = ""
            self.repo.save(b)
        return {"was_partner": pid}

    def songtu(self, user_id: str) -> dict:
        a = self.repo.get(str(user_id))
        if a is None:
            raise ValueError("Chưa có thể đạo.")
        if not a.partner_id:
            raise ValueError("Chưa có Đạo Lữ — `.ketduyen @user`.")
        b = self.repo.get(a.partner_id)
        if b is None or b.partner_id != str(user_id):
            raise ValueError("Quan hệ Đạo Lữ không còn hiệu lực.")
        now = time.time()
        left_a = SONGTU_COOLDOWN - (now - float(a.last_songtu_at or 0))
        left_b = SONGTU_COOLDOWN - (now - float(b.last_songtu_at or 0))
        if left_a > 0:
            raise ValueError(f"Bạn còn {left_a/3600:.1f}h mới `.songtu` lại.")
        if left_b > 0:
            raise ValueError(f"Đạo Lữ còn {left_b/3600:.1f}h mới song tu lại.")
        if a.stamina < SONGTU_STAMINA or b.stamina < SONGTU_STAMINA:
            raise ValueError("Cả hai cần đủ thể lực.")

        def apply(p):
            from ktt112026.game.rules.cultivation import cultivation_gain as cg
            need = stage_requirement(p.major_realm, p.minor_stage)
            gain = cg(ngo_tinh=p.stats.ngo_tinh, root_quality=p.root_quality, major_realm=p.major_realm)
            gain = int(gain * (1 + SONGTU_BONUS_PCT / 100.0) * 3)  # session-like chunk
            p.cultivation = min(need, p.cultivation + gain)
            p.stamina -= SONGTU_STAMINA
            p.last_songtu_at = now
            return gain

        ga = apply(a)
        gb = apply(b)
        self.repo.save(a)
        self.repo.save(b)
        return {
            "partner_name": b.display_name,
            "gain_self": ga,
            "gain_partner": gb,
            "bonus_pct": SONGTU_BONUS_PCT,
        }
