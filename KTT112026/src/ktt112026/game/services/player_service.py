"""Player use-cases."""
from __future__ import annotations

import random
import time
from datetime import date

from ktt112026.game.content.realms import STAMINA_BY_MAJOR, realm_display, stage_requirement
from ktt112026.game.models.player import Player, PlayerStats
from ktt112026.game.rules import (
    DP_FAIL_LOSS_PCT,
    can_auto_advance_minor,
    cultivation_gain,
    minor_breakthrough_chance,
    minor_needs_breakthrough,
)
from ktt112026.game.rules.stamina import REGEN_INTERVAL_SECONDS
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services._tx import atomic

CULTIVATE_COOLDOWN = 4.0
CULTIVATE_STAMINA_COST = 2
MAX_BATCH = 20  # .tu max
STAMINA_BUY_PER_DAY = 5
STAMINA_BUY_AMOUNT = 30
STAMINA_BUY_COST_PER_MAJOR = 200  # Linh Thạch × đại cảnh giới
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
        return self.repo.get(str(user_id))

    def create(self, user_id: str, display_name: str) -> Player:
        if self.repo.get(str(user_id)) is not None:
            raise ValueError("Đạo hữu đã có thể đạo. Dùng `.me` để xem.")
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
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe`.")
        if p.path:
            raise ValueError("Đã chọn Đạo Lộ rồi, không đổi được.")
        # GDD: end of major 1
        if p.major_realm < 1 or (p.major_realm == 1 and p.minor_stage < 2 and p.cultivation < stage_requirement(1, p.minor_stage)):
            # Allow from Hậu kỳ cấp 1 or any time after major>1; soft: allow from major1 minor>=1 for playability
            if p.major_realm == 1 and p.minor_stage < 1:
                raise ValueError("Cần đạt Luyện Khí/Dẫn Khí Trung Kỳ trở lên mới phân nhánh Đạo Lộ.")
        p.path = path
        self.repo.save(p)
        return p

    def choose_faction(self, user_id: str, faction: str) -> Player:
        faction = faction.strip().lower()
        if faction in ("tongmon", "tông", "tong", "mon"):
            faction = "tongmon"
        elif faction in ("tantu", "tán", "tan", "tu"):
            faction = "tantu"
        else:
            raise ValueError("Dùng `.gianhap tongmon` hoặc `.gianhap tantu`.")
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe`.")
        if not p.path:
            raise ValueError("Hãy `.chon tien/ma` trước.")
        if p.major_realm < 2:
            raise ValueError("Cần Cấp 2 (sau Độ Kiếp) mới gia nhập thế lực.")
        if p.faction:
            raise ValueError("Đã gia nhập thế lực.")
        p.faction = faction
        self.repo.save(p)
        return p

    @staticmethod
    def is_locked(p: Player) -> bool:
        """GDD 100% Lock: đầy thanh thì khóa `.tu` (Cấp 1 tiểu cảnh tự lên nên không khóa)."""
        need = stage_requirement(p.major_realm, p.minor_stage)
        if p.cultivation < need:
            return False
        return not (p.major_realm == 1 and p.minor_stage < 2)

    @staticmethod
    def lock_message(p: Player) -> str:
        if p.minor_stage >= 2:
            return "Hậu Kỳ viên mãn 100% — hãy `.dokiep` để tiến Đại Cảnh Giới."
        return "Tu Vi đầy 100% — gõ `.dp` để đột phá Tiểu Cảnh Giới rồi mới tu tiếp."

    def cultivate(self, user_id: str, times: int = 1) -> dict:
        """`.tu [số_lần|max]` — gộp nhiều lượt trong một lệnh, cooldown tính một lần."""
        player = self.repo.get(str(user_id))
        if player is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        now = time.time()
        elapsed = now - float(player.last_cultivate_at or 0)
        if elapsed < CULTIVATE_COOLDOWN:
            raise ValueError(f"Đang điều tức. Còn **{CULTIVATE_COOLDOWN - elapsed:.1f}s** mới `.tu` tiếp.")
        if self.is_locked(player):
            raise ValueError(self.lock_message(player))
        if player.stamina < CULTIVATE_STAMINA_COST:
            mins = int(REGEN_INTERVAL_SECONDS // 60)
            raise ValueError(
                f"Thể lực không đủ. Tự hồi 1 điểm / {mins} phút (kể cả khi offline), "
                "hoặc dùng đan / `.hoithe`."
            )
        times = max(1, min(MAX_BATCH, int(times)))

        total_gain = 0
        ticks = 0
        advanced = False
        for _ in range(times):
            if player.stamina < CULTIVATE_STAMINA_COST or self.is_locked(player):
                break
            need = stage_requirement(player.major_realm, player.minor_stage)
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
            player.spirit_stones += max(1, 2 + player.major_realm)
            before = player.cultivation
            player.cultivation = min(need, player.cultivation + gain)
            total_gain += player.cultivation - before
            player.stamina -= CULTIVATE_STAMINA_COST
            ticks += 1
            if player.major_realm == 1 and can_auto_advance_minor(
                player.cultivation, player.major_realm, player.minor_stage
            ):
                player.minor_stage += 1
                player.cultivation = 0
                advanced = True
        player.last_cultivate_at = now
        self.repo.save(player)

        locked = self.is_locked(player)
        hint = self.lock_message(player) if locked else ""
        if not hint and advanced and player.minor_stage >= 2 and not player.path:
            hint = "Đã tới Hậu Kỳ — hãy chọn đạo lộ: `.chon tien` hoặc `.chon ma` trước khi Độ Kiếp."
        new_need = stage_requirement(player.major_realm, player.minor_stage)
        return {
            "gain": total_gain, "ticks": ticks, "cultivation": player.cultivation,
            "need": new_need, "stamina": player.stamina, "max_stamina": player.max_stamina,
            "advanced": advanced, "locked": locked, "hint": hint,
            "realm": realm_display(player.major_realm, player.minor_stage, player.path),
            "player": player,
        }

    @atomic
    def breakthrough_minor(self, user_id: str) -> dict:
        """`.dp` — đột phá Tiểu Cảnh Giới (Cấp 2+): tỷ lệ theo Ngộ Tính / Căn Cốt."""
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        if p.minor_stage >= 2:
            raise ValueError("Đã Hậu Kỳ — dùng `.dokiep` để lên Đại Cảnh Giới.")
        if not minor_needs_breakthrough(p.major_realm):
            raise ValueError("Cấp 1 tự động lên Tiểu Cảnh Giới khi đầy Tu Vi — cứ `.tu`.")
        need = stage_requirement(p.major_realm, p.minor_stage)
        if p.cultivation < need:
            raise ValueError(f"Tu Vi chưa đầy ({p.cultivation:,}/{need:,}).")
        chance = minor_breakthrough_chance(p.stats.ngo_tinh, p.stats.can_cot)
        success = self.rng.random() < chance
        if success:
            p.minor_stage += 1
            p.cultivation = 0
        else:
            p.cultivation = int(need * (100 - DP_FAIL_LOSS_PCT) / 100)
        self.repo.save(p)
        return {
            "success": success, "chance": chance,
            "realm": realm_display(p.major_realm, p.minor_stage, p.path),
            "cultivation": p.cultivation,
            "need": stage_requirement(p.major_realm, p.minor_stage),
            "loss_pct": 0 if success else DP_FAIL_LOSS_PCT,
        }

    @atomic
    def buy_stamina(self, user_id: str) -> dict:
        """`.hoithe` — mua thêm Thể Lực bằng Linh Thạch, giới hạn mỗi ngày."""
        p = self.repo.get(str(user_id))
        if p is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        today = date.today().isoformat()
        used = p.stamina_buy_count if p.stamina_buy_day == today else 0
        if used >= STAMINA_BUY_PER_DAY:
            raise ValueError(f"Hôm nay đã mua tối đa {STAMINA_BUY_PER_DAY} lượt hồi Thể Lực.")
        if p.stamina >= p.max_stamina:
            raise ValueError("Thể Lực đã đầy.")
        cost = STAMINA_BUY_COST_PER_MAJOR * p.major_realm
        if p.spirit_stones < cost:
            raise ValueError(f"Cần {cost:,} Linh Thạch (đang có {p.spirit_stones:,}).")
        before = p.stamina
        p.spirit_stones -= cost
        p.stamina = min(p.max_stamina, p.stamina + STAMINA_BUY_AMOUNT)
        p.stamina_buy_day = today
        p.stamina_buy_count = used + 1
        self.repo.save(p)
        return {
            "gained": p.stamina - before, "cost": cost, "stamina": p.stamina,
            "max_stamina": p.max_stamina, "left_today": STAMINA_BUY_PER_DAY - p.stamina_buy_count,
            "stones": p.spirit_stones,
        }
