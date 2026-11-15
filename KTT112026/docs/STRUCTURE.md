# Cây thư mục KTT112026

```
src/ktt112026/
  bot.py              # Khởi động bot, gắn voice + game
  config.py           # Biến môi trường
  db/                 # SQLite dùng chung
    connection.py
    schema.py
  voice/              # Nhạc, TTS, treo phòng
    commands.py       # /join /play /tts …
    presence.py
    audio/
    music/
    tts/
  game/               # Đạo Lộ Tu Tiên
    models/           # Player, stats
    rules/            # Công thức thuần (không Discord)
    content/          # realms, shop data
    services/         # Use-case: tu, shop, dokiep, tháp…
    repo/             # Đọc/ghi DB
    render/           # Vẽ ảnh PNG
    discord/          # Lệnh .xxx + nút View
```

## Quy tắc sửa code

| Muốn đổi… | Sửa ở |
|-----------|--------|
| Công thức tu / độ kiếp | `game/rules/` |
| Tên cảnh giới, giá shop | `game/content/` |
| Luồng `.tu` `.mua` | `game/services/` |
| Ảnh thẻ / shop | `game/render/cards.py` |
| Lệnh & nút Discord | `game/discord/` |
| Cột DB | `db/schema.py` + `game/repo/` |
| Voice | `voice/` |

Không đặt công thức trong `discord/` hoặc `render/`.
