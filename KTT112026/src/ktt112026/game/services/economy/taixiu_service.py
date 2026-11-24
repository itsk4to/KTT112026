"""Tài Xỉu bàn chung — xem cược rồi mới đặt, đóng ván mới roll."""
from __future__ import annotations

import time
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num

MIN_BET = 50
MAX_BET = 50_000
ROUND_SECONDS = 60
HOUSE_EDGE = 0.05


class TaiXiuService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def _now(self) -> float:
        return time.time()

    def get_or_create_open(self, guild_id: str) -> dict[str, Any]:
        guild_id = str(guild_id)
        row = self.repo.db.fetchone(
            "SELECT * FROM taixiu_rounds WHERE guild_id=? AND status='open' ORDER BY id DESC LIMIT 1",
            (guild_id,),
        )
        now = self._now()
        if row and row["closes_at"] > now:
            return self._round_to_dict(row)

        # Close expired open rounds
        self.repo.db.execute(
            "UPDATE taixiu_rounds SET status='closed' WHERE guild_id=? AND status='open' AND closes_at<=?",
            (guild_id, now),
        )
        self.repo.db.commit()

        # Create new
        closes = now + ROUND_SECONDS
        self.repo.db.execute(
            "INSERT INTO taixiu_rounds(guild_id, status, created_at, closes_at) VALUES(?, 'open', ?, ?)",
            (guild_id, now, closes),
        )
        self.repo.db.commit()
        new_id = self.repo.db.fetchone("SELECT last_insert_rowid() AS id")["id"]
        row = self.repo.db.fetchone("SELECT * FROM taixiu_rounds WHERE id=?", (new_id,))
        return self._round_to_dict(row)

    def place_bet(self, guild_id: str, user_id: str, amount: int, side: str) -> dict[str, Any]:
        amount = int(amount)
        side = (side or "").strip().lower()
        if side not in ("tai", "xiu"):
            raise ValueError("Chọn `tai` hoặc `xiu`.")
        if amount < MIN_BET or amount > MAX_BET:
            raise ValueError(f"Cược {MIN_BET}–{fmt_num(MAX_BET)} Linh Thạch.")

        rnd = self.get_or_create_open(guild_id)
        if rnd["status"] != "open" or rnd["closes_at"] <= self._now():
            raise ValueError("Bàn đã đóng.")

        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. `.taothe` trước.")
        if p.spirit_stones < amount:
            raise ValueError(f"Không đủ Linh Thạch (cần {fmt_num(amount)}).")

        # Check existing bet
        existing = self.repo.db.fetchone(
            "SELECT amount, side FROM taixiu_bets WHERE round_id=? AND user_id=?",
            (rnd["id"], str(user_id)),
        )
        if existing:
            raise ValueError("Bạn đã đặt cược ván này rồi.")

        # Deduct
        p.spirit_stones -= amount
        self.repo.save(p)

        self.repo.db.execute(
            "INSERT INTO taixiu_bets(round_id, user_id, side, amount) VALUES(?, ?, ?, ?)",
            (rnd["id"], str(user_id), side, amount),
        )
        if side == "tai":
            self.repo.db.execute(
                "UPDATE taixiu_rounds SET total_tai = total_tai + ? WHERE id=?",
                (amount, rnd["id"]),
            )
        else:
            self.repo.db.execute(
                "UPDATE taixiu_rounds SET total_xiu = total_xiu + ? WHERE id=?",
                (amount, rnd["id"]),
            )
        self.repo.db.commit()

        return self.status(guild_id)

    def status(self, guild_id: str) -> dict[str, Any]:
        rnd = self.get_or_create_open(guild_id)
        bets = self.repo.db.fetchall(
            "SELECT user_id, side, amount FROM taixiu_bets WHERE round_id=? ORDER BY amount DESC",
            (rnd["id"],),
        )
        left = max(0, int(rnd["closes_at"] - self._now()))
        return {
            **rnd,
            "time_left": left,
            "bets": [dict(b) for b in bets],
            "count": len(bets),
        }

    def close_and_roll(self, guild_id: str) -> dict[str, Any]:
        rnd = self.get_or_create_open(guild_id)
        if rnd["status"] != "open":
            raise ValueError("Không có bàn đang mở.")

        # Roll 1-6, >=4 = Tài
        import random
        roll = random.randint(1, 6)
        winner = "tai" if roll >= 4 else "xiu"

        self.repo.db.execute(
            "UPDATE taixiu_rounds SET status='closed', roll=?, winner=? WHERE id=?",
            (roll, winner, rnd["id"]),
        )

        # Payout
        bets = self.repo.db.fetchall(
            "SELECT user_id, side, amount FROM taixiu_bets WHERE round_id=?",
            (rnd["id"],),
        )
        results = []
        for b in bets:
            uid = b["user_id"]
            amount = b["amount"]
            side = b["side"]
            p = self.repo.get(uid)
            if p is None:
                continue
            if side == winner:
                payout = int(amount * (1.0 - HOUSE_EDGE) * 2)
                p.spirit_stones += payout
                self.repo.save(p)
                self.repo.db.execute(
                    "UPDATE taixiu_bets SET payout=? WHERE round_id=? AND user_id=?",
                    (payout, rnd["id"], uid),
                )
                results.append({"user_id": uid, "win": True, "net": payout - amount, "amount": amount})
            else:
                results.append({"user_id": uid, "win": False, "net": -amount, "amount": amount})

        self.repo.db.commit()

        return {
            "roll": roll,
            "winner": winner,
            "results": results,
            "total_tai": rnd["total_tai"],
            "total_xiu": rnd["total_xiu"],
        }

    def _round_to_dict(self, row) -> dict[str, Any]:
        if row is None:
            return {}
        d = dict(row)
        return d
