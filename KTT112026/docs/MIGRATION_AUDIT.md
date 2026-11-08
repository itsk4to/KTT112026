# KTT102026 V3.10.0 -> KTT112026 0.1.0 migration audit

## Scope selected

The source archive contains a combined cultivation game and Discord utility bot. This new project intentionally carries forward the reusable voice/audio functions only: voice connection, optional 24/7 presence, YouTube music, queue controls, Vietnamese TTS and FFmpeg support. Gameplay, moderation, prison and game persistence are not copied.

## Carried forward

| Source in 102026 | Destination in 112026 | Result |
|---|---|---|
| `ui/voice_presence.py` | `features/voice/presence.py` | Reworked as a cancellable service with idempotent startup and no game imports. |
| `ui/music/player.py` | `features/voice/music/player.py` | Reworked per-guild player, shared music/TTS queue, bounded queue and thread-safe callback handoff. |
| `ui/music/tts.py` | `features/voice/tts/service.py` | Split validation/synthesis from playback; clips enter the shared queue; temp-file lifecycle is explicit. |
| `ui/music/ffmpeg_util.py` | `features/voice/audio/ffmpeg.py` | System FFmpeg first, imageio binary fallback, stale cache checked. |
| `ui/commands/music.py` and utility slash handlers in `bot.py` | `platform/discord_app/voice_commands.py` | Replaced game-coupled command registration with a standalone Cog. |
| `config.py` voice settings | `config.py` | New immutable, environment-only settings model. |

## Defects addressed from the source review

1. Audio callback previously called `asyncio.get_event_loop()` from the callback thread. The new player captures the owning event loop and uses `call_soon_threadsafe`.
2. TTS previously set an `asyncio.Event` from the audio callback thread. The new TTS path does not mutate asyncio primitives in that callback.
3. TTS previously stopped whatever audio was playing before speaking. Music and TTS now share one queue, so TTS waits its turn instead of unexpectedly cutting a song.
4. The previous player attempted the next track through recursive retry on repeated source failures. The new implementation advances iteratively.
5. The previous TTS module imported an unused audio-source helper and depended directly on player internals. TTS now depends on the public `enqueue_tts` method.
6. The previous queue had no configured size limit. The new queue is bounded per guild.
7. Partial/queued TTS files could outlive an error or stop. The new service cleans synthesis failures, skipped clips, playback completion and stopped queues.
8. The previous voice-presence task had no explicit cancellation path. The new service exposes `stop()` and is shut down with the bot.
9. Configuration and deployment still referenced game database/owner/moderation settings. Those settings have been removed from the new project.

## Not carried over

All `game/` packages, game commands/views, player database, schema/migrations, economy, moderation, prison, admin game sessions and game-only dependencies/configuration are excluded. No game DB is migrated.

## Verification boundary

Static source review and isolated unit tests are included. A real Discord connection, YouTube extraction, Edge TTS network synthesis and FFmpeg playback require a configured Discord bot and live network/runtime environment; they are not claimed as end-to-end verified here.
