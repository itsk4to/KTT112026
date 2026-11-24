import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.content.realms import stage_requirement
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.economy.auction_service import AuctionService
from ktt112026.game.services.player.dokiep_service import DokiepService
from ktt112026.game.services.player.player_service import PlayerService


def _repo():
    db = Database(":memory:")
    ensure_schema(db)
    return PlayerRepository(db)


def test_dokiep_hints_and_partner_shield():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    a = ps.create("a", "A")
    b = ps.create("b", "B")
    a.path = "tien"
    a.major_realm = 1
    a.minor_stage = 2
    a.cultivation = stage_requirement(1, 2)
    a.stats.can_cot = 80
    a.stats.khi_van = 90
    a.partner_id = "b"
    b.partner_id = "a"
    repo.save(a)
    repo.save(b)
    dk = DokiepService(repo, rng=random.Random(2))
    sess = dk.start("a")
    assert sess.shields >= 5  # 4 from can_cot + 1 partner
    assert sess.hints
    prompt = sess.prompt()
    assert 1 <= len(prompt["options"]) <= 3


def test_auction_list_buy():
    repo = _repo()
    ps = PlayerService(repo, rng=random.Random(1))
    ps.create("s", "Seller")
    ps.create("b", "Buyer")
    repo.inventory_add("s", "linhthao", 3)
    buyer = repo.get("b")
    buyer.spirit_stones = 10000
    repo.save(buyer)
    auc = AuctionService(repo)
    r = auc.create("s", "linhthao", 100, 2)
    rows = auc.list_open()
    assert any(x["id"] == r["id"] for x in rows)
    bought = auc.buy("b", r["id"])
    assert bought["price"] == 100
