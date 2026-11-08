# KTT112026 — Voice & TTS Foundation

**Phiên bản khởi tạo:** `0.1.0`  
**Nguồn kế thừa:** `KTT102026 V3.10.0`  
**Phạm vi bản mới:** Discord Voice, nhạc YouTube, TTS tiếng Việt và voice presence 24/7. Không mang hệ thống gameplay sang bản này.

## Chức năng đang có

| Nhóm | Chức năng | Cách dùng |
|---|---|---|
| Voice | Bot vào kênh thoại | `/join` |
| Voice | Bot rời kênh thoại | `/leave` |
| Voice | Kiểm tra trạng thái kết nối | `/voice-status` |
| Music | Tìm và phát nhạc YouTube | `/play <link hoặc tên bài>` |
| Music | Xem hàng chờ nhạc/TTS | `/queue` |
| Music | Bỏ qua mục hiện tại | `/skip` |
| Music | Tạm dừng / tiếp tục | `/pause`, `/resume` |
| Music | Dừng và xóa hàng chờ | `/stop` |
| TTS | Đọc tiếng Việt bằng Edge TTS | `/tts` hoặc `.tts <văn bản>` |
| System | Kiểm tra độ trễ / dependency audio | `/ping`, `/health` |
| Voice presence | Tự kết nối lại một voice channel | Cấu hình `KTT_VOICE_CHANNEL_ID` |

TTS và nhạc dùng chung **một hàng chờ theo từng server**. TTS không tự cắt bài nhạc đang phát; clip TTS sẽ phát theo thứ tự đã xếp. File MP3 tạm được xóa khi phát xong, bị bỏ qua hoặc hàng chờ bị dừng.

## Cài đặt nhanh

Cần Python 3.11+, FFmpeg và một Discord bot đã được mời vào server với quyền xem/kết nối/phát âm thanh. Dự án dùng `discord.py` 2.7.1+ trong nhánh 2.x (voice extra).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

Điền `DISCORD_TOKEN` trong biến môi trường của host (hoặc file `.env` nếu bạn tự nạp dotenv). Sau đó chạy:

```bash
pip install -e .
python -m ktt112026
```

Ứng dụng không tự đọc `.env`; `.env.example` chỉ là mẫu để bạn cấu hình trên host. Không đưa token thật vào Git, ZIP chia sẻ hoặc log.

## Discord Developer Portal

Bật **Message Content Intent** trong Discord Developer Portal để dùng lệnh tương thích `.tts`. `voice_states` đã được bật trong mã bot; đây không phải privileged member intent. Bot cần quyền Connect và Speak; nếu dùng kênh giới hạn quyền, cấp quyền tại chính kênh đó.

## Cấu hình

Xem [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md). Voice presence 24/7 mặc định tắt. Muốn dùng, đặt `KTT_VOICE_CHANNEL_ID` bằng ID kênh thoại thường. Khi bật self-deaf, bot chỉ nghe voice/presence; các lệnh `/play` và `/tts` sẽ chuyển kết nối sang chế độ không deaf để phát âm thanh.

## Tài liệu kỹ thuật

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — cấu trúc và ranh giới module.
- [`docs/VOICE_SYSTEM.md`](docs/VOICE_SYSTEM.md) — kết nối voice, hàng chờ, TTS và dọn file.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Docker/Nixpacks.
- [`docs/MIGRATION_AUDIT.md`](docs/MIGRATION_AUDIT.md) — những gì kế thừa, sửa, bỏ và giới hạn đã biết.

## Kiểm thử

```bash
pip install -r requirements-dev.txt
pytest -q
```

Bản 0.1.0 là nền tảng Voice/Music/TTS đã tách khỏi game, không phải bản thay thế toàn bộ KTT102026 và không chứa dữ liệu/database game.
