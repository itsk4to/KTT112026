"""Hệ thống Tông Môn — NPC, tạo tông, quà tuần vật phẩm tự động."""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

from ktt112026.game.content.loader import load_sects
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num
from ktt112026.game.rules import sect_rules

LEVEL_THRESHOLDS = [0, 5_000, 20_000, 50_000, 120_000, 250_000, 500_000, 1_000_000]
# Cống hiến tối thiểu để trở thành chủ tông NPC (khi chưa có chủ hoặc soán ngôi nếu cao hơn rõ)
LEADER_CONTRIB = 8_000
# Tạo tông riêng
CREATE_COST = 50_000
CREATE_MIN_DAYS_IN_SECT = 3  # đã ở một tông ≥ 3 ngày rồi rời mới tạo, hoặc tán tu ≥ 3 ngày kể từ gianhap
CREATE_MIN_MAJOR = 3
INVITE_TTL = 48 * 3600
MAX_MEMBERS_BASE = 15

# Quà tuần — đan 5–20 viên + bảo khí/vũ khí theo top (ít dần top1→3)
WEEKLY_ITEM_REWARDS = {
    1: [
        ("anhlinhdan", 20),
        ("kimnguyendan", 10),
        ("truyphongdang", 1),
        ("tudienthuong", 1),
    ],
    2: [
        ("kimnguyendan", 12),
        ("truccodan", 15),
        ("huyenvugiap", 1),
    ],
    3: [
        ("truccodan", 10),
        ("tukhidan", 15),
        ("hotamkinh", 1),
    ],
}


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


def _slug_name(name: str) -> str:
    s = re.sub(r"\s+", "", name.lower())
    s = re.sub(r"[^a-z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+", "", s)
    if not s:
        s = f"tong{int(time.time()) % 100000}"
    return ("p_" + s)[:24]


