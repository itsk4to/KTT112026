"""BXH helpers."""
from __future__ import annotations

from ktt112026.game.content.realms import realm_display
from ktt112026.game.repo.players import PlayerRepository


class LeaderboardService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def top(self, kind: str = "tuvi", limit: int = 10) -> dict:
        kind = (kind or "tuvi").lower()
        rows = self.repo.leaderboard(kind, limit)
        lines = []
        for i, r in enumerate(rows, 1):
            name = r.get("display_name") or r.get("user_id")
            path = r.get("path") or ""
            if kind in ("tien", "ls", "stones"):
                score = f"{int(r.get('score') or 0):,} LS"
            elif kind in ("cancot", "cot", "can_cot"):
                score = f"Căn Cốt {int(r.get('score') or 0)}"
            elif kind in ("tongmon", "faction"):
                realm = realm_display(int(r.get("score") or 1), int(r.get("minor_stage") or 0), path)
                score = realm
            else:
                realm = realm_display(int(r.get("major_realm") or 1), int(r.get("minor_stage") or 0), path)
                score = f"{realm} · {int(r.get('cultivation') or 0):,} TV"
            lines.append(f"{i}. {name} — {score}")
        title = {
            "tuvi": "BXH Tu Vi",
            "cancot": "BXH Căn Cốt",
            "cot": "BXH Căn Cốt",
            "tien": "BXH Linh Thạch",
            "ls": "BXH Linh Thạch",
            "tongmon": "BXH Tông Môn",
        }.get(kind, "BXH Tu Vi")
        return {"title": title, "lines": lines, "kind": kind}
