"""Player domain — GDD Đạo Lộ Tu Tiên."""
from __future__ import annotations

from dataclasses import dataclass, field

STAT_HARD_CAP = 200
STAT_DEFAULT = 50
STAT_NAMES = ("can_cot", "ngo_tinh", "than_thuc", "than_phap", "khi_van")
STAT_LABELS = {
    "can_cot": "Căn Cốt",
    "ngo_tinh": "Ngộ Tính",
    "than_thuc": "Thần Thức",
    "than_phap": "Thân Pháp",
    "khi_van": "Khí Vận",
}

ROOT_SYSTEMS = ("kim", "moc", "thuy", "hoa", "tho", "loi", "phong", "bang", "quang", "am")
ROOT_QUALITY = ("tap", "chan", "dia", "thien", "hon_don")
ROOT_QUALITY_MULT = {"tap": 1.0, "chan": 1.25, "dia": 1.5, "thien": 1.8, "hon_don": 2.2}
ROOT_QUALITY_LABEL = {
    "tap": "Tạp", "chan": "Chân", "dia": "Địa", "thien": "Thiên", "hon_don": "Hỗn Độn",
}
ROOT_SYSTEM_LABEL = {
    "kim": "Kim", "moc": "Mộc", "thuy": "Thủy", "hoa": "Hỏa", "tho": "Thổ",
    "loi": "Lôi", "phong": "Phong", "bang": "Băng", "quang": "Quang", "am": "Ám",
}


@dataclass
class PlayerStats:
    can_cot: int = STAT_DEFAULT
    ngo_tinh: int = STAT_DEFAULT
    than_thuc: int = STAT_DEFAULT
    than_phap: int = STAT_DEFAULT
    khi_van: int = STAT_DEFAULT

    def clamped(self) -> "PlayerStats":
        def c(v: int) -> int:
            return max(1, min(STAT_HARD_CAP, int(v)))

        return PlayerStats(
            can_cot=c(self.can_cot), ngo_tinh=c(self.ngo_tinh), than_thuc=c(self.than_thuc),
            than_phap=c(self.than_phap), khi_van=c(self.khi_van),
        )

    def as_dict(self) -> dict[str, int]:
        s = self.clamped()
        return {
            "can_cot": s.can_cot, "ngo_tinh": s.ngo_tinh, "than_thuc": s.than_thuc,
            "than_phap": s.than_phap, "khi_van": s.khi_van,
        }


@dataclass
class Player:
    user_id: str
    display_name: str
    major_realm: int = 1
    minor_stage: int = 0
    path: str = ""  # "" | tien | ma
    faction: str = ""  # "" | tongmon | tantu
    cultivation: int = 0
    spirit_stones: int = 100
    stamina: int = 100
    max_stamina: int = 100
    stats: PlayerStats = field(default_factory=PlayerStats)
    root_system: str = "kim"
    root_quality: str = "tap"
    weapon1: str = ""
    weapon2: str = ""
    treasure: str = ""
    pet1: str = ""
    pet2: str = ""
    pet3: str = ""
    last_cultivate_at: float = 0.0
    last_tower_day: str = ""
    tower_runs_today: int = 0
    cultivate_bonus_pct: int = 0
    cultivate_bonus_charges: int = 0
    last_gather_day: str = ""
    gather_count_today: int = 0
    last_bicanh_at: float = 0.0
    partner_id: str = ""
    last_songtu_at: float = 0.0
    last_stamina_at: float = 0.0
    stamina_buy_day: str = ""
    stamina_buy_count: int = 0
    created_at: int = 0
    updated_at: int = 0

    def ensure_invariants(self) -> None:
        self.stats = self.stats.clamped()
        self.cultivation = max(0, int(self.cultivation))
        self.spirit_stones = max(0, int(self.spirit_stones))
        self.stamina = max(0, min(self.max_stamina, int(self.stamina)))
        self.major_realm = max(1, min(6, int(self.major_realm)))
        self.minor_stage = max(0, min(2, int(self.minor_stage)))
        if self.root_system not in ROOT_SYSTEMS:
            self.root_system = "kim"
        if self.root_quality not in ROOT_QUALITY:
            self.root_quality = "tap"
        if self.path not in ("", "tien", "ma"):
            self.path = ""
        if self.faction not in ("", "tongmon", "tantu"):
            self.faction = ""
