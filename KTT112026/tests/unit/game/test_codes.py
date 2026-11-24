import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.economy.code_service import CodeService
from ktt112026.game.services.player.player_service import PlayerService


def test_create_and_redeem():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    cs = CodeService(repo)
    r = cs.create_code(code="TESTCODE1", stones=1000, max_uses=2)
    assert r["code"] == "TESTCODE1"
    got = cs.redeem("u", "testcode1")
    assert got["stones"] == 1000
    try:
        cs.redeem("u", "TESTCODE1")
        assert False
    except ValueError:
        pass
