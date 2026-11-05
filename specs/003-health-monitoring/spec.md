# Feature Spec: Health Monitoring

- **ID**: 003-health-monitoring
- **Phụ thuộc**: 001, 002
- **Trạng thái**: Implemented (v1)
- **Ngày**: 2026-11-06

## 1. Bối cảnh
Người dùng cần một endpoint để nhanh chóng biết bot còn sống không, bao lâu quét 1 lần, lần cuối
quét khi nào, có lỗi không — và gắn được vào công cụ uptime monitor (UptimeRobot, Better Stack…).

## 2. Yêu cầu chức năng
| ID | Yêu cầu |
|----|---------|
| FR-1 | `GET /health` trả JSON gồm 4 nhóm: **tổng quát** (status, uptime, started_at, now), **scan** (interval, last_scan, last_success, next_scan_at, thời gian quét, tổng số lần quét/lỗi, lỗi liên tiếp, lỗi cuối, số cặp, số cơ hội, tổng alert đã gửi), **dashboard** (bật/tắt, chu kỳ, lần cập nhật cuối, message id), **telegram** (enabled, polling, lần poll thành công cuối, channel, paused, số admin). |
| FR-2 | `status` tính theo quy tắc (I = scan interval): |
| | `starting` — chưa quét thành công lần nào và app chạy < 3·I |
| | `down` — lần quét thành công cuối cách đây > 3·I (hoặc chưa từng thành công sau 3·I) |
| | `degraded` — lần quét gần nhất lỗi, hoặc lần thành công cuối cách đây > 2·I |
| | `ok` — còn lại |
| FR-3 | HTTP **503** khi `down`, **200** cho các trạng thái khác (để uptime monitor bắt được). |
| FR-4 | `GET /health/live` — chỉ trả `{"alive": true}` (liveness tối giản, không logic). |

## 3. Tiêu chí chấp nhận
- AC-1: Ngay sau khởi động (chưa quét) → `starting`, 200.
- AC-2: Quét thành công gần đây → `ok`.
- AC-3: Lần quét cuối lỗi nhưng lần thành công còn mới → `degraded`.
- AC-4: Không có lần quét thành công trong > 3·I → `down`, 503.
