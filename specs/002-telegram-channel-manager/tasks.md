# Tasks: 002-telegram-channel-manager

## Phase 1 — Nền tảng
- [x] T001 `app/config.py` — thêm `TELEGRAM_ADMIN_IDS`, `DASHBOARD_ENABLED`, `DASHBOARD_INTERVAL_MINUTES`, `STATE_FILE`, `TELEGRAM_POLLING`
- [x] T002 `app/state.py` — BotState + StateStore (FR-6)

## Phase 2 — Core (test trước)
- [x] T003 [P] `tests/test_commands.py` — parse lệnh, `/set` hợp lệ/không hợp lệ (AC-2, AC-3), state roundtrip
- [x] T004 `app/core/commands.py` (FR-5, NFR-3)
- [x] T005 `app/core/formatter.py` — format_dashboard, format_status (FR-3)

## Phase 3 — Telegram
- [x] T006 `app/clients/telegram.py` — các method Bot API ở plan.md
- [x] T007 `app/services/telegram_bot.py` — polling, my_chat_member (FR-1), lệnh admin (FR-5, AC-5), setMyCommands (FR-7)

## Phase 4 — Tích hợp
- [x] T008 `app/services/scanner.py` — ngưỡng hiệu lực, pause (AC-4), dashboard (FR-3, AC-6)
- [x] T009 `app/main.py` + `app/api/routes.py` — chạy bot, `/health` hiện channel/pause
- [x] T010 `.env.example`, README — hướng dẫn thêm bot vào channel
- [x] T010b `tests/test_telegram_bot.py` — AC-1, AC-2, AC-4, AC-5, AC-6 với Telegram giả

- [x] T013 FR-3b: tắt dashboard → unpin + xoá tin cũ (khởi động & `/dashboard off`)

## Phase 5 — Kiểm thử thực tế (cần người dùng)
- [ ] T011 Thêm bot làm admin channel → kiểm AC-1
- [ ] T012 Thử `/set`, `/pause`, xoá dashboard → kiểm AC-2, AC-4, AC-6
