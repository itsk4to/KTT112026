"""Load game content from JSON data files."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=16)
def load_danduoc() -> list[dict[str, Any]]:
    return list(_load("danduoc.json")["items"])


@lru_cache(maxsize=16)
def load_linhthu() -> list[dict[str, Any]]:
    return list(_load("linhthu.json")["items"])


@lru_cache(maxsize=16)
def load_congphap() -> list[dict[str, Any]]:
    return list(_load("congphap.json")["items"])


@lru_cache(maxsize=16)
def load_vukhi() -> list[dict[str, Any]]:
    return list(_load("vukhi.json")["items"])


@lru_cache(maxsize=16)
def load_phapbao() -> list[dict[str, Any]]:
    return list(_load("phapbao.json")["items"])


@lru_cache(maxsize=16)
def load_zones() -> list[dict[str, Any]]:
    return list(_load("zones.json")["zones"])


@lru_cache(maxsize=16)
def load_herbs() -> list[dict[str, Any]]:
    return list(_load("herbs.json")["items"])


@lru_cache(maxsize=16)
def load_recipes() -> list[dict[str, Any]]:
    return list(_load("recipes.json")["recipes"])


def catalog_by_id() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for kind, loader in (
        ("danduoc", load_danduoc),
        ("linhthu", load_linhthu),
        ("congphap", load_congphap),
        ("vukhi", load_vukhi),
        ("phapbao", load_phapbao),
        ("herb", load_herbs),
    ):
        for it in loader():
            row = dict(it)
            row.setdefault("kind", kind)
            out[row["id"]] = row
    return out


def shop_stats_line(item: dict[str, Any]) -> str:
    if item.get("desc"):
        return str(item["desc"])
    parts = []
    for k, v in (item.get("bonuses") or {}).items():
        parts.append(f"+{v} {k}")
    for k, v in (item.get("penalties") or {}).items():
        parts.append(f"{v} {k}")
    return ", ".join(parts) if parts else ""
