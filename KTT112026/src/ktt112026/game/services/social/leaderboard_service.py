"""Bảng xếp hạng — nhiều loại, số rút gọn."""
from __future__ import annotations

from typing import Any

from ktt112026.game.content.realms import realm_display
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num


class LeaderboardService:
    KINDS = ("lucchien", "linhthach", "canhgioi", "tongmon", "cunghien")

    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def top(self, kind: str = "lucchien", limit: int = 10) -> dict[str, Any]:
        kind = (kind or "lucchien").strip().lower()
        aliases = {
            "ls": "linhthach",
            "stones": "linhthach",
            "power": "lucchien",
            "lc": "lucchien",
            "realm": "canhgioi",
            "cg": "canhgioi",
            "tuvi": "canhgioi",
            "sect": "tongmon",
            "tm": "tongmon",
            "contrib": "cunghien",
            "ch": "cunghien",
        }
        kind = aliases.get(kind, kind)
        limit = max(3, min(20, int(limit)))

        if kind == "linhthach":
            rows = self.repo.db.fetchall(
                "SELECT user_id, display_name, spirit_stones AS score, major_realm, minor_stage, path "
                "FROM players ORDER BY spirit_stones DESC, major_realm DESC LIMIT ?",
                (limit,),
            )
            title = "Bảng Xếp Hạng · Linh Thạch"
            score_label = "LS"
        elif kind == "canhgioi":
            rows = self.repo.db.fetchall(
                "SELECT user_id, display_name, "
                "(major_realm * 1000000000 + minor_stage * 1000000 + cultivation) AS score, "
                "major_realm, minor_stage, path "
                "FROM players ORDER BY major_realm DESC, minor_stage DESC, cultivation DESC LIMIT ?",
                (limit,),
            )
            title = "Bảng Xếp Hạng · Cảnh Giới"
            score_label = "cảnh"
        elif kind == "tongmon":
            rows = self.repo.db.fetchall(
                "SELECT sect_id AS user_id, sect_id AS display_name, "
                "COALESCE(SUM(sect_contrib),0) AS score, COUNT(*) AS major_realm, 0 AS minor_stage, '' AS path "
                "FROM players WHERE sect_id != '' GROUP BY sect_id "
                "ORDER BY score DESC LIMIT ?",
                (limit,),
            )
            title = "Bảng Xếp Hạng · Tông Môn"
            score_label = "cống hiến"
        elif kind == "cunghien":
            rows = self.repo.db.fetchall(
                "SELECT user_id, display_name, sect_contrib AS score, major_realm, minor_stage, path "
                "FROM players WHERE sect_id != '' ORDER BY sect_contrib DESC LIMIT ?",
                (limit,),
            )
            title = "Bảng Xếp Hạng · Cống Hiến Tông"
            score_label = "CH"
        else:
            # lực chiến ước lượng SQL: stats + realm
            rows = self.repo.db.fetchall(
                "SELECT user_id, display_name, "
                "(can_cot + than_thuc + than_phap + major_realm * 20 + minor_stage * 5) AS score, "
                "major_realm, minor_stage, path "
                "FROM players ORDER BY score DESC, spirit_stones DESC LIMIT ?",
                (limit,),
            )
            title = "Bảng Xếp Hạng · Lực Chiến"
            score_label = "LC"
            kind = "lucchien"

        entries = []
        for i, r in enumerate(rows, 1):
            name = str(r["display_name"])
            if kind == "tongmon":
                # map id -> pretty later in command
                name = str(r["display_name"])
            realm = ""
            if kind not in ("tongmon",):
                realm = realm_display(int(r["major_realm"] or 1), int(r["minor_stage"] or 0), str(r["path"] or ""))
            entries.append({
                "rank": i,
                "user_id": str(r["user_id"]),
                "name": name[:24],
                "score": int(r["score"] or 0),
                "score_fmt": fmt_num(int(r["score"] or 0)),
                "realm": realm,
            })
        lines = [f"#{e['rank']} {e['name']} {e['score_fmt']}" for e in entries]
        return {"kind": kind, "title": title, "score_label": score_label, "entries": entries, "lines": lines}
