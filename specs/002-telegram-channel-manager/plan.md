# Implementation Plan: 002-telegram-channel-manager

## Thành phần mới / thay đổi
```
app/
├── state.py                  # MỚI: BotState (pydantic) + StateStore (đọc/ghi JSON)
├── core/
│   ├── commands.py           # MỚI: parse_command(), parse_set() — thuần, có test
│   └── formatter.py          # THÊM: format_dashboard(), format_status()
├── clients/telegram.py       # MỞ RỘNG: call(), send(chat_id) -> message_id, edit(), pin(),
│                             #          get_updates(), get_chat(), set_commands()
├── services/
│   ├── scanner.py            # SỬA: đọc ngưỡng hiệu lực từ state, tôn trọng pause,
│   │                         #      cập nhật dashboard theo chu kỳ
│   └── telegram_bot.py       # MỚI: vòng long-polling, xử lý my_chat_member + lệnh admin
└── main.py                   # SỬA: tạo StateStore, chạy song song Scanner + TelegramBot
```

## Telegram Bot API dùng
| Method | Dùng cho |
|--------|----------|
| `getUpdates` (timeout=30, allowed_updates=[message, my_chat_member]) | nhận lệnh + sự kiện bot được thêm/gỡ khỏi channel |
| `sendMessage` | alert, trả lời lệnh, đăng dashboard |
| `editMessageText` | cập nhật dashboard |
| `pinChatMessage` (disable_notification) | ghim dashboard |
| `getChat` | đổi `@username` → chat id số cho `/setchannel` |
| `setMyCommands` | menu lệnh |

## Ngưỡng hiệu lực
`effective(key) = state.overrides.get(key, settings.key)` cho các key:
`funding_min_rate`, `basis_min_pct`, `min_quote_volume_usdt`, `alert_cooldown_minutes`.
Đổi cooldown → cập nhật `dedup.cooldown` ngay.

## Quyết định
- **Chống tin "not modified"**: dashboard luôn có dòng thời gian cập nhật (đến giây).
- **Edit lỗi** (tin bị xoá / quá cũ) → gửi tin mới, ghim, lưu `dashboard_message_id`.
- **Khi đang pause**: không gọi `dedup.filter_new` → khi resume, cơ hội đang mở sẽ được báo ngay.
- **Claim owner**: chỉ khi chưa có admin nào (env + state). Ghi log WARNING để người dùng biết.
- Đổi channel → reset `dashboard_message_id`.
- Ghi state JSON theo kiểu atomic (ghi file tạm rồi `replace`).
