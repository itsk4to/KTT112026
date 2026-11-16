"""Sàn đấu giá tối giản — đăng / xem / mua ngay."""
from __future__ import annotations

import time
from typing import Any

from ktt112026.game.content.loader import catalog_by_id
from ktt112026.game.repo.players import PlayerRepository

DURATION = 48 * 3600
MAX_LISTINGS_PER_USER = 5
TAX_RATE = 0.05  # 5% phí người bán


class AuctionService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo
        self.items = catalog_by_id()

    def _purge(self) -> None:
        now = int(time.time())
        rows = self.repo.db.fetchall(
            "SELECT id, seller_id, item_id, quantity FROM auction_listings WHERE expires_at < ?",
            (now,),
        )
        for r in rows:
            self.repo.inventory_add(str(r["seller_id"]), str(r["item_id"]), int(r["quantity"]))
            self.repo.db.execute("DELETE FROM auction_listings WHERE id=?", (int(r["id"]),))
        if rows:
            self.repo.db.commit()

    def list_open(self, limit: int = 15) -> list[dict[str, Any]]:
        self._purge()
        rows = self.repo.db.fetchall(
            "SELECT id, seller_id, item_id, quantity, price, expires_at FROM auction_listings "
            "WHERE expires_at >= ? ORDER BY id DESC LIMIT ?",
            (int(time.time()), limit),
        )
        out = []
        for r in rows:
            meta = self.items.get(str(r["item_id"]), {})
            out.append({
                "id": int(r["id"]),
                "seller_id": str(r["seller_id"]),
                "item_id": str(r["item_id"]),
                "name": meta.get("name", r["item_id"]),
                "quantity": int(r["quantity"]),
                "price": int(r["price"]),
                "expires_at": int(r["expires_at"]),
            })
        return out

    def create(self, seller_id: str, item_id: str, price: int, qty: int = 1) -> dict:
        self._purge()
        item_id = item_id.strip().lower()
        price = int(price)
        qty = max(1, min(99, int(qty)))
        if price < 10:
            raise ValueError("Giá tối thiểu 10 Linh Thạch.")
        p = self.repo.get(str(seller_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        if self.repo.inventory_qty(seller_id, item_id) < qty:
            raise ValueError("Túi không đủ vật phẩm.")
        cnt = self.repo.db.fetchone(
            "SELECT COUNT(*) AS c FROM auction_listings WHERE seller_id=?",
            (str(seller_id),),
        )
        if cnt and int(cnt["c"]) >= MAX_LISTINGS_PER_USER:
            raise ValueError(f"Tối đa {MAX_LISTINGS_PER_USER} tin đăng.")
        if not self.repo.inventory_remove(seller_id, item_id, qty):
            raise ValueError("Không trừ được túi đồ.")
        now = int(time.time())
        self.repo.db.execute(
            "INSERT INTO auction_listings(seller_id, item_id, quantity, price, created_at, expires_at) "
            "VALUES(?,?,?,?,?,?)",
            (str(seller_id), item_id, qty, price, now, now + DURATION),
        )
        self.repo.db.commit()
        lid = self.repo.db.fetchone("SELECT last_insert_rowid() AS id")["id"]
        name = self.items.get(item_id, {}).get("name", item_id)
        return {"id": int(lid), "name": name, "qty": qty, "price": price}

    def buy(self, buyer_id: str, listing_id: int) -> dict:
        self._purge()
        row = self.repo.db.fetchone(
            "SELECT * FROM auction_listings WHERE id=?",
            (int(listing_id),),
        )
        if not row:
            raise ValueError("Tin không tồn tại hoặc đã hết hạn.")
        if str(row["seller_id"]) == str(buyer_id):
            raise ValueError("Không mua tin của chính mình.")
        buyer = self.repo.get(str(buyer_id))
        seller = self.repo.get(str(row["seller_id"]))
        if buyer is None:
            raise ValueError("Chưa có thể đạo.")
        price = int(row["price"])
        if buyer.spirit_stones < price:
            raise ValueError("Không đủ Linh Thạch.")
        buyer.spirit_stones -= price
        fee = int(price * TAX_RATE)
        gain = price - fee
        if seller:
            seller.spirit_stones += gain
            self.repo.save(seller)
        self.repo.save(buyer)
        self.repo.inventory_add(buyer_id, str(row["item_id"]), int(row["quantity"]))
        self.repo.db.execute("DELETE FROM auction_listings WHERE id=?", (int(listing_id),))
        self.repo.db.commit()
        name = self.items.get(str(row["item_id"]), {}).get("name", row["item_id"])
        return {"name": name, "qty": int(row["quantity"]), "price": price, "fee": fee}
