"""Logic ticket / đơn hàng / legit của Shop Delta (SQLite, không phụ thuộc Discord)."""
from __future__ import annotations

import json
import time
from typing import Any

from .fmt import WARRANTY_HOURS, normalize_code


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
        return _row(self.db.fetchone("SELECT * FROM shop_tickets WHERE code=?", (normalize_code(code),)))

    def open_tickets(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM shop_tickets WHERE user_id=? AND status='open' AND channel_id NOT LIKE 'pending-%'",
            (str(user_id),),
        )
        return [dict(r) for r in rows]

    def open_all(self, limit: int = 25) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM shop_tickets WHERE status='open' AND channel_id NOT LIKE 'pending-%' "
            "ORDER BY id DESC LIMIT ?", (int(limit),),
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

    def complete(self, channel_id: int, staff_id: int, now: float | None = None,
                 allow_repeat: bool = False) -> dict[str, Any]:
        """Đánh dấu hoàn thành. `allow_repeat=True` cho phép /done lại để gửi lại thông báo bị lỗi."""
        t = self.get_by_channel(channel_id)
        if t is None:
            raise ValueError("Kênh này không phải ticket của Shop Delta.")
        if t["status"] == "done":
            if allow_repeat:
                return t
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

    def legit(self, author_id: int, tagged_id: int, code: str, now: float | None = None,
              seller_ids: tuple[int, ...] | list[int] = ()) -> dict[str, Any]:
        """`+1 legit <@người_bán> <mã>` — kiểm tra rồi cấp bảo hành 48h. Lỗi → ValueError (tiếng Việt).

        Người được tag phải là người bán cố định (`seller_ids`) hoặc staff đã /done đơn này.
        """
        now = now or time.time()
        t = self.get_by_code(code)
        if t is None:
            raise ValueError(f"Không tìm thấy mã đơn `{code.upper()}`.")
        if t["user_id"] != str(author_id):
            raise ValueError("Mã đơn này không phải của bạn.")
        if t["status"] != "done":
            raise ValueError("Đơn này chưa được shop xác nhận hoàn thành.")
        allowed = {str(i) for i in seller_ids} | ({t["staff_id"]} if t["staff_id"] else set())
        if allowed and str(tagged_id) not in allowed:
            right = sorted(allowed)[0]
            raise ValueError(f"Sai người bán. Hãy gửi đúng mẫu: `+1 legit <@{right}> {t['code']}`")
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

    def warranty_info(self, code: str, now: float | None = None) -> dict[str, Any] | None:
        now = now or time.time()
        t = self.get_by_code(code)
        if t is None:
            return None
        active = bool(t["legit_at"]) and t["warranty_until"] > now
        return {"ticket": t, "active": active, "expired": bool(t["legit_at"]) and not active}

    # ---------- tra cứu / thống kê ----------
    def warranty_status(self, code: str, now: float | None = None) -> dict[str, Any]:
        now = now or time.time()
        t = self.get_by_code(code)
        if t is None:
            raise ValueError(f"Không tìm thấy mã đơn `{normalize_code(code)}`.")
        if not t["legit_at"]:
            state = "chua_legit"
        elif now <= t["warranty_until"]:
            state = "con_han"
        else:
            state = "het_han"
        return {"ticket": t, "state": state}

    def stats(self, now: float | None = None) -> dict[str, Any]:
        now = now or time.time()

        def agg(since: float) -> tuple[int, int]:
            r = self.db.fetchone(
                "SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS s FROM shop_tickets "
                "WHERE status='done' AND done_at>=?", (since,))
            return int(r["n"]), int(r["s"])

        open_n = self.db.fetchone("SELECT COUNT(*) AS n FROM shop_tickets WHERE status='open' "
                                  "AND channel_id NOT LIKE 'pending-%'")
        return {
            "day": agg(now - 86400), "week": agg(now - 7 * 86400), "all": agg(0),
            "open": int(open_n["n"]), "legit": self.legit_count(),
        }
