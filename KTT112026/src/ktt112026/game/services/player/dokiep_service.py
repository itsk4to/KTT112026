"""Interactive 5-round tribulation — transparent support (Phase F)."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from ktt112026.game.content.realms import STAMINA_BY_MAJOR, realm_display, stage_requirement
from ktt112026.game.rules.breakthrough import (
    pick_removed_wrong,
    shield_charges,
    wrong_option_removal_chance,
)
from ktt112026.game.repo.players import PlayerRepository

OPTIONS = (
    "Luyện khí nghênh lôi, lấy nhu khắc cương",
    "Cường hành công pháp, lấy cương chế cương",
    "Tĩnh tâm bế quan, lấy bất động ứng vạn động",
)


@dataclass
class DokiepSession:
    user_id: str
    round_index: int = 0
    shields: int = 3
    correct: list[int] = field(default_factory=list)
    # per round: list of removed option indices
    removed: list[list[int]] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    fail_loss_pct: int = 20
    first_miss_immune: bool = False
    finished: bool = False
    success: bool = False
    started_at: float = field(default_factory=time.time)

    def visible_options(self) -> list[tuple[int, str]]:
        """List of (original_index, text) still visible this round."""
        rm = set(self.removed[self.round_index]) if self.round_index < len(self.removed) else set()
        return [(i, OPTIONS[i]) for i in range(3) if i not in rm]

    def prompt(self) -> dict:
        vis = self.visible_options()
        return {
            "round": self.round_index + 1,
            "total": 5,
            "shields": self.shields,
            "options": [t for _, t in vis],
            "option_indices": [i for i, _ in vis],
            "hints": list(self.hints),
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
        if not p.path:
            raise ValueError("Cần `.chon tien` hoặc `.chon ma` trước khi Độ Kiếp.")
        if p.major_realm >= 6 and p.minor_stage >= 2:
            raise ValueError("Đã ở đỉnh phong Đại Cảnh Giới cao nhất.")
        if str(user_id) in self._sessions and not self._sessions[str(user_id)].finished:
            raise ValueError("Đang trong Lôi Kiếp — chọn nút tương ứng.")

        shields = shield_charges(p.stats.can_cot)
        hints: list[str] = []
        if p.stats.can_cot >= 70:
            hints.append("Căn Cốt ≥ 70: +1 Hộ Thể (4 thanh).")

        # Đạo Lữ +1 shield
        if p.partner_id:
            partner = self.repo.get(p.partner_id)
            if partner and partner.partner_id == str(user_id):
                shields += 1
                hints.append(f"Đạo Lữ {partner.display_name} hộ pháp: +1 Hộ Thể.")

        # Buffs from .dung (stored on player)
        extra_shield = int(getattr(p, "dokiep_extra_shield", 0) or 0)
        remove_wrong = int(getattr(p, "dokiep_remove_wrong", 0) or 0)
        fail_pct = int(getattr(p, "dokiep_fail_loss_pct", 20) or 20)
        first_immune = bool(getattr(p, "dokiep_first_immune", 0) or 0)
        if extra_shield:
            shields = min(5, shields + extra_shield)
            hints.append(f"Đan dược: +{extra_shield} Hộ Thể.")
        if remove_wrong:
            hints.append(f"Đan dược: loại {remove_wrong} đáp án sai / vòng.")
        if first_immune:
            hints.append("Đan dược: miễn lần sai đầu + khiên.")
        if fail_pct < 20:
            hints.append(f"Đan dược: thất bại chỉ mất {fail_pct}% Tu Vi.")

        # Khí Vận: chance to remove 1 wrong globally per round
        kv_chance = wrong_option_removal_chance(p.stats.khi_van)
        if kv_chance > 0.05:
            hints.append(f"Khí Vận {p.stats.khi_van}: ~{kv_chance*100:.0f}% loại 1 đáp án sai mỗi vòng.")

        correct = [self.rng.randint(0, 2) for _ in range(5)]
        removed: list[list[int]] = []
        for c in correct:
            n_remove = remove_wrong
            if self.rng.random() < kv_chance:
                n_remove += 1
            n_remove = min(2, n_remove)  # always leave at least 1 option
            removed.append(pick_removed_wrong(c, n_remove, self.rng))

        # clear one-shot buffs
        p.dokiep_extra_shield = 0
        p.dokiep_remove_wrong = 0
        p.dokiep_fail_loss_pct = 20
        p.dokiep_first_immune = 0
        self.repo.save(p)

        sess = DokiepSession(
            user_id=str(user_id),
            shields=shields,
            correct=correct,
            removed=removed,
            hints=hints,
            fail_loss_pct=fail_pct,
            first_miss_immune=first_immune,
        )
        self._sessions[str(user_id)] = sess
        return sess

    def choose(self, user_id: str, choice: int) -> dict:
        """choice is visible slot 0..n-1 OR absolute option index 0..2 depending on caller."""
        sess = self._sessions.get(str(user_id))
        if sess is None or sess.finished:
            raise ValueError("Không có phiên Độ Kiếp. Gõ `.dokiep` khi đủ điều kiện.")
        vis = sess.visible_options()
        if not vis:
            raise ValueError("Không còn phương án — lỗi phiên.")
        # Map button index (0..len-1) to original option index
        if choice < 0 or choice >= len(vis):
            # also accept absolute 0..2 if still visible
            abs_map = {orig: i for i, (orig, _) in enumerate(vis)}
            if choice in abs_map:
                choice = abs_map[choice]
            else:
                raise ValueError("Phương án không hợp lệ.")
        abs_choice = vis[choice][0]
        ok = abs_choice == sess.correct[sess.round_index]
        msg_extra = ""
        if not ok:
            if sess.first_miss_immune:
                sess.first_miss_immune = False
                msg_extra = " (Đan miễn lần sai đầu!)"
            else:
                sess.shields -= 1
        if sess.shields <= 0:
            sess.finished = True
            sess.success = False
            self._apply_fail(user_id, sess.fail_loss_pct)
            return {
                "ok": False,
                "session": sess,
                "message": f"Hộ Thể vỡ — thất bại, mất {sess.fail_loss_pct}% Tu Vi.",
            }
        sess.round_index += 1
        if sess.round_index >= 5:
            sess.finished = True
            sess.success = True
            realm = self._apply_success(user_id)
            return {"ok": True, "session": sess, "message": f"Độ Kiếp thành công! Tiến tới {realm}."}
        base = ("Hộ pháp đúng." if ok else f"Sai — còn {sess.shields} Hộ Thể.{msg_extra}")
        # transparency: mention removals this next round
        nxt = sess.removed[sess.round_index] if sess.round_index < len(sess.removed) else []
        if nxt:
            base += f" | Vòng sau đã loại {len(nxt)} đáp án sai."
        return {
            "ok": ok,
            "session": sess,
            "message": base + f" Vòng {sess.round_index + 1}/5.",
        }

    def _apply_fail(self, user_id: str, loss_pct: int = 20) -> None:
        p = self.repo.get(str(user_id))
        if not p:
            return
        p.cultivation = int(p.cultivation * (1 - max(5, min(50, loss_pct)) / 100.0))
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
            p.stats.can_cot = min(200, p.stats.can_cot + 1)
            p.stats.ngo_tinh = min(200, p.stats.ngo_tinh + 1)
        self.repo.save(p)
        self._sessions.pop(str(user_id), None)
        return realm_display(p.major_realm, p.minor_stage, p.path)
