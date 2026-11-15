import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.item_use_service import ItemUseService
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.stats_service import StatsService
from ktt112026.game.services.technique_service import TechniqueService


def _env():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    return repo, PlayerService(repo, rng=random.Random(1))


def test_use_tukhidan():
    repo, ps = _env()
    ps.create("u", "A")
    repo.inventory_add("u", "tukhidan", 2)
    r = ItemUseService(repo).use("u", "tukhidan")
    assert r["player"].cultivation >= 500
    assert repo.inventory_qty("u", "tukhidan") == 1


def test_learn_technique_tier():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.major_realm = 2
    repo.save(p)
    repo.inventory_add("u", "dankhiquyet", 2)
    tech = TechniqueService(repo)
    r1 = tech.learn("u", "dankhiquyet")
    assert r1["tier"] == 1
    r2 = tech.learn("u", "dankhiquyet")
    assert r2["tier"] == 2


def test_stats_include_technique():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.major_realm = 2
    repo.save(p)
    repo.inventory_add("u", "dankhiquyet", 1)
    TechniqueService(repo).learn("u", "dankhiquyet")
    eff = StatsService(repo).effective("u")
    assert eff["power"] > 0
    assert "can_cot" in eff["stats"]
