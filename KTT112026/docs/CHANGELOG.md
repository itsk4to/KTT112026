# Changelog

## 1.9.2 — Mẫu ĐƠN HÀNG mới
- Mẫu thông báo đơn hàng theo mẫu mới (emoji_67 tiêu đề, emoji_74 trạng thái, bỏ dòng thời gian).
- Tự thêm emoji của sản phẩm (két, kèn/tên lửa, rank, xu) vào dòng **Sản Phẩm** nếu có; sản phẩm không có emoji thì chỉ ghi tên. Emoji lấy từ `CATEGORIES` trong `shop_delta/catalog.py`.

## 1.9.1 — Shop Delta: sửa gửi thông báo xong đơn, mẫu legit mới
- **Sửa lỗi "nghẹn" khi xong đơn:** `/done` giờ báo từng bước ✅/❌ kèm lý do, không còn nuốt lỗi; có thể gõ lại `/done` để gửi lại; tự fetch kênh nếu không có trong cache; gửi cả thông báo "ĐƠN HÀNG HOÀN THÀNH" ra kênh đơn hàng (kể cả khi chưa có `/donhang`). Mọi lệnh có error handler, không còn treo "đang suy nghĩ".
- **Mẫu legit mới:** `+1 legit <@người_bán> <mã sp>` với người bán cố định (`/shopcfg nguoi_ban`); mã gõ `DL-0001`/`dl-1`/`1` đều nhận.
- **Bảng copy sẵn:** khối code trong thông báo xong đơn (ticket + DM), nút 📋 Copy mẫu legit, `/legitbang` gửi + ghim bảng hướng dẫn.
- Thêm `/baohanh`, `/thongke`, `/huydon`.

# Changelog

## 1.9.0 — Shop Delta: ticket tự phân loại + đơn hàng + legit
- Khách nhập sản phẩm khi mở ticket; bot tự phân loại theo từ khoá và tạo kênh trong danh mục Discord tương ứng.
- Tự gửi thông báo "chưa có staff online" đầu ticket; mỗi người 1 ticket đang mở.
- `/donhang` gửi thông báo ĐƠN HÀNG (mẫu có trạng thái ⌛ Chờ) vào kênh chỉ định; gọi lại sẽ sửa đơn cũ.
- `/done` cảm ơn trong ticket + DM khách, đổi trạng thái đơn → ✅ Hoàn thành.
- `+1 legit @người_bán <mã_đơn>` ở kênh legit: bot kiểm tra và cấp bảo hành 48h.
- `/shopcfg` đặt kênh đơn hàng / kênh legit / role staff (lưu DB, schema v21).
- Chi tiết: `docs/SHOP_DELTA.md`.

