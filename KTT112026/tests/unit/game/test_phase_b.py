import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.alchemy_service import AlchemyService
from ktt112026.game.services.exploration_service import ExplorationService
from ktt112026.game.services.gather_service import GatherService
from ktt112026.game.services.pet_service import PetService
from ktt112026.game.services.player_service import PlayerService


def _repo():
    db = Database(":memory:")
    ensure_schema(db)
    return PlayerRepository(db)


def test_summon_and_deploy():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    p = ps.create("u", "A")
    p.spirit_stones = 60000
    repo.save(p)
    pets = PetService(repo, rng=random.Random(2))
    r = pets.summon("u", 1)
    assert r["got"]
    pid = r["got"][0]["id"]
    name = pets.deploy("u", pid)
    assert name
    p2 = repo.get("u")
    assert pid in (p2.pet1, p2.pet2, p2.pet3)


def test_bicanh():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    ex = ExplorationService(repo, rng=random.Random(3))
    r = ex.explore("u", "linh_cuc")
    assert r["stones"] > 0


def test_gather_requires_sect():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    g = GatherService(repo, rng=random.Random(1))
    try:
        g.gather("u")
        assert False
    except ValueError:
        pass
    p = repo.get("u")
    p.path = "tien"
    p.major_realm = 2
    p.faction = "tongmon"
    repo.save(p)
    r = g.gather("u")
    assert r["qty"] >= 1


def test_alchemy():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    repo.inventory_add("u", "linhthao", 5)
    repo.inventory_add("u", "thanhtrucdiep", 5)
    al = AlchemyService(repo, rng=random.Random(0))
    # force many attempts - at least structure works
    r = al.craft("u", "tukhidan")
    assert "success" in r
