"""Phase E — hồi Thể Lực ngoại tuyến, .tu [n], .dp, Độ Kiếp hỗ trợ, transaction, sàn đấu giá."""
import random
import time

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.rules import minor_breakthrough_chance, regen
from ktt112026.game.services.auction_service import AuctionService
from ktt112026.game.services.dokiep_service import DokiepService
from ktt112026.game.services.economy_service import EconomyService
from ktt112026.game.services.item_use_service import ItemUseService
from ktt112026.game.services.player_service import MAX_BATCH, PlayerService


def _env(seed=1):
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    return repo, PlayerService(repo, rng=random.Random(seed))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError as exc:
        return str(exc)
    raise AssertionError("expected ValueError")


# ---- hồi Thể Lực ----
def test_regen_pure():
    assert regen(10, 100, 1000.0, 1000.0 + 180 * 5) == (15, 1000.0 + 180 * 5)
    st, last = regen(10, 100, 1000.0, 1000.0 + 180 * 5 + 50)
    assert st == 15 and last == 1000.0 + 900  # giữ phần dư
    assert regen(99, 100, 0.0, 5000.0)[0] == 99  # chưa có mốc → không hồi lậu
    assert regen(95, 100, 1000.0, 1000.0 + 180 * 50)[0] == 100


def test_offline_regen_via_repo():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.stamina = 10
    p.last_stamina_at = time.time() - 180 * 7 - 5
    repo.save(p)
    assert repo.get("u").stamina == 17


# ---- .tu [n] + khóa 100% ----
def test_batch_cultivate_and_cooldown_once():
    repo, ps = _env()
    ps.create("u", "A")
    r = ps.cultivate("u", 5)
    assert r["ticks"] == 5 and r["gain"] > 0
    assert "Đang điều tức" in _raises(ps.cultivate, "u", 5)


def test_batch_capped_and_stops_when_out_of_stamina():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.stamina = 6
    p.last_stamina_at = time.time()
    repo.save(p)
    r = ps.cultivate("u", 999)
    assert r["ticks"] == 3  # 6 thể lực / 2 mỗi lượt


def test_lock_at_100_requires_dp_from_major2():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.major_realm, p.minor_stage, p.cultivation = 2, 0, 10_000
    p.max_stamina = p.stamina = 120
    repo.save(p)
    assert ".dp" in _raises(ps.cultivate, "u")


def test_major1_auto_advances_no_lock():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.cultivation = 999
    repo.save(p)
    r = ps.cultivate("u")
    assert r["advanced"] and repo.get("u").minor_stage == 1


def test_dp_success_and_fail():
    repo, ps = _env(seed=3)
    p = ps.create("u", "A")
    p.major_realm, p.minor_stage, p.cultivation = 2, 0, 10_000
    p.stats.ngo_tinh = p.stats.can_cot = 200  # tỷ lệ tối đa 0.95
    repo.save(p)
    assert minor_breakthrough_chance(200, 200) == 0.95
    ps.rng = random.Random(0)
    r = ps.breakthrough_minor("u")
    assert r["success"] and repo.get("u").minor_stage == 1 and repo.get("u").cultivation == 0
    # thất bại: ép rng luôn cao
    p = repo.get("u")
    p.cultivation = 20_000
    repo.save(p)

    class Hi:
        def random(self):
            return 0.999

    ps.rng = Hi()
    r = ps.breakthrough_minor("u")
    assert not r["success"] and repo.get("u").cultivation == 18_000


def test_dp_rejections():
    repo, ps = _env()
    ps.create("u", "A")
    assert "Cấp 1" in _raises(ps.breakthrough_minor, "u")


def test_buy_stamina_limits():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.stamina = 0
    p.spirit_stones = 10_000
    p.last_stamina_at = time.time()
    repo.save(p)
    r = ps.buy_stamina("u")
    assert r["gained"] == 30 and r["cost"] == 200
    for _ in range(4):
        q = repo.get("u")
        q.stamina = 0
        q.last_stamina_at = time.time()
        repo.save(q)
        ps.buy_stamina("u")
    q = repo.get("u")
    q.stamina = 0
    repo.save(q)
    assert "tối đa" in _raises(ps.buy_stamina, "u")


# ---- Độ Kiếp hỗ trợ ----
def _ready_for_kiep(repo, ps, **stats):
    p = ps.create("u", "A")
    p.major_realm, p.minor_stage, p.cultivation, p.path = 2, 2, 35_000, "tien"
    for k, v in stats.items():
        setattr(p.stats, k, v)
    repo.save(p)
    return p


def test_dokiep_requires_path():
    repo, ps = _env()
    p = ps.create("u", "A")
    p.major_realm, p.minor_stage, p.cultivation = 2, 2, 35_000
    repo.save(p)
    assert ".chon" in _raises(DokiepService(repo).start, "u")


def test_dokiep_khi_van_removes_wrong_with_message():
    repo, ps = _env()
    _ready_for_kiep(repo, ps, khi_van=200)  # tỷ lệ tối đa 0.45
    for seed in range(20):
        svc = DokiepService(repo, rng=random.Random(seed))
        sess = svc.start("u")
        svc._sessions.pop("u")
        hits = [(r, h) for r, h in enumerate(sess.hints) if h["removed"]]
        for r, h in hits:
            assert sess.correct[r] not in h["removed"]  # không bao giờ loại đáp án đúng
            assert any("Khí Vận" in n for n in h["notes"])
        if hits:
            return
    raise AssertionError("Khí Vận 200 nên loại được đáp án ở ít nhất một seed")


