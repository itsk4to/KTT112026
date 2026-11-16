# Railway Volume — giữ DB người chơi khi Update code

## Mục tiêu
Deploy / push GitHub **không** xóa tiến trình người chơi. SQLite nằm trên **Volume** gắn vào container, tách khỏi image và repo.

## Cách làm trên Railway

1. Mở service bot → **Settings** → **Volumes** (hoặc Data → Volumes).
2. **Add Volume**
   - **Mount Path:** `/data`  
   - Size: tùy (1 GB đủ lâu cho SQLite nhỏ)
3. Biến môi trường (khuyến nghị ghi rõ):

```text
KTT_DATABASE_PATH=/data/ktt112026.db
DISCORD_TOKEN=...
```

4. Redeploy một lần để mount có hiệu lực.

## Hành vi code

| Môi trường | Đường dẫn DB |
|------------|----------------|
| Có `KTT_DATABASE_PATH` | Đúng path đó |
| Có thư mục `/data` (Volume) | `/data/ktt112026.db` |
| Chạy local không volume | `data/ktt112026.db` (trong project, gitignore) |

Dockerfile cũng set `ENV KTT_DATABASE_PATH=/data/ktt112026.db` và `VOLUME ["/data"]`.

## Lưu ý

- **Không** commit file `.db` lên GitHub.
- Đổi code / redeploy từ GitHub **không** đụng Volume.
- Xóa Volume hoặc đổi Mount Path = mất DB (backup nếu cần).
- Backup thủ công: tải file `/data/ktt112026.db` từ volume/shell khi Railway hỗ trợ.

## Kiểm tra sau deploy

Log khi bot start có thể thêm (tùy bản): path DB.  
Trong Discord: tạo `.taothe`, redeploy, `.me` vẫn còn là Volume đúng.
