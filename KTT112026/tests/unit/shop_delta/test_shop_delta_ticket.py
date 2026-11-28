"""Shop Delta: phân loại từ khoá, định dạng đơn, ticket → done → +1 legit / bảo hành 48h."""
from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.shop_delta.catalog import CATEGORIES, classify
from ktt112026.shop_delta.fmt import (
    SELLER_ID_DEFAULT,
    build_done_notice,
    build_order_message,
    done_thanks_text,
    format_money,
    legit_template,
    normalize_code,
    parse_legit,
    parse_money,
)
from ktt112026.shop_delta.service import ShopTicketService

H = 3600


def _svc():
    db = Database(":memory:")
    ensure_schema(db)
    return ShopTicketService(db)


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError as exc:
        return str(exc)
    raise AssertionError("expected ValueError")


# ---------- từ khoá ----------
def test_classify_keywords():
    assert classify("két mùa 3x3") == ["ket"]
    assert classify("Mua KÈN harmonica") == ["item"]
    assert classify("tên lửa") == ["item"]
    assert classify("cày rank từ đồng lên KC") == ["rank"]
    assert classify("2 triệu xu") == ["xu"]
    assert classify("làm hợp đồng định mệnh") == ["nhiemvu"]
    assert classify("nhà sưu tầm") == ["nhiemvu"]


def test_classify_multi_order_and_fallback():
    assert classify("kèn harmonica và két mùa")[:2] == ["item", "ket"]
    assert classify("két mùa + hợp đồng sưu tập") == ["ket", "nhiemvu"]
    assert classify("abc xyz") == ["khac"]
    assert classify("") == ["khac"]
    assert classify("25 đồng") == ["khac"]  # "đồng" là tiền, không phải rank


def test_every_category_has_discord_name_and_slug():
    for key, c in CATEGORIES.items():
        assert c["discord_category"] and c["slug"] and c["label"], key


# ---------- tiền ----------
def test_parse_money():
    assert parse_money("25k") == 25_000
    assert parse_money("25K") == 25_000
    assert parse_money("25000") == 25_000
    assert parse_money("150.000") == 150_000
    assert parse_money("1,500,000") == 1_500_000
    assert parse_money("1tr5") == 1_500_000
    assert parse_money("2tr") == 2_000_000
    assert parse_money("2.5k") == 2_500
    assert parse_money("25.000₫") == 25_000
    for bad in ("", "abc", "k"):
        _raises(parse_money, bad)


def test_format_money_matches_template():
    assert format_money(25_000) == "25K VNĐ (25.000 VNĐ)"
    assert format_money(150_000) == "150K VNĐ (150.000 VNĐ)"
    assert format_money(1_500_000) == "1.500K VNĐ (1.500.000 VNĐ)"
    assert format_money(2_500) == "2.500 VNĐ"


def test_order_message_matches_requested_layout():
    msg = build_order_message(amount=25_000, channel_id=111, user_id=222,
                              product="x2 bút sivi 1 tháng", status="pending", created_ts=1795762399)
    assert msg.startswith("## <:order:1544918574106148895> **ĐƠN HÀNG**\n")
    assert "> **Số Tiền**: **``25K VNĐ (25.000 VNĐ)``**" in msg
    assert "> **Ticket**: <#111>" in msg
    assert "> **Khách hàng**: <@222>" in msg
    assert ">>> **Sản Phẩm**: <a:Boost1:1426859771406979202>  x2 bút sivi 1 tháng" in msg
    assert "**Trạng thái**: ⌛ **Chờ**" in msg
    assert msg.endswith("✦ <t:1795762399:f>")
    done = build_order_message(amount=25_000, channel_id=1, user_id=2, product="p", status="done", created_ts=1)
    assert "✅ **Hoàn thành**" in done and "⌛" not in done


# ---------- cú pháp legit ----------
def test_parse_legit():
    assert parse_legit("+1 legit <@123> dl-0001") == (123, "DL-0001")
    assert parse_legit("+1 LEGIT <@!123> DL-0001 cảm ơn shop") == (123, "DL-0001")
    assert parse_legit("  +1   legit   <@9>   DL-12") == (9, "DL-0012")
    assert parse_legit(f"+1 legit <@{SELLER_ID_DEFAULT}> 7") == (SELLER_ID_DEFAULT, "DL-0007")
    assert parse_legit("+1 legit shop DL-1") is None
    assert parse_legit("legit <@1> DL-1") is None
    assert parse_legit("+1 legit <@1>") is None


