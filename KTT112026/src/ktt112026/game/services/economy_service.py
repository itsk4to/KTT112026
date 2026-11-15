"""Transfer LS + sell to NPC."""
from __future__ import annotations

from ktt112026.game.services._tx import atomic
from ktt112026.game.content.loader import catalog_by_id
from ktt112026.game.repo.players import PlayerRepository

# NPC buyback rate of shop price (if known)
BUYBACK_RATE = 0.4
DEFAULT_HERB_PRICE = {
    "linhthao": 40,
    "thanhtrucdiep": 50,
    "huyenlinhhoa": 120,
    "loctamthao": 150,
    "kimtinhthao": 400,
}


class EconomyService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self.items = catalog_by_id()

    @atomic
    def transfer(self, from_id: str, to_id: str, amount: int) -> dict:
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Số Linh Thạch phải > 0.")
        if str(from_id) == str(to_id):
            raise ValueError("Không thể chuyển cho chính mình.")
        sender = self.repo.get(str(from_id))
        recv = self.repo.get(str(to_id))
        if sender is None:
            raise ValueError("Bạn chưa có thể đạo.")
        if recv is None:
            raise ValueError("Đối phương chưa tạo thể đạo (`.taothe`).")
        if sender.spirit_stones < amount:
            raise ValueError(f"Không đủ Linh Thạch (đang có {sender.spirit_stones:,}).")
        sender.spirit_stones -= amount
        recv.spirit_stones += amount
        self.repo.save(sender)
        self.repo.save(recv)
        return {
            "amount": amount,
            "from_left": sender.spirit_stones,
            "to_name": recv.display_name,
            "to_left": recv.spirit_stones,
        }

    @atomic
    def sell_npc(self, user_id: str, item_id: str, qty: int = 1) -> dict:
        item_id = item_id.strip().lower()
        qty = max(1, min(99, int(qty)))
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        have = self.repo.inventory_qty(user_id, item_id)
        if have < qty:
            raise ValueError("Túi không đủ vật phẩm.")
        unit = self._unit_price(item_id)
        if unit <= 0:
            raise ValueError("NPC không thu mua vật phẩm này.")
        total = unit * qty
        if not self.repo.inventory_remove(user_id, item_id, qty):
            raise ValueError("Không trừ được túi đồ.")
        p.spirit_stones += total
        self.repo.save(p)
        name = self.items.get(item_id, {}).get("name", item_id)
        return {"item_id": item_id, "name": name, "qty": qty, "unit": unit, "total": total, "stones": p.spirit_stones}

    def _unit_price(self, item_id: str) -> int:
        if item_id in DEFAULT_HERB_PRICE:
            return DEFAULT_HERB_PRICE[item_id]
        meta = self.items.get(item_id)
        if not meta:
            return 0
        # Don't buy back techniques/pets via NPC easily
        kind = meta.get("kind") or meta.get("category")
        if kind in ("congphap", "linhthu", "vukhi", "phapbao"):
            price = int(meta.get("price") or 0)
            return max(1, int(price * BUYBACK_RATE)) if price else 0
        if kind == "danduoc" or "price" in meta:
            price = int(meta.get("price") or 0)
            return max(1, int(price * BUYBACK_RATE)) if price else 0
        return 0
