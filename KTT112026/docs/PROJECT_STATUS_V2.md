# Kato Tu Tiên (Đạo Lộ Tu Tiên) — Trạng thái dự án & Lộ trình

**Mã nguồn:** KTT112026  
**Phiên bản code:** **v1.7.2**  
**Đối chiếu:** GDD V2 (*Dự Án Kato Tu Tiên V2*)  
**Cập nhật:** 2026-11-17  

Tài liệu này là **source of truth** kỹ thuật. GDD V2 là ý tưởng thiết kế; khi lệch → **ưu tiên bảng dưới**.

**Baseline merge:** V1.6.3 + chuỗi PR1→PR8 (logic chọn lọc từ KTT102026 V3.9.9).  
**Cấm port:** Secret Realm legacy (`secret_realm_*`). Bí cảnh V1 (`.bicanh`) vẫn còn trên baseline — gỡ riêng nếu product zero-bí-cảnh.

---

## 1. Tóm tắt một dòng

Vòng chơi chính, tông môn cộng đồng, combat PvE (tháp / tông tháp), PvP cọc, sự kiện ngày, nhiệm vụ ngày + dài hạn, kinh tế/shop/đấu giá — **chạy được trên Railway** với SQLite Volume `/data`.  
Còn: cân LS sâu, prison/moderation, NPC thoại, anti-dupe stress, closed beta.

---

## 2. Phiên bản gần đây

| Ver | Nội dung |
|-----|----------|
| 1.6.3 | Fix trùng lệnh `.info` / alias `.me` |
| 1.6.4 **PR1** | `combat_rules` thuần + unit tests |
| 1.6.5 **PR2** | `CombatService` + `.thap` đánh PvE thật |
| 1.6.6 **PR3+4** | `.tim`/`.tra` catalog; `sect_rules` rank kick/promote |
| 1.6.7 **PR5+6** | `.sukien`; `.pvp` escrow; schema **v16** |
| 1.6.8 **PR7+8** | `.nvda` nhiệm vụ dài; `.tongthap`; schema **v18** |
| **1.7.0** | Mốc chính: `.muatl` mua TL bằng LS (GDD V.2); schema **v18**; gộp PR1–8 |

Chi tiết PR: `docs/PR1_COMBAT_RULES.md` … `docs/PR7_PR8.md`.

---

## 3. Đã làm (Implemented)

### 3.1 Nền tảng
| Hạng mục | Chi tiết |
|----------|----------|
| Kiến trúc | `db/` · `voice/` · `game/{models,rules,content,services,repo,render,discord}` |
| Database | SQLite schema **v17** (sects, weekly, codes, auction, pets, world_event_claims, pvp_challenges, player_missions, sect_tower_runs…) |
| Deploy | Dockerfile; `PYTHONPATH=/app/src`; `KTT_DATABASE_PATH=/data/ktt112026.db`; JSON trong package + fallback `sects` |
| Data-driven | JSON: vũ khí, đan, linh thú, công pháp, zones, recipes, herbs, sects NPC |
| UI | Pillow + nút Discord; thẻ `.me` theme Đạo Lộ |
| Admin | `/admin tutien` (version, stones, codes, lookup) |
| Giftcode | `.code <mã>` |
| Rules thuần | `cultivation`, `breakthrough`, `combat_rules`, `sect_rules` |

### 3.2 Vòng chơi & xã hội
| Hệ | Lệnh / ghi chú |
|----|----------------|
| Nhân vật | `.taothe` · `.me` · `.info @user` · `.chon` · `.gianhap` |
| Tu luyện | `.tu` / batch · offline AP · `.dp` · `.dokiep` |
| Kho / shop | `.shop` · `.mua` · `.tui` · `.mac` · `.dung` · `.hoc` · `.tim`/`.tra` |
| PvE | `.thap` (combat) · `.tongthap` (cần tông) · `.bicanh` (baseline — xem mục loại trừ) |
| Tông môn | `.tongmon` vao/moi/kick/chuc/gop/bxh/info/tao/roi · quyền rank · quà tuần item tự động |
| PvP | `.pvp @user <cược>` · `.pvp chap` · `.pvp huy` (escrow SQLite) |
| Sự kiện | `.sukien` · `.sukien nhan` (1 lần/ngày) |
| Nhiệm vụ | `.nhiemvu`/`.nhannv` (ngày) · `.nvda`/`.nvda nhan` (dài hạn) |
| Kinh tế | `.chuyen` · `.ban` · `.daugia` · `.bxh` (fmt 1k) |
| Đạo lữ | `.ketduyen` · `.daolu` · `.songtu` |
| Voice | join / play / tts / … |

### 3.3 Merge từ V3.9.9 (đã chọn)
- Công thức combat (hit/dmg/crit/mastery/shield/DoT) → `combat_rules` + service  
- Rank quyền tông → `sect_rules`  
- Hướng PvP escrow / world event / mission / sect tower — **viết lại** trên schema & StatsService V1, không copy engine/UI embed  

---

## 4. Còn thiếu / hạn chế

| # | Hạng mục | Mức | Ghi chú |
|---|----------|-----|---------|
| T1 | Ma trận LS mid–late | TB | Sink/source chưa đủ bảng |
| T2 | Combat skill/status đầy đủ | TB | PvE 1v1 swing; chưa skill tree/boss phase |
| T3 | Prison / moderation Discord | TB | Có trong V3 — **chưa** port |
| T4 | NPC dialogue | Thấp | Chưa |
| T5 | Anti-dupe stress tests | TB | Atomic cơ bản; thiếu tải |
| T6 | Gỡ / giữ `.bicanh` | QĐ product | Brief từng yêu cầu zero bí cảnh — chưa cleanup |
| T7 | Closed beta vận hành | TB | Playtest thật |
| T8 | Railway Root Directory | Ops | Monorepo phải trỏ đúng folder có Dockerfile |

---

## 5. Lộ trình tiếp

| Phase | Nội dung | Trạng thái |
|-------|----------|------------|
| PR1–PR8 | Combat → tháp → lookup → sect rank → event → PvP → mission → tông tháp | **Xong** |
| K | Cân LS + anti-dupe tests | Chưa |
| L | Prison/moderation (nếu cần) | Chưa |
| M | Quyết định `.bicanh` (giữ / gỡ) | Chưa |
| N | Closed beta | Chưa |

---

## 6. Deploy (nhắc)

- Start: `python -m ktt112026`  
- Volume: `/data` · env `KTT_DATABASE_PATH`  
- Root Directory Railway = thư mục có `Dockerfile` + `src/ktt112026/`  
- Commit đủ `game/content/data/*.json` (có `sects.json`)

---

## 7. Kiểm thử

Unit `tests/unit/game/`: **54+ passed** tại mốc v1.6.8 (máy build PR7+8).  
Không thay thế playtest Discord/Railway.

---

*Ghi chú cập nhật 2026-11-17 theo yêu cầu “Note vào file dự án” sau chuỗi merge PR1–PR8.*
