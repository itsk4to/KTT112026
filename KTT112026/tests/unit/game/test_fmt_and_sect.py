import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.sect_service import SectService
from ktt112026.game.util.formatters import fmt_num


def test_fmt_num():
    assert fmt_num(999) == "999"
    assert fmt_num(1000) == "1k"
    assert fmt_num(1500) in ("1.5k", "1.5k")
    assert "M" in fmt_num(2_500_000) or "m" in fmt_num(2_500_000).lower()


def test_sect_join():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("u", "A")
    p = repo.get("u")
    p.path = "tien"
    p.major_realm = 2
    p.faction = "tongmon"
    repo.save(p)
    ss = SectService(repo)
    r = ss.join("u", "thanhvan")
    assert r["sect"]["id"] == "thanhvan"
    d = ss.donate("u", 100)
    assert d["contrib"] >= 100
