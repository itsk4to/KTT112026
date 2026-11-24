"""Redeem codes + admin gift helpers."""
from __future__ import annotations

import secrets
import string
import time
from typing import Any

from ktt112026.game.repo.players import PlayerRepository


class CodeService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def create_code(
        self,
        *,
        code: str | None,
        stones: int,
        max_uses: int = 1,
        expires_days: int = 0,
        item_id: str = "",
        item_qty: int = 0,
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        stones = max(0, int(stones))
        max_uses = max(1, min(100_000, int(max_uses)))
        item_qty = max(0, int(item_qty))
        if stones <= 0 and not (item_id and item_qty):
            raise ValueError("Cần ít nhất Linh Thạch > 0 hoặc vật phẩm.")
        raw = (code or "").strip().upper()
        if not raw:
            alphabet = string.ascii_uppercase + string.digits
            raw = "KTT-" + "".join(secrets.choice(alphabet) for _ in range(8))
        if len(raw) < 3 or len(raw) > 32:
            raise ValueError("Mã dài 3–32 ký tự.")
        exists = self.repo.db.fetchone("SELECT code FROM redeem_codes WHERE code=?", (raw,))
        if exists:
            raise ValueError("Mã đã tồn tại.")
        now = int(time.time())
        exp = now + int(expires_days) * 86400 if expires_days > 0 else 0
        self.repo.db.execute(
            """INSERT INTO redeem_codes(
                code, reward_stones, reward_item_id, reward_item_qty,
                max_uses, used_count, expires_at, note, created_by, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                raw, stones, (item_id or "").strip().lower(), item_qty,
                max_uses, 0, exp, note[:120], created_by, now,
            ),
        )
        self.repo.db.commit()
        return {
            "code": raw,
            "stones": stones,
            "max_uses": max_uses,
            "expires_at": exp,
            "item_id": item_id,
            "item_qty": item_qty,
        }

    def list_codes(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.repo.db.fetchall(
            "SELECT code, reward_stones, reward_item_id, reward_item_qty, max_uses, used_count, expires_at, note "
            "FROM redeem_codes ORDER BY created_at DESC LIMIT ?",
            (max(1, min(50, limit)),),
        )
        return [dict(r) for r in rows]

    def delete_code(self, code: str) -> None:
        code = code.strip().upper()
        cur = self.repo.db.execute("DELETE FROM redeem_codes WHERE code=?", (code,))
        self.repo.db.commit()
        if cur.rowcount == 0:
            raise ValueError("Không tìm thấy mã.")

    def redeem(self, user_id: str, code: str) -> dict[str, Any]:
        code = code.strip().upper()
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        row = self.repo.db.fetchone("SELECT * FROM redeem_codes WHERE code=?", (code,))
        if not row:
            raise ValueError("Mã không hợp lệ.")
        now = int(time.time())
        exp = int(row["expires_at"] or 0)
        if exp and now > exp:
            raise ValueError("Mã đã hết hạn.")
        if int(row["used_count"]) >= int(row["max_uses"]):
            raise ValueError("Mã đã hết lượt sử dụng.")
        used = self.repo.db.fetchone(
            "SELECT 1 FROM code_redemptions WHERE code=? AND user_id=?",
            (code, str(user_id)),
        )
        if used:
            raise ValueError("Bạn đã nhập mã này rồi.")
        stones = int(row["reward_stones"] or 0)
        item_id = str(row["reward_item_id"] or "")
        item_qty = int(row["reward_item_qty"] or 0)
        if stones:
            p.spirit_stones += stones
            self.repo.save(p)
        if item_id and item_qty > 0:
            self.repo.inventory_add(user_id, item_id, item_qty)
        self.repo.db.execute(
            "UPDATE redeem_codes SET used_count = used_count + 1 WHERE code=?",
            (code,),
        )
        self.repo.db.execute(
            "INSERT INTO code_redemptions(code, user_id, redeemed_at) VALUES(?,?,?)",
            (code, str(user_id), now),
        )
        self.repo.db.commit()
        return {
            "code": code,
            "stones": stones,
            "item_id": item_id,
            "item_qty": item_qty,
            "stones_left": p.spirit_stones,
        }

    def gift_stones(self, user_id: str, amount: int) -> dict[str, Any]:
        amount = int(amount)
        if amount == 0:
            raise ValueError("Số LS khác 0.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Người chơi chưa `.taothe`.")
        p.spirit_stones = max(0, p.spirit_stones + amount)
        self.repo.save(p)
        return {"user_id": user_id, "name": p.display_name, "stones": p.spirit_stones, "delta": amount}

    def lookup(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo.")
        return {
            "user_id": p.user_id,
            "name": p.display_name,
            "stones": p.spirit_stones,
            "major": p.major_realm,
            "minor": p.minor_stage,
            "path": p.path,
            "faction": p.faction,
            "cultivation": p.cultivation,
            "stamina": f"{p.stamina}/{p.max_stamina}",
        }
