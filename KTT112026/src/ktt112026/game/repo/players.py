"""Player + inventory + techniques + pets + limits."""
from __future__ import annotations

import time
import json
from datetime import date
from typing import Any

from ktt112026.db.connection import Database
from ktt112026.game.models.player import Player, PlayerStats
from ktt112026.game.rules.stamina import regen


def _row_to_player(row: Any) -> Player:
    def g(name: str, default=None):
        try:
            return row[name]
        except (IndexError, KeyError):
            return default

    return Player(
        user_id=str(row["user_id"]),
        display_name=str(row["display_name"]),
        major_realm=int(row["major_realm"]),
        minor_stage=int(row["minor_stage"]),
        path=str(g("path") or ""),
        faction=str(g("faction") or ""),
        cultivation=int(row["cultivation"]),
        spirit_stones=int(row["spirit_stones"]),
        stamina=int(row["stamina"]),
        max_stamina=int(row["max_stamina"]),
        stats=PlayerStats(
            can_cot=int(row["can_cot"]),
            ngo_tinh=int(row["ngo_tinh"]),
            than_thuc=int(row["than_thuc"]),
            than_phap=int(row["than_phap"]),
            khi_van=int(row["khi_van"]),
        ),
        root_system=str(row["root_system"]),
        root_quality=str(row["root_quality"]),
        weapon1=str(g("weapon1") or ""),
        weapon2=str(g("weapon2") or ""),
        treasure=str(g("treasure") or ""),
        pet1=str(g("pet1") or ""),
        pet2=str(g("pet2") or ""),
        pet3=str(g("pet3") or ""),
        last_cultivate_at=float(g("last_cultivate_at") or 0),
        last_tower_day=str(g("last_tower_day") or ""),
        tower_runs_today=int(g("tower_runs_today") or 0),
        cultivate_bonus_pct=int(g("cultivate_bonus_pct") or 0),
        cultivate_bonus_charges=int(g("cultivate_bonus_charges") or 0),
        last_gather_day=str(g("last_gather_day") or ""),
        gather_count_today=int(g("gather_count_today") or 0),
        last_bicanh_at=float(g("last_bicanh_at") or 0),
        partner_id=str(g("partner_id") or ""),
        last_songtu_at=float(g("last_songtu_at") or 0),
        last_stamina_at=float(g("last_stamina_at") or 0),
        stamina_buy_day=str(g("stamina_buy_day") or ""),
        stamina_buy_count=int(g("stamina_buy_count") or 0),
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


class PlayerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def atomic(self):
        """`with repo.atomic():` — mọi ghi DB trong khối cùng commit / cùng rollback."""
        return self.db.transaction()

    def get(self, user_id: str) -> Player | None:
        row = self.db.fetchone("SELECT * FROM players WHERE user_id=?", (str(user_id),))
        if not row:
            return None
        player = _row_to_player(row)
        # Hồi Thể Lực theo thời gian thực (kể cả lúc offline). Được lưu khi service gọi save().
        player.stamina, player.last_stamina_at = regen(
            player.stamina, player.max_stamina, player.last_stamina_at, time.time()
        )
        return player

    _COLUMNS = (
        "user_id", "display_name", "major_realm", "minor_stage", "path", "faction",
        "cultivation", "spirit_stones", "stamina", "max_stamina",
        "can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van",
        "root_system", "root_quality", "weapon1", "weapon2", "treasure",
        "pet1", "pet2", "pet3",
        "last_cultivate_at", "last_tower_day", "tower_runs_today",
        "cultivate_bonus_pct", "cultivate_bonus_charges",
        "last_gather_day", "gather_count_today", "last_bicanh_at",
        "partner_id", "last_songtu_at",
        "last_stamina_at", "stamina_buy_day", "stamina_buy_count",
        "created_at", "updated_at",
    )

    @staticmethod
    def _values(player: Player) -> dict[str, Any]:
        s = player.stats.clamped()
        return {
            "user_id": player.user_id, "display_name": player.display_name,
            "major_realm": player.major_realm, "minor_stage": player.minor_stage,
            "path": player.path, "faction": player.faction,
            "cultivation": player.cultivation, "spirit_stones": player.spirit_stones,
            "stamina": player.stamina, "max_stamina": player.max_stamina,
            "can_cot": s.can_cot, "ngo_tinh": s.ngo_tinh, "than_thuc": s.than_thuc,
            "than_phap": s.than_phap, "khi_van": s.khi_van,
            "root_system": player.root_system, "root_quality": player.root_quality,
            "weapon1": player.weapon1, "weapon2": player.weapon2, "treasure": player.treasure,
            "pet1": player.pet1, "pet2": player.pet2, "pet3": player.pet3,
            "last_cultivate_at": player.last_cultivate_at,
            "last_tower_day": player.last_tower_day, "tower_runs_today": player.tower_runs_today,
            "cultivate_bonus_pct": player.cultivate_bonus_pct,
            "cultivate_bonus_charges": player.cultivate_bonus_charges,
            "last_gather_day": player.last_gather_day,
            "gather_count_today": player.gather_count_today,
            "last_bicanh_at": player.last_bicanh_at,
            "partner_id": player.partner_id, "last_songtu_at": player.last_songtu_at,
            "last_stamina_at": player.last_stamina_at,
            "stamina_buy_day": player.stamina_buy_day,
            "stamina_buy_count": player.stamina_buy_count,
            "created_at": player.created_at, "updated_at": player.updated_at,
        }

    def insert(self, player: Player) -> None:
        player.ensure_invariants()
        now = int(time.time())
        player.created_at = player.created_at or now
        player.updated_at = now
        player.last_stamina_at = player.last_stamina_at or float(now)
        vals = self._values(player)
        cols = self._COLUMNS
        self.db.execute(
            f"INSERT INTO players({', '.join(cols)}) VALUES({', '.join('?' for _ in cols)})",
            tuple(vals[c] for c in cols),
        )
        self.db.commit()

    def save(self, player: Player) -> None:
        player.ensure_invariants()
        player.updated_at = int(time.time())
        vals = self._values(player)
        cols = [c for c in self._COLUMNS if c not in ("user_id", "created_at")]
        self.db.execute(
            f"UPDATE players SET {', '.join(c + '=?' for c in cols)} WHERE user_id=?",
            tuple(vals[c] for c in cols) + (player.user_id,),
        )
        self.db.commit()

    def inventory_list(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT item_id, quantity FROM inventory WHERE user_id=? AND quantity>0 ORDER BY item_id",
            (str(user_id),),
        )
        return [{"item_id": r["item_id"], "quantity": int(r["quantity"])} for r in rows]

    def inventory_qty(self, user_id: str, item_id: str) -> int:
        row = self.db.fetchone(
            "SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",
            (str(user_id), str(item_id)),
        )
        return int(row["quantity"]) if row else 0

    def inventory_add(self, user_id: str, item_id: str, qty: int) -> None:
        self.db.execute(
            """INSERT INTO inventory(user_id, item_id, quantity) VALUES(?,?,?)
               ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (str(user_id), str(item_id), int(qty)),
        )
        self.db.commit()

    def inventory_remove(self, user_id: str, item_id: str, qty: int) -> bool:
        have = self.inventory_qty(user_id, item_id)
        if have < qty:
            return False
        self.db.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE user_id=? AND item_id=?",
            (int(qty), str(user_id), str(item_id)),
        )
        self.db.commit()
        return True

    def list_techniques(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT technique_id, tier FROM learned_techniques WHERE user_id=? ORDER BY technique_id",
            (str(user_id),),
        )
        return [{"technique_id": r["technique_id"], "tier": int(r["tier"])} for r in rows]

    def get_technique_tier(self, user_id: str, technique_id: str) -> int:
        row = self.db.fetchone(
            "SELECT tier FROM learned_techniques WHERE user_id=? AND technique_id=?",
            (str(user_id), str(technique_id)),
        )
        return int(row["tier"]) if row else 0

    def set_technique_tier(self, user_id: str, technique_id: str, tier: int) -> None:
        self.db.execute(
            """INSERT INTO learned_techniques(user_id, technique_id, tier) VALUES(?,?,?)
               ON CONFLICT(user_id, technique_id) DO UPDATE SET tier=excluded.tier""",
            (str(user_id), str(technique_id), int(tier)),
        )
        self.db.commit()

    def get_use_limit(self, user_id: str, item_id: str) -> dict[str, Any]:
        row = self.db.fetchone(
            "SELECT day_key, day_count, life_count FROM item_use_limits WHERE user_id=? AND item_id=?",
            (str(user_id), str(item_id)),
        )
        if not row:
            return {"day_key": "", "day_count": 0, "life_count": 0}
        return {
            "day_key": str(row["day_key"] or ""),
            "day_count": int(row["day_count"]),
            "life_count": int(row["life_count"]),
        }

    def bump_use_limit(self, user_id: str, item_id: str, *, day: bool, life: bool) -> None:
        today = date.today().isoformat()
        cur = self.get_use_limit(user_id, item_id)
        day_count = cur["day_count"] if cur["day_key"] == today else 0
        if day:
            day_count += 1
        life_count = cur["life_count"] + (1 if life else 0)
        self.db.execute(
            """INSERT INTO item_use_limits(user_id, item_id, day_key, day_count, life_count)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id, item_id) DO UPDATE SET
                 day_key=excluded.day_key,
                 day_count=excluded.day_count,
                 life_count=excluded.life_count""",
            (str(user_id), str(item_id), today, day_count, life_count),
        )
        self.db.commit()

    # pets ownership
    def list_pets(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT pet_id, quantity FROM owned_pets WHERE user_id=? AND quantity>0 ORDER BY pet_id",
            (str(user_id),),
        )
        return [{"pet_id": r["pet_id"], "quantity": int(r["quantity"])} for r in rows]

    def pet_qty(self, user_id: str, pet_id: str) -> int:
        row = self.db.fetchone(
            "SELECT quantity FROM owned_pets WHERE user_id=? AND pet_id=?",
            (str(user_id), str(pet_id)),
        )
        return int(row["quantity"]) if row else 0

    def pet_add(self, user_id: str, pet_id: str, qty: int = 1) -> None:
        self.db.execute(
            """INSERT INTO owned_pets(user_id, pet_id, quantity) VALUES(?,?,?)
               ON CONFLICT(user_id, pet_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (str(user_id), str(pet_id), int(qty)),
        )
        self.db.commit()

    # --- buffs (đan hỗ trợ Độ Kiếp chờ được dùng ở lần .dokiep kế tiếp) ---
    def buff_set(self, user_id: str, kind: str, value: dict[str, Any]) -> None:
        self.db.execute(
            """INSERT INTO player_buffs(user_id, kind, value) VALUES(?,?,?)
               ON CONFLICT(user_id, kind) DO UPDATE SET value=excluded.value""",
            (str(user_id), str(kind), json.dumps(value, ensure_ascii=False)),
        )
        self.db.commit()

    def buff_list(self, user_id: str, prefix: str = "") -> dict[str, dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT kind, value FROM player_buffs WHERE user_id=? AND kind LIKE ?",
            (str(user_id), prefix + "%"),
        )
        return {r["kind"]: json.loads(r["value"] or "{}") for r in rows}

    def buff_clear(self, user_id: str, prefix: str = "") -> None:
        self.db.execute(
            "DELETE FROM player_buffs WHERE user_id=? AND kind LIKE ?",
            (str(user_id), prefix + "%"),
        )
        self.db.commit()

    # --- auctions (Sàn Đấu Giá) ---
    def auction_create(self, seller_id: str, item_id: str, quantity: int, price: int,
                       created_at: float, expires_at: float) -> int:
        cur = self.db.execute(
            "INSERT INTO auctions(seller_id, item_id, quantity, price, created_at, expires_at) "
            "VALUES(?,?,?,?,?,?)",
            (str(seller_id), str(item_id), int(quantity), int(price), created_at, expires_at),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def auction_get(self, auction_id: int) -> dict[str, Any] | None:
        row = self.db.fetchone("SELECT * FROM auctions WHERE id=?", (int(auction_id),))
        return dict(row) if row else None

    def auction_list_open(self, limit: int = 10, seller_id: str | None = None) -> list[dict[str, Any]]:
        if seller_id is not None:
            rows = self.db.fetchall(
                "SELECT * FROM auctions WHERE status='open' AND seller_id=? ORDER BY id DESC LIMIT ?",
                (str(seller_id), int(limit)),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM auctions WHERE status='open' ORDER BY id DESC LIMIT ?", (int(limit),)
            )
        return [dict(r) for r in rows]

    def auction_open_count(self, seller_id: str) -> int:
        row = self.db.fetchone(
            "SELECT COUNT(*) AS n FROM auctions WHERE status='open' AND seller_id=?", (str(seller_id),)
        )
        return int(row["n"]) if row else 0

    def auction_set_status(self, auction_id: int, status: str, buyer_id: str = "") -> bool:
        """Chỉ đổi từ 'open' — chống bán/hủy hai lần cùng một lô."""
        cur = self.db.execute(
            "UPDATE auctions SET status=?, buyer_id=? WHERE id=? AND status='open'",
            (status, str(buyer_id), int(auction_id)),
        )
        self.db.commit()
        return cur.rowcount == 1

    def auction_expired_open(self, now: float) -> list[dict[str, Any]]:
        rows = self.db.fetchall(
            "SELECT * FROM auctions WHERE status='open' AND expires_at<=?", (now,)
        )
        return [dict(r) for r in rows]

    def leaderboard(self, kind: str, limit: int = 10) -> list[dict]:
        limit = max(1, min(25, int(limit)))
        kind = (kind or "tuvi").lower()
        if kind in ("tien", "ls", "stones"):
            rows = self.db.fetchall(
                "SELECT user_id, display_name, spirit_stones AS score, major_realm, minor_stage, path, faction "
                "FROM players ORDER BY spirit_stones DESC, major_realm DESC LIMIT ?",
                (limit,),
            )
        elif kind in ("cancot", "cot", "can_cot"):
            rows = self.db.fetchall(
                "SELECT user_id, display_name, can_cot AS score, major_realm, minor_stage, path, faction "
                "FROM players ORDER BY can_cot DESC, major_realm DESC LIMIT ?",
                (limit,),
            )
        elif kind in ("tongmon", "faction"):
            rows = self.db.fetchall(
                "SELECT user_id, display_name, major_realm AS score, cultivation, minor_stage, path, faction "
                "FROM players WHERE faction='tongmon' "
                "ORDER BY major_realm DESC, cultivation DESC LIMIT ?",
                (limit,),
            )
        else:
            rows = self.db.fetchall(
                "SELECT user_id, display_name, major_realm, minor_stage, cultivation, path, faction, "
                "(major_realm * 1000000000 + minor_stage * 100000000 + cultivation) AS score "
                "FROM players ORDER BY major_realm DESC, minor_stage DESC, cultivation DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]
