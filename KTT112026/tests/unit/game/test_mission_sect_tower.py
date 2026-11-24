import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.world.mission_service import MissionService
from ktt112026.game.services.player.player_service import PlayerService
from ktt112026.game.services.social.sect_service import SectService
from ktt112026.game.services.combat.sect_tower_service import SectTowerService


def test_missions_path_and_claim():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ps = PlayerService(repo, rng=random.Random(0))
    ps.create("u", "U")
    p = repo.get("u")
    p.path = "tien"
    p.faction = "tongmon"
    p.major_realm = 2
    repo.save(p)
    ms = MissionService(repo)
    st = ms.status("u")
    ids = {m["id"]: m for m in st["missions"]}
    assert ids["tien_dao"]["ready"] or ids["tien_dao"]["progress"] >= 1
    r = ms.claim("u", "tien_dao")
    assert r["stones"] > 0


def test_sect_tower_requires_sect():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ps = PlayerService(repo, rng=random.Random(0))
    ps.create("u", "U")
    p = repo.get("u")
    p.stamina = 50
    repo.save(p)
    st = SectTowerService(repo, rng=random.Random(0))
    try:
        st.start("u")
        assert False
    except ValueError as e:
        assert "tông" in str(e).lower() or "tong" in str(e).lower()
    p.path = "tien"
    p.faction = "tongmon"
    p.major_realm = 2
    repo.save(p)
    SectService(repo).join("u", "thanhvan")
    p = repo.get("u")
    p.stamina = 50
    repo.save(p)
    run = st.start("u")
    assert run.floor >= 1
