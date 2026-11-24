"""Schema v7 — partner / songtu."""
from __future__ import annotations

SCHEMA_VERSION = 20

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
    last_stamina_tick REAL NOT NULL DEFAULT 0,
    stamina_buy_day TEXT NOT NULL DEFAULT '',
    stamina_buys_today INTEGER NOT NULL DEFAULT 0,
    dokiep_first_immune INTEGER NOT NULL DEFAULT 0,
    dokiep_fail_loss_pct INTEGER NOT NULL DEFAULT 20,
    dokiep_remove_wrong INTEGER NOT NULL DEFAULT 0,
    dokiep_extra_shield INTEGER NOT NULL DEFAULT 0,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    sect_joined_at REAL NOT NULL DEFAULT 0,
    sect_role TEXT NOT NULL DEFAULT '',
    sect_contrib INTEGER NOT NULL DEFAULT 0,
    sect_id TEXT NOT NULL DEFAULT '',
    last_daily_day TEXT NOT NULL DEFAULT '',
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

CREATE TABLE IF NOT EXISTS daily_progress (
    user_id TEXT NOT NULL,
    day_key TEXT NOT NULL,
    tu_count INTEGER NOT NULL DEFAULT 0,
    explore_count INTEGER NOT NULL DEFAULT 0,
    tower_count INTEGER NOT NULL DEFAULT 0,
    claimed_mask INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, day_key)
);

CREATE TABLE IF NOT EXISTS custom_sects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT 'any',
    owner_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    major_min INTEGER NOT NULL DEFAULT 2
);

CREATE TABLE IF NOT EXISTS sect_state (
    sect_id TEXT PRIMARY KEY,
    level INTEGER NOT NULL DEFAULT 1,
    bank_stones INTEGER NOT NULL DEFAULT 0,
    leader_id TEXT NOT NULL DEFAULT '',
    last_weekly_key TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sect_invites (
    sect_id TEXT NOT NULL,
    inviter_id TEXT NOT NULL,
    invitee_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(sect_id, invitee_id)
);

CREATE TABLE IF NOT EXISTS sect_weekly_payout (
    week_key TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    reward INTEGER NOT NULL,
    PRIMARY KEY(week_key, user_id)
);

CREATE TABLE IF NOT EXISTS redeem_codes (
    code TEXT PRIMARY KEY,
    reward_stones INTEGER NOT NULL DEFAULT 0,
    reward_item_id TEXT NOT NULL DEFAULT '',
    reward_item_qty INTEGER NOT NULL DEFAULT 0,
    max_uses INTEGER NOT NULL DEFAULT 1,
    used_count INTEGER NOT NULL DEFAULT 0,
    expires_at INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS code_redemptions (
    code TEXT NOT NULL,
    user_id TEXT NOT NULL,
    redeemed_at INTEGER NOT NULL,
    PRIMARY KEY(code, user_id)
);

CREATE TABLE IF NOT EXISTS auction_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS world_event_claims (
    day_key TEXT NOT NULL,
    event_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    claimed_at REAL NOT NULL,
    PRIMARY KEY(day_key, event_id, user_id)
);

CREATE TABLE IF NOT EXISTS pvp_challenges (
    id TEXT PRIMARY KEY,
    challenger_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    wager INTEGER NOT NULL,
    status TEXT NOT NULL,
    winner_id TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS player_missions (
    user_id TEXT NOT NULL,
    mission_id TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    claimed INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, mission_id)
);

CREATE TABLE IF NOT EXISTS sect_tower_runs (
    user_id TEXT NOT NULL,
    day_key TEXT NOT NULL,
    runs INTEGER NOT NULL DEFAULT 0,
    best_floor INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, day_key)
);

CREATE TABLE IF NOT EXISTS leader_weekly (
    week_key TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    stones INTEGER NOT NULL DEFAULT 0,
    item_id TEXT NOT NULL DEFAULT '',
    qty INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    PRIMARY KEY(week_key, user_id)
);

CREATE TABLE IF NOT EXISTS owned_pets (
    user_id TEXT NOT NULL,
    pet_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity >= 0),
    PRIMARY KEY(user_id, pet_id)
);

CREATE TABLE IF NOT EXISTS taixiu_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open', -- open | closed
    created_at REAL NOT NULL,
    closes_at REAL NOT NULL,
    roll INTEGER,
    winner TEXT,
    total_tai INTEGER NOT NULL DEFAULT 0,
    total_xiu INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS taixiu_bets (
    round_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    side TEXT NOT NULL, -- tai | xiu
    amount INTEGER NOT NULL,
    payout INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(round_id, user_id),
    FOREIGN KEY(round_id) REFERENCES taixiu_rounds(id)
);
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
        ("last_stamina_tick", "REAL NOT NULL DEFAULT 0"),
        ("stamina_buy_day", "TEXT NOT NULL DEFAULT ''"),
        ("stamina_buys_today", "INTEGER NOT NULL DEFAULT 0"),
        ("dokiep_first_immune", "INTEGER NOT NULL DEFAULT 0"),
        ("dokiep_fail_loss_pct", "INTEGER NOT NULL DEFAULT 20"),
        ("dokiep_remove_wrong", "INTEGER NOT NULL DEFAULT 0"),
        ("dokiep_extra_shield", "INTEGER NOT NULL DEFAULT 0"),
        ("daily_streak", "INTEGER NOT NULL DEFAULT 0"),
        ("sect_joined_at", "REAL NOT NULL DEFAULT 0"),
        ("sect_role", "TEXT NOT NULL DEFAULT ''"),
        ("sect_contrib", "INTEGER NOT NULL DEFAULT 0"),
        ("sect_id", "TEXT NOT NULL DEFAULT ''"),
        ("last_daily_day", "TEXT NOT NULL DEFAULT ''"),
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

# auction table created in ensure_schema patch below
