import random

from ktt112026.game.rules import combat_rules as cr


def test_hit_chance_bounds():
    assert 0.35 <= cr.hit_chance(0, 1000) <= 0.97
    assert 0.35 <= cr.hit_chance(1000, 0) <= 0.97
    mid = cr.hit_chance(50, 50)
    assert 0.74 <= mid <= 0.76


def test_damage_positive_and_defense_helps():
    rng = random.Random(0)
    high = cr.calculate_damage(100, 10, rng=rng)
    rng = random.Random(0)
    low = cr.calculate_damage(100, 80, rng=rng)
    assert high >= 1 and low >= 1
    assert high >= low


def test_mastery_cap_and_stage():
    assert cr.mastery_multiplier(0) == 1.0
    assert abs(cr.mastery_multiplier(12) - 1.12) < 1e-9
    assert cr.mastery_multiplier(99) == 1.12
    assert cr.mastery_stage(0) == "Nhập môn"
    assert cr.mastery_stage(4) == "Tiểu thành"
    assert cr.mastery_stage(8) == "Đại thành"
    assert cr.mastery_stage(12) == "Viên mãn"


def test_crit_and_shield_and_dot():
    # force crit with 100% and seeded rng that draws low
    dmg, crit = cr.critical_hit(100, 100.0, crit_mult=2.0, rng=random.Random(1))
    assert crit is True and dmg == 200
    assert cr.apply_shield(100, 0.5) == 50
    assert cr.apply_shield(100, 0.95) == 10  # cap 0.9 -> 10
    assert cr.tick_dot(1000, 0.05) == 50


def test_resolve_attack_miss_and_hit():
    # accuracy far below evasion -> often miss; force with rng=1.0 path
    class R:
        def random(self):
            return 0.99  # above any hit chance -> miss

        def uniform(self, a, b):
            return 0.0

    miss = cr.resolve_attack(
        attack=50, defense=10, accuracy=0, evasion=500, rng=R()  # type: ignore[arg-type]
    )
    assert miss["hit"] is False and miss["damage"] == 0

    class R2:
        def random(self):
            return 0.0  # always hit / no crit if crit rolled second — use separate

        def uniform(self, a, b):
            return 0.0

    # For hit we need first random < chance; for no crit second random for crit
    # resolve_attack uses same rng.random for hit then critical_hit also random()
    # Use fixed Random seed that hits
    hit = cr.resolve_attack(
        attack=80,
        defense=20,
        accuracy=100,
        evasion=0,
        crit_pct=0,
        mastery=4,
        rng=random.Random(42),
    )
    assert hit["hit"] is True
    assert int(hit["damage"]) >= 1
    assert hit["mastery_stage"] == "Tiểu thành"


def test_combat_power_from_effective():
    assert cr.combat_power_from_effective({"power": 123}) == 123
    assert cr.combat_power_from_effective({
        "stats": {"can_cot": 10, "than_thuc": 10, "than_phap": 10},
        "derived": {"atk": 100, "def": 50},
    }) >= 30
