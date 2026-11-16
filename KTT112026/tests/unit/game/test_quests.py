import random

from ktt112026.db.connection import Database
from ktt112026.db.schema import ensure_schema
from ktt112026.game.repo.players import PlayerRepository
from ktt112026.game.services.player_service import PlayerService
from ktt112026.game.services.quest_service import QuestService


def test_quest_progress_and_claim():
    db = Database(":memory:")
    ensure_schema(db)
    repo = PlayerRepository(db)
    PlayerService(repo, rng=random.Random(1)).create("u", "A")
    qs = QuestService(repo)
    qs.bump("u", "tu", 5)
    qs.bump("u", "bicanh", 2)
    qs.bump("u", "thap", 1)
    st = qs.status("u")
    assert st["all_complete"]
    r = qs.claim("u", "all")
    assert r["stones"] >= 120 + 150 + 180 + 250
    try:
        qs.claim("u", "all")
        assert False
    except ValueError:
        pass
