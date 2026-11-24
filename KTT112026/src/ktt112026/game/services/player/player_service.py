"""Player use-cases — Phase E: batch .tu, offline AP, lock 100%, .dp."""
from __future__ import annotations

import random
import time

from ktt112026.game.content.realms import STAMINA_BY_MAJOR, realm_display, stage_requirement
from ktt112026.game.models.player import Player, PlayerStats
from ktt112026.game.rules import cultivation_gain
from ktt112026.game.repo.players import PlayerRepository

CULTIVATE_COOLDOWN = 3.0
CULTIVATE_STAMINA_COST = 2
# Offline AP: +1 stamina every STAMINA_REGEN_SECONDS
STAMINA_REGEN_SECONDS = 120.0
MAX_BATCH_TU = 50

_QUALITY_WEIGHTS = [("tap", 45), ("chan", 35), ("dia", 14), ("thien", 5), ("hon_don", 1)]
_SYSTEM_WEIGHTS = [
    ("kim", 14), ("moc", 14), ("thuy", 14), ("hoa", 14), ("tho", 14),
    ("loi", 7), ("phong", 7), ("bang", 7), ("quang", 4.5), ("am", 4.5),
]


def _weighted_choice(pairs, rng: random.Random) -> str:
    total = sum(w for _, w in pairs)
    roll = rng.uniform(0, total)
    acc = 0.0
    for key, w in pairs:
        acc += w
        if roll <= acc:
            return key
    return pairs[-1][0]


def _roll_stats(rng: random.Random) -> PlayerStats:
    vals = [rng.randint(40, 60) for _ in range(5)]
    return PlayerStats(
        can_cot=vals[0], ngo_tinh=vals[1], than_thuc=vals[2],
        than_phap=vals[3], khi_van=vals[4],
    ).clamped()


