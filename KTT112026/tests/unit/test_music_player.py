import asyncio
import threading
from pathlib import Path

import pytest

from ktt112026.features.voice.music.manager import MusicManager
from ktt112026.features.voice.music.models import TTSClip, Track
from ktt112026.features.voice.music.player import GuildMusicPlayer


class FakeVoice:
    def __init__(self):
        self.connected = True
        self.playing = False
        self.paused = False
        self.callback = None
        self.last_source = None

    def is_connected(self):
        return self.connected

    def is_playing(self):
        return self.playing

    def is_paused(self):
        return self.paused

    def play(self, source, *, after):
        if self.playing or self.paused:
            raise RuntimeError("already playing")
        self.last_source = source
        self.callback = after
        self.playing = True

    def finish(self):
        callback = self.callback
        self.callback = None
        self.playing = False
        if callback:
            callback(None)

    def stop(self):
        self.finish()

    def pause(self):
        self.playing = False
        self.paused = True

    def resume(self):
        self.paused = False
        self.playing = True

    async def disconnect(self, force=False):
        self.connected = False


class FakeSource:
    pass


def fake_track(title="track"):
    return Track(title, f"https://stream/{title}", f"https://example.com/{title}", 100, 1)


@pytest.mark.asyncio
async def test_queue_advances_from_audio_callback_thread():
    voice = FakeVoice()
    player = GuildMusicPlayer(1, source_factory=lambda item, ffmpeg: FakeSource())
    player.voice = voice
    player._loop = asyncio.get_running_loop()

    await player.enqueue(fake_track("one"))
    await player.enqueue(fake_track("two"))
    assert player.current.title == "one"
    assert len(player.queue) == 1

    thread = threading.Thread(target=voice.finish)
    thread.start()
    thread.join()
    await asyncio.sleep(0.05)

    assert player.current.title == "two"
    assert voice.playing is True


@pytest.mark.asyncio
async def test_bad_audio_source_does_not_recurse_and_next_item_plays():
    voice = FakeVoice()
    calls = []

    def factory(item, ffmpeg):
        calls.append(item.title)
        if item.title == "bad":
            raise RuntimeError("invalid source")
        return FakeSource()

    player = GuildMusicPlayer(2, source_factory=factory)
    player.voice = voice
    player._loop = asyncio.get_running_loop()
    player.queue.append(fake_track("bad"))
    player.queue.append(fake_track("good"))

    await player._play_next()
    assert calls == ["bad", "good"]
    assert player.current.title == "good"
    assert voice.playing is True


@pytest.mark.asyncio
async def test_tts_clip_is_deleted_after_playback(tmp_path):
    voice = FakeVoice()
    player = GuildMusicPlayer(3, source_factory=lambda item, ffmpeg: FakeSource())
    player.voice = voice
    player._loop = asyncio.get_running_loop()
    clip_path = tmp_path / "speech.mp3"
    clip_path.write_bytes(b"audio")

    await player.enqueue_tts(TTSClip("speech", str(clip_path), 8))
    assert clip_path.exists()
    voice.finish()
    await asyncio.sleep(0.05)
    assert not clip_path.exists()
    assert player.current is None


@pytest.mark.asyncio
async def test_queue_limit_cleans_rejected_tts_clip(tmp_path):
    player = GuildMusicPlayer(4, max_queue=1)
    clip_path = tmp_path / "rejected.mp3"
    clip_path.write_bytes(b"audio")
    player.queue.append(fake_track("pending"))

    with pytest.raises(RuntimeError, match="giới hạn"):
        await player.enqueue_tts(TTSClip("speech", str(clip_path), 8))
    assert not clip_path.exists()


def test_music_manager_keeps_players_per_guild():
    manager = MusicManager()
    assert manager.player(10) is manager.player(10)
    assert manager.player(10) is not manager.player(11)

@pytest.mark.asyncio
async def test_stale_stream_url_is_refreshed_before_playback(monkeypatch):
    import time
    import ktt112026.features.voice.music.resolver as resolver

    voice = FakeVoice()
    seen = []
    monkeypatch.setattr(resolver, "refresh_stream_url", lambda url: asyncio.sleep(0, result="https://fresh/audio"))
    player = GuildMusicPlayer(5, source_factory=lambda item, ffmpeg: seen.append(item.stream_url) or FakeSource())
    player.voice = voice
    player._loop = asyncio.get_running_loop()
    old = Track("stale", "https://expired/audio", "https://example.com/watch", 10, 1, resolved_at=time.monotonic() - 300)

    player.queue.append(old)
    await player._play_next()
    assert seen == ["https://fresh/audio"]
    assert player.current.stream_url == "https://fresh/audio"

@pytest.mark.asyncio
async def test_late_callback_does_not_clear_new_current_item():
    voice = FakeVoice()
    player = GuildMusicPlayer(6, source_factory=lambda item, ffmpeg: FakeSource())
    player.voice = voice
    player._loop = asyncio.get_running_loop()
    await player.enqueue(fake_track("old"))
    old_callback = voice.callback
    new_item = fake_track("new")
    player.current = new_item
    voice.playing = True

    old_callback(None)
    await asyncio.sleep(0.05)
    assert player.current is new_item
    assert voice.playing is True
