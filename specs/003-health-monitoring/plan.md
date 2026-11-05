# Plan: 003-health-monitoring

- `app/core/health.py` — hàm thuần `compute_status(now, started_at, last_success, interval_s, last_failed)`.
- `app/services/scanner.py` — thêm `ScanStats` (started_at, scans_total, scans_failed,
  consecutive_failures, last_success_at, last_duration_ms, alerts_total, next_scan_at, last_dashboard_at).
- `app/services/telegram_bot.py` — ghi `last_poll_ok_at` mỗi lần getUpdates thành công.
  `TelegramNotifier.get_updates` trả `None` khi lỗi (phân biệt với "không có update").
- `app/api/routes.py` — `/health` dựng JSON theo spec, 503 khi down; `/health/live`.
- `app/main.py` — lưu `app.state.bot` để `/health` đọc trạng thái polling.
