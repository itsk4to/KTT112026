# Cấu trúc mã nguồn KTT112026 (v1.8.0+)

## Nguyên tắc
- **Data-driven**: JSON nằm trong `game/content/data/`, logic không hardcode số liệu.
- **Tách lớp**: Rules (thuần) → Services (nghiệp vụ) → Discord (UI/lệnh) → Render (ảnh).
- **Nhóm theo domain**: Dễ tìm, dễ mở rộng, dễ review.

```
src/ktt112026/
├── bot.py                  # Khởi tạo bot, wire services, setup cogs
├── config.py               # Settings (env, path)
├── db/                     # SQLite schema + connection
│   ├── schema.py
│   └── connection.py
├── game/
│   ├── content/            # Dữ liệu tĩnh + loader
│   │   ├── data/           # *.json (danduoc, linhthu, congphap, ...)
│   │   ├── loader.py
│   │   ├── realms.py
│   │   ├── shop.py
│   │   └── item_search.py
│   ├── rules/              # Logic thuần (không DB, không Discord)
│   │   ├── combat_rules.py
│   │   ├── cultivation.py
│   │   └── sect_rules.py
│   ├── models/             # Dataclass / Player
│   ├── repo/               # Truy cập DB (PlayerRepository)
│   ├── services/           # Nghiệp vụ — nhóm theo domain
│   │   ├── player/         # player, stats, dokiep, technique
│   │   ├── combat/         # combat, tower, sect_tower, pvp
│   │   ├── economy/        # shop, auction, bet, inventory, item_use, code
│   │   ├── social/         # sect, partner, leaderboard, leader
│   │   └── world/          # quest, mission, world_event, daily, gather, alchemy, pet
│   ├── discord/            # Lệnh + View
│   │   ├── commands.py     # GameCommands (có thể tách tiếp theo feature)
│   │   ├── admin_commands.py
│   │   └── *_view.py       # ShopView, TowerView, DokiepView, ...
│   └── render/             # Pillow cards / gacha image
│       ├── cards.py
│       └── gacha.py
└── voice/                  # Voice / Music / TTS
    ├── commands.py
    ├── presence.py
    ├── music/              # manager, player, resolver, models
    ├── tts/                # service, voices
    └── audio/              # ffmpeg helper
```

## Quy ước khi thêm tính năng mới
1. Dữ liệu số liệu → `game/content/data/*.json`
2. Công thức thuần → `game/rules/`
3. Nghiệp vụ + DB → `game/services/<domain>/`
4. Lệnh Discord → `game/discord/` (hoặc tách file nếu lớn)
5. Ảnh kết quả → `game/render/`

## Voice
Độc lập với game. Chỉ dùng khi bật voice/music/tts.
