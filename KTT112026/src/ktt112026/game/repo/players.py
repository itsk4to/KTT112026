"""Player + inventory + techniques + pets + limits."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from ktt112026.db.connection import Database
from ktt112026.game.models.player import Player, PlayerStats


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
        last_stamina_tick=float(g("last_stamina_tick") or 0),
        stamina_buy_day=str(g("stamina_buy_day") or ""),
        stamina_buys_today=int(g("stamina_buys_today") or 0),
        dokiep_extra_shield=int(g("dokiep_extra_shield") or 0),
        dokiep_remove_wrong=int(g("dokiep_remove_wrong") or 0),
        dokiep_fail_loss_pct=int(g("dokiep_fail_loss_pct") or 20),
        dokiep_first_immune=int(g("dokiep_first_immune") or 0),
        last_daily_day=str(g("last_daily_day") or ""),
        daily_streak=int(g("daily_streak") or 0),
        sect_id=str(g("sect_id") or ""),
        sect_contrib=int(g("sect_contrib") or 0),
        sect_joined_at=float(g("sect_joined_at") or 0),
        sect_role=str(g("sect_role") or ""),
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


class PlayerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, user_id: str) -> Player | None:
        row = self.db.fetchone("SELECT * FROM players WHERE user_id=?", (str(user_id),))
        return _row_to_player(row) if row else None

    def insert(self, player: Player) -> None:
        player.ensure_invariants()
        now = int(time.time())
        player.created_at = player.created_at or now
        player.updated_at = now
        s = player.stats.clamped()
        self.db.execute(
            """INSERT INTO players(
                user_id, display_name, major_realm, minor_stage, path, faction,
                cultivation, spirit_stones, stamina, max_stamina,
                can_cot, ngo_tinh, than_thuc, than_phap, khi_van,
                root_system, root_quality, weapon1, weapon2, treasure,
                pet1, pet2, pet3,
                last_cultivate_at, last_tower_day, tower_runs_today,
                cultivate_bonus_pct, cultivate_bonus_charges,
                last_gather_day, gather_count_today, last_bicanh_at,
                partner_id, last_songtu_at, last_stamina_tick,
                stamina_buy_day, stamina_buys_today,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                player.user_id, player.display_name, player.major_realm, player.minor_stage,
                player.path, player.faction, player.cultivation, player.spirit_stones,
                player.stamina, player.max_stamina, s.can_cot, s.ngo_tinh, s.than_thuc,
                s.than_phap, s.khi_van, player.root_system, player.root_quality,
                player.weapon1, player.weapon2, player.treasure,
                player.pet1, player.pet2, player.pet3,
                player.last_cultivate_at, player.last_tower_day, player.tower_runs_today,
                player.cultivate_bonus_pct, player.cultivate_bonus_charges,
                player.last_gather_day, player.gather_count_today, player.last_bicanh_at,
                player.partner_id, player.last_songtu_at, player.last_stamina_tick,
                player.stamina_buy_day, player.stamina_buys_today,
                player.created_at, player.updated_at,
            ),
        )
        self.db.commit()

    def save(self, player: Player) -> None:
        player.ensure_invariants()
        player.updated_at = int(time.time())
        s = player.stats.clamped()
        self.db.execute(
            """UPDATE players SET
                display_name=?, major_realm=?, minor_stage=?, path=?, faction=?,
                cultivation=?, spirit_stones=?, stamina=?, max_stamina=?,
                can_cot=?, ngo_tinh=?, than_thuc=?, than_phap=?, khi_van=?,
                root_system=?, root_quality=?, weapon1=?, weapon2=?, treasure=?,
                pet1=?, pet2=?, pet3=?,
                last_cultivate_at=?, last_tower_day=?, tower_runs_today=?,
                cultivate_bonus_pct=?, cultivate_bonus_charges=?,
                last_gather_day=?, gather_count_today=?, last_bicanh_at=?,
                partner_id=?, last_songtu_at=?, last_stamina_tick=?,
                stamina_buy_day=?, stamina_buys_today=?,
                dokiep_extra_shield=?, dokiep_remove_wrong=?, dokiep_fail_loss_pct=?, dokiep_first_immune=?,
                last_daily_day=?, daily_streak=?,
                sect_id=?, sect_contrib=?, sect_joined_at=?, sect_role=?,
                updated_at=?
            WHERE user_id=?""",
            (
                player.display_name, player.major_realm, player.minor_stage, player.path,
                player.faction, player.cultivation, player.spirit_stones, player.stamina,
                player.max_stamina, s.can_cot, s.ngo_tinh, s.than_thuc, s.than_phap,
                s.khi_van, player.root_system, player.root_quality,
                player.weapon1, player.weapon2, player.treasure,
                player.pet1, player.pet2, player.pet3,
                player.last_cultivate_at, player.last_tower_day, player.tower_runs_today,
                player.cultivate_bonus_pct, player.cultivate_bonus_charges,
                player.last_gather_day, player.gather_count_today, player.last_bicanh_at,
                player.partner_id, player.last_songtu_at, player.last_stamina_tick,
                player.stamina_buy_day, player.stamina_buys_today,
                player.dokiep_extra_shield, player.dokiep_remove_wrong,
                player.dokiep_fail_loss_pct, player.dokiep_first_immune,
                player.last_daily_day, player.daily_streak,
                player.sect_id, player.sect_contrib, player.sect_joined_at, player.sect_role,
                player.updated_at, player.user_id,
            ),
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
