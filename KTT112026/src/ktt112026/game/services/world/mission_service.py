"""Nhiệm vụ dài hạn (PR7) — tách daily quest."""
from __future__ import annotations

import time
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num

# Progressive missions (account-lifetime progress until claimed)
MISSIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "tien_dao",
        "name": "Mở Đạo",
        "desc": "Tạo thể đạo và chọn Tiên/Ma",
        "need": 1,
        "kind": "path",
        "stones": 200,
    },
    {
        "id": "the_luc",
        "name": "Chọn thế lực",
        "desc": "`.gianhap tongmon` hoặc `.gianhap tantu`",
        "need": 1,
        "kind": "faction",
        "stones": 250,
    },
    {
        "id": "tong_de",
        "name": "Đệ tử tông môn",
        "desc": "Gia nhập một tông (NPC hoặc PC)",
        "need": 1,
        "kind": "sect_join",
        "stones": 300,
    },
    {
        "id": "cung_hien",
        "name": "Cống hiến sơ",
        "desc": "Cống hiến tổng 500 LS cho tông",
        "need": 500,
        "kind": "sect_contrib",
        "stones": 400,
    },
    {
        "id": "chien_thap",
        "name": "Tháp chiến",
        "desc": "Hoàn thành 3 lần `.thap` (bắt đầu run)",
        "need": 3,
        "kind": "thap",
        "stones": 350,
    },
    {
        "id": "the_su",
        "name": "Hưởng thiên thời",
        "desc": "Nhận sự kiện thế giới 2 lần (các ngày)",
        "need": 2,
        "kind": "sukien",
        "stones": 280,
    },
)


class MissionService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def _get(self, user_id: str, mission_id: str) -> dict[str, int]:
        r = self.repo.db.fetchone(
            "SELECT progress, claimed FROM player_missions WHERE user_id=? AND mission_id=?",
            (str(user_id), mission_id),
        )
        if r:
            return {"progress": int(r["progress"]), "claimed": int(r["claimed"])}
        self.repo.db.execute(
            "INSERT INTO player_missions(user_id, mission_id, progress, claimed, updated_at) VALUES(?,?,0,0,?)",
            (str(user_id), mission_id, time.time()),
        )
        self.repo.db.commit()
        return {"progress": 0, "claimed": 0}

    def _set(self, user_id: str, mission_id: str, progress: int, claimed: int) -> None:
        self.repo.db.execute(
            "UPDATE player_missions SET progress=?, claimed=?, updated_at=? WHERE user_id=? AND mission_id=?",
            (int(progress), int(claimed), time.time(), str(user_id), mission_id),
        )
        self.repo.db.commit()

    def sync_from_player(self, user_id: str) -> None:
        """Pull path/faction/sect state into mission progress."""
        p = self.repo.get(str(user_id))
        if not p:
            return
        if p.path:
            self.bump(user_id, "path", 1, absolute_min=1)
        if p.faction:
            self.bump(user_id, "faction", 1, absolute_min=1)
        if p.sect_id:
            self.bump(user_id, "sect_join", 1, absolute_min=1)
            self.bump(user_id, "sect_contrib", int(p.sect_contrib or 0), absolute=True)

    def bump(
        self,
        user_id: str,
        kind: str,
        amount: int = 1,
        *,
        absolute: bool = False,
        absolute_min: int | None = None,
    ) -> None:
        if self.repo.get(str(user_id)) is None:
            return
        for m in MISSIONS:
            if m["kind"] != kind:
                continue
            st = self._get(user_id, m["id"])
            if st["claimed"]:
                continue
            if absolute:
                prog = max(st["progress"], int(amount))
            elif absolute_min is not None:
                prog = max(st["progress"], int(absolute_min))
            else:
                prog = st["progress"] + max(0, int(amount))
            need = int(m["need"])
            prog = min(need, prog)
            if prog != st["progress"]:
                self._set(user_id, m["id"], prog, st["claimed"])

    def status(self, user_id: str) -> dict[str, Any]:
        self.sync_from_player(user_id)
        lines = []
        for m in MISSIONS:
            st = self._get(user_id, m["id"])
            need = int(m["need"])
            prog = min(need, st["progress"])
            flag = "✅" if st["claimed"] else ("🎁" if prog >= need else "…")
            lines.append(
                {
                    "id": m["id"],
                    "name": m["name"],
                    "desc": m["desc"],
                    "progress": prog,
                    "need": need,
                    "claimed": bool(st["claimed"]),
                    "ready": prog >= need and not st["claimed"],
                    "stones": int(m["stones"]),
                    "flag": flag,
                }
            )
        return {"missions": lines}

    def claim(self, user_id: str, mission_id: str | None = None) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        self.sync_from_player(user_id)
        gained = 0
        names: list[str] = []
        targets = list(MISSIONS)
        if mission_id and mission_id not in ("all", "het"):
            mid = mission_id.strip().lower()
            targets = [m for m in MISSIONS if m["id"] == mid]
            if not targets:
                raise ValueError("Không có nhiệm vụ này. `.nhiemvu dai` xem danh sách.")
        for m in targets:
            st = self._get(user_id, m["id"])
            if st["claimed"]:
                continue
            if st["progress"] < int(m["need"]):
                continue
            self._set(user_id, m["id"], st["progress"], 1)
            gained += int(m["stones"])
            names.append(m["name"])
        if gained <= 0:
            raise ValueError("Chưa có nhiệm vụ dài hạn để nhận.")
        p.spirit_stones += gained
        self.repo.save(p)
        return {"stones": gained, "names": names, "player": p}
