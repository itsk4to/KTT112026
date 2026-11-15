"""Thin SQLite wrapper — transactions only, no game rules."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Row | None:
        return self._conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[sqlite3.Row]:
        return list(self._conn.execute(sql, params).fetchall())

    def commit(self) -> None:
        self._conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self) -> None:
        self._conn.close()
