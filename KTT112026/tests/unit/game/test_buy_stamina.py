import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService


def test_buy_stamina_and_cap():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ps = PlayerService(repo, rng=random.Random(0))
    ps.create("u", "U")
    p = repo.get("u")
    p.spirit_stones = 10_000
    p.stamina = 10
    repo.save(p)
    r = ps.buy_stamina("u", 1)
    assert r["gain"] > 0
    assert repo.get("u").spirit_stones < 10_000
    # fill and fail
    p = repo.get("u")
    p.stamina = p.max_stamina
    p.spirit_stones = 10_000
    repo.save(p)
    try:
        ps.buy_stamina("u", 1)
        assert False
    except ValueError:
        pass
