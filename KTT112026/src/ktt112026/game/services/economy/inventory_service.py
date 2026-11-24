"""Bag + equip."""
from __future__ import annotations

from ktt112026.game.content.shop import ITEM_INDEX, find_item
from ktt112026.game.repo.players import PlayerRepository


class InventoryService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def list_items(self, user_id: str) -> list[dict]:
        rows = self.repo.inventory_list(str(user_id))
        out = []
        for r in rows:
            meta = ITEM_INDEX.get(r["item_id"], {})
            out.append({
                "item_id": r["item_id"],
                "quantity": r["quantity"],
                "name": meta.get("name", r["item_id"]),
                "kind": meta.get("kind", "vatpham"),
            })
        return out

    def equip(self, user_id: str, item_id: str) -> str:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        found = find_item(item_id)
        if found is None:
            raise ValueError("Không rõ vật phẩm.")
        cat, item = found
        if self.repo.inventory_qty(user_id, item["id"]) < 1:
            raise ValueError("Túi không có vật phẩm này.")
        if cat == "vukhi":
            if not p.weapon1:
                p.weapon1 = item["id"]
            elif not p.weapon2:
                p.weapon2 = item["id"]
            else:
                raise ValueError("Đã đủ 2 vũ khí — tháo một món trước (sẽ có .thao).")
        elif cat == "phapbao":
            if p.treasure:
                raise ValueError("Đã đeo pháp bảo — tháo trước.")
            p.treasure = item["id"]
        else:
            raise ValueError("Chỉ trang bị vũ khí / pháp bảo.")
        self.repo.save(p)
        return item["name"]
