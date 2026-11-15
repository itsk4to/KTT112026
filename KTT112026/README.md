# KTT112026 — Đạo Lộ Tu Tiên

**v0.9.0** — Phase E: hồi Thể Lực ngoại tuyến, `.tu [n]`, `.dp`, Độ Kiếp minh bạch hỗ trợ, transaction, Sàn Đấu Giá.

## Cây chính
```
src/ktt112026/
  bot.py config.py
  db/          # SQLite (schema v8)
  voice/       # nhạc + TTS
  game/
    models/ rules/ content/
    services/ repo/
    render/    # ảnh
    discord/   # lệnh + nút
```
Chi tiết: `docs/STRUCTURE.md` · Thay đổi: `docs/CHANGELOG.md`

## Lệnh game
`.taothe` `.me` `.tu [n|max]` `.dp` `.dokiep` `.hoithe` `.chon` `.gianhap` `.shop` `.mua` `.tui` `.mac` `.dung` `.hoc` `.congphap` `.lucchien`
`.bicanh` `.haiduoc` `.congthuc` `.luyendan` `.thap` `.trieuhoi` `.thu` `.mang` `.thuve`
`.chuyen` `.ban` `.daugia` `.bxh` `.ketduyen` `.huyduyen` `.songtu` `.help`

## Chạy
```bash
pip install -r requirements.txt
export DISCORD_TOKEN=...
python -m ktt112026
```

## Test
```bash
pip install -r requirements-dev.txt
pytest
```