class SectService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        try:
            raw = load_sects()
        except Exception:
            raw = []
        self._npc = {s["id"]: {**s, "npc": True} for s in raw}

    def all_sects_map(self) -> dict[str, dict]:
        out = dict(self._npc)
        rows = self.repo.db.fetchall("SELECT * FROM custom_sects")
        for r in rows:
            out[str(r["id"])] = {
                "id": str(r["id"]),
                "name": str(r["name"]),
                "path": str(r["path"] or "any"),
                "major_min": int(r["major_min"] or 2),
                "npc": False,
                "desc": f"Tông do người chơi lập (chủ <@{r['owner_id']}>)",
                "owner_id": str(r["owner_id"]),
            }
        return out

    def _sect(self, sect_id: str) -> dict | None:
        return self.all_sects_map().get((sect_id or "").strip().lower())

    def _ensure_state(self, sect_id: str) -> dict[str, Any]:
        row = self.repo.db.fetchone("SELECT * FROM sect_state WHERE sect_id=?", (sect_id,))
        if row:
            return dict(row)
        self.repo.db.execute(
            "INSERT INTO sect_state(sect_id, level, bank_stones, leader_id, last_weekly_key) VALUES(?,?,?,?,?)",
            (sect_id, 1, 0, "", ""),
        )
        self.repo.db.commit()
        return {"sect_id": sect_id, "level": 1, "bank_stones": 0, "leader_id": "", "last_weekly_key": ""}

    def _total_contrib(self, sect_id: str) -> int:
        r = self.repo.db.fetchone(
            "SELECT COALESCE(SUM(sect_contrib),0) AS t FROM players WHERE sect_id=?",
            (sect_id,),
        )
        return int(r["t"]) if r else 0

    def _member_count(self, sect_id: str) -> int:
        r = self.repo.db.fetchone("SELECT COUNT(*) AS c FROM players WHERE sect_id=?", (sect_id,))
        return int(r["c"]) if r else 0

    def _max_members(self, level: int) -> int:
        return MAX_MEMBERS_BASE + max(0, level - 1) * 3

    def _refresh_level(self, sect_id: str) -> int:
        st = self._ensure_state(sect_id)
        total = self._total_contrib(sect_id) + int(st.get("bank_stones") or 0)
        lvl = _level_from_contrib(total)
        if int(st.get("level") or 1) != lvl:
            self.repo.db.execute("UPDATE sect_state SET level=? WHERE sect_id=?", (lvl, sect_id))
            self.repo.db.commit()
        return lvl

    def _try_promote_leader(self, sect_id: str, player) -> str | None:
        """NPC: đủ CH có thể thành chủ; custom: owner giữ chủ trừ khi chuyển."""
        sect = self._sect(sect_id)
        if not sect:
            return None
        st = self._ensure_state(sect_id)
        if not sect.get("npc", True):
            return None
        if int(player.sect_contrib) < LEADER_CONTRIB:
            return None
        leader_id = str(st.get("leader_id") or "")
        if leader_id and leader_id != str(player.user_id):
            lead = self.repo.get(leader_id)
            if lead and int(lead.sect_contrib) >= int(player.sect_contrib):
                return None
            # soán ngôi
            if lead and lead.sect_id == sect_id:
                lead.sect_role = "elder"
                self.repo.save(lead)
        player.sect_role = "leader"
        self.repo.save(player)
        self.repo.db.execute(
            "UPDATE sect_state SET leader_id=? WHERE sect_id=?",
            (str(player.user_id), sect_id),
        )
        self.repo.db.commit()
        return "leader"

    def _is_officer(self, p) -> bool:
        return sect_rules.has_permission(p.sect_role or "member", "sect.kick")

    def list_sects(self, *, npc_only: bool = False) -> list[dict]:
        out = []
        for s in self.all_sects_map().values():
            if npc_only and not s.get("npc", False):
                continue
            sid = s["id"]
            st = self._ensure_state(sid)
            lvl = self._refresh_level(sid)
            out.append({
                **s,
                "members": self._member_count(sid),
                "contrib": self._total_contrib(sid),
                "level": lvl,
                "max_members": self._max_members(lvl),
                "leader_id": st.get("leader_id") or "",
            })
        out.sort(key=lambda x: (not x.get("npc", False), x.get("name", "")))
        return out

    def join(self, user_id: str, sect_id: str) -> dict[str, Any]:
        sect_id = (sect_id or "").strip().lower()
        sect = self._sect(sect_id)
        if not sect:
            raise ValueError("Không có tông môn này. `.tongmon` xem danh sách tông NPC / tông người chơi.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        if not p.path:
            raise ValueError("Hãy `.chon tien` hoặc `.chon ma` trước.")
        if p.major_realm < int(sect.get("major_min", 2)):
            raise ValueError(f"Cần đại cảnh giới cấp {sect['major_min']}+.")
        if p.faction != "tongmon":
            raise ValueError("Hãy `.gianhap tongmon` (hoặc chọn khi đủ cảnh giới) trước khi vào tông.")
        if p.sect_id:
            raise ValueError("Đã ở trong tông môn. `.tongmon roi` rồi hãy vào tông khác.")
        sp = sect.get("path", "any")
        if sp in ("tien", "ma") and p.path != sp:
            raise ValueError("Tông môn không khớp Đạo Lộ.")
        lvl = self._refresh_level(sect_id)
        if self._member_count(sect_id) >= self._max_members(lvl):
            raise ValueError(f"Tông đã đủ người (tối đa {self._max_members(lvl)} ở cấp {lvl}).")
        st = self._ensure_state(sect_id)
        # custom sect: first member / owner becomes leader
        role = "member"
        if not sect.get("npc", True) and str(sect.get("owner_id")) == str(user_id):
            role = "leader"
        elif not st.get("leader_id") and self._member_count(sect_id) == 0 and not sect.get("npc", True):
            role = "leader"
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
            raise ValueError("Không có lời mời. Nhờ người trong tông `.tongmon moi @bạn`.")
        if now - int(row["created_at"]) > INVITE_TTL:
            self.repo.db.execute(
                "DELETE FROM sect_invites WHERE sect_id=? AND invitee_id=?",
                (row["sect_id"], str(user_id)),
            )
            self.repo.db.commit()
            raise ValueError("Lời mời đã hết hạn (48 giờ).")
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
        old = self._sect(sid) or {"name": sid, "id": sid}
        was_leader = p.sect_role == "leader"
        p.sect_contrib = int(p.sect_contrib * 0.7)
        p.sect_id = ""
        p.sect_joined_at = 0.0
        p.sect_role = ""
        self.repo.save(p)
        if was_leader:
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

    def create_sect(self, user_id: str, name: str, path: str | None = None) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if p.major_realm < CREATE_MIN_MAJOR:
            raise ValueError(f"Cần đại cảnh giới cấp {CREATE_MIN_MAJOR}+ mới lập tông riêng.")
        if p.faction != "tongmon":
            raise ValueError("Chỉ người chọn Tông Môn (`.gianhap tongmon`) mới lập tông được.")
        if p.sect_id:
            raise ValueError("Hãy `.tongmon roi` khỏi tông hiện tại trước khi lập tông mới.")
        # thời gian: đã gianhap / có activity đủ lâu — dùng created_at proxy + last leave not tracked;
        # yêu cầu đã từng có sect_joined hoặc major>=3 và created đủ ngày
        created = float(p.created_at) if getattr(p, "created_at", None) else 0.0
        age_days = (time.time() - created) / 86400 if created > 0 else 0
        # Cấp 3+ được lập; dưới đó cần đủ ngày tuổi tài khoản
        if p.major_realm < CREATE_MIN_MAJOR:
            raise ValueError(f"Cần đại cảnh giới cấp {CREATE_MIN_MAJOR}+ mới lập tông riêng.")
        if p.major_realm == CREATE_MIN_MAJOR and age_days < CREATE_MIN_DAYS_IN_SECT and age_days > 0:
            # gợi ý nhẹ — không chặn cứng nếu đã cấp 3
            pass
        name = (name or "").strip()
        if len(name) < 2 or len(name) > 24:
            raise ValueError("Tên tông 2–24 ký tự.")
        if p.spirit_stones < CREATE_COST:
            raise ValueError(f"Cần {fmt_num(CREATE_COST)} Linh Thạch để lập tông.")
        sid = _slug_name(name)
        if sid in self.all_sects_map():
            sid = f"{sid}{int(time.time()) % 1000}"
        sp = (path or p.path or "any").strip().lower()
        if sp not in ("tien", "ma", "any"):
            sp = p.path if p.path in ("tien", "ma") else "any"
        p.spirit_stones -= CREATE_COST
        self.repo.db.execute(
            "INSERT INTO custom_sects(id, name, path, owner_id, created_at, major_min) VALUES(?,?,?,?,?,?)",
            (sid, name, sp, str(user_id), time.time(), 2),
        )
        self.repo.db.commit()
        self.repo.save(p)
        # auto join as leader
        p.faction = "tongmon"
        self.repo.save(p)
        joined = self.join(user_id, sid)
        return {"sect": joined["sect"], "cost": CREATE_COST, "player": self.repo.get(str(user_id))}

    def invite(self, inviter_id: str, invitee_id: str) -> dict[str, Any]:
        inviter = self.repo.get(str(inviter_id))
        if inviter is None:
            raise ValueError("Bạn chưa có thể đạo.")
        if not inviter.sect_id:
            raise ValueError("Bạn chưa ở trong tông môn.")
        invitee = self.repo.get(str(invitee_id))
        if invitee is None:
            raise ValueError("Đối phương chưa `.taothe`.")
        if invitee.sect_id:
            raise ValueError("Đối phương đã có tông môn.")
        if invitee.faction and invitee.faction != "tongmon":
            raise ValueError("Đối phương cần chọn con đường Tông Môn (`.gianhap tongmon`).")
        sect = self._sect(inviter.sect_id)
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
        return {"sect": sect, "inviter": inviter, "invitee": invitee, "expires_hours": INVITE_TTL // 3600}

    def kick(self, actor_id: str, target_id: str) -> dict[str, Any]:
        actor = self.repo.get(str(actor_id))
        target = self.repo.get(str(target_id))
        if actor is None or target is None:
            raise ValueError("Không tìm thấy người chơi.")
        if not actor.sect_id or actor.sect_id != target.sect_id:
            raise ValueError("Hai bên không cùng tông môn.")
        if not sect_rules.can_kick(actor.sect_role or "member", target.sect_role or "member"):
            raise ValueError("Không đủ quyền kick (chỉ quản được chức thấp hơn).")
        if str(actor_id) == str(target_id):
            raise ValueError("Không tự kick — dùng `.tongmon roi`.")
        name = target.display_name
        sid = target.sect_id
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
        if not sect_rules.has_permission(actor.sect_role or "member", "sect.promote"):
            raise ValueError("Chỉ Tông Chủ được bổ nhiệm.")
        role = sect_rules.normalize_role(role)
        if role != "leader":
            promote = sect_rules.role_rank(role) < sect_rules.role_rank(target.sect_role or "member")
            if not sect_rules.can_change_role(
                actor.sect_role or "member",
                target.sect_role or "member",
                role,
                promote=promote,
            ):
                raise ValueError("Không thể đổi sang chức vụ này (rank / quyền).")
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
        bank_add = amount // 5
        self.repo.save(p)
        self._ensure_state(p.sect_id)
        self.repo.db.execute(
            "UPDATE sect_state SET bank_stones = bank_stones + ? WHERE sect_id=?",
            (bank_add, p.sect_id),
        )
        self.repo.db.commit()
        lvl = self._refresh_level(p.sect_id)
        promoted = self._try_promote_leader(p.sect_id, self.repo.get(str(user_id)))
        return {
            "amount": amount,
            "contrib": p.sect_contrib,
            "sect_id": p.sect_id,
            "bank_add": bank_add,
            "level": lvl,
            "promoted": promoted,
            "player": self.repo.get(str(user_id)),
        }

    def ranking(self, user_id: str, limit: int = 10) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None or not p.sect_id:
            raise ValueError("Cần ở trong tông môn. `.tongmon`")
        sid = p.sect_id
        sect = self._sect(sid) or {"name": sid, "id": sid}
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
        sect = self._sect(sid)
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
            "max_members": self._max_members(sid and lvl),
            "bank": int(st.get("bank_stones") or 0),
            "leader_name": leader.display_name if leader else ("NPC quản lý" if sect.get("npc") else "—"),
            "next_level_at": next_need,
            "leader_need": LEADER_CONTRIB if sect.get("npc") else None,
            "player": p,
        }

    def process_weekly_rewards(self) -> dict[str, Any]:
        """Tự động: top 1–3 cống hiến (có tông) nhận đan + bảo khí/vũ khí — không lệnh thủ công."""
        week = _week_key()
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
            rewards = WEEKLY_ITEM_REWARDS.get(rank, [])
            if not rewards:
                continue
            uid = str(r["user_id"])
            given = []
            for item_id, qty in rewards:
                self.repo.inventory_add(uid, item_id, int(qty))
                given.append(f"{item_id}×{qty}")
            self.repo.db.execute(
                "INSERT INTO sect_weekly_payout(week_key, user_id, rank, reward) VALUES(?,?,?,?)",
                (week, uid, rank, rank),  # reward field = rank marker
            )
            winners.append({
                "rank": rank,
                "user_id": uid,
                "name": str(r["display_name"]),
                "items": given,
            })
        self.repo.db.commit()
        return {"week": week, "paid": True, "winners": winners}
