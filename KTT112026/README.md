# KTT112026 — Đạo Lộ Tu Tiên

**v0.5.0** — Cây thư mục gọn, dễ sửa.

## Cây chính
```
src/ktt112026/
  bot.py config.py
  db/          # SQLite
  voice/       # nhạc + TTS
  game/
    models/ rules/ content/
    services/ repo/
    render/    # ảnh
    discord/   # lệnh + nút
```

Chi tiết: `docs/STRUCTURE.md`

## Lệnh game
`.taothe` `.me` `.tu` `.chon` `.dokiep` `.gianhap` `.shop` `.mua` `.tui` `.mac` `.dung` `.hoc` `.congphap` `.lucchien` `.thap`

## Chạy
```bash
pip install -r requirements.txt
export DISCORD_TOKEN=...
python -m ktt112026
```

## Tài liệu dự án
- Trạng thái & lộ trình: `docs/PROJECT_STATUS_V2.md`
- Roadmap ngắn: `docs/ROADMAP_SUMMARY.md`

## Railway — không mất DB khi Update

Gắn **Volume** mount path `/data`, set:

```text
KTT_DATABASE_PATH=/data/ktt112026.db
```

Chi tiết: `docs/RAILWAY_VOLUME.md`.

Phiên bản: xem `VERSION.txt` · quy ước `docs/VERSIONING.md`.
