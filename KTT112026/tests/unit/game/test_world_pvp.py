import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.pvp_service import PvpService
from ktt112026.game.services.world_event_service import WorldEventService


def _mk(repo, uid, name, stones=5000):
    ps = PlayerService(repo, rng=random.Random(0))
    if repo.get(uid) is None:
        ps.create(uid, name)
    p = repo.get(uid)
    p.spirit_stones = stones
    repo.save(p)
    return p


def test_world_event_claim_once():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    _mk(repo, "u", "U")
    we = WorldEventService(repo)
    r1 = we.claim("u")
    assert r1["stones"] > 0
    try:
        we.claim("u")
        assert False
    except ValueError:
        pass


def test_pvp_challenge_cancel_refund():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    _mk(repo, "a", "A", 1000)
    _mk(repo, "b", "B", 1000)
    pvp = PvpService(repo)
    r = pvp.challenge("a", "b", 100)
    assert repo.get("a").spirit_stones == 900
    pvp.cancel("a")
    assert repo.get("a").spirit_stones == 1000


def test_pvp_accept_transfers_pot():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    _mk(repo, "a", "A", 2000)
    _mk(repo, "b", "B", 2000)
    pvp = PvpService(repo)
    pvp.challenge("a", "b", 100)
    before_a = repo.get("a").spirit_stones
    before_b = repo.get("b").spirit_stones
    r = pvp.accept("b")
    assert before_a == 1900
    # one side gained pot 200 or draw refunded
    if r.get("draw"):
        assert repo.get("a").spirit_stones == 2000
        assert repo.get("b").spirit_stones == 2000
    else:
        total = repo.get("a").spirit_stones + repo.get("b").spirit_stones
        assert total == 4000  # conserved
