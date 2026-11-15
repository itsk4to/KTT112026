"""Interactive 5-round tribulation (.dokiep)."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from ktt112026.game.content.realms import STAMINA_BY_MAJOR, realm_display, stage_requirement
from ktt112026.game.rules.breakthrough import shield_charges
from ktt112026.game.repo.players import PlayerRepository

OPTIONS = (
    "Luyện khí nghênh lôi, lấy nhu khắc cương",
    "Cường hành công pháp, lấy cương chế cương",
    "Tĩnh tâm bế quan, lấy bất động ứng vạn động",
)


@dataclass
class DokiepSession:
    user_id: str
    round_index: int = 0  # 0..4
    shields: int = 3
    correct: list[int] = field(default_factory=list)
    finished: bool = False
    success: bool = False
    started_at: float = field(default_factory=time.time)

    def prompt(self) -> dict:
        return {
            "round": self.round_index + 1,
            "total": 5,
            "shields": self.shields,
            "options": list(OPTIONS),
            "finished": self.finished,
            "success": self.success,
        }


class DokiepService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self._sessions: dict[str, DokiepSession] = {}

    def start(self, user_id: str) -> DokiepSession:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        need = stage_requirement(p.major_realm, p.minor_stage)
        if p.minor_stage < 2 or p.cultivation < need:
            raise ValueError("Cần Hậu Kỳ 100% tu vi mới Độ Kiếp.")
        if p.major_realm >= 6 and p.minor_stage >= 2:
            raise ValueError("Đã ở đỉnh phong Đại Cảnh Giới cao nhất.")
        if str(user_id) in self._sessions and not self._sessions[str(user_id)].finished:
            raise ValueError("Đang trong Lôi Kiếp — chọn nút 1 / 2 / 3.")
        shields = shield_charges(p.stats.can_cot)
        # Khí Vận mildly helps by pre-rolling less brutal — still 1 correct/round
        correct = [self.rng.randint(0, 2) for _ in range(5)]
        sess = DokiepSession(user_id=str(user_id), shields=shields, correct=correct)
        self._sessions[str(user_id)] = sess
        return sess

    def choose(self, user_id: str, choice: int) -> dict:
        sess = self._sessions.get(str(user_id))
        if sess is None or sess.finished:
            raise ValueError("Không có phiên Độ Kiếp. Gõ `.dokiep` khi đủ điều kiện.")
        if choice not in (0, 1, 2):
            raise ValueError("Chọn 1, 2 hoặc 3.")
        ok = choice == sess.correct[sess.round_index]
        if not ok:
            sess.shields -= 1
        if sess.shields <= 0:
            sess.finished = True
            sess.success = False
            self._apply_fail(user_id)
            return {"ok": False, "session": sess, "message": "Hộ Thể vỡ — Độ Kiếp thất bại, mất 20% Tu Vi."}
        sess.round_index += 1
        if sess.round_index >= 5:
            sess.finished = True
            sess.success = True
            realm = self._apply_success(user_id)
            return {"ok": True, "session": sess, "message": f"Độ Kiếp thành công! Tiến tới {realm}."}
        return {
            "ok": ok,
            "session": sess,
            "message": ("Hộ pháp đúng." if ok else f"Sai — còn {sess.shields} Hộ Thể.") + f" Vòng {sess.round_index + 1}/5.",
        }

    def _apply_fail(self, user_id: str) -> None:
        p = self.repo.get(str(user_id))
        if not p:
            return
        p.cultivation = int(p.cultivation * 0.8)
        self.repo.save(p)
        self._sessions.pop(str(user_id), None)

    def _apply_success(self, user_id: str) -> str:
        p = self.repo.get(str(user_id))
        if not p:
            return "?"
        if p.major_realm < 6:
            p.major_realm += 1
            p.minor_stage = 0
            p.cultivation = 0
            p.max_stamina = STAMINA_BY_MAJOR.get(p.major_realm, p.max_stamina)
            p.stamina = p.max_stamina
            # small permanent bonus
            p.stats.can_cot = min(200, p.stats.can_cot + 1)
            p.stats.ngo_tinh = min(200, p.stats.ngo_tinh + 1)
        self.repo.save(p)
        self._sessions.pop(str(user_id), None)
        return realm_display(p.major_realm, p.minor_stage, p.path)
