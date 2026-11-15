"""Sàn Đấu Giá (.daugia) — người chơi niêm yết vật phẩm, giá cố định, phí 5%, hết hạn 24h."""
from __future__ import annotations

import time

from ktt112026.game.content.loader import catalog_by_id
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services._tx import atomic

LISTING_SECONDS = 24 * 3600
FEE_RATE = 0.05  # sink Linh Thạch
MAX_ACTIVE_PER_SELLER = 5
MAX_PRICE = 10_000_000_000
MAX_QTY = 99


class AuctionService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self.items = catalog_by_id()

    def _item_name(self, item_id: str) -> str:
        return self.items.get(item_id, {}).get("name", item_id)

    def _expire(self, now: float) -> None:
        """Lô hết hạn → trả đồ về túi người bán (chạy lười mỗi lần truy cập)."""
        for a in self.repo.auction_expired_open(now):
            if self.repo.auction_set_status(a["id"], "expired"):
                self.repo.inventory_add(a["seller_id"], a["item_id"], a["quantity"])

    @atomic
    def list_open(self, limit: int = 10, seller_id: str | None = None) -> list[dict]:
        self._expire(time.time())
        rows = self.repo.auction_list_open(limit, seller_id)
        for r in rows:
            r["name"] = self._item_name(r["item_id"])
            r["minutes_left"] = max(0, int((r["expires_at"] - time.time()) // 60))
        return rows

    @atomic
    def create(self, seller_id: str, item_id: str, qty: int, price: int) -> dict:
        item_id = item_id.strip().lower()
        qty, price = int(qty), int(price)
        if item_id not in self.items:
            raise ValueError("Vật phẩm không có trong danh mục.")
        if not (1 <= qty <= MAX_QTY):
            raise ValueError(f"Số lượng 1–{MAX_QTY}.")
        if not (1 <= price <= MAX_PRICE):
            raise ValueError("Giá không hợp lệ.")
        if self.repo.get(str(seller_id)) is None:
            raise ValueError("Chưa có thể đạo.")
        now = time.time()
        self._expire(now)
        if self.repo.auction_open_count(seller_id) >= MAX_ACTIVE_PER_SELLER:
            raise ValueError(f"Tối đa {MAX_ACTIVE_PER_SELLER} lô đang bán cùng lúc.")
        if not self.repo.inventory_remove(seller_id, item_id, qty):  # ký gửi đồ vào sàn
            raise ValueError("Túi không đủ vật phẩm.")
        aid = self.repo.auction_create(seller_id, item_id, qty, price, now, now + LISTING_SECONDS)
        return {"id": aid, "name": self._item_name(item_id), "qty": qty, "price": price,
                "fee_pct": int(FEE_RATE * 100)}

    @atomic
    def buy(self, buyer_id: str, auction_id: int) -> dict:
        now = time.time()
        self._expire(now)
        a = self.repo.auction_get(auction_id)
        if a is None or a["status"] != "open":
            raise ValueError("Lô này không còn trên sàn.")
        if a["seller_id"] == str(buyer_id):
            raise ValueError("Không thể mua lô của chính mình (dùng `.daugia huy <id>`).")
        buyer = self.repo.get(str(buyer_id))
        seller = self.repo.get(a["seller_id"])
        if buyer is None:
            raise ValueError("Chưa có thể đạo.")
        if buyer.spirit_stones < a["price"]:
            raise ValueError(f"Không đủ Linh Thạch (cần {a['price']:,}).")
        if not self.repo.auction_set_status(a["id"], "sold", str(buyer_id)):
            raise ValueError("Lô vừa được người khác mua.")
        fee = int(a["price"] * FEE_RATE)
        buyer.spirit_stones -= a["price"]
        self.repo.save(buyer)
        if seller is not None:
            seller.spirit_stones += a["price"] - fee
            self.repo.save(seller)
        self.repo.inventory_add(str(buyer_id), a["item_id"], a["quantity"])
        return {"id": a["id"], "name": self._item_name(a["item_id"]), "qty": a["quantity"],
                "price": a["price"], "fee": fee, "stones_left": buyer.spirit_stones}

    @atomic
    def cancel(self, seller_id: str, auction_id: int) -> dict:
        a = self.repo.auction_get(auction_id)
        if a is None or a["status"] != "open":
            raise ValueError("Lô này không còn trên sàn.")
        if a["seller_id"] != str(seller_id):
            raise ValueError("Đây không phải lô của đạo hữu.")
        if not self.repo.auction_set_status(a["id"], "cancelled"):
            raise ValueError("Lô vừa được xử lý.")
        self.repo.inventory_add(str(seller_id), a["item_id"], a["quantity"])
        return {"id": a["id"], "name": self._item_name(a["item_id"]), "qty": a["quantity"]}
