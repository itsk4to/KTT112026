from ktt112026.game.content.realms import realm_display, stage_requirement
from ktt112026.game.rules import can_auto_advance_minor, clamp, cultivation_gain


def test_clamp():
    assert clamp(-1, 0, 1) == 0
    assert clamp(2, 0, 1) == 1


def test_cultivation_gain_positive():
    assert cultivation_gain(ngo_tinh=50, root_quality="chan", major_realm=1) >= 1


def test_stage_requirement_grows():
    assert stage_requirement(1, 0) < stage_requirement(1, 1)
    assert stage_requirement(1, 2) < stage_requirement(2, 0)


def test_auto_advance():
    assert can_auto_advance_minor(1000, 1, 0) is True
    assert can_auto_advance_minor(999, 1, 0) is False
    assert can_auto_advance_minor(99999, 1, 2) is False


def test_realm_display():
    assert "Luyện Khí" in realm_display(1, 0, "tien")
    assert "Dẫn Khí" in realm_display(1, 0, "ma")
