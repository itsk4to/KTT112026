# Kato Tu Tiên (Đạo Lộ Tu Tiên) — Trạng thái dự án & Lộ trình

**Mã nguồn:** KTT112026  
**Phiên bản code:** v0.8.0  
**Đối chiếu:** GDD V2 (*Dự Án Kato Tu Tiên V2*)  
**Cập nhật:** 2026-11-16  

Tài liệu này là **source of truth** về trạng thái kỹ thuật.  
GDD V2 vẫn là tài liệu thiết kế ý tưởng; khi lệch nhau thì **ưu tiên bảng trạng thái bên dưới**.

---

## 1. Tóm tắt một dòng

Xương sống game (tu → độ kiếp → shop → xã hội cơ bản) **đã chạy**.  
GDD V2 bổ sung gộp lệnh, hồi thể lực offline, `.dp` + % đột phá, UI độ kiếp minh bạch — **code chưa đủ**.  
Phần báo cáo trong PDF V2 (mục VII) **lệch thực tế**: vài mục ghi “đã làm” chưa có; vài mục ghi “chưa” thực ra đã có khung.

---

## 2. Đã làm (Implemented)

### 2.1 Nền tảng
| Hạng mục | Chi tiết |
|----------|----------|
| Kiến trúc | `db/` · `voice/` · `game/{models,rules,content,services,repo,render,discord}` |
| Database | SQLite, schema v7 (inventory, techniques, pets, partner, limits) |
| Data-driven | JSON: vũ khí, đan (35), linh thú (36), công pháp (20), pháp bảo, zone, thảo, công thức, summon |
| UI | Ảnh Pillow + nút Discord (shop, độ kiếp, tháp) — **không** dùng Embed thuần / Chart.js |

### 2.2 Vòng chơi
| Lệnh / Hệ | Trạng thái |
|-----------|------------|
| `.taothe` · `.me` | Có — radar, trang bị, thú, lực chiến, đạo lữ |
| `.tu` | Có — 1 lần/lệnh, cooldown ~4s, trừ thể lực |
| `.chon tien/ma` · `.gianhap` | Có |
| `.dokiep` 5 vòng + Hộ Thể | Có — nút 1/2/3; Căn Cốt ảnh hưởng Hộ Thể |
| Auto lên Sơ→Trung→Hậu khi đầy tu vi | Có (khác V2: V2 muốn khóa + `.dp`) |
| `.shop` / `.mua` / `.tui` / `.mac` | Có — shop lọc cảnh giới + Đạo |
| `.dung` · `.hoc` · `.lucchien` | Có |
| `.thap` | Có — hộp đen, Tiếp tục / Rút lui |
| `.trieuhoi` (5000 LS) · `.mang` · `.thuve` | Có — tối đa 3 xuất chiến |
| `.bicanh` | Có — 2 zone, nhãn yêu cầu Tiên/Ma |
| `.haiduoc` · `.luyendan` · `.congthuc` | Có — khung tối thiểu |
| `.chuyen` · `.ban` · `.bxh` | Có |
| `.ketduyen` · `.huyduyen` · `.songtu` | Có |
| Voice (nhạc/TTS/treo phòng) | Có — tách module `voice/` |

---

## 3. Chưa làm / Làm chưa đủ (Gaps vs GDD V2)

### 3.1 Cơ chế V2 — **bắt buộc sửa / bổ sung**

| # | Hạng mục | Mức độ | Mô tả cần làm |
|---|----------|--------|----------------|
| G1 | `.tu [n]` / `.tu max` | Cao | Gộp nhiều lượt trong 1 lệnh; trừ thể lực × n; chống spam/bot-click |
| G2 | Hồi thể lực offline | Cao | Hồi AP theo thời gian real-time khi không online; không hồi Tu Vi AFK |
| G3 | Khóa `.tu` khi 100% | Cao | Đầy thanh → khóa tu; bắt đột phá mới tu tiếp |
| G4 | Lệnh `.dp` tiểu cảnh | Cao | Thay auto-up Sơ/Trung/Hậu bằng `.dp` + **% thành công** (Ngộ, Căn, đan) |
| G5 | UI độ kiếp minh bạch | Cao | Hiện rõ: Khí Vận / đan đã loại đáp án nào |
| G6 | Đan độ kiếp gắn phiên | Cao | Hộ Tâm, Tị Lôi, +Hộ Thể… áp vào session `.dokiep` |
| G7 | Đạo Lữ +1 Hộ Thể khi độ kiếp | Trung | Buff khi có partner còn hiệu lực |
| G8 | Bảng mốc Tu Vi V2 | Trung | Đồng bộ `realms.py` với bảng 1k → 200M trong GDD |
| G9 | `.daugia` | Trung | Sàn đấu giá — chưa có |
| G10 | Bí cảnh mở rộng + event | Trung | Mới 2 zone; thiếu event ngẫu nhiên / boss |
| G11 | Luyện đan đầy đủ | Thấp–TB | Mới vài công thức; chưa full nhóm thảo |
| G12 | Gradient / Thẻ 2 theo đạo & cảnh giới | Thấp | Chuẩn màu V2 (Tiên cyan→vàng, Ma đỏ→tím; khung theo cấp) |
| G13 | `.help` / `.huongdan` onboarding | Cao | Sau `.taothe` hướng dẫn tân thủ |
| G14 | Ép chọn đạo ở tiểu cảnh 3 | Trung | Thông báo bắt buộc `.chon` trước khi lên tiếp |

### 3.2 Nợ kỹ thuật / cân bằng

