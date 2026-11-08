import pytest

from ktt112026.features.voice.tts.service import validate_tts_text


def test_tts_text_is_trimmed():
    assert validate_tts_text("  xin chào  ", 20) == "xin chào"


def test_tts_rejects_empty_and_oversized_text():
    with pytest.raises(ValueError, match="trống"):
        validate_tts_text("  ")
    with pytest.raises(ValueError, match="giới hạn"):
        validate_tts_text("12345", 4)

from ktt112026.features.voice.music.models import TTSClip, Track
import ktt112026.features.voice.tts.service as tts_service


class FakePlayer:
    def __init__(self, current=None):
        self.current = current
        self.added = None

    async def enqueue_tts(self, clip):
        self.added = clip
        if self.current is None:
            self.current = clip
        return 1


@pytest.mark.asyncio
async def test_tts_reports_whether_clip_started_immediately(monkeypatch, tmp_path):
    clip_path = tmp_path / "sample.mp3"
    clip_path.write_bytes(b"audio")

    async def fake_synthesize(text, **kwargs):
        return TTSClip("TTS test", str(clip_path), kwargs["requester_id"])

    monkeypatch.setattr(tts_service, "synthesize", fake_synthesize)
    idle_player = FakePlayer()
    position, started = await tts_service.enqueue_speech(idle_player, "hello", 11)
    assert (position, started) == (1, True)
    assert idle_player.added.requester_id == 11

    music = Track("song", "stream", "https://example.com", 10, 2)
    busy_player = FakePlayer(current=music)
    position, started = await tts_service.enqueue_speech(busy_player, "hello", 11)
    assert (position, started) == (1, False)
    assert busy_player.current is music
