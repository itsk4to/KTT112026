"""Luyện đan tối thiểu từ recipes.json."""
from __future__ import annotations

import random
from typing import Any

from ktt112026.game.content.loader import load_recipes
from ktt112026.game.repo.players import PlayerRepository


class AlchemyService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self.recipes = {r["id"]: r for r in load_recipes()}
        # also index by output
        for r in load_recipes():
            self.recipes.setdefault(r["output_id"], r)

    def list_recipes(self) -> list[dict]:
        return load_recipes()

    def craft(self, user_id: str, recipe_id: str) -> dict[str, Any]:
        recipe_id = recipe_id.strip().lower()
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            raise ValueError("Không có công thức. `.congthuc` để xem.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if p.major_realm < int(recipe.get("major_min", 1)):
            raise ValueError("Cảnh giới chưa đủ để luyện đan này.")

        ings = recipe.get("ingredients") or {}
        for item_id, need in ings.items():
            if self.repo.inventory_qty(user_id, item_id) < int(need):
                raise ValueError(f"Thiếu nguyên liệu `{item_id}` (cần {need}).")

        for item_id, need in ings.items():
            self.repo.inventory_remove(user_id, item_id, int(need))

        rate = float(recipe.get("base_success", 0.6)) + p.stats.ngo_tinh * 0.002
        rate = min(0.95, rate)
        ok = self.rng.random() <= rate
        if ok:
            out_id = recipe["output_id"]
            qty = int(recipe.get("output_qty", 1))
            self.repo.inventory_add(user_id, out_id, qty)
            return {
                "success": True,
                "recipe": recipe,
                "rate": rate,
                "output_id": out_id,
                "qty": qty,
            }
        return {"success": False, "recipe": recipe, "rate": rate, "output_id": None, "qty": 0}
