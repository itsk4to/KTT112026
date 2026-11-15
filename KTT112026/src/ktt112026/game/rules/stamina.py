"""Hồi Thể Lực ngoại tuyến (GDD: Offline AP Recovery) — công thức thuần."""
from __future__ import annotations

# 1 điểm Thể Lực mỗi 3 phút, tính theo thời gian thực kể cả khi người chơi offline.
REGEN_INTERVAL_SECONDS = 180.0


def regen(
    stamina: int,
    max_stamina: int,
    last_at: float,
    now: float,
    interval: float = REGEN_INTERVAL_SECONDS,
) -> tuple[int, float]:
    """Trả về (stamina mới, mốc thời gian hồi mới). Phần dư thời gian được giữ lại."""
    if stamina >= max_stamina:
        return stamina, now
    if last_at <= 0 or now <= last_at:
        return stamina, now if last_at <= 0 else last_at
    ticks = int((now - last_at) // interval)
    if ticks <= 0:
        return stamina, last_at
    new = min(max_stamina, stamina + ticks)
    if new >= max_stamina:
        return new, now
    return new, last_at + ticks * interval


def seconds_to_full(stamina: int, max_stamina: int, last_at: float, now: float,
                    interval: float = REGEN_INTERVAL_SECONDS) -> int:
    missing = max(0, max_stamina - stamina)
    if missing == 0:
        return 0
    into_tick = max(0.0, now - last_at) % interval if last_at > 0 else 0.0
    return int(missing * interval - into_tick)