| # | Vấn đề | Hướng xử lý |
|---|--------|-------------|
| T1 | Source/sink LS dễ lệch mid–late | Ma trận thu nhập–giá shop theo đại cảnh giới |
| T2 | Effect đan combat nhiều cái mới “ghi nhận” | Map dần vào service, không để placeholder |
| T3 | PDF V2 mục VII lệch code | Dùng file này làm báo cáo trạng thái; cập nhật PDF sau |
| T4 | Chống dupe LS/đồ | Kiểm tra atomic SQL khi transfer/mua/bán; test regression |

---

## 4. Việc cần sửa đổi ngay (patch list)

Ưu tiên implement theo thứ tự:

### Patch 1 — Tu luyện & thể lực (khớp trang 1 GDD V2)
1. `.tu [n]` và `.tu max` (cap theo thể lực còn lại)
2. Hồi thể lực offline: công thức ví dụ `+1 AP / N phút`, không vượt `max_stamina`
3. Khi tu vi = 100% tiểu cảnh / hậu kỳ đại cảnh: **khóa `.tu`**, message chỉ sang `.dp` hoặc `.dokiep`

### Patch 2 — Đột phá tiểu cảnh `.dp`
1. Bỏ (hoặc tắt) auto-advance Sơ→Trung→Hậu
2. `.dp`: roll % theo Ngộ Tính (+ đan hỗ trợ nếu có)
3. Thành công → lên tiểu cảnh, tu vi về 0; thất bại → trừ một phần tu vi

### Patch 3 — Độ kiếp “build có nghĩa”
1. Khí Vận cao → loại 1 đáp án sai (hiện text trên ảnh)
2. Đan Tị Lôi / Hộ Tâm… apply trước khi hiện 3 lựa chọn
3. Căn Cốt ≥ 70 → 4 Hộ Thể; Đạo Lữ → +1 Hộ Thể (cap hợp lý)

### Patch 4 — Onboarding & số liệu
1. `.help` / `.huongdan`
2. Đồng bộ bảng tu vi GDD
3. Sau `.taothe` gửi hướng dẫn ngắn

### Patch 5 — Kinh tế & nội dung
1. `.daugia` tối giản (đăng / xem / mua hoặc hết giờ)
2. Thêm zone bí cảnh + 1–2 event
3. Mở rộng recipes luyện đan

---

## 5. Lộ trình phase (cập nhật lại)

> Phase A–D trong code **đã xong khung**.  
> Phase dưới đây là **theo GDD V2 + thực tế còn thiếu** (không lặp lại B/C/D cũ).

| Phase | Tên | Nội dung chính | Kết quả mong đợi |
|-------|-----|----------------|------------------|
| **E** | Tu & Đột phá V2 | G1–G4, G8, G13 | Vòng `.tu n` → khóa 100% → `.dp` / `.dokiep` đúng GDD |
| **F** | Độ kiếp & Build | G5–G7, đan độ kiếp | Người chơi cảm nhận chỉ số/đan có giá trị |
| **G** | Kinh tế sâu | G9, T1, mở rộng shop/sink | Có `.daugia`, LS không vỡ mid-game |
| **H** | PvE & Đan | G10–G11 | Bí cảnh/event, luyện đan đủ dùng |
| **I** | UI Thẻ 2 | G12 | Gradient đạo lộ + khung theo đại cảnh giới |
| **J** | Closed Beta | T4, stress test, anti-dupe | Ổn định data + throughput lệnh |

### Định nghĩa Closed Beta (giữ hướng V2)
- Không dupe LS / vật phẩm  
- Vòng tân thủ tự chạy với `.huongdan`  
- `.tu n`, hồi AP, `.dp`, `.dokiep` minh bạch hoạt động ổn  
- Thu thập feedback cân bằng chỉ số & drop  

---

## 6. Không làm ngay (tránh đứt mạch)

- Đổi stack sang Node/Chart.js chỉ để vẽ thẻ (Pillow đủ)  
- PVP lớn  
- Full 10+ map một lần  
- Viết lại toàn bộ GDD thay vì patch đúng gap  

---

## 7. Ma trận lệnh (nhanh)

| Nhóm | Lệnh | Code |
|------|------|------|
| Nhân vật | `.taothe` `.me` `.lucchien` | OK |
| Tu luyện | `.tu` | OK 1 lần — **thiếu** `[n]`/`max` |
| Đột phá | `.dokiep` | OK khung — **thiếu** UI hỗ trợ & `.dp` |
| Đạo / thế lực | `.chon` `.gianhap` | OK |
| Kinh tế | `.shop` `.mua` `.ban` `.chuyen` | OK — **thiếu** `.daugia` |
| Sức mạnh | `.dung` `.hoc` `.trieuhoi` `.mang` | OK khung |
| PvE | `.thap` `.bicanh` | OK cơ bản |
| Xã hội | `.bxh` `.ketduyen` `.songtu` | OK |
| Hỗ trợ | `.help` `.huongdan` `.dp` | **Thiếu** |

---

## 8. Kết luận điều hướng

1. **Sửa PDF / giao tiếp team:** dùng file này thay mục VII của PDF V2.  
2. **Code tiếp theo:** Phase **E** (Patch 1–2) trước — đúng trọng tâm trang 1–4 GDD V2.  
3. **Sau đó:** Phase **F** (độ kiếp minh bạch) → mới mở đấu giá / map lớn.

**Người phụ trách kỹ thuật** triển khai theo thứ tự Patch 1 → 5.  
**Thiết kế** chỉ chỉnh số trong JSON/`realms` khi không đổi rule.
