import random
import time

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.world.daily_service import DailyService
from ktt112026.game.services.world.exploration_service import ExplorationService
from ktt112026.game.services.player.player_service import PlayerService


def _repo():
    db = Database(":memory:")
    ensure_schema(db)
    return PlayerRepository(db)


def test_explore_event_fields():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    p = repo.get("u")
    p.stamina = 100
    p.last_bicanh_at = 0
    p.major_realm = 1
    repo.save(p)
    ex = ExplorationService(repo, rng=random.Random(3))
    r = ex.explore("u", "linh_cuc")
    assert "event" in r
    assert r["stones"] >= 0
    assert "event_notes" in r


def test_daily_once():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    d = DailyService(repo)
    r = d.claim("u")
    assert r["stones"] > 0
    assert r["streak"] == 1
    try:
        d.claim("u")
        assert False
    except ValueError:
        pass
