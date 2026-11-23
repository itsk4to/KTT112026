"""System shop — catalog filtered by player realm/path."""
from __future__ import annotations

from ktt112026.game.content.shop import find_item, get_catalog
from ktt112026.game.repo.players import PlayerRepository

# Show items up to +1 major realm ahead so player can plan
REALM_PREVIEW = 1


class ShopService:
    def __init__(self, players: PlayerRepository) -> None:
        self.players = players

    def catalog(self, category: str, user_id: str | None = None) -> list[dict]:
        items = list(get_catalog(category))
        if not user_id:
            return items
        p = self.players.get(str(user_id))
        if p is None:
            return items
        out = []
        for it in items:
            major_min = int(it.get("major_min", 1))
            if major_min > p.major_realm + REALM_PREVIEW:
                continue  # hide far future
            path = it.get("path", "any")
            if path in ("tien", "ma") and p.path and p.path != path:
                continue  # hide opposite dao
            row = dict(it)
            # mark locked if same-ish realm but stage/path not ready
            locked = major_min > p.major_realm
            if locked:
                row = dict(row)
                row["stats"] = f"[Sắp mở C{major_min}] " + str(row.get("stats") or "")
                row["locked"] = True
            else:
                row["locked"] = False
            out.append(row)
        return out

    def buy(self, user_id: str, item_id: str, qty: int = 1) -> dict:
        qty = max(1, min(99, int(qty)))
        found = find_item(item_id)
        if found is None:
            raise ValueError("Không tìm thấy vật phẩm trong cửa hàng hệ thống. Kiểm tra mã (`.shop`) hoặc vật phẩm chỉ rơi từ bí cảnh/luyện đan.")
        _cat, item = found
        if item.get("purchasable") is False or item.get("shop") is False:
            raise ValueError(f"**{item.get('name', item_id)}** không thể mua — chỉ nhận từ rơi/đan/nhiệm vụ.")
        if item.get("locked"):
            raise ValueError("Vật phẩm đang khóa theo cảnh giới. Tu luyện thêm rồi hãy mua.")
        player = self.players.get(str(user_id))
        if player is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        if player.major_realm < int(item.get("major_min", 1)):
            raise ValueError("Cảnh giới chưa đủ để mua vật phẩm này.")
        if player.path and item.get("path") in {"tien", "ma"} and player.path != item["path"]:
            raise ValueError("Vật phẩm không khớp Đạo Lộ (Tiên/Ma).")
        unit = self._price_for(player, int(item["price"]))
        total = unit * qty
        if player.spirit_stones < total:
            raise ValueError(f"Không đủ Linh Thạch (cần {total:,}, đang có {player.spirit_stones:,}).")
        player.spirit_stones -= total
        self.players.save(player)
        self.players.inventory_add(str(user_id), item["id"], qty)
        return {"item": item, "qty": qty, "spent": total, "stones_left": player.spirit_stones}


    def _price_for(self, player, base_price: int) -> int:
        """Scale price lightly by major realm (8% per major above 1)."""
        major = max(1, int(getattr(player, "major_realm", 1) or 1))
        mult = 1.0 + max(0, major - 1) * 0.08
        return max(1, int(base_price * mult))
