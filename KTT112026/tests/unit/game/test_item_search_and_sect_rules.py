from ktt112026.game.content.item_search import search_items
from ktt112026.game.rules.sect_rules import can_change_role, can_kick, has_permission


def test_search_by_id_and_name():
    rows = search_items("tukhidan")
    assert rows and rows[0]["id"] == "tukhidan"
    rows2 = search_items("dan")
    assert len(rows2) >= 1


def test_sect_rules_rank():
    assert can_kick("leader", "member")
    assert can_kick("elder", "member")
    assert not can_kick("member", "elder")
    assert not can_kick("elder", "leader")
    assert has_permission("leader", "sect.promote")
    assert not has_permission("elder", "sect.promote")
    assert can_change_role("leader", "member", "elder", promote=True)
    assert not can_change_role("elder", "member", "elder", promote=True)
