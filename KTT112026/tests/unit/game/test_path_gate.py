import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player.dokiep_service import DokiepService
from ktt112026.game.services.player.player_service import PlayerService


def test_dp_requires_path_for_hau():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    svc = PlayerService(repo, rng=random.Random(1))
    svc.create("u", "A")
    p = repo.get("u")
    p.minor_stage = 1
    p.cultivation = stage_requirement(1, 1)
    p.path = ""
    repo.save(p)
    try:
        svc.breakthrough_minor("u")
        assert False
    except ValueError as e:
        assert "chon" in str(e).lower()


def test_dokiep_requires_path():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    svc = PlayerService(repo, rng=random.Random(1))
    svc.create("u", "A")
    p = repo.get("u")
    p.minor_stage = 2
    p.cultivation = stage_requirement(1, 2)
    p.path = ""
    repo.save(p)
    dk = DokiepService(repo, rng=random.Random(1))
    try:
        dk.start("u")
        assert False
    except ValueError as e:
        assert "chon" in str(e).lower()
