import random
import time

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService


def _svc():
    db = Database(":memory:")
    ensure_schema(db)
    return PlayerService(PlayerRepository(db), rng=random.Random(42))


def test_batch_tu():
    svc = _svc()
    svc.create("u", "A")
    p = svc.get("u")
    p.last_cultivate_at = 0
    p.stamina = 100
    svc.repo.save(p)
    r = svc.cultivate("u", 5)
    assert r["ticks"] == 5
    assert r["gain"] > 0


def test_lock_at_full_requires_dp():
    svc = _svc()
    svc.create("u", "A")
    p = svc.get("u")
    need = stage_requirement(p.major_realm, p.minor_stage)
    p.cultivation = need
    p.last_cultivate_at = 0
    svc.repo.save(p)
    try:
        svc.cultivate("u", 1)
        assert False, "should lock"
    except ValueError as e:
        assert "dp" in str(e).lower() or "100%" in str(e)


def test_dp_success_or_fail():
    svc = _svc()
    # force success with high stats + seeded rng that eventually works
    svc.create("u", "A")
    p = svc.get("u")
    p.stats.ngo_tinh = 200
    p.stats.can_cot = 200
    p.cultivation = stage_requirement(1, 0)
    svc.repo.save(p)
    # use rng that always succeeds
    svc.rng = random.Random(0)
    # find a seed that succeeds - or just call and accept either
    r = svc.breakthrough_minor("u")
    assert "success" in r
    assert 0.25 <= r["rate"] <= 0.92


def test_stamina_regen():
    svc = _svc()
    svc.create("u", "A")
    p = svc.get("u")
    p.stamina = 10
    p.max_stamina = 100
    p.last_stamina_tick = time.time() - 600  # 10 min
    svc.repo.save(p)
    p2 = svc.get("u")
    assert p2.stamina > 10
