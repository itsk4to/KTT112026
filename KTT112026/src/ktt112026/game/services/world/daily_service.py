"""Điểm danh / nhiệm vụ ngày."""
from __future__ import annotations

from datetime import date
from typing import Any

from ktt112026.game.repo.players import PlayerRepository


class DailyService:
    def __init__(self, repo: PlayerRepository) -> None:
        self.repo = repo

    def claim(self, user_id: str) -> dict[str, Any]:
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. `.taothe` trước.")
        today = date.today().isoformat()
        last = str(getattr(p, "last_daily_day", "") or "")
        if last == today:
            raise ValueError("Hôm nay đã điểm danh rồi. Mai hãy quay lại.")
        # streak
        streak = int(getattr(p, "daily_streak", 0) or 0)
        # simple: if last was yesterday +1 else reset 1
        from datetime import datetime, timedelta
        try:
            if last and (date.today() - date.fromisoformat(last)).days == 1:
                streak += 1
            else:
                streak = 1
        except ValueError:
            streak = 1
        streak = min(30, streak)
        base = 80 + p.major_realm * 20
        bonus = min(200, streak * 15)
        stones = base + bonus
        sta = min(p.max_stamina, p.stamina + 10 + min(20, streak))
        gain_sta = sta - p.stamina
        p.spirit_stones += stones
        p.stamina = sta
        p.last_daily_day = today  # type: ignore[attr-defined]
        p.daily_streak = streak  # type: ignore[attr-defined]
        self.repo.save(p)
        return {
            "stones": stones,
            "stamina": gain_sta,
            "streak": streak,
            "player": p,
        }
