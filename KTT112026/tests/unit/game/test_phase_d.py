import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.render.cards import render_profile_card
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.shop_service import ShopService


def test_shop_hides_far_realm_and_wrong_path():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    ps = PlayerService(repo, rng=random.Random(1))
    p = ps.create("u", "A")
    p.path = "tien"
    p.major_realm = 1
    repo.save(p)
    shop = ShopService(repo)
    items = shop.catalog("vukhi", "u")
    assert items
    for it in items:
        assert int(it["major_min"]) <= 2
        assert it.get("path") in ("any", "tien", None) or it["path"] == "tien"


def test_profile_card_bytes():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    p = PlayerService(repo, rng=random.Random(1)).create("u", "Đạo Hữu Test")
    png = render_profile_card(p, power=123, gear_names={"weapon1": "Thanh Trúc Kiếm"}, pet_names=["Hỏa Vân Báo"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