def test_normalize_code():
    assert normalize_code("dl-1") == "DL-0001"
    assert normalize_code("DL0001") == "DL-0001"
    assert normalize_code("12") == "DL-0012"
    assert normalize_code("`DL-0001`.") == "DL-0001"
    assert normalize_code("abc") == "ABC"


def test_copy_template_and_done_message():
    assert legit_template(SELLER_ID_DEFAULT, "DL-0001") == f"+1 legit <@{SELLER_ID_DEFAULT}> DL-0001"
    txt = done_thanks_text(code="DL-0001", product="két", user_id=5, seller_id=SELLER_ID_DEFAULT, legit_channel_id=9)
    assert f"```\n+1 legit <@{SELLER_ID_DEFAULT}> DL-0001\n```" in txt  # khối code để copy
    assert "<#9>" in txt and "48h" in txt


def test_done_notice_and_unset_amount():
    n = build_done_notice(code="DL-0001", channel_id=1, user_id=2, product="két", amount=25_000)
    assert "ĐƠN HÀNG HOÀN THÀNH" in n and "`DL-0001`" in n and "25K VNĐ" in n and "<@2>" in n
    assert "Số Tiền" not in build_done_notice(code="DL-1", channel_id=1, user_id=2, product="p", amount=0)
    m = build_order_message(amount=0, channel_id=1, user_id=2, product="p", status="pending", created_ts=1)
    assert "Chưa cập nhật" in m
    c = build_order_message(amount=5_000, channel_id=1, user_id=2, product="p", status="cancelled", created_ts=1)
    assert "❌" in c


# ---------- ticket → done → legit ----------
def _ticket(svc, user=10, channel=500, **k):
    r = svc.reserve_ticket(guild_id=1, user_id=user, kind="buy", categories=["ket"],
                           product_text="két mùa 3x3", detail="", now=1000.0)
    svc.attach_channel(r["id"], channel)
    return r


def test_reserve_makes_sequential_codes_and_channel_lookup():
    svc = _svc()
    a = _ticket(svc, channel=500)
    b = _ticket(svc, user=11, channel=501)
    assert a["code"] == "DL-0001" and b["code"] == "DL-0002"
    assert svc.get_by_channel(500)["user_id"] == "10"
    assert svc.get_by_code("dl-0002")["channel_id"] == "501"


def test_one_open_ticket_per_user_and_discard():
    svc = _svc()
    r = _ticket(svc)
    assert len(svc.open_tickets(10)) == 1
    svc.mark_closed(r["id"])
    assert svc.open_tickets(10) == []
    p = svc.reserve_ticket(guild_id=1, user_id=12, kind="buy", categories=["khac"], product_text="x", detail="")
    assert svc.open_tickets(12) == []  # chưa gắn kênh → không tính
    svc.discard(p["id"])
    assert svc.get_by_code(p["code"]) is None


def test_complete_once_only():
    svc = _svc()
    _ticket(svc)
    t = svc.complete(500, staff_id=99, now=2000.0)
    assert t["status"] == "done" and t["staff_id"] == "99" and t["done_at"] == 2000.0
    assert "đã hoàn thành" in _raises(svc.complete, 500, 99)
    assert "không phải ticket" in _raises(svc.complete, 777, 99)


def test_legit_grants_48h_warranty():
    svc = _svc()
    r = _ticket(svc)
    svc.complete(500, staff_id=99, now=2000.0)
    res = svc.legit(10, 99, r["code"], now=5000.0)
    assert res["warranty_until"] == 5000.0 + 48 * H
    assert res["count"] == 1
    assert svc.get_by_code(r["code"])["legit_at"] == 5000.0


