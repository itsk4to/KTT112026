from ktt112026.game.models.player import Player
from ktt112026.game.render.cards import render_cultivate_card, render_profile_card


def test_profile_png():
    p = Player(user_id="1", display_name="Thử Nghiệm")
    data = render_profile_card(p)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_cultivate_png():
    data = render_cultivate_card(
        name="A",
        realm="Luyện Khí · Sơ Kỳ",
        gain=30,
        cultivation=30,
        need=1000,
        stamina=98,
        max_stamina=100,
        advanced=False,
    )
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
