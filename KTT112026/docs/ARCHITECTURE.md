# Kiến trúc ngắn

```
Discord message/button
        │
        ▼
 game/discord  or  voice/commands
        │
        ▼
 game/services  (use-case)
        │
   ┌────┴────┐
   ▼         ▼
 rules    content
   │
   ▼
 repo → db
```

Ảnh UI: `services` trả data → `render` tạo PNG → `discord` gửi file + View.
