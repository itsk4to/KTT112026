# Voice, Music and TTS

## Connection lifecycle

`GuildMusicPlayer.connect()` reuses an existing guild VoiceClient when possible, moves it to the caller's voice channel and enables audio playback (not self-deaf). `VoicePresenceService` is optional and reconnects to the configured channel on a periodic loop. It does not pull the bot away from another channel while that guild has active queued/current audio.

## Shared queue

Music tracks and TTS clips are separate queue item types but share one per-guild player. This prevents music and TTS from concurrently calling `VoiceClient.play()`. A TTS request is synthesized first and then enqueued; it does not interrupt the current item.

## Audio callback safety

Discord's `after` callback can run outside the asyncio event-loop thread. The player captures the running loop when it connects and uses `call_soon_threadsafe` to schedule queue advancement. Failed audio-source creation is handled in an iterative loop so repeated invalid sources do not recurse indefinitely.

## Temporary-file lifecycle

TTS MP3 files are deleted after successful or failed playback, when skipped, or when the queue is stopped/left. Synthesis failures delete partial files. The cleanup operation is idempotent (`missing_ok=True`).

## FFmpeg

FFmpeg lookup order: system PATH, then the binary supplied by `imageio-ffmpeg`. Opus encoding is preferred; the player falls back to PCM when Opus source creation fails.
