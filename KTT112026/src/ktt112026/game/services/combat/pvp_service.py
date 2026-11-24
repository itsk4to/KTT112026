"""PvP challenge + wager escrow (PR6). Uses CombatService; SQLite-backed."""
from __future__ import annotations

import secrets
import time
from typing import Any

from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.combat.combat_service import CombatService, MonsterProfile
from ktt112026.game.services.player.stats_service import StatsService
from ktt112026.game.util.formatters import fmt_num

CHALLENGE_TTL = 300  # 5 minutes
MIN_WAGER = 50
MAX_WAGER = 50_000


class PvpService:
    def __init__(
        self,
        repo: PlayerRepository,
        stats: StatsService | None = None,
        combat: CombatService | None = None,
    ) -> None:
        self.repo = repo
        self.stats = stats or StatsService(repo)
        self.combat = combat or CombatService(repo, self.stats)

    def _expire_old(self) -> None:
        now = time.time()
        rows = self.repo.db.fetchall(
            "SELECT * FROM pvp_challenges WHERE status='pending' AND expires_at < ?",
            (now,),
        )
        for r in rows:
            self._refund_challenger(dict(r), reason="expired")

    def _refund_challenger(self, row: dict[str, Any], *, reason: str) -> None:
        if row.get("status") != "pending":
            return
        cid = str(row["challenger_id"])
        wager = int(row["wager"])
        p = self.repo.get(cid)
        if p:
            p.spirit_stones += wager
            self.repo.save(p)
        self.repo.db.execute(
            "UPDATE pvp_challenges SET status=? WHERE id=?",
            (reason, row["id"]),
        )
        self.repo.db.commit()

    def challenge(self, challenger_id: str, target_id: str, wager: int) -> dict[str, Any]:
        self._expire_old()
        wager = int(wager)
        if wager < MIN_WAGER or wager > MAX_WAGER:
            raise ValueError(f"Cược {MIN_WAGER}–{fmt_num(MAX_WAGER)} Linh Thạch.")
        if str(challenger_id) == str(target_id):
            raise ValueError("Không thể thách đấu chính mình.")
        a = self.repo.get(str(challenger_id))
        b = self.repo.get(str(target_id))
        if a is None:
            raise ValueError("Bạn chưa có thể đạo.")
        if b is None:
            raise ValueError("Đối phương chưa `.taothe`.")
        # one pending at a time per user
        pending = self.repo.db.fetchone(
            "SELECT id FROM pvp_challenges WHERE status='pending' AND (challenger_id=? OR target_id=?)",
            (str(challenger_id), str(challenger_id)),
        )
        if pending:
            raise ValueError("Bạn đang có lời thách chờ xử lý. `.pvp huy` hoặc đợi hết hạn.")
        if a.spirit_stones < wager:
            raise ValueError(f"Không đủ Linh Thạch để đặt cọc (cần {fmt_num(wager)}).")
        a.spirit_stones -= wager
        self.repo.save(a)
        cid = secrets.token_hex(8)
        now = time.time()
        self.repo.db.execute(
            "INSERT INTO pvp_challenges(id, challenger_id, target_id, wager, status, winner_id, created_at, expires_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cid, str(challenger_id), str(target_id), wager, "pending", "", now, now + CHALLENGE_TTL),
        )
        self.repo.db.commit()
        return {
            "id": cid,
            "wager": wager,
            "target_name": b.display_name,
            "expires_sec": CHALLENGE_TTL,
            "challenger_left": a.spirit_stones,
        }

    def cancel(self, user_id: str) -> dict[str, Any]:
        self._expire_old()
        row = self.repo.db.fetchone(
            "SELECT * FROM pvp_challenges WHERE status='pending' AND challenger_id=? ORDER BY created_at DESC LIMIT 1",
            (str(user_id),),
        )
        if not row:
            raise ValueError("Không có lời thách nào của bạn đang chờ.")
        self._refund_challenger(dict(row), reason="cancelled")
        return {"wager": int(row["wager"]), "id": str(row["id"])}

    def accept(self, user_id: str, challenge_id: str | None = None) -> dict[str, Any]:
        self._expire_old()
        if challenge_id:
            row = self.repo.db.fetchone(
                "SELECT * FROM pvp_challenges WHERE id=? AND status='pending'",
                (challenge_id.strip(),),
            )
        else:
            row = self.repo.db.fetchone(
                "SELECT * FROM pvp_challenges WHERE status='pending' AND target_id=? ORDER BY created_at DESC LIMIT 1",
                (str(user_id),),
            )
        if not row:
            raise ValueError("Không có lời thách phù hợp. Hết hạn hoặc đã xử lý.")
        row = dict(row)
        if str(row["target_id"]) != str(user_id):
            raise ValueError("Lời thách này không gửi tới bạn.")
        if time.time() > float(row["expires_at"]):
            self._refund_challenger(row, reason="expired")
            raise ValueError("Lời thách đã hết hạn — đã hoàn cọc cho đối phương.")
        wager = int(row["wager"])
        b = self.repo.get(str(user_id))
        if b is None:
            raise ValueError("Bạn chưa có thể đạo.")
        if b.spirit_stones < wager:
            raise ValueError(f"Không đủ Linh Thạch đặt cọc (cần {fmt_num(wager)}).")
        b.spirit_stones -= wager
        self.repo.save(b)

        # Resolve: map defender as "monster" from their combat stats — use mirrored PvE
        ca = self.combat.player_combat_stats(str(row["challenger_id"]))
        cb = self.combat.player_combat_stats(str(user_id))
        # Fight as challenger attacking profile of defender, then check HP; simplified: compare resolve both ways
        mon_b = MonsterProfile(
            name=b.display_name,
            attack=int(cb["attack"]),
            defense=int(cb["defense"]),
            hp=int(cb["hp"]),
            accuracy=float(cb["accuracy"]),
            evasion=float(cb["evasion"]),
            crit_pct=float(cb["crit_pct"]),
        )
        result = self.combat.resolve_pve(str(row["challenger_id"]), mon_b)
        pot = wager * 2
        if result["won"]:
            winner_id = str(row["challenger_id"])
        elif result.get("drew"):
            # refund both
            wa = self.repo.get(str(row["challenger_id"]))
            wb = self.repo.get(str(user_id))
            if wa:
                wa.spirit_stones += wager
                self.repo.save(wa)
            if wb:
                wb.spirit_stones += wager
                self.repo.save(wb)
            self.repo.db.execute(
                "UPDATE pvp_challenges SET status='draw', winner_id='' WHERE id=?",
                (row["id"],),
            )
            self.repo.db.commit()
            return {
                "draw": True,
                "wager": wager,
                "log": result.get("log") or [],
                "id": row["id"],
            }
        else:
            winner_id = str(user_id)

        winner = self.repo.get(winner_id)
        if winner:
            winner.spirit_stones += pot
            self.repo.save(winner)
        self.repo.db.execute(
            "UPDATE pvp_challenges SET status='done', winner_id=? WHERE id=?",
            (winner_id, row["id"]),
        )
        self.repo.db.commit()
        wname = winner.display_name if winner else winner_id
        return {
            "draw": False,
            "winner_id": winner_id,
            "winner_name": wname,
            "pot": pot,
            "wager": wager,
            "log": result.get("log") or [],
            "id": row["id"],
        }
