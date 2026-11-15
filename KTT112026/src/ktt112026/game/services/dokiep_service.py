"""Độ Kiếp 5 vòng (.dokiep) — minh bạch hỗ trợ: Khí Vận, đan dược, Căn Cốt, Đạo Lữ."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from ktt112026.game.content.realms import STAMINA_BY_MAJOR, realm_display, stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.rules.breakthrough import (
    DOKIEP_FAIL_LOSS_PCT,
    shield_charges,
    wrong_option_removal_chance,
)
from ktt112026.game.services._tx import atomic

OPTIONS = (
    "Luyện khí nghênh lôi, lấy nhu khắc cương",
    "Cường hành công pháp, lấy cương chế cương",
    "Tĩnh tâm bế quan, lấy bất động ứng vạn động",
)
ROUNDS = 5


@dataclass
class DokiepSession:
    user_id: str
    round_index: int = 0  # 0..4
    shields: int = 3
    correct: list[int] = field(default_factory=list)
    # hints[r] = {"removed": [idx...], "notes": [str...]} — tính sẵn lúc bắt đầu
    hints: list[dict] = field(default_factory=list)
    fail_loss_pct: int = DOKIEP_FAIL_LOSS_PCT
    damage_reduce_pct: int = 0
    first_miss_immune: bool = False
    support_notes: list[str] = field(default_factory=list)  # Hộ Thể từ Căn Cốt / Đạo Lữ / đan
    finished: bool = False
    success: bool = False
    started_at: float = field(default_factory=time.time)

    def current_hint(self) -> dict:
        if 0 <= self.round_index < len(self.hints):
            return self.hints[self.round_index]
        return {"removed": [], "notes": []}

    def prompt(self) -> dict:
        hint = self.current_hint()
        return {
            "round": self.round_index + 1,
            "total": ROUNDS,
            "shields": self.shields,
            "options": list(OPTIONS),
            "removed": list(hint["removed"]),
            "notes": list(hint["notes"]),
            "support_notes": list(self.support_notes),
            "finished": self.finished,
            "success": self.success,
        }


class DokiepService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self._sessions: dict[str, DokiepSession] = {}

    def session(self, user_id: str) -> DokiepSession | None:
        return self._sessions.get(str(user_id))

    @atomic
    def start(self, user_id: str) -> DokiepSession:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        need = stage_requirement(p.major_realm, p.minor_stage)
        if p.minor_stage < 2 or p.cultivation < need:
            raise ValueError("Cần Hậu Kỳ 100% tu vi mới Độ Kiếp.")
        if p.major_realm >= 6 and p.minor_stage >= 2:
            raise ValueError("Đã ở đỉnh phong Đại Cảnh Giới cao nhất.")
        if not p.path:
            raise ValueError("Hãy chọn đạo lộ trước khi Độ Kiếp: `.chon tien` hoặc `.chon ma`.")
        old = self._sessions.get(str(user_id))
        if old is not None and not old.finished:
            raise ValueError("Đang trong Lôi Kiếp — chọn nút 1 / 2 / 3.")

        buffs = self.repo.buff_list(str(user_id), "dokiep_")
        self.repo.buff_clear(str(user_id), "dokiep_")  # đan chỉ có hiệu lực một lần Độ Kiếp

        # --- Hộ Thể ---
        support: list[str] = []
        base = shield_charges(p.stats.can_cot)
        if base > 3:
            support.append(f"Căn Cốt {p.stats.can_cot} mở khóa {base} thanh Hộ Thể.")
        shields = base
        partner = self.repo.get(p.partner_id) if p.partner_id else None
        if partner is not None and partner.partner_id == p.user_id:
            shields += 1
            support.append(f"Đạo Lữ {partner.display_name} truyền công: +1 Hộ Thể.")
        pill = buffs.get("dokiep_shield_bonus")
        if pill:
            cap = int(pill.get("max_shields", 5))
            boosted = min(cap, shields + int(pill.get("amount", 1)))
            if boosted > shields:
                support.append("Ngưng Thần Hộ Mạch Đan: +%d Hộ Thể." % (boosted - shields))
                shields = boosted
        kim = buffs.get("dokiep_first_miss_immune_and_shield")
        if kim:
            shields += int(kim.get("shield", 1))
            support.append("Bất Diệt Kim Thân Đan: +%d Hộ Thể, miễn nhiễm lần sai đầu." % int(kim.get("shield", 1)))

        sess = DokiepSession(
            user_id=str(user_id),
            shields=shields,
            correct=[self.rng.randint(0, 2) for _ in range(ROUNDS)],
            support_notes=support,
            first_miss_immune=bool(kim),
        )
        hotam = buffs.get("dokiep_damage_reduce_pct")
        if hotam:
            sess.damage_reduce_pct = int(hotam.get("amount", 0))
            support.append(f"Hộ Tâm Đan: {sess.damage_reduce_pct}% cơ hội hóa giải một lần sai.")
        hoan = buffs.get("dokiep_fail_loss_pct")
        if hoan:
            sess.fail_loss_pct = min(DOKIEP_FAIL_LOSS_PCT, int(hoan.get("amount", DOKIEP_FAIL_LOSS_PCT)))
            support.append(f"Cửu Chuyển Hoàn Hồn Đan: nếu thất bại chỉ mất {sess.fail_loss_pct}% Tu Vi.")

        # --- Loại đáp án sai từng vòng ---
        tilo = buffs.get("dokiep_remove_wrong")
        tilo_rounds = {int(r) - 1 for r in tilo.get("rounds", [])} if tilo else set()
        phachuong = buffs.get("dokiep_remove_wrong_all_rounds")
        luck_chance = wrong_option_removal_chance(p.stats.khi_van)
        for r in range(ROUNDS):
            removed: list[int] = []
            notes: list[str] = []

            def remove_one() -> int | None:
                wrong = [i for i in range(3) if i != sess.correct[r] and i not in removed]
                if not wrong:
                    return None
                pick = self.rng.choice(wrong)
                removed.append(pick)
                return pick

            if phachuong:
                if remove_one() is not None:
                    notes.append("Thiên Kiếp Phá Chướng Đan đã vô hiệu hóa 1 phương án sai!")
            if r in tilo_rounds:
                if remove_one() is not None:
                    notes.append("Tị Lôi Đan đã vô hiệu hóa 1 phương án sai!")
            if len(removed) < 2 and self.rng.random() < luck_chance:
                pick = remove_one()
                if pick is not None:
                    notes.append(f"Khí Vận cao đã giúp bạn loại bỏ đáp án .{pick + 1}!")
            sess.hints.append({"removed": sorted(removed), "notes": notes})

        self._sessions[str(user_id)] = sess
        return sess

    @atomic
    def choose(self, user_id: str, choice: int) -> dict:
        sess = self._sessions.get(str(user_id))
        if sess is None or sess.finished:
            raise ValueError("Không có phiên Độ Kiếp. Gõ `.dokiep` khi đủ điều kiện.")
        if choice not in (0, 1, 2):
            raise ValueError("Chọn 1, 2 hoặc 3.")
        if choice in sess.current_hint()["removed"]:
            raise ValueError(f"Phương án .{choice + 1} đã bị loại ở vòng này.")
        ok = choice == sess.correct[sess.round_index]
        absorbed = ""
        if not ok:
            if sess.first_miss_immune:
                sess.first_miss_immune = False
                absorbed = "Kim Thân Đan hóa giải lần sai đầu — không mất Hộ Thể."
            elif sess.damage_reduce_pct and self.rng.random() * 100 < sess.damage_reduce_pct:
                sess.damage_reduce_pct = 0
                absorbed = "Hộ Tâm Đan hóa giải — không mất Hộ Thể."
            else:
                sess.shields -= 1
        if sess.shields <= 0:
            sess.finished = True
            sess.success = False
            self._apply_fail(user_id, sess.fail_loss_pct)
            return {
                "ok": False, "session": sess,
                "message": f"Hộ Thể vỡ — Độ Kiếp thất bại, mất {sess.fail_loss_pct}% Tu Vi.",
            }
        sess.round_index += 1
        if sess.round_index >= ROUNDS:
            sess.finished = True
            sess.success = True
            realm = self._apply_success(user_id)
            return {"ok": True, "session": sess, "message": f"Độ Kiếp thành công! Tiến tới {realm}."}
        head = "Hộ pháp đúng." if ok else (absorbed or f"Sai — còn {sess.shields} Hộ Thể.")
        return {
            "ok": ok,
            "session": sess,
            "message": f"{head} Vòng {sess.round_index + 1}/{ROUNDS}.",
        }

    def _apply_fail(self, user_id: str, loss_pct: int) -> None:
        p = self.repo.get(str(user_id))
        if not p:
            return
        p.cultivation = int(p.cultivation * (100 - loss_pct) / 100)
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
