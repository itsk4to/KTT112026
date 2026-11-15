import re
from pathlib import Path

from ktt112026.game.content.help import ORDER, TOPICS, overview_rows, resolve_topic
from ktt112026.game.render.cards import render_help_card

COMMANDS_SRC = Path(__file__).parents[3] / "src/ktt112026/game/discord/commands.py"


def test_resolve_topic_variants():
    assert resolve_topic("dokiep") == "dokiep"
    assert resolve_topic(".dokiep") == "dokiep"
    assert resolve_topic("Độ Kiếp") is None or resolve_topic("Độ Kiếp") == "dokiep"
    assert resolve_topic("DAUGIA") == "kinhte"
    assert resolve_topic("tưởng tượng") is None
    assert resolve_topic(None) is None


def test_every_game_command_is_documented():
    names = re.findall(r'@commands\.(?:command|group)\(name="(\w+)"', COMMANDS_SRC.read_text())
    skip = {"help", "taothe_alias"}
    missing = [n for n in names if n not in skip and resolve_topic(n) is None]
    assert not missing, f"lệnh chưa có trong .help: {missing}"


def test_topics_well_formed():
    assert set(ORDER) == set(TOPICS)
    for t in TOPICS.values():
        assert t["rows"] and t["title"] and t["tip"]
    assert len(overview_rows()) == len(ORDER)


def test_help_cards_render():
    for k in ORDER:
        t = TOPICS[k]
        png = render_help_card(title=t["title"], rows=t["rows"], tip=t["tip"], footer="x")
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
