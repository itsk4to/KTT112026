"""Schema v8 — offline stamina, dokiep buffs, auction house."""
from __future__ import annotations

SCHEMA_VERSION = 8

DDL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    major_realm INTEGER NOT NULL DEFAULT 1,
    minor_stage INTEGER NOT NULL DEFAULT 0,
    path TEXT NOT NULL DEFAULT '',
    faction TEXT NOT NULL DEFAULT '',
    cultivation INTEGER NOT NULL DEFAULT 0,
    spirit_stones INTEGER NOT NULL DEFAULT 100,
    stamina INTEGER NOT NULL DEFAULT 100,
    max_stamina INTEGER NOT NULL DEFAULT 100,
    can_cot INTEGER NOT NULL DEFAULT 50,
    ngo_tinh INTEGER NOT NULL DEFAULT 50,
    than_thuc INTEGER NOT NULL DEFAULT 50,
    than_phap INTEGER NOT NULL DEFAULT 50,
    khi_van INTEGER NOT NULL DEFAULT 50,
    root_system TEXT NOT NULL DEFAULT 'kim',
    root_quality TEXT NOT NULL DEFAULT 'tap',
    weapon1 TEXT NOT NULL DEFAULT '',
    weapon2 TEXT NOT NULL DEFAULT '',
    treasure TEXT NOT NULL DEFAULT '',
    pet1 TEXT NOT NULL DEFAULT '',
    pet2 TEXT NOT NULL DEFAULT '',
    pet3 TEXT NOT NULL DEFAULT '',
    last_cultivate_at REAL NOT NULL DEFAULT 0,
    last_tower_day TEXT NOT NULL DEFAULT '',
    tower_runs_today INTEGER NOT NULL DEFAULT 0,
    cultivate_bonus_pct INTEGER NOT NULL DEFAULT 0,
    cultivate_bonus_charges INTEGER NOT NULL DEFAULT 0,
    last_gather_day TEXT NOT NULL DEFAULT '',
    gather_count_today INTEGER NOT NULL DEFAULT 0,
    last_bicanh_at REAL NOT NULL DEFAULT 0,
    partner_id TEXT NOT NULL DEFAULT '',
    last_songtu_at REAL NOT NULL DEFAULT 0,
    last_stamina_at REAL NOT NULL DEFAULT 0,
    stamina_buy_day TEXT NOT NULL DEFAULT '',
    stamina_buy_count INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    user_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    PRIMARY KEY(user_id, item_id)
);

CREATE TABLE IF NOT EXISTS learned_techniques (
    user_id TEXT NOT NULL,
    technique_id TEXT NOT NULL,
    tier INTEGER NOT NULL DEFAULT 1 CHECK(tier >= 1 AND tier <= 5),
    PRIMARY KEY(user_id, technique_id)
);

CREATE TABLE IF NOT EXISTS item_use_limits (
    user_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    day_key TEXT NOT NULL DEFAULT '',
    day_count INTEGER NOT NULL DEFAULT 0,
    life_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, item_id)
);

CREATE TABLE IF NOT EXISTS owned_pets (
    user_id TEXT NOT NULL,
    pet_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity >= 0),
    PRIMARY KEY(user_id, pet_id)
);

CREATE TABLE IF NOT EXISTS player_buffs (
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    value TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY(user_id, kind)
);

CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    price INTEGER NOT NULL CHECK(price > 0),
    status TEXT NOT NULL DEFAULT 'open',
    buyer_id TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auctions_open ON auctions(status, expires_at);
"""


def ensure_schema(db) -> None:
    db._conn.executescript(DDL)
    cols = {r[1] for r in db._conn.execute("PRAGMA table_info(players)").fetchall()}
    for col, decl in [
        ("weapon1", "TEXT NOT NULL DEFAULT ''"),
        ("weapon2", "TEXT NOT NULL DEFAULT ''"),
        ("treasure", "TEXT NOT NULL DEFAULT ''"),
        ("pet1", "TEXT NOT NULL DEFAULT ''"),
        ("pet2", "TEXT NOT NULL DEFAULT ''"),
        ("pet3", "TEXT NOT NULL DEFAULT ''"),
        ("last_tower_day", "TEXT NOT NULL DEFAULT ''"),
        ("tower_runs_today", "INTEGER NOT NULL DEFAULT 0"),
        ("cultivate_bonus_pct", "INTEGER NOT NULL DEFAULT 0"),
        ("cultivate_bonus_charges", "INTEGER NOT NULL DEFAULT 0"),
        ("last_gather_day", "TEXT NOT NULL DEFAULT ''"),
        ("gather_count_today", "INTEGER NOT NULL DEFAULT 0"),
        ("last_bicanh_at", "REAL NOT NULL DEFAULT 0"),
        ("partner_id", "TEXT NOT NULL DEFAULT ''"),
        ("last_songtu_at", "REAL NOT NULL DEFAULT 0"),
        ("last_stamina_at", "REAL NOT NULL DEFAULT 0"),
        ("stamina_buy_day", "TEXT NOT NULL DEFAULT ''"),
        ("stamina_buy_count", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        if col not in cols:
            try:
                db.execute(f"ALTER TABLE players ADD COLUMN {col} {decl}")
            except Exception:
                pass
    row = db.fetchone("SELECT value FROM schema_meta WHERE key='schema_version'")
    if row is None:
        db.execute("INSERT INTO schema_meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
    else:
        db.execute("UPDATE schema_meta SET value=? WHERE key='schema_version'", (str(SCHEMA_VERSION),))
    db.commit()
