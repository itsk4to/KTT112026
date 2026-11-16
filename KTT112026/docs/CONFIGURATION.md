# Configuration

All runtime settings are environment variables. The application deliberately does not load `.env` files implicitly.

| Variable | Default | Description |
|---|---:|---|
| `DISCORD_TOKEN` | empty | Required bot token; keep it secret. |
| `KTT_COMMAND_PREFIX` | `.` | Prefix for the retained `.tts` command. |
| `KTT_VOICE_CHANNEL_ID` | `0` | Standard voice channel ID for optional 24/7 presence; `0` disables it. |
| `KTT_VOICE_SELF_DEAF` | `1` | Deafens bot while it is idle in the presence channel. |
| `KTT_VOICE_KEEPALIVE_SECONDS` | `45` | Reconnect check interval; values below 10 are raised to 10. |
| `KTT_MAX_MUSIC_QUEUE` | `100` | Maximum waiting items per server (does not count the current item). |
| `KTT_MAX_TTS_CHARS` | `500` | Maximum TTS characters per request. |
| `KTT_LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR or CRITICAL. |
| `KTT_SYNC_COMMANDS_ON_START` | `1` | Synchronize slash commands on startup. |

Supported voices: `vi-VN-HoaiMyNeural` and `vi-VN-NamMinhNeural`. The TTS service uses Edge TTS and therefore requires network access when a clip is synthesized.

## Python 3.13+

`audioop-lts` được cài có điều kiện trên Python 3.13+, nơi module `audioop` đã bị loại khỏi standard library.


## Database / Railway Volume

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `KTT_DATABASE_PATH` | `/data/ktt112026.db` (khi có `/data`) hoặc `data/ktt112026.db` | File SQLite người chơi |

Xem chi tiết: `docs/RAILWAY_VOLUME.md`.

## Admin

| Biến | Ý nghĩa |
|------|---------|
| `KTT_ADMIN_IDS` | Danh sách Discord user ID (phẩy) được dùng `/admin tutien` |

Lệnh:
- `/admin tutien version|give_stones|create_code|list_codes|delete_code|lookup|set_stones`
- Người chơi: `.code <mã>`
