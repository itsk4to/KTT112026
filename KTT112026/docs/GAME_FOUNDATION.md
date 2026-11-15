# Game — Đạo Lộ Tu Tiên (KTT112026)

Bám GDD mới. **Không** dùng ý tưởng/game loop bản KTT102026 cũ.

## UI
Game gửi **ảnh PNG** (Pillow), không dùng embed cho hồ sơ / tu luyện.

## Lệnh MVP (prefix `.`)
| Lệnh | Việc |
|------|------|
| `.taothe` | Tạo nhân vật, random linh căn + 5 chỉ số |
| `.me` | Thẻ nhân vật (ảnh) |
| `.tu [n\|max]` | Tu luyện gộp lệnh (cooldown ~4s, tốn thể lực) |
| `.dp` | Đột phá tiểu cảnh giới (Cấp 2+), có tỷ lệ |
| `.dokiep` | Độ Kiếp 5 vòng, có hỗ trợ Khí Vận / đan / Đạo Lữ |
| `.daugia` | Sàn đấu giá giá cố định |

## Chỉ số (GDD)
Căn Cốt · Ngộ Tính · Thần Thức · Thân Pháp · Khí Vận

## Cảnh giới
6 đại × 3 tiểu (Sơ/Trung/Hậu), song song Tiên/Ma. Cấp 1 đầy tu vi → tự lên tiểu cảnh.

## Tiếp theo
`.chon tien/ma` · `.dokiep` · shop · tháp · túi đồ
