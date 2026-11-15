# Content data-driven

## Thư mục
```
game/content/data/
  danduoc.json    # 35 đan
  linhthu.json    # 36 linh thú
  congphap.json   # 20 công pháp
  vukhi.json      # 20 vũ khí
  phapbao.json    # 16 pháp bảo
```

## Loader
`game/content/loader.py` — đọc JSON, cache.
`game/content/shop.py` — dựng catalog shop từ JSON.

## Sửa số liệu
Chỉ sửa file JSON tương ứng, **không** hardcode trong service.
Sau khi đổi JSON cần restart bot (loader có cache process).

## Schema item (chung)
- `id`, `name`, `path` (`tien`|`ma`|`any`)
- `major_min`, `stage_min`, `price`
- `desc` (hiển thị shop)
- `bonuses` / `penalties` (dict chỉ số)
- Đan thêm: `effect`, `limits`, `side_effects`, `group`
