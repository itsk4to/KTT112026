# Architecture

```text
src/ktt112026/
├── __main__.py                 # python -m ktt112026
├── bot.py                      # Discord startup/shutdown only
├── config.py                   # environment -> immutable Settings
├── platform/discord_app/
│   └── voice_commands.py       # slash commands + .tts adapter
└── features/voice/
    ├── presence.py             # optional 24/7 voice reconnect loop
    ├── audio/ffmpeg.py         # shared FFmpeg discovery
    ├── music/
    │   ├── models.py           # Track, TTSClip
    │   ├── resolver.py         # yt-dlp extraction
    │   ├── player.py           # per-guild queue and playback lifecycle
    │   └── manager.py          # guild -> player registry
    └── tts/
        ├── voices.py           # allow-listed Vietnamese voices
        └── service.py          # validation, Edge synthesis, queue integration
```

## Dependency direction

- `platform/discord_app` adapts Discord interactions to feature services.
- `features/voice/music` owns queue and playback state; it does not know command names.
- `features/voice/tts` synthesizes files and submits them to the same audio queue.
- `features/voice/audio` provides FFmpeg discovery only.
- `bot.py` wires settings, managers, command adapters and graceful shutdown.

No module imports `game/`; no game package is part of this project. A future game feature should be added as a separate `features/<name>/` package and must not take ownership of the voice player.

## Runtime ownership

Each Discord guild receives one `GuildMusicPlayer`. Each player owns one `VoiceClient` reference, queue, current item and transition lock. The audio callback may be invoked from Discord's audio thread, so it only schedules advancement onto the asyncio loop captured during connection.
