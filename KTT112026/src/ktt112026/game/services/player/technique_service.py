"""Learn / upgrade techniques (.hoc) — max tier 5."""
from __future__ import annotations

from ktt112026.game.content.loader import load_congphap
from ktt112026.game.repo.players import PlayerRepository

MAX_TIER = 5


class TechniqueService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self._by_id = {t["id"]: t for t in load_congphap()}

    def learn(self, user_id: str, technique_id: str) -> dict:
        technique_id = technique_id.strip().lower()
        tech = self._by_id.get(technique_id)
        if tech is None:
            raise ValueError("Không có công pháp này. Xem `.shop congphap`.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if p.major_realm < int(tech.get("major_min", 1)):
            raise ValueError("Cảnh giới chưa đủ để học.")
        path = tech.get("path", "any")
        if path in ("tien", "ma") and p.path and p.path != path:
            raise ValueError("Công pháp không khớp Đạo Lộ.")
        if self.repo.inventory_qty(user_id, technique_id) < 1:
            raise ValueError("Túi không có bí kíp này — hãy `.mua` trước.")

        tier = self.repo.get_technique_tier(user_id, technique_id)
        if tier >= MAX_TIER:
            raise ValueError("Đã Đại Viên Mãn (tầng 5).")
        if not self.repo.inventory_remove(user_id, technique_id, 1):
            raise ValueError("Không trừ được bí kíp.")
        new_tier = tier + 1 if tier > 0 else 1
        self.repo.set_technique_tier(user_id, technique_id, new_tier)
        return {
            "technique": tech,
            "tier": new_tier,
            "max_tier": MAX_TIER,
            "first_learn": tier == 0,
        }

    def list_learned(self, user_id: str) -> list[dict]:
        out = []
        for row in self.repo.list_techniques(user_id):
            tech = self._by_id.get(row["technique_id"], {})
            out.append({
                "id": row["technique_id"],
                "name": tech.get("name", row["technique_id"]),
                "tier": row["tier"],
            })
        return out
