import random

from ktt112026.game.services.player_service import PlayerService
from ktt112026.db.connection import Database
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.db.schema import ensure_schema


def _svc():
    db = Database(":memory:")
    ensure_schema(db)
    return PlayerService(PlayerRepository(db), rng=random.Random(42))


def test_create_and_profile():
    svc = _svc()
    p = svc.create("u1", "Đạo Hữu A")
    assert p.user_id == "u1"
    assert 40 <= p.stats.can_cot <= 60


def test_duplicate_create():
    svc = _svc()
    svc.create("u1", "A")
    try:
        svc.create("u1", "A")
        assert False
    except ValueError:
        pass


def test_cultivate():
    svc = _svc()
    svc.create("u1", "A")
    p = svc.get("u1")
    assert p
    p.last_cultivate_at = 0
    svc.repo.save(p)
    result = svc.cultivate("u1")
    assert result["gain"] >= 1