class PlayerService:
    def __init__(self, repo: PlayerRepository, rng: random.Random | None = None) -> None:
        self.repo = repo
        self.rng = rng or random.Random()

    def get(self, user_id: str) -> Player | None:
        player = self.repo.get(str(user_id))
        if player is None:
            return None
        if self._regen_stamina(player):
            self.repo.save(player)
        return player

    def _regen_stamina(self, player: Player) -> bool:
        """Offline / passive AP recovery. Returns True if changed."""
        now = time.time()
        # Use last_cultivate_at as activity anchor; also track via updated-like field
        # Prefer a dedicated stamp: fall back to last_cultivate_at or created_at
        anchor = float(getattr(player, "last_stamina_tick", 0) or 0)
        if anchor <= 0:
            anchor = float(player.last_cultivate_at or player.created_at or now)
        if player.stamina >= player.max_stamina:
            player.last_stamina_tick = now  # type: ignore[attr-defined]
            return False
        elapsed = now - anchor
        if elapsed < STAMINA_REGEN_SECONDS:
            return False
        gained = int(elapsed // STAMINA_REGEN_SECONDS)
        if gained <= 0:
            return False
        before = player.stamina
        player.stamina = min(player.max_stamina, player.stamina + gained)
        # keep remainder time
        player.last_stamina_tick = now - (elapsed % STAMINA_REGEN_SECONDS)  # type: ignore[attr-defined]
        return player.stamina != before

    def create(self, user_id: str, display_name: str) -> Player:
        if self.repo.get(str(user_id)) is not None:
            raise ValueError("Đạo hữu đã có thể đạo. Dùng `.me` để xem.")
        now = time.time()
        player = Player(
            user_id=str(user_id),
            display_name=display_name[:64],
            stats=_roll_stats(self.rng),
            root_system=_weighted_choice(_SYSTEM_WEIGHTS, self.rng),
            root_quality=_weighted_choice(_QUALITY_WEIGHTS, self.rng),
            spirit_stones=500,
            stamina=100,
            max_stamina=STAMINA_BY_MAJOR[1],
        )
        player.last_stamina_tick = now  # type: ignore[attr-defined]
        player.ensure_invariants()
        self.repo.insert(player)
        return player

    def choose_path(self, user_id: str, path: str) -> Player:
        path = path.strip().lower()
        if path in ("tien", "tiên", "tien-dao", "tiendao"):
            path = "tien"
        elif path in ("ma", "ma-dao", "madao"):
            path = "ma"
        else:
            raise ValueError("Chọn `.chon tien` hoặc `.chon ma`.")
        p = self.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe`.")
        if p.path:
            raise ValueError("Đã chọn Đạo Lộ rồi, không đổi được.")
        if p.major_realm == 1 and p.minor_stage < 1:
            raise ValueError("Cần đạt Luyện Khí/Dẫn Khí Trung Kỳ trở lên mới phân nhánh Đạo Lộ.")
        p.path = path
        self.repo.save(p)
        return p

    def choose_faction(self, user_id: str, faction: str) -> Player:
        faction = faction.strip().lower()
        if faction in ("tongmon", "tông", "tong", "mon", "tong_mon"):
            faction = "tongmon"
        elif faction in ("tantu", "tán", "tan", "tu", "tan_tu"):
            faction = "tantu"
        else:
            raise ValueError("Đủ cảnh giới cấp 2+: `.gianhap tongmon` (vào tông NPC) hoặc `.gianhap tantu` (tự tu).")
        p = self.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe`.")
        if not p.path:
            raise ValueError("Hãy `.chon tien` hoặc `.chon ma` trước.")
        if p.major_realm < 2:
            raise ValueError("Cần đại cảnh giới cấp 2 (sau Độ Kiếp Luyện Khí/Dẫn Khí) mới chọn Tán Tu hoặc Tông Môn.")
        if p.faction:
            raise ValueError("Đã chọn thế lực rồi.")
        p.faction = faction
        self.repo.save(p)
        return p

    def is_bar_full(self, player: Player) -> bool:
        need = stage_requirement(player.major_realm, player.minor_stage)
        return player.cultivation >= need

    def cultivate(self, user_id: str, times: int | str = 1) -> dict:
        player = self.get(str(user_id))
        if player is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        now = time.time()
        elapsed = now - float(player.last_cultivate_at or 0)
        if elapsed < CULTIVATE_COOLDOWN:
            raise ValueError(f"Đang điều tức. Còn **{CULTIVATE_COOLDOWN - elapsed:.1f}s** mới `.tu` tiếp.")

        need = stage_requirement(player.major_realm, player.minor_stage)
        if self.is_bar_full(player):
            if player.minor_stage >= 2:
                raise ValueError("Hậu Kỳ viên mãn (100%). Hãy `.dokiep` để tiến Đại Cảnh Giới — `.tu` đã khóa.")
            raise ValueError("Tu Vi đã 100%. Hãy `.dp` để đột phá tiểu cảnh giới — `.tu` đã khóa.")

        # parse batch
        if isinstance(times, str):
            raw = times.strip().lower()
            if raw in ("max", "full", "all"):
                n = MAX_BATCH_TU
            else:
                n = int(raw)
        else:
            n = int(times)
        n = max(1, min(MAX_BATCH_TU, n))

        max_by_stamina = player.stamina // CULTIVATE_STAMINA_COST
        if max_by_stamina < 1:
            raise ValueError("Thể lực không đủ. Chờ hồi offline hoặc dùng đan thể lực.")
        n = min(n, max_by_stamina)

        total_gain = 0
        stones_gained = 0
        ticks = 0
        for _ in range(n):
            if self.is_bar_full(player):
                break
            gain = cultivation_gain(
                ngo_tinh=player.stats.ngo_tinh,
                root_quality=player.root_quality,
                major_realm=player.major_realm,
            )
            if player.path == "tien" and player.root_system == "quang":
                gain = int(gain * 1.1)
            if player.path == "ma" and player.root_system == "am":
                gain = int(gain * 1.1)
            if player.cultivate_bonus_charges > 0 and player.cultivate_bonus_pct > 0:
                gain = int(gain * (1 + player.cultivate_bonus_pct / 100.0))
                player.cultivate_bonus_charges -= 1
                if player.cultivate_bonus_charges <= 0:
                    player.cultivate_bonus_pct = 0
            room = need - player.cultivation
            gain = min(gain, room)
            player.cultivation += gain
            player.stamina -= CULTIVATE_STAMINA_COST
            drip = max(1, 2 + player.major_realm)
            player.spirit_stones += drip
            total_gain += gain
            stones_gained += drip
            ticks += 1
            if player.cultivation >= need:
                player.cultivation = need
                break

        player.last_cultivate_at = now
        player.last_stamina_tick = now  # type: ignore[attr-defined]
        self.repo.save(player)
        locked = self.is_bar_full(player)
        return {
            "gain": total_gain,
            "ticks": ticks,
            "stones_gained": stones_gained,
            "cultivation": player.cultivation,
            "need": need,
            "stamina": player.stamina,
            "max_stamina": player.max_stamina,
            "advanced": False,
            "locked": locked,
            "realm": realm_display(player.major_realm, player.minor_stage, player.path),
            "player": player,
        }

    def breakthrough_minor(self, user_id: str) -> dict:
        """`.dp` — đột phá tiểu cảnh giới (Sơ→Trung→Hậu) với % thành công."""
        player = self.get(str(user_id))
        if player is None:
            raise ValueError("Chưa có thể đạo.")
        need = stage_requirement(player.major_realm, player.minor_stage)
        if player.cultivation < need:
            raise ValueError(f"Chưa đủ Tu Vi ({player.cultivation:,}/{need:,}). Hãy `.tu` thêm.")
        if player.minor_stage >= 2:
            raise ValueError("Đã Hậu Kỳ — dùng `.dokiep` để vượt Đại Cảnh Giới.")
        # G14: ép chọn đạo trước khi vào Hậu Kỳ (tiểu cảnh 3)
        if player.minor_stage >= 1 and not player.path:
            raise ValueError("Cần `.chon tien` hoặc `.chon ma` trước khi đột phá lên Hậu Kỳ.")

        # Success rate: base 55% + Ngộ Tính * 0.35 + Căn Cốt * 0.1, cap 92%
        rate = 0.55 + player.stats.ngo_tinh * 0.0035 + player.stats.can_cot * 0.001
        rate = max(0.25, min(0.92, rate))
        roll = self.rng.random()
        success = roll <= rate
        if success:
            player.minor_stage += 1
            player.cultivation = 0
            self.repo.save(player)
            return {
                "success": True,
                "rate": rate,
                "realm": realm_display(player.major_realm, player.minor_stage, player.path),
                "player": player,
                "message": f"Đột phá thành công! → {realm_display(player.major_realm, player.minor_stage, player.path)}",
            }
        # fail: lose 15% of bar
        loss = max(1, int(need * 0.15))
        player.cultivation = max(0, player.cultivation - loss)
        self.repo.save(player)
        return {
            "success": False,
            "rate": rate,
            "loss": loss,
            "cultivation": player.cultivation,
            "need": need,
            "player": player,
            "message": f"Đột phá thất bại (tỷ lệ ~{rate*100:.0f}%). Mất {loss:,} Tu Vi.",
        }

    def buy_stamina(self, user_id: str, packs: int = 1) -> dict:
        """Mua hồi thể lực bằng Linh Thạch (GDD V.2) — giới hạn theo ngày."""
        from datetime import date
        packs = max(1, min(5, int(packs)))
        player = self.get(str(user_id))
        if player is None:
            raise ValueError("Chưa có thể đạo.")
        today = date.today().isoformat()
        if getattr(player, "stamina_buy_day", "") != today:
            player.stamina_buy_day = today
            player.stamina_buys_today = 0
        max_buys = 5
        if player.stamina_buys_today + packs > max_buys:
            left = max(0, max_buys - player.stamina_buys_today)
            raise ValueError(f"Hôm nay chỉ mua thêm được {left} gói (tối đa {max_buys}/ngày).")
        # cost scales with major: 80 * major per pack; pack = 25% max_stamina
        unit_cost = 60 + player.major_realm * 40
        cost = unit_cost * packs
        if player.spirit_stones < cost:
            raise ValueError(f"Không đủ Linh Thạch (cần {cost:,}).")
        # ensure max_stamina tracks realm
        from ktt112026.game.content.realms import STAMINA_BY_MAJOR
        player.max_stamina = max(player.max_stamina, STAMINA_BY_MAJOR.get(player.major_realm, 100))
        gain_each = max(15, player.max_stamina // 4)
        gain = gain_each * packs
        room = player.max_stamina - player.stamina
        if room <= 0:
            raise ValueError("Thể lực đã đầy.")
        actual = min(gain, room)
        # still charge full packs requested if any room
        player.spirit_stones -= cost
        player.stamina = min(player.max_stamina, player.stamina + actual)
        player.stamina_buys_today += packs
        self.repo.save(player)
        return {
            "cost": cost,
            "gain": actual,
            "packs": packs,
            "stamina": player.stamina,
            "max_stamina": player.max_stamina,
            "buys_left": max_buys - player.stamina_buys_today,
            "player": player,
        }

