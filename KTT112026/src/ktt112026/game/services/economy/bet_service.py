"""Cá cược Linh Thạch đơn giản — chẵn/lẻ hoặc mặt/xỉu (house edge nhẹ)."""
from __future__ import annotations

import random
import time
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.util.formatters import fmt_num

MIN_BET = 50
MAX_BET = 20_000
HOUSE_EDGE = 0.05  # 5%
COOLDOWN_SEC = 8


class BetService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()
        self._last: dict[str, float] = {}

    def bet(self, user_id: str, amount: int, choice: str = "chan") -> dict[str, Any]:
        amount = int(amount)
        if amount < MIN_BET or amount > MAX_BET:
            raise ValueError(f"Cược {MIN_BET}–{fmt_num(MAX_BET)} Linh Thạch.")
        choice = (choice or "chan").strip().lower()
        aliases = {
            "chan": "even", "le": "odd", "even": "even", "odd": "odd",
            "mat": "big", "xiu": "small", "tai": "big", "xiu": "small",
            "lon": "big", "nho": "small",
        }
        side = aliases.get(choice)
        if side is None:
            raise ValueError("Chọn: `chan` / `le` / `mat` / `xiu`.")

        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. `.taothe` trước.")
        if p.spirit_stones < amount:
            raise ValueError(f"Không đủ Linh Thạch (cần {fmt_num(amount)}).")

        now = time.time()
        last = self._last.get(str(user_id), 0)
        if now - last < COOLDOWN_SEC:
            raise ValueError(f"Đợi {int(COOLDOWN_SEC - (now - last))}s nữa.")

        # Roll
        roll = self.rng.randint(1, 6)
        win = False
        if side in ("even", "odd"):
            win = (roll % 2 == 0) == (side == "even")
        else:
            win = (roll >= 4) == (side == "big")

        # Payout with house edge
        if win:
            payout = int(amount * (1.0 - HOUSE_EDGE) * 2)  # ~1.9x
            net = payout - amount
        else:
            payout = 0
            net = -amount

        p.spirit_stones += net
        self.repo.save(p)
        self._last[str(user_id)] = now

        return {
            "roll": roll,
            "choice": choice,
            "side": side,
            "win": win,
            "amount": amount,
            "payout": payout,
            "net": net,
            "stones_left": p.spirit_stones,
        }