def test_legit_rejections():
    svc = _svc()
    r = _ticket(svc)
    assert "Không tìm thấy" in _raises(svc.legit, 10, 99, "DL-9999")
    assert "chưa được shop xác nhận" in _raises(svc.legit, 10, 99, r["code"])  # chưa /done
    svc.complete(500, staff_id=99, now=2000.0)
    assert "không phải của bạn" in _raises(svc.legit, 11, 99, r["code"])  # người lạ dùng mã
    assert "Sai người bán" in _raises(svc.legit, 10, 55, r["code"])  # tag sai người
    svc.legit(10, 99, r["code"], now=3000.0)
    assert "đã legit rồi" in _raises(svc.legit, 10, 99, r["code"])  # legit hai lần
    assert svc.legit_count() == 1


def test_order_fields_and_settings():
    svc = _svc()
    r = _ticket(svc)
    svc.set_order(r["id"], amount=25_000, product="p", channel_id=7, message_id=8, now=1500.0)
    t = svc.get_by_code(r["code"])
    assert (t["amount"], t["order_message_id"], t["order_at"]) == (25_000, "8", 1500.0)
    svc.set_order(r["id"], amount=30_000, product="p", channel_id=7, message_id=8, keep_time=True)
    assert svc.get_by_code(r["code"])["order_at"] == 1500.0  # sửa đơn không đổi giờ
    assert svc.get_int("order_channel", 42) == 42
    svc.set_setting("order_channel", "123")
    svc.set_setting("order_channel", "456")
    assert svc.get_int("order_channel", 42) == 456


def test_legit_accepts_fixed_seller_even_if_other_staff_did_done():
    svc = _svc()
    r = _ticket(svc)
    svc.complete(500, staff_id=99, now=2000.0)  # staff 99 bấm /done
    res = svc.legit(10, SELLER_ID_DEFAULT, "1", now=3000.0, seller_ids=(SELLER_ID_DEFAULT,))  # mã gõ tắt "1"
    assert res["ticket"]["code"] == r["code"]
    r2 = _ticket(svc, user=11, channel=501)
    svc.complete(501, staff_id=99, now=2000.0)
    assert "Sai người bán" in _raises(svc.legit, 11, 12345, r2["code"], seller_ids=(SELLER_ID_DEFAULT,))
    assert f"<@{SELLER_ID_DEFAULT}>" in _raises(svc.legit, 11, 12345, r2["code"], seller_ids=(SELLER_ID_DEFAULT,))


def test_done_can_be_repeated_to_resend_notifications():
    svc = _svc()
    _ticket(svc)
    first = svc.complete(500, staff_id=99, now=2000.0)
    again = svc.complete(500, staff_id=98, now=9999.0, allow_repeat=True)
    assert again["done_at"] == first["done_at"] == 2000.0 and again["staff_id"] == "99"
    assert "đã hoàn thành" in _raises(svc.complete, 500, 99)  # mặc định vẫn chặn


def test_warranty_status_states():
    svc = _svc()
    r = _ticket(svc)
    assert svc.warranty_status(r["code"])["state"] == "chua_legit"
    svc.complete(500, staff_id=99, now=100.0)
    svc.legit(10, 99, r["code"], now=1000.0)
    assert svc.warranty_status(r["code"], now=1000.0 + 47 * H)["state"] == "con_han"
    assert svc.warranty_status(r["code"], now=1000.0 + 49 * H)["state"] == "het_han"
    assert "Không tìm thấy" in _raises(svc.warranty_status, "DL-9999")


def test_stats():
    svc = _svc()
    a = _ticket(svc, user=10, channel=500)
    b = _ticket(svc, user=11, channel=501)
    _ticket(svc, user=12, channel=502)  # vẫn mở
    svc.set_order(a["id"], amount=25_000, product="p", channel_id=1, message_id=1, now=1.0)
    svc.set_order(b["id"], amount=150_000, product="p", channel_id=1, message_id=2, now=1.0)
    svc.complete(500, 99, now=1_000_000.0)
    svc.complete(501, 99, now=1_000_000.0 - 3 * 86400)
    st = svc.stats(now=1_000_000.0 + 10)
    assert st["day"] == (1, 25_000) and st["week"] == (2, 175_000) and st["all"] == (2, 175_000)
    assert st["open"] == 1 and st["legit"] == 0
