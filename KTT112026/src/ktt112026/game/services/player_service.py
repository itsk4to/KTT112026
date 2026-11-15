"""Player use-cases."""
from __future__ import annotations

import random
import time

from ktt112026.game.content.realms import STAMINA_BY_MAJOR, realm_display, stage_requirement
from ktt112026.game.models.player import Player, PlayerStats
from ktt112026.game.rules import can_auto_advance_minor, cultivation_gain
from ktt112026.game.repo.players import PlayerRepository

CULTIVATE_COOLDOWN = 4.0
CULTIVATE_STAMINA_COST = 2
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

    def cultivate(self, user_id: str) -> dict:
        player = self.repo.get(str(user_id))
        if player is None:
            raise ValueError("Chưa có thể đạo. Gõ `.taothe` trước.")
        now = time.time()
        elapsed = now - float(player.last_cultivate_at or 0)
        if elapsed < CULTIVATE_COOLDOWN:
            raise ValueError(f"Đang điều tức. Còn **{CULTIVATE_COOLDOWN - elapsed:.1f}s** mới `.tu` tiếp.")
        if player.stamina < CULTIVATE_STAMINA_COST:
            raise ValueError("Thể lực không đủ. Dùng đan hồi thể lực hoặc chờ (sẽ có hồi theo thời gian).")
        need = stage_requirement(player.major_realm, player.minor_stage)
        if player.minor_stage >= 2 and player.cultivation >= need:
            raise ValueError("Hậu Kỳ viên mãn — hãy `.dokiep` để tiến Đại Cảnh Giới.")
        gain = cultivation_gain(
            ngo_tinh=player.stats.ngo_tinh,
            root_quality=player.root_quality,
            major_realm=player.major_realm,
        )
        # path bonus for matching root
        if player.path == "tien" and player.root_system == "quang":
            gain = int(gain * 1.1)
        if player.path == "ma" and player.root_system == "am":
            gain = int(gain * 1.1)
        if player.cultivate_bonus_charges > 0 and player.cultivate_bonus_pct > 0:
            gain = int(gain * (1 + player.cultivate_bonus_pct / 100.0))
            player.cultivate_bonus_charges -= 1
            if player.cultivate_bonus_charges <= 0:
                player.cultivate_bonus_pct = 0
        # light economy: small stone drip while cultivating
        player.spirit_stones += max(1, 2 + player.major_realm)
        player.cultivation = min(need, player.cultivation + gain)
        player.stamina -= CULTIVATE_STAMINA_COST
        player.last_cultivate_at = now
        advanced = False
        if can_auto_advance_minor(player.cultivation, player.major_realm, player.minor_stage):
            player.minor_stage += 1
            player.cultivation = 0
            advanced = True
        self.repo.save(player)
        new_need = stage_requirement(player.major_realm, player.minor_stage)
        return {
            "gain": gain, "cultivation": player.cultivation, "need": new_need,
            "stamina": player.stamina, "max_stamina": player.max_stamina,
            "advanced": advanced,
            "realm": realm_display(player.major_realm, player.minor_stage, player.path),
            "player": player,
        }
