# Kato Tu Tiên (Đạo Lộ Tu Tiên) — Trạng thái dự án & Lộ trình

**Mã nguồn:** KTT112026  
**Phiên bản code:** **v1.5.0**  
**Đối chiếu:** GDD V2 (*Dự Án Kato Tu Tiên V2*)  
**Cập nhật:** 2026-11-16  

Tài liệu này là **source of truth** kỹ thuật. GDD V2 là ý tưởng thiết kế; khi lệch → **ưu tiên bảng dưới**.

---

## 1. Tóm tắt một dòng

Vòng chơi chính + độ kiếp build + kinh tế cơ bản + nhiệm vụ ngày **đã chạy trên Railway** (DB Volume `/data`).  
Còn lại chủ yếu: cân LS sâu, polish UI, hardened anti-dupe, feedback closed beta.

---

## 2. Đã làm (Implemented) — v1.3.0

### 2.1 Nền tảng
| Hạng mục | Chi tiết |
|----------|----------|
| Kiến trúc | `db/` · `voice/` · `game/{models,rules,content,services,repo,render,discord}` |
| Database | SQLite schema **v12** (pets, partner, codes, auction, daily_progress, dokiep buffs…) |
| Deploy | Dockerfile không `VOLUME`; `KTT_DATABASE_PATH=/data/...`; JSON content trong `src` |
| Data-driven | JSON: vũ khí, đan (~38), linh thú (36), công pháp (20), zones (6), recipes (9), summon |
| UI | Pillow + nút Discord; **thẻ `.me` theo màu Đạo Lộ + khung cảnh giới** |
| Admin | `/admin tutien` (version, give/set stones, codes, lookup) |
| Giftcode | `.code <mã>` |

### 2.2 Vòng chơi
| Lệnh / Hệ | Trạng thái |
|-----------|------------|
| `.taothe` · `.me` | Có — radar, trang bị, thú, lực chiến, đạo lữ, theme Tiên/Ma |
| `.tu` / `.tu n` / `.tu max` | Có — batch, cooldown, trừ TL |
| Hồi thể lực offline | Có — ~2 phút/điểm |
| Khóa `.tu` khi 100% | Có → `.dp` / `.dokiep` |
| `.dp` tiểu cảnh + % | Có — Ngộ/Căn; fail mất ~15% TV |
| Ép `.chon` trước Hậu Kỳ / Độ Kiếp | Có (G14) |
| `.dokiep` 5 vòng | Có — Khí Vận/đan loại đáp án, Hộ Thể, Đạo Lữ +1 |
| `.shop` / `.mua` / `.tui` / `.mac` | Có — lọc cảnh giới/đạo; giá scale nhẹ theo major |
| `.dung` · `.hoc` · `.lucchien` | Có |
| `.thap` | Có |
| `.trieuhoi` (5000 LS) · `.mang` | Có |
| `.bicanh` | Có — 6 zone, event + boss Cấp 3+ |
| `.haiduoc` · `.luyendan` · `.congthuc` | Có — 9 công thức |
| `.daugia` | Có — đăng/xem/mua, phí 5%, 48h |
| `.chuyen` · `.ban` · `.bxh` | Có |
| `.ketduyen` · `.songtu` | Có |
| `.diemdanh` · `.nhiemvu` · `.nhannv` | Có |
| `.help` / `.huongdan` | Có |
| Voice | Có — join/play/tts… |

---

## 3. Còn thiếu / làm chưa đủ

| # | Hạng mục | Mức | Ghi chú |
|---|----------|-----|---------|
| T1 | Ma trận LS mid–late đầy đủ | TB | Mới scale giá shop 8%/major — chưa bảng sink/source đủ |
| T2 | Effect đan combat còn placeholder | TB | Đan độ kiếp đã gắn; combat thuần chưa |
| T4 | Anti-dupe regression suite | TB | Atomic SQL cơ bản; thiếu test tải |
| G12+ | UI gradient mượt / shop card theme | Thấp | `.me` đã theme; shop/cultivate chưa đồng bộ hết |
| — | Event boss theo từng zone (skill text) | Thấp | Boss generic đã có |
| — | Closed Beta checklist vận hành | TB | Cần playtest thật |

---

## 4. Lộ trình tiếp

| Phase | Nội dung | Trạng thái |
|-------|----------|------------|
| E Tu & `.dp` | G1–G4, G8, G13 | **Xong** |
| F Độ kiếp build | G5–G7 | **Xong** |
| G Kinh tế | `.daugia` + scale giá nhẹ | **Xong khung** — T1 còn |
| H PvE & đan | zones/event/boss/recipes | **Xong khung** |
| I UI Thẻ 2 | theme `.me` + ép đạo | **Xong phần chính** |
| J Closed Beta | anti-dupe, cân số, feedback | **Chưa** |

### Ưu tiên code tiếp
1. Playtest / cân LS (T1)  
2. Suite chống dupe (T4)  
3. Đồng bộ theme shop/cultivate  
4. Không mở PVP / full map một lần  

---

## 5. Ma trận lệnh (cập nhật)

| Nhóm | Lệnh | Code |
|------|------|------|
| Nhân vật | `.taothe` `.me` `.lucchien` | OK |
| Tu luyện | `.tu` `[n]`/`max` | OK |
| Đột phá | `.dp` `.dokiep` | OK |
| Đạo / thế lực | `.chon` `.gianhap` | OK + gate |
| Kinh tế | `.shop` `.mua` `.ban` `.chuyen` `.daugia` | OK |
| Ngày | `.diemdanh` `.nhiemvu` `.nhannv` | OK |
| PvE | `.thap` `.bicanh` | OK |
| Admin | `/admin tutien …` · `.code` | OK |
| Voice | `/join` `/play` `/tts` … | OK |

---

## 6. Deploy Railway

- Volume mount: **`/data`**  
- `KTT_DATABASE_PATH=/data/ktt112026.db`  
- `KTT_ADMIN_IDS=<discord_ids>`  
- `DISCORD_TOKEN=…`  
- Không dùng Docker `VOLUME` instruction  

---

## 7. Kết luận

Bản **v1.5.0** đủ vòng tân thủ → mid game nhẹ.  
Bước tiếp: **playtest + cân bằng**, không phình feature lớn.


### v1.5.0
- Hệ Tông Môn `.tongmon`
- BXH mới + format 1k
- `.dung [n]` · `.daolu` · `.info @user` · case-insensitive


### v1.5.0 Tông môn cộng đồng
- mời/kick/chức vụ, BXH nội bộ, cấp tông, quà top tuần
