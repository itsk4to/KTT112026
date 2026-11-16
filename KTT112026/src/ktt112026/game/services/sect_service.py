"""Hệ thống Tông Môn — cộng đồng, cấp tông, mời/kick, quà tuần."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ktt112026.game.content.loader import load_sects
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num

# Tổng cống hiến cả tông để lên cấp
LEVEL_THRESHOLDS = [0, 5_000, 20_000, 50_000, 120_000, 250_000, 500_000, 1_000_000]
# Quà top cống hiến cá nhân trong tuần (toàn server theo sect_contrib tuần — dùng total contrib rank)
WEEKLY_REWARDS = {1: 3000, 2: 1800, 3: 1000}
INVITE_TTL = 48 * 3600
MAX_MEMBERS_BASE = 15


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _level_from_contrib(total: int) -> int:
    lvl = 1
    for i, need in enumerate(LEVEL_THRESHOLDS):
        if total >= need:
            lvl = i + 1
    return min(lvl, len(LEVEL_THRESHOLDS))


class SectService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self.sects = {s["id"]: s for s in load_sects()}

    def _ensure_state(self, sect_id: str) -> dict[str, Any]:
        row = self.repo.db.fetchone("SELECT * FROM sect_state WHERE sect_id=?", (sect_id,))
        if row:
            return dict(row)
        self.repo.db.execute(
            "INSERT INTO sect_state(sect_id, level, bank_stones, leader_id, last_weekly_key) VALUES(?,?,?,?,?)",
            (sect_id, 1, 0, "", ""),
        )
        self.repo.db.commit()
        return {
            "sect_id": sect_id,
            "level": 1,
            "bank_stones": 0,
            "leader_id": "",
            "last_weekly_key": "",
        }

    def _total_contrib(self, sect_id: str) -> int:
        r = self.repo.db.fetchone(
            "SELECT COALESCE(SUM(sect_contrib),0) AS t FROM players WHERE sect_id=?",
            (sect_id,),
        )
        return int(r["t"]) if r else 0

    def _member_count(self, sect_id: str) -> int:
        r = self.repo.db.fetchone(
            "SELECT COUNT(*) AS c FROM players WHERE sect_id=?",
            (sect_id,),
        )
        return int(r["c"]) if r else 0

    def _max_members(self, level: int) -> int:
        return MAX_MEMBERS_BASE + max(0, level - 1) * 3

    def _refresh_level(self, sect_id: str) -> int:
        st = self._ensure_state(sect_id)
        total = self._total_contrib(sect_id) + int(st.get("bank_stones") or 0)
        lvl = _level_from_contrib(total)
        if int(st.get("level") or 1) != lvl:
            self.repo.db.execute(
                "UPDATE sect_state SET level=? WHERE sect_id=?",
                (lvl, sect_id),
            )
            self.repo.db.commit()
        return lvl

    def _is_officer(self, p) -> bool:
        return (p.sect_role or "") in ("leader", "elder")

    def list_sects(self) -> list[dict]:
        out = []
        for s in load_sects():
            st = self._ensure_state(s["id"])
            lvl = self._refresh_level(s["id"])
            out.append({
                **s,
                "members": self._member_count(s["id"]),
                "contrib": self._total_contrib(s["id"]),
                "level": lvl,
                "max_members": self._max_members(lvl),
                "leader_id": st.get("leader_id") or "",
            })
        return out

    def join(self, user_id: str, sect_id: str) -> dict[str, Any]:
        sect_id = (sect_id or "").strip().lower()
        sect = self.sects.get(sect_id)
        if not sect:
            raise ValueError("Không có tông môn này. Dùng `.tongmon` để xem danh sách.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        if not p.path:
            raise ValueError("Hãy `.chon tien` hoặc `.chon ma` trước.")
        if p.major_realm < int(sect.get("major_min", 2)):
            raise ValueError(f"Cần đại cảnh giới cấp {sect['major_min']}+.")
        if p.faction != "tongmon":
            raise ValueError("Cần `.gianhap tongmon` trước khi vào tông.")
        if p.sect_id:
            raise ValueError("Đã ở trong tông môn. Dùng `.tongmon roi` hoặc nhận lời mời khác.")
        sp = sect.get("path", "any")
        if sp in ("tien", "ma") and p.path != sp:
            raise ValueError("Tông môn không khớp Đạo Lộ của đạo hữu.")
        lvl = self._refresh_level(sect_id)
        if self._member_count(sect_id) >= self._max_members(lvl):
            raise ValueError(f"Tông đã đủ người (tối đa {self._max_members(lvl)} ở cấp {lvl}).")
        st = self._ensure_state(sect_id)
        role = "leader" if not st.get("leader_id") and self._member_count(sect_id) == 0 else "member"
        p.sect_id = sect_id
        p.sect_joined_at = time.time()
        p.sect_role = role
        if p.sect_contrib < 0:
            p.sect_contrib = 0
        self.repo.save(p)
        if role == "leader":
            self.repo.db.execute(
                "UPDATE sect_state SET leader_id=? WHERE sect_id=?",
                (str(user_id), sect_id),
            )
            self.repo.db.commit()
        return {"sect": sect, "player": p, "role": role, "level": lvl}

    def join_via_invite(self, user_id: str, sect_id: str | None = None) -> dict[str, Any]:
        """Nhận lời mời đang chờ."""
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if p.sect_id:
            raise ValueError("Đã có tông môn.")
        now = int(time.time())
        if sect_id:
            row = self.repo.db.fetchone(
                "SELECT * FROM sect_invites WHERE invitee_id=? AND sect_id=?",
                (str(user_id), sect_id.strip().lower()),
            )
        else:
            row = self.repo.db.fetchone(
                "SELECT * FROM sect_invites WHERE invitee_id=? ORDER BY created_at DESC LIMIT 1",
                (str(user_id),),
            )
        if not row:
            raise ValueError("Không có lời mời nào. Nhờ thành viên `.tongmon moi @bạn`.")
        if now - int(row["created_at"]) > INVITE_TTL:
            self.repo.db.execute(
                "DELETE FROM sect_invites WHERE sect_id=? AND invitee_id=?",
                (row["sect_id"], str(user_id)),
            )
            self.repo.db.commit()
            raise ValueError("Lời mời đã hết hạn (48 giờ).")
        # clear invites then join
        sid = str(row["sect_id"])
        self.repo.db.execute("DELETE FROM sect_invites WHERE invitee_id=?", (str(user_id),))
        self.repo.db.commit()
        return self.join(user_id, sid)

    def leave(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if not p.sect_id:
            raise ValueError("Chưa gia nhập tông môn.")
        sid = p.sect_id
        old = self.sects.get(sid, {"name": sid, "id": sid})
        was_leader = p.sect_role == "leader"
        p.sect_contrib = int(p.sect_contrib * 0.7)
        p.sect_id = ""
        p.sect_joined_at = 0.0
        p.sect_role = ""
        self.repo.save(p)
        if was_leader:
            # transfer to highest contrib member
            nxt = self.repo.db.fetchone(
                "SELECT user_id FROM players WHERE sect_id=? ORDER BY sect_contrib DESC LIMIT 1",
                (sid,),
            )
            new_leader = str(nxt["user_id"]) if nxt else ""
            if new_leader:
                np = self.repo.get(new_leader)
                if np:
                    np.sect_role = "leader"
                    self.repo.save(np)
            self.repo.db.execute(
                "UPDATE sect_state SET leader_id=? WHERE sect_id=?",
                (new_leader, sid),
            )
            self.repo.db.commit()
        return {"old": old, "player": p}

    def invite(self, inviter_id: str, invitee_id: str) -> dict[str, Any]:
        inviter = self.repo.get(str(inviter_id))
        if inviter is None:
            raise ValueError("Bạn chưa có thể đạo.")
        if not inviter.sect_id:
            raise ValueError("Bạn chưa ở trong tông môn.")
        if not self._is_officer(inviter) and inviter.sect_role != "member":
            pass  # members can invite too
        invitee = self.repo.get(str(invitee_id))
        if invitee is None:
            raise ValueError("Đối phương chưa `.taothe`.")
        if invitee.sect_id:
            raise ValueError("Đối phương đã có tông môn.")
        if invitee.faction and invitee.faction != "tongmon":
            raise ValueError("Đối phương cần `.gianhap tongmon` trước.")
        sect = self.sects.get(inviter.sect_id)
        if not sect:
            raise ValueError("Tông không hợp lệ.")
        sp = sect.get("path", "any")
        if sp in ("tien", "ma") and invitee.path and invitee.path != sp:
            raise ValueError("Đạo Lộ đối phương không khớp tông.")
        now = int(time.time())
        self.repo.db.execute(
            "INSERT OR REPLACE INTO sect_invites(sect_id, inviter_id, invitee_id, created_at) VALUES(?,?,?,?)",
            (inviter.sect_id, str(inviter_id), str(invitee_id), now),
        )
        self.repo.db.commit()
        return {
            "sect": sect,
            "inviter": inviter,
            "invitee": invitee,
            "expires_hours": INVITE_TTL // 3600,
        }

    def kick(self, actor_id: str, target_id: str) -> dict[str, Any]:
        actor = self.repo.get(str(actor_id))
        target = self.repo.get(str(target_id))
        if actor is None or target is None:
            raise ValueError("Không tìm thấy người chơi.")
        if not actor.sect_id or actor.sect_id != target.sect_id:
            raise ValueError("Hai bên không cùng tông môn.")
        if not self._is_officer(actor):
            raise ValueError("Chỉ Tông Chủ / Trưởng Lão mới kick được.")
        if target.sect_role == "leader":
            raise ValueError("Không thể kick Tông Chủ.")
        if target.sect_role == "elder" and actor.sect_role != "leader":
            raise ValueError("Chỉ Tông Chủ mới kick Trưởng Lão.")
        if str(actor_id) == str(target_id):
            raise ValueError("Không tự kick — dùng `.tongmon roi`.")
        sid = target.sect_id
        name = target.display_name
        target.sect_id = ""
        target.sect_role = ""
        target.sect_joined_at = 0.0
        target.sect_contrib = int(target.sect_contrib * 0.5)
        self.repo.save(target)
        return {"name": name, "sect_id": sid}

    def promote(self, actor_id: str, target_id: str, role: str = "elder") -> dict[str, Any]:
        role = role.strip().lower()
        if role not in ("elder", "member", "leader"):
            raise ValueError("Chức vụ: elder | member | leader")
        actor = self.repo.get(str(actor_id))
        target = self.repo.get(str(target_id))
        if not actor or not target or actor.sect_id != target.sect_id or not actor.sect_id:
            raise ValueError("Không cùng tông môn.")
        if actor.sect_role != "leader":
            raise ValueError("Chỉ Tông Chủ được bổ nhiệm.")
        if role == "leader":
            actor.sect_role = "member"
            target.sect_role = "leader"
            self.repo.save(actor)
            self.repo.save(target)
            self.repo.db.execute(
                "UPDATE sect_state SET leader_id=? WHERE sect_id=?",
                (str(target_id), actor.sect_id),
            )
            self.repo.db.commit()
            return {"name": target.display_name, "role": "leader"}
        target.sect_role = role
        self.repo.save(target)
        return {"name": target.display_name, "role": role}

    def donate(self, user_id: str, amount: int) -> dict[str, Any]:
        amount = int(amount)
        if amount < 10:
            raise ValueError("Cống hiến tối thiểu 10 Linh Thạch.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if not p.sect_id:
            raise ValueError("Chưa vào tông. `.tongmon vao <id>` hoặc `.tongmon nhan`")
        if p.spirit_stones < amount:
            raise ValueError(f"Không đủ Linh Thạch (cần {fmt_num(amount)}).")
        p.spirit_stones -= amount
        p.sect_contrib += amount
        # 20% vào ngân khố tông
        bank_add = amount // 5
        self.repo.save(p)
        st = self._ensure_state(p.sect_id)
        self.repo.db.execute(
            "UPDATE sect_state SET bank_stones = bank_stones + ? WHERE sect_id=?",
            (bank_add, p.sect_id),
        )
        self.repo.db.commit()
        lvl = self._refresh_level(p.sect_id)
        return {
            "amount": amount,
            "contrib": p.sect_contrib,
            "sect_id": p.sect_id,
            "bank_add": bank_add,
            "level": lvl,
            "player": p,
        }

    def ranking(self, user_id: str, limit: int = 10) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None or not p.sect_id:
            raise ValueError("Cần ở trong tông môn. `.tongmon`")
        sid = p.sect_id
        sect = self.sects.get(sid, {"name": sid, "id": sid})
        lvl = self._refresh_level(sid)
        rows = self.repo.db.fetchall(
            "SELECT user_id, display_name, sect_contrib, sect_role, major_realm "
            "FROM players WHERE sect_id=? ORDER BY sect_contrib DESC LIMIT ?",
            (sid, max(3, min(20, limit))),
        )
        entries = []
        for i, r in enumerate(rows, 1):
            role = str(r["sect_role"] or "member")
            role_lbl = {"leader": "Tông Chủ", "elder": "Trưởng Lão"}.get(role, "Đệ tử")
            entries.append({
                "rank": i,
                "name": str(r["display_name"]),
                "contrib": int(r["sect_contrib"] or 0),
                "contrib_fmt": fmt_num(int(r["sect_contrib"] or 0)),
                "role": role_lbl,
            })
        return {
            "sect": sect,
            "level": lvl,
            "max_members": self._max_members(lvl),
            "members": self._member_count(sid),
            "total": self._total_contrib(sid),
            "entries": entries,
        }

    def info(self, user_id: str, sect_id: str | None = None) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        sid = (sect_id or (p.sect_id if p else "") or "").strip().lower()
        if not sid:
            raise ValueError("Chưa có tông — `.tongmon` xem danh sách.")
        sect = self.sects.get(sid)
        if not sect:
            raise ValueError("Không tìm thấy tông môn.")
        st = self._ensure_state(sid)
        lvl = self._refresh_level(sid)
        members = self.repo.db.fetchall(
            "SELECT user_id, display_name, sect_contrib, sect_role, major_realm FROM players "
            "WHERE sect_id=? ORDER BY sect_contrib DESC LIMIT 10",
            (sid,),
        )
        leader = self.repo.get(str(st.get("leader_id") or ""))
        next_need = LEVEL_THRESHOLDS[lvl] if lvl < len(LEVEL_THRESHOLDS) else None
        total = self._total_contrib(sid)
        return {
            "sect": sect,
            "members": [dict(m) for m in members],
            "member_count": self._member_count(sid),
            "contrib_total": total,
            "level": lvl,
            "max_members": self._max_members(lvl),
            "bank": int(st.get("bank_stones") or 0),
            "leader_name": leader.display_name if leader else "—",
            "next_level_at": next_need,
            "player": p,
        }

    def process_weekly_rewards(self) -> dict[str, Any]:
        """Top 1–3 cống hiến toàn server (có tông) nhận quà mỗi tuần ISO — gọi khi online."""
        week = _week_key()
        # already paid?
        paid = self.repo.db.fetchone(
            "SELECT COUNT(*) AS c FROM sect_weekly_payout WHERE week_key=?",
            (week,),
        )
        if paid and int(paid["c"]) > 0:
            return {"week": week, "paid": False, "reason": "already", "winners": []}
        rows = self.repo.db.fetchall(
            "SELECT user_id, display_name, sect_contrib, sect_id FROM players "
            "WHERE sect_id != '' ORDER BY sect_contrib DESC LIMIT 3",
        )
        winners = []
        for rank, r in enumerate(rows, 1):
            reward = WEEKLY_REWARDS.get(rank, 0)
            if reward <= 0:
                continue
            uid = str(r["user_id"])
            pl = self.repo.get(uid)
            if not pl:
                continue
            pl.spirit_stones += reward
            self.repo.save(pl)
            self.repo.db.execute(
                "INSERT INTO sect_weekly_payout(week_key, user_id, rank, reward) VALUES(?,?,?,?)",
                (week, uid, rank, reward),
            )
            winners.append({
                "rank": rank,
                "user_id": uid,
                "name": str(r["display_name"]),
                "reward": reward,
            })
        self.repo.db.commit()
        return {"week": week, "paid": True, "winners": winners}
