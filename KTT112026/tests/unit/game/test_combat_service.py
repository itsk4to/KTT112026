import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.combat.combat_service import CombatService, monster_for_tower_floor
from ktt112026.game.services.player.player_service import PlayerService
from ktt112026.game.services.combat.tower_service import TowerService


def test_pve_and_tower_floor_combat():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    rng = random.Random(0)
    ps = PlayerService(repo, rng=rng)
    ps.create("u1", "Hero")
    p = repo.get("u1")
    p.stamina = 100
    p.spirit_stones = 0
    repo.save(p)
    combat = CombatService(repo, rng=rng)
    m = monster_for_tower_floor(1, player_power=50)
    r = combat.resolve_pve("u1", m)
    assert "won" in r and r["rounds"] >= 1
    assert r["log"]

    tower = TowerService(repo, rng=random.Random(1), combat=CombatService(repo, rng=random.Random(1)))
    run = tower.start("u1")
    assert run.floor >= 1
    assert run.last_monster
