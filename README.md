# 🦈 Sharkio — BingX Arbitrage Alert Bot

Bot FastAPI quét BingX và báo qua Telegram 2 loại cơ hội, đều theo chiều **Mua Spot + Short Perp**:
- **Funding arbitrage**: funding dương cao → thu funding, delta-neutral.
- **Basis spot vs perp**: giá perp (bid) cao hơn giá spot (ask) ≥ 2%, tính bằng giá **khớp được**,
  và **lệch bất thường so với 24h của chính coin đó** (bỏ qua coin "đó giờ vẫn lệch vậy").

Dự án theo **Spec-Driven Development (SDD)**:

```
.specify/memory/constitution.md   # Nguyên tắc chung của repo
specs/001-bingx-arb-alert/          # quét BingX + alert
  ├── spec.md    # WHAT/WHY: yêu cầu, tiêu chí chấp nhận
  ├── plan.md    # HOW: kiến trúc, endpoint BingX, quyết định
  └── tasks.md   # Danh sách task, đánh dấu tiến độ
specs/002-telegram-channel-manager/ # bot quản lý channel, lệnh admin, dashboard ghim
specs/003-health-monitoring/        # /health chi tiết, 503 khi down
specs/004-basis-baseline/           # so basis với trung vị 24h của chính coin
specs/005-smallcap-executable-basis/# coin nhỏ, basis theo bid/ask, lãi sau phí, chỉ chiều Mua Spot
```
Feature mới → tạo `specs/006-.../` (spec → plan → tasks) rồi mới code.

## 1. Tạo bot & kết nối channel (spec 002)
1. Chat với **@BotFather** → `/newbot` → lấy **token**, điền vào `.env`.
2. Chạy app (mục 2), rồi nhắn **`/start`** cho bot trong chat riêng → bạn thành **owner**
   (hoặc điền sẵn user id vào `TELEGRAM_ADMIN_IDS`).
3. Tạo channel → *Manage channel → Administrators → Add admin* → chọn bot, bật quyền
   **Post / Edit / Pin messages**. Bot tự nhận channel, chào trong channel và ghim **Bảng tin**.
   (Hoặc nhắn bot `/setchannel @ten_channel`.)

Điều khiển bot trong chat riêng: `/status`, `/top`, `/post`, `/scan`, `/pause`, `/resume`,
`/set funding 0.05`, `/set basis 0.5`, `/set volume 300000`, `/set cooldown 30`, `/reset`,
`/dashboard on|off`. Thay đổi được lưu ở `data/state.json`, restart vẫn giữ.

Không dùng channel? Đặt `TELEGRAM_CHAT_ID` là chat đích cố định.

## 2. Cài đặt & chạy
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env      # điền TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
.\.venv\Scripts\uvicorn app.main:app --port 8000
```
Mở http://localhost:8000/docs để xem Swagger.

## 3. API
| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/health` | Trạng thái chi tiết (ok/degraded/down, 503 khi down) |
| GET | `/health/live` | Liveness tối giản |
| GET | `/opportunities` | Kết quả quét gần nhất |
| POST | `/scan` | Quét ngay |
| POST | `/test-alert` | Gửi tin Telegram thử |
| GET | `/config` | Cấu hình đang dùng (ẩn token) |

## 4. Cấu hình chính (`.env`)
| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `SCAN_INTERVAL_SECONDS` | 60 | Chu kỳ quét |
| `MIN_QUOTE_VOLUME_USDT` | 10000 | Volume 24h tối thiểu (cả spot & perp); 0 = quét tất cả |
| `FUNDING_MIN_RATE` | 0.0005 | Funding tối thiểu/kỳ (0.05%) |
| `FUNDING_INTERVAL_HOURS` | 8 | Để tính APR |
| `BASIS_MIN_PCT` | 0.02 | Basis khớp được tối thiểu (2%) |
| `BASIS_ALLOW_REVERSE` | false | true = báo cả chiều perp < spot |
| `SPOT_TAKER_FEE` / `PERP_TAKER_FEE` | 0.001 / 0.0005 | Để tính lãi sau phí |
| `BASIS_MIN_DEVIATION_PCT` | 0.01 | Phải lệch khỏi trung vị 24h ≥ 1% |
| `BASIS_MIN_ZSCORE` | 3 | …và ≥ 3 lần độ dao động thường ngày |
| `DASHBOARD_ENABLED` | true | Bảng tin ghim trong channel |
| `ALERT_COOLDOWN_MINUTES` | 30 | Không báo lại cùng coin trong khoảng này… |
| `ALERT_ESCALATION_RATIO` | 1.5 | …trừ khi giá trị tăng ≥ 1.5x |

## 5. Test
```powershell
.\.venv\Scripts\python -m pytest -q
```

## ⚠️ Lưu ý
Bot chỉ cảnh báo, **không đặt lệnh**. "Lãi sau phí" chỉ trừ phí taker 2 chiều, chưa tính spread lúc
đóng lệnh và slippage; coin nhỏ thường chỉ có vài chục USDT ở giá tốt nhất. Funding có thể đổi chiều.