def test_tiloidan_buff_consumed_and_applied_rounds_1_2():
    repo, ps = _env()
    _ready_for_kiep(repo, ps, khi_van=1)
    repo.inventory_add("u", "tiloidan", 1)
    ItemUseService(repo).use("u", "tiloidan")
    assert "dokiep_remove_wrong" in repo.buff_list("u", "dokiep_")
    sess = DokiepService(repo, rng=random.Random(5)).start("u")
    for r in (0, 1):
        assert len(sess.hints[r]["removed"]) >= 1
        assert any("Tị Lôi Đan" in n for n in sess.hints[r]["notes"])
    assert not repo.buff_list("u", "dokiep_")  # đã tiêu thụ


def test_removed_option_rejected():
    repo, ps = _env()
    _ready_for_kiep(repo, ps)
    repo.inventory_add("u", "tiloidan", 1)
    ItemUseService(repo).use("u", "tiloidan")
    svc = DokiepService(repo, rng=random.Random(2))
    sess = svc.start("u")
    gone = sess.hints[0]["removed"][0]
    assert "bị loại" in _raises(svc.choose, "u", gone)


def test_shields_from_can_cot_and_partner():
    repo, ps = _env()
    _ready_for_kiep(repo, ps, can_cot=70)
    ps.create("v", "B")
    p, q = repo.get("u"), repo.get("v")
    p.partner_id, q.partner_id = "v", "u"
    repo.save(p)
    repo.save(q)
    sess = DokiepService(repo).start("u")
    assert sess.shields == 5  # 4 (Căn Cốt) + 1 (Đạo Lữ)


def test_dokiep_full_success_and_fail_loss():
    repo, ps = _env()
    _ready_for_kiep(repo, ps, khi_van=1)
    svc = DokiepService(repo, rng=random.Random(9))
    sess = svc.start("u")
    for r in range(5):
        pick = sess.correct[r]
        res = svc.choose("u", pick)
    assert res["session"].success and repo.get("u").major_realm == 3
    # thất bại
    p = repo.get("u")
    p.minor_stage, p.cultivation = 2, 350_000
    repo.save(p)
    svc2 = DokiepService(repo, rng=random.Random(9))
    sess = svc2.start("u")
    while not sess.finished:
        wrong = (sess.correct[sess.round_index] + 1) % 3
        if wrong in sess.current_hint()["removed"]:
            wrong = (wrong + 1) % 3
        svc2.choose("u", wrong)
    assert repo.get("u").cultivation == 280_000  # mất 20%


# ---- transaction ----
def test_transfer_is_atomic_on_failure():
    repo, ps = _env()
    ps.create("a", "A")
    ps.create("b", "B")
    eco = EconomyService(repo)
    orig = repo.save
    calls = {"n": 0}

    def flaky(player):
        calls["n"] += 1
        if calls["n"] == 2:  # lưu người nhận thì lỗi
            raise RuntimeError("boom")
        orig(player)

    repo.save = flaky
    try:
        eco.transfer("a", "b", 100)
    except RuntimeError:
        pass
    repo.save = orig
    assert repo.get("a").spirit_stones == 500 and repo.get("b").spirit_stones == 500


# ---- sàn đấu giá ----
def test_auction_flow_and_fee():
    repo, ps = _env()
    ps.create("s", "S")
    ps.create("b", "B")
    repo.inventory_add("s", "tukhidan", 3)
    au = AuctionService(repo)
    r = au.create("s", "tukhidan", 2, 400)
    assert repo.inventory_qty("s", "tukhidan") == 1  # ký gửi
    assert "chính mình" in _raises(au.buy, "s", r["id"])
    res = au.buy("b", r["id"])
    assert res["fee"] == 20
    assert repo.inventory_qty("b", "tukhidan") == 2
    assert repo.get("b").spirit_stones == 100
    assert repo.get("s").spirit_stones == 500 + 380
    assert "không còn" in _raises(au.buy, "b", r["id"])  # không mua hai lần


def test_auction_cancel_and_expire_return_items():
    repo, ps = _env()
    ps.create("s", "S")
    repo.inventory_add("s", "tukhidan", 2)
    au = AuctionService(repo)
    a = au.create("s", "tukhidan", 1, 100)
    au.cancel("s", a["id"])
    assert repo.inventory_qty("s", "tukhidan") == 2
    b = au.create("s", "tukhidan", 2, 100)
    repo.db.execute("UPDATE auctions SET expires_at=? WHERE id=?", (time.time() - 1, b["id"]))
    assert au.list_open() == []
    assert repo.inventory_qty("s", "tukhidan") == 2


def test_auction_rejects_unaffordable_and_missing():
    repo, ps = _env()
    ps.create("s", "S")
    ps.create("b", "B")
    au = AuctionService(repo)
    assert "không đủ" in _raises(au.create, "s", "tukhidan", 1, 100).lower()
    repo.inventory_add("s", "tukhidan", 1)
    a = au.create("s", "tukhidan", 1, 99_999)
    assert "Không đủ Linh Thạch" in _raises(au.buy, "b", a["id"])
    assert repo.inventory_qty("b", "tukhidan") == 0
