# Feature Spec: BingX Arbitrage Alert Bot

- **ID**: 001-bingx-arb-alert
- **Trạng thái**: Implemented (v1)
- **Ngày**: 2026-11-06

## 1. Bối cảnh / Vấn đề
Trader muốn được báo qua Telegram khi trên sàn **BingX** xuất hiện cơ hội chênh lệch giữa thị
trường **Spot** và **Perpetual (USDT-M)** của cùng một coin, mà không phải ngồi canh màn hình.

## 2. Hai loại cơ hội cần phát hiện

### 2.1 Funding Arbitrage (FUNDING)
Chiến lược: **mua Spot + short Perp** cùng khối lượng → delta-neutral, thu funding khi funding dương.
- Điều kiện: `funding_rate >= FUNDING_MIN_RATE` (mặc định `0.0005` = 0.05%/kỳ).
- Coin phải có **cả cặp Spot và Perp** (`XXX-USDT`) — vì phải mua được spot.
- Thông tin hiển thị: funding rate/kỳ, APR ước tính, basis hiện tại, giờ funding kế tiếp.
- APR ước tính = `funding_rate × (24 / FUNDING_INTERVAL_HOURS) × 365`.

### 2.2 Spot vs Perp Basis (BASIS)
Khi giá perp lệch xa giá spot (thường lúc biến động mạnh).
- `basis = (perp_price − spot_price) / spot_price`
- Điều kiện: `|basis| >= BASIS_MIN_PCT` (mặc định `0.005` = 0.5%).
- Basis dương (perp > spot, contango) → gợi ý: *Long Spot / Short Perp*.
- Basis âm (perp < spot, backwardation) → gợi ý: *Short Spot (vay) / Long Perp* (ghi chú rủi ro).

## 3. Yêu cầu chức năng
| ID | Yêu cầu |
|----|---------|
| FR-1 | Quét định kỳ mỗi `SCAN_INTERVAL_SECONDS` (mặc định 60s) toàn bộ cặp USDT trên BingX. |
| FR-2 | Lọc thanh khoản: bỏ coin có volume 24h (USDT) của spot **hoặc** perp < `MIN_QUOTE_VOLUME_USDT` (mặc định 500,000). |
| FR-3 | Phát hiện FUNDING và BASIS theo mục 2. |
| FR-4 | Gửi Telegram cho mỗi cơ hội mới; gộp nhiều cơ hội cùng chu kỳ vào 1 tin (tối đa `MAX_ALERTS_PER_MESSAGE`). |
| FR-5 | Chống spam: cùng (loại, symbol) chỉ báo lại sau `ALERT_COOLDOWN_MINUTES` (mặc định 30) **trừ khi** giá trị chính tăng thêm ≥ 50% so với lần báo trước. |
| FR-6 | API FastAPI: `GET /health`, `GET /opportunities` (kết quả quét gần nhất), `POST /scan` (quét ngay), `POST /test-alert` (gửi tin thử), `GET /config`. |
| FR-7 | Tùy chọn whitelist/blacklist symbol (`SYMBOL_WHITELIST`, `SYMBOL_BLACKLIST`). |
| FR-8 | Nếu chưa cấu hình Telegram → vẫn quét, chỉ log, không crash. |

## 4. Yêu cầu phi chức năng
- NFR-1: Mỗi chu kỳ quét ≤ 3 request public tới BingX (lấy toàn thị trường, không gọi từng symbol).
- NFR-2: Lỗi mạng không dừng vòng quét (Constitution VI).
- NFR-3: Không cần API key BingX.

## 5. Ngoài phạm vi (v1)
- Tự động đặt lệnh, quản lý vị thế.
- So sánh chênh lệch giữa các sàn khác nhau.
- Lưu lịch sử vào database (chỉ giữ trong RAM).
- Tính phí giao dịch / chi phí vay chính xác.

## 6. Tiêu chí chấp nhận
- AC-1: Với dữ liệu giả `spot=100, perp=101` và `BASIS_MIN_PCT=0.005` → sinh 1 cơ hội BASIS +1.00%.
- AC-2: Với `funding=0.001`, interval 8h → APR = 109.5%.
- AC-3: Coin có funding cao nhưng **không có spot** → không sinh FUNDING.
- AC-4: Cùng cơ hội gọi 2 lần trong cooldown → chỉ gửi 1 lần; nếu giá trị tăng ≥50% → gửi lại.
- AC-5: `POST /test-alert` gửi được tin tới chat đã cấu hình.
