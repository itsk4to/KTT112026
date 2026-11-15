# Changelog

## 0.9.0 — Phase E (bám GDD "Dự Án Kato Tu Tiên V2")

### Thêm mới
- **Hồi Thể Lực ngoại tuyến:** 1 điểm / 3 phút theo thời gian thực (`game/rules/stamina.py`), áp dụng khi đọc người chơi từ DB.
- **`.tu [số_lần|max]`:** gộp tối đa 20 lượt trong một lệnh, cooldown tính một lần; dừng khi hết Thể Lực hoặc đầy thanh.
- **Khóa 100% + `.dp`:** từ Cấp 2, đầy Tu Vi thì khóa `.tu`; `.dp` đột phá tiểu cảnh với tỷ lệ theo Ngộ Tính/Căn Cốt (50–95%), thất bại mất 10% mốc Tu Vi. Cấp 1 vẫn tự lên tiểu cảnh.
- **Độ Kiếp minh bạch:** Khí Vận loại đáp án sai; Tị Lôi Đan (vòng 1–2), Phá Chướng Đan (mọi vòng), Hộ Mạch Đan (+Hộ Thể), Kim Thân Đan, Hộ Tâm Đan, Hoàn Hồn Đan thực sự có hiệu lực; Đạo Lữ +1 Hộ Thể; thông báo hỗ trợ hiện trên thẻ, nút đáp án bị loại bị khóa.
- **Phải `.chon tien|ma` trước khi `.dokiep`.**
- **`.hoithe`:** mua +30 Thể Lực bằng Linh Thạch, tối đa 5 lần/ngày (200 LS × đại cảnh giới).
- **`.daugia`:** Sàn Đấu Giá giá cố định giữa người chơi (`ban`/`mua`/`huy`/`cua`), ký gửi đồ, phí 5%, hết hạn 24h tự trả đồ, tối đa 5 lô/người.
- **`.help`** dạng thẻ ảnh: `.help` (tổng quan + 4 bước mở đầu) và `.help <chủ_đề|lệnh>` (vd `.help dokiep`, `.help daugia`, có/không dấu, có/không dấu chấm). 7 chủ đề, nội dung ở `game/content/help.py`; test đảm bảo mọi lệnh game đều có trong help. Gợi ý tân thủ sau `.taothe`.
- Thanh tu vi chuyển cam-đỏ khi 100%.

### Sửa lỗi / độ tin cậy
- **Transaction:** `chuyen`, `ban`, `mua`, `dung`, `hoc`, `luyendan`, `trieuhoi`, kết duyên/song tu, Độ Kiếp và sàn đấu giá chạy trong một transaction (lỗi giữa chừng → rollback, không mất/nhân đôi đồ hay Linh Thạch).
- Đan Độ Kiếp trước đây bị tiêu hao mà không có tác dụng — nay lưu thành buff dùng ở lần `.dokiep` kế tiếp.

### Chưa làm (so với GDD)
- Đấu giá theo kiểu trả giá tăng dần (hiện là giá cố định).
- Thẻ 2 / gradient động, Đạo Lữ truyền công qua lệnh riêng.
- Cân bằng kinh tế (Source & Sink) và mở rộng hái dược / công thức luyện đan (hiện 5 thảo dược, 4 công thức).
- Công thức tu vi: các hằng số mới (hồi 3 phút, 10%/20%, 5%) cần playtest.
