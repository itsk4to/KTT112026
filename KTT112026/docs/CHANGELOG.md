# Changelog

## 1.9.0 — Shop Delta: ticket tự phân loại + đơn hàng + legit
- Khách nhập sản phẩm khi mở ticket; bot tự phân loại theo từ khoá và tạo kênh trong danh mục Discord tương ứng.
- Tự gửi thông báo "chưa có staff online" đầu ticket; mỗi người 1 ticket đang mở.
- `/donhang` gửi thông báo ĐƠN HÀNG (mẫu có trạng thái ⌛ Chờ) vào kênh chỉ định; gọi lại sẽ sửa đơn cũ.
- `/done` cảm ơn trong ticket + DM khách, đổi trạng thái đơn → ✅ Hoàn thành.
- `+1 legit @người_bán <mã_đơn>` ở kênh legit: bot kiểm tra và cấp bảo hành 48h.
- `/shopcfg` đặt kênh đơn hàng / kênh legit / role staff (lưu DB, schema v21).
- Chi tiết: `docs/SHOP_DELTA.md`.

