# Feature Spec: Telegram Channel Manager

- **ID**: 002-telegram-channel-manager
- **Phụ thuộc**: 001-bingx-arb-alert
- **Trạng thái**: Implemented (v1)
- **Ngày**: 2026-11-06

## 1. Bối cảnh
Spec 001 chỉ gửi alert tới một `TELEGRAM_CHAT_ID` cố định. Người dùng muốn bot **quản lý một
channel Telegram**: tự đăng bài, giữ một bảng tin cập nhật liên tục, và admin điều khiển bot ngay
trong Telegram mà không phải sửa `.env` / restart.

## 2. Vai trò
- **Admin**: user Telegram được phép điều khiển bot. Lấy từ `TELEGRAM_ADMIN_IDS`; nếu trống thì
  **người đầu tiên gửi `/start` trong chat riêng** được nhận làm owner (lưu vào state).
- **Channel**: nơi bot đăng alert + dashboard. Bot phải là admin của channel.

## 3. Yêu cầu chức năng
| ID | Yêu cầu |
|----|---------|
| FR-1 | **Tự nhận channel**: khi admin thêm bot làm *administrator* của channel/group, bot tự lưu chat id đó làm channel đích, báo cho admin và đăng lời chào trong channel. Khi bị gỡ khỏi channel → xoá channel đích, báo admin. |
| FR-2 | Có thể đặt channel thủ công: `/setchannel @ten_channel` hoặc `/setchannel -100xxxx`. Thứ tự ưu tiên chat đích: channel đã lưu > `TELEGRAM_CHAT_ID`. |
| FR-3 | **Dashboard ghim**: bot đăng 1 tin "Bảng tin" trong channel (top funding + top basis), ghim lại, và **sửa** tin đó mỗi `DASHBOARD_INTERVAL_MINUTES` (mặc định 5). Nếu tin bị xoá → đăng tin mới và ghim lại. |
| FR-3b | Khi dashboard bị tắt (`DASHBOARD_ENABLED=false` lúc khởi động, hoặc `/dashboard off`) → bot **gỡ ghim và xoá** tin dashboard cũ trong channel. *(bổ sung 2026-11-06)* |
| FR-4 | Alert theo spec 001 vẫn đăng vào channel như tin riêng (có thông báo). |
| FR-5 | **Lệnh admin** (chỉ trong chat riêng với bot, user không phải admin bị từ chối): |
| | `/start`, `/help` — hướng dẫn |
| | `/status` — channel, trạng thái, ngưỡng, lần quét cuối |
| | `/pause`, `/resume` — tạm dừng / tiếp tục đăng alert (vẫn quét, dashboard vẫn cập nhật) |
| | `/set funding <pct>` · `/set basis <pct>` · `/set volume <usdt>` · `/set cooldown <phút>` — đổi ngưỡng lúc đang chạy (pct nhập theo %, vd `0.05` = 0.05%) |
| | `/reset` — bỏ mọi ngưỡng đã đổi, quay về `.env` |
| | `/top` — xem top cơ hội hiện tại (trả lời riêng) |
| | `/post` — đăng ngay top cơ hội lên channel (bỏ qua chống spam) |
| | `/scan` — quét ngay |
| | `/dashboard on\|off` — bật/tắt dashboard |
| | `/setchannel <id\|@username>` — đặt channel thủ công |
| FR-6 | Trạng thái chạy (channel, admin, pause, ngưỡng đã đổi, id tin dashboard) **lưu ra file** `STATE_FILE` (mặc định `data/state.json`) → restart vẫn giữ. |
| FR-7 | Bot đăng ký menu lệnh với Telegram (`setMyCommands`) khi khởi động. |

## 4. Phi chức năng
- NFR-1: Nhận lệnh bằng long-polling `getUpdates` (không cần domain/webhook, chạy được trên máy cá nhân).
- NFR-2: Lỗi Telegram không làm dừng vòng quét hay vòng polling (Constitution VI).
- NFR-3: Lệnh `/set` phải validate; giá trị sai → báo lỗi, không đổi state.

## 5. Ngoài phạm vi
- Webhook mode, nhiều channel cùng lúc, phân quyền nhiều cấp, lệnh trong chính channel.

## 6. Tiêu chí chấp nhận
- AC-1: Thêm bot làm admin channel → `GET /health` hiển thị `channel_id` của channel đó, channel nhận lời chào.
- AC-2: `/set funding 0.03` → `/status` hiện funding min 0.03%; restart vẫn giữ.
- AC-3: `/set funding abc` → báo lỗi, ngưỡng không đổi.
- AC-4: `/pause` → không có alert mới trong channel, dashboard vẫn cập nhật.
- AC-5: User lạ (không phải admin) gửi `/pause` → bị từ chối.
- AC-6: Xoá tin dashboard trong channel → chu kỳ sau bot đăng và ghim lại tin mới.
