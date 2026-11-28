# Shop Delta — hệ thống ticket & đơn hàng

## Luồng
1. **Khách** bấm **MUA HÀNG** ở panel (`/panel`) → nhập *Sản phẩm cần mua* (+ ghi chú).
2. **Bot** tự phân loại theo từ khoá (`shop_delta/catalog.py`) và tạo kênh ticket trong **danh mục Discord** tương ứng
   (tự tạo nếu chưa có): Két mùa 3x3 · Nhiệm vụ · Cày rank · Cày xu · Item Layali · Hỗ trợ · Khác.
   Tên kênh: `ket-0001`, mã đơn: `DL-0001`. Mỗi người chỉ có 1 ticket đang mở.
3. Bot gửi ngay: "Thông báo: Hiện không có staff online, vui lòng chờ staff online sẽ hỗ trợ bạn sớm nhất".
4. Staff và khách trao đổi; `/pay` hiện nút BANK / THẺ CÀO.
5. `/donhang so_tien:25k [san_pham]` → gửi thông báo **ĐƠN HÀNG** (trạng thái ⌛ Chờ) vào kênh đơn hàng.
   Gọi lại `/donhang` = sửa đơn cũ, không gửi trùng. Số tiền nhận `25k`, `25000`, `150.000`, `1tr5`.
6. `/done [ghi_chu]` → cảm ơn trong ticket **và** DM khách, đổi trạng thái đơn thành ✅ Hoàn thành,
   hướng dẫn khách gõ legit.
7. Khách vào **kênh legit** copy mẫu `+1 legit <@875320426711117844> DL-0001` (thay mã) → bot kiểm tra rồi báo **bảo hành 48 giờ**.
   Mẫu có sẵn trong tin nhắn `/done`, nút **📋 Copy mẫu legit**, và bảng ghim bởi `/legitbang`.

## Bot kiểm tra khi +1 legit
Mã đơn tồn tại (gõ `DL-0001`, `dl-1` hay `1` đều được) · đúng chủ đơn · đơn đã `/done` · tag đúng người bán cố định (hoặc staff đã `/done`) · mỗi đơn chỉ legit 1 lần.
Bảo hành 48h tính **từ lúc legit thành công**.

## Cấu hình
`/shopcfg kenh_don_hang:#… kenh_legit:#… role_staff:@… nguoi_ban:@…` (admin). `nguoi_ban` là người được tag trong mẫu legit (mặc định 875320426711117844). Chưa đặt role staff thì chỉ admin dùng được lệnh staff.
Mặc định lấy hằng số ở đầu `shop_delta/__init__.py`.

## Quyền bot cần
Manage Channels, Manage Messages, View Channel, Send Messages, Embed Links, Read Message History.
Bot cần **Message Content Intent** để đọc `+1 legit` (đã bật trong `bot.py`).

## Thêm từ khoá / danh mục
Sửa `CATEGORIES` trong `shop_delta/catalog.py` (từ khoá viết không dấu, chữ thường).

## Lệnh khác
- `/legitbang` — gửi + ghim bảng hướng dẫn +1 legit (mẫu copy sẵn) vào kênh legit.
- `/baohanh ma:DL-0001` — khách/staff xem còn hạn bảo hành không.
- `/thongke` — đơn & doanh thu 24h / 7 ngày / tổng, ticket đang mở, số legit.
- `/huydon` — đổi trạng thái đơn trong kênh đơn hàng → ❌ Đã huỷ.

## Gửi thông báo xong đơn bị lỗi?
`/done` báo từng bước ✅/❌ kèm lý do (thiếu quyền, sai kênh…). Sửa xong gõ **`/done` lại** để gửi lại — đơn không bị đánh dấu hai lần.
Bot cần quyền **View Channel + Send Messages + Embed Links + Read Message History** ở kênh đơn hàng.
