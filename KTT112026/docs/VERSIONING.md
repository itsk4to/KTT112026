# Phiên bản (semver gọn)

Định dạng: **`MAJOR.MINOR.PATCH`** (ví dụ `1.0.0` → `1.0.1` → … → `1.0.9` → `1.1.0`).

| Thành phần | Khi tăng |
|------------|----------|
| PATCH (0–9 rồi lên MINOR) | Sửa lỗi, chỉnh nhỏ, config/deploy |
| MINOR | Thêm lệnh/hệ trong game, không phá save lớn |
| MAJOR | Đổi lớn schema/gameplay |

File ghi phiên bản: `VERSION.txt` và `pyproject.toml`.
