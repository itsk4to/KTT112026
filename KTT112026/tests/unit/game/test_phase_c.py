import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.economy_service import EconomyService
from ktt112026.game.services.leaderboard_service import LeaderboardService
from ktt112026.game.services.partner_service import PartnerService
from ktt112026.game.services.player_service import PlayerService


def _repo():
    db = Database(":memory:")
    ensure_schema(db)
    return PlayerRepository(db)


def test_transfer():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    a = ps.create("a", "A")
    b = ps.create("b", "B")
    a.spirit_stones = 1000
    repo.save(a)
    r = EconomyService(repo).transfer("a", "b", 300)
    assert r["amount"] == 300
    assert repo.get("a").spirit_stones == 700
    assert repo.get("b").spirit_stones == 500 + 300  # start 500 in create?


def test_sell_herb():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("a", "A")
    repo.inventory_add("a", "linhthao", 3)
    r = EconomyService(repo).sell_npc("a", "linhthao", 2)
    assert r["total"] > 0


def test_partner_songtu():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("a", "A")
    ps.create("b", "B")
    part = PartnerService(repo)
    part.bind("a", "b")
    r = part.songtu("a")
    assert r["gain_self"] > 0


def test_bxh():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("a", "A")
    data = LeaderboardService(repo).top("tuvi", 5)
    assert data["lines"]
