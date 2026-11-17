import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.sect_service import LEADER_CONTRIB, SectService


def _ready(repo, uid, name, path="tien"):
    ps = PlayerService(repo, rng=random.Random(1))
    if repo.get(uid) is None:
        ps.create(uid, name)
    p = repo.get(uid)
    p.path = path
    p.major_realm = 3
    p.faction = "tongmon"
    p.spirit_stones = 200_000
    p.created_at = 0  # old account
    repo.save(p)
    return p


def test_npc_leader_by_contrib_and_create():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ss = SectService(repo)
    _ready(repo, "a", "A")
    ss.join("a", "thanhvan")
    # donate enough for leadership
    need = max(LEADER_CONTRIB, 8000)
    repo.get("a").spirit_stones = need + 1000
    repo.save(repo.get("a"))
    r = ss.donate("a", need)
    assert r.get("promoted") == "leader" or repo.get("a").sect_role == "leader"
    ss.leave("a")
    created = ss.create_sect("a", "Thiên Cơ Các")
    assert created["sect"]["id"]
    assert repo.get("a").sect_role == "leader"


def test_weekly_items_not_stones():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ss = SectService(repo)
    _ready(repo, "a", "A")
    ss.join("a", "thanhvan")
    ss.donate("a", 100)
    w = ss.process_weekly_rewards()
    assert w["paid"] is True
    assert w["winners"]
    assert "items" in w["winners"][0]
    # inventory got something
    assert repo.inventory_qty("a", "anhlinhdan") >= 1 or repo.inventory_qty("a", "truccodan") >= 1
    w2 = ss.process_weekly_rewards()
    assert w2["paid"] is False
