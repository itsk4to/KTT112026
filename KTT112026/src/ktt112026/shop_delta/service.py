"""Logic ticket / đơn hàng / legit của Shop Delta (SQLite, không phụ thuộc Discord)."""
from __future__ import annotations

import json
import time
from typing import Any

from .fmt import WARRANTY_HOURS


def _row(r) -> dict[str, Any] | None:
    return dict(r) if r is not None else None


class ShopTicketService:
    def __init__(self, db) -> None:
        self.db = db

    # ---------- cấu hình (đặt bằng /shopcfg, ghi đè hằng số mặc định) ----------
    def get_setting(self, key: str, default: str = "") -> str:
        r = self.db.fetchone("SELECT value FROM shop_settings WHERE key=?", (key,))
        return str(r["value"]) if r else default

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get_setting(key, str(default)) or default)
        except ValueError:
            return default

    def set_setting(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO shop_settings(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.db.commit()

    # ---------- ticket ----------
    def reserve_ticket(self, *, guild_id: int, user_id: int, kind: str, categories: list[str],
                       product_text: str, detail: str, now: float | None = None) -> dict[str, Any]:
        """Giữ chỗ id/mã đơn trước khi tạo kênh Discord (tên kênh dùng mã)."""
        now = now or time.time()
        cur = self.db.execute(
            "INSERT INTO shop_tickets(guild_id, channel_id, user_id, kind, category, categories, "
            "product_text, detail, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (str(guild_id), f"pending-{now}-{user_id}", str(user_id), kind,
             categories[0] if categories else "khac", json.dumps(categories),
             product_text, detail, now),
        )
        tid = int(cur.lastrowid)
        code = f"DL-{tid:04d}"
        self.db.execute("UPDATE shop_tickets SET code=? WHERE id=?", (code, tid))
        self.db.commit()
        return {"id": tid, "code": code}

    def attach_channel(self, ticket_id: int, channel_id: int) -> None:
        self.db.execute("UPDATE shop_tickets SET channel_id=? WHERE id=?", (str(channel_id), ticket_id))
        self.db.commit()

    def discard(self, ticket_id: int) -> None:
        self.db.execute("DELETE FROM shop_tickets WHERE id=? AND status='open'", (ticket_id,))
        self.db.commit()

    def get_by_channel(self, channel_id: int) -> dict[str, Any] | None:
        return _row(self.db.fetchone("SELECT * FROM shop_tickets WHERE channel_id=?", (str(channel_id),)))

    def get_by_code(self, code: str) -> dict[str, Any] | None:
        return _row(self.db.fetchone("SELECT * FROM shop_tickets WHERE code=?", (code.strip().upper(),)))

    def open_tickets(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM shop_tickets WHERE user_id=? AND status='open' AND channel_id NOT LIKE 'pending-%'",
            (str(user_id),),
        )
        return [dict(r) for r in rows]

    def mark_closed(self, ticket_id: int) -> None:
        self.db.execute("UPDATE shop_tickets SET status='closed' WHERE id=? AND status='open'", (ticket_id,))
        self.db.commit()

    # ---------- đơn hàng ----------
    def set_order(self, ticket_id: int, *, amount: int, product: str, channel_id: int,
                  message_id: int, now: float | None = None, keep_time: bool = False) -> None:
        if keep_time:
            self.db.execute(
                "UPDATE shop_tickets SET amount=?, order_product=?, order_channel_id=?, order_message_id=? WHERE id=?",
                (int(amount), product, str(channel_id), str(message_id), ticket_id),
            )
        else:
            self.db.execute(
                "UPDATE shop_tickets SET amount=?, order_product=?, order_channel_id=?, order_message_id=?, "
                "order_at=? WHERE id=?",
                (int(amount), product, str(channel_id), str(message_id), now or time.time(), ticket_id),
            )
        self.db.commit()

    def complete(self, channel_id: int, staff_id: int, now: float | None = None) -> dict[str, Any]:
        t = self.get_by_channel(channel_id)
        if t is None:
            raise ValueError("Kênh này không phải ticket của Shop Delta.")
        if t["status"] == "done":
            raise ValueError(f"Đơn `{t['code']}` đã hoàn thành trước đó.")
        if t["status"] != "open":
            raise ValueError("Ticket này đã đóng.")
        self.db.execute(
            "UPDATE shop_tickets SET status='done', staff_id=?, done_at=? WHERE id=? AND status='open'",
            (str(staff_id), now or time.time(), t["id"]),
        )
        self.db.commit()
        return self.get_by_channel(channel_id)  # type: ignore[return-value]

    # ---------- legit / bảo hành ----------
    def legit_count(self) -> int:
        r = self.db.fetchone("SELECT COUNT(*) AS n FROM shop_tickets WHERE legit_at>0")
        return int(r["n"]) if r else 0

    def legit(self, author_id: int, staff_id: int, code: str, now: float | None = None) -> dict[str, Any]:
        """`+1 legit @staff <mã>` — kiểm tra rồi cấp bảo hành 48h. Lỗi → ValueError (tiếng Việt)."""
        now = now or time.time()
        t = self.get_by_code(code)
        if t is None:
            raise ValueError(f"Không tìm thấy mã đơn `{code.upper()}`.")
        if t["user_id"] != str(author_id):
            raise ValueError("Mã đơn này không phải của bạn.")
        if t["status"] != "done":
            raise ValueError("Đơn này chưa được shop xác nhận hoàn thành.")
        if t["staff_id"] and t["staff_id"] != str(staff_id):
            raise ValueError(f"Đơn này do <@{t['staff_id']}> phụ trách — hãy tag đúng người bán.")
        if t["legit_at"]:
            raise ValueError(
                f"Đơn `{t['code']}` đã legit rồi, bảo hành đến <t:{int(t['warranty_until'])}:f>."
            )
        until = now + WARRANTY_HOURS * 3600
        cur = self.db.execute(
            "UPDATE shop_tickets SET legit_at=?, warranty_until=? WHERE id=? AND legit_at=0",
            (now, until, t["id"]),
        )
        self.db.commit()
        if cur.rowcount != 1:  # hai tin nhắn legit cùng lúc
            raise ValueError(f"Đơn `{t['code']}` đã legit rồi.")
        t = self.get_by_code(code)  # type: ignore[assignment]
        return {"ticket": t, "warranty_until": until, "count": self.legit_count()}
