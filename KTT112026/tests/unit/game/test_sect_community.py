import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.sect_service import SectService


def _ready(repo, uid, name, path="tien"):
    ps = PlayerService(repo, rng=random.Random(1))
    if repo.get(uid) is None:
        ps.create(uid, name)
    p = repo.get(uid)
    p.path = path
    p.major_realm = 2
    p.faction = "tongmon"
    p.spirit_stones = 50_000
    repo.save(p)
    return p


def test_invite_kick_rank_weekly():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ss = SectService(repo)
    _ready(repo, "leader", "L")
    _ready(repo, "m1", "M1")
    _ready(repo, "m2", "M2")
    ss.join("leader", "thanhvan")
    inv = ss.invite("leader", "m1")
    assert inv["sect"]["id"] == "thanhvan"
    ss.join_via_invite("m1")
    assert repo.get("m1").sect_id == "thanhvan"
    ss.donate("leader", 1000)
    ss.donate("m1", 500)
    rank = ss.ranking("leader")
    assert rank["entries"]
    ss.kick("leader", "m1")
    assert repo.get("m1").sect_id == ""
    # weekly
    w = ss.process_weekly_rewards()
    assert w["paid"] is True
    w2 = ss.process_weekly_rewards()
    assert w2["paid"] is False
