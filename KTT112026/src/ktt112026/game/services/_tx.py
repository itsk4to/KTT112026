"""Decorator: chạy cả use-case trong một transaction (chống dupe / mất đồ khi lỗi giữa chừng)."""
from __future__ import annotations

import functools
from typing import Any, Callable


def atomic(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        repo = getattr(self, "repo", None) or getattr(self, "players")
        with repo.db.transaction():
            return fn(self, *args, **kwargs)

    return wrapper
