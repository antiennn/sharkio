# Feature Spec: Quét coin vốn hoá nhỏ + Basis khớp được

- **ID**: 005-smallcap-executable-basis
- **Phụ thuộc**: 001, 004
- **Trạng thái**: Implemented (v1)
- **Ngày**: 2026-11-06

## 1. Bối cảnh
Người dùng nhận định chênh lệch spot/perp lớn chủ yếu xuất hiện ở **coin vốn hoá nhỏ**, và muốn
ngưỡng basis **≥ 2%** (0.5% quá nhỏ).

Dữ liệu thực BingX (2026-11-06, 386 coin có cả spot & perp):
| Lọc volume 24h tối thiểu | Số coin | Số coin |basis| ≥ 2% |
|---|---|---|
| 500,000 (cũ) | 28 | 0 |
| 100,000 | 91 | 1 |
| 50,000 | 200 | 4 |
| 10,000 | 382 | 10 |

→ Xác nhận: muốn bắt được chênh lệch ≥ 2% phải hạ lọc thanh khoản.

**Rủi ro phát hiện được**: coin nhỏ có `lastPrice` cũ / spread rộng → basis giả.
Ví dụ AGI-USDT basis theo last price +22%, nhưng spot volume 24h chỉ $3, spread spot 48% —
không thể vào lệnh. ERA, RAVE tương tự.

## 2. Thay đổi
| ID | Yêu cầu |
|----|---------|
| FR-1 | Đổi mặc định: `BASIS_MIN_PCT = 0.02` (2%), `MIN_QUOTE_VOLUME_USDT = 10,000`. |
| FR-2 | **Basis khớp được** (executable) dùng bid/ask tốt nhất thay vì last price: |
| | Perp cao hơn spot: `(perp_bid − spot_ask) / spot_ask` — mua spot ở ask, short perp ở bid. Báo khi > 0 và ≥ ngưỡng. |
| | Perp thấp hơn spot: `(perp_ask − spot_bid) / spot_bid` — bán spot ở bid, long perp ở ask. Báo khi < 0 và |·| ≥ ngưỡng. |
| | Không chiều nào khớp được (sổ lệnh chồng nhau) → basis khớp được = 0 → không báo. |
| | Thiếu bid/ask → dùng last price như spec 001. |
| FR-3 | Tin alert hiển thị: basis khớp được, basis theo last price, volume 24h spot/perp, và **khối lượng USDT có sẵn ở giá tốt nhất** (min của 2 phía) để biết vào được bao nhiêu tiền. |
| FR-5 | Hiển thị **lãi ước tính sau phí** = `|basis khớp được| − 2 × (SPOT_TAKER_FEE + PERP_TAKER_FEE)` (mặc định 0.1% + 0.05% → phí 2 chiều 0.3%). Lý do: ở basis 0.5% phí gần như ăn hết lợi nhuận. Chưa tính spread lúc đóng lệnh & phí vay. |
| FR-6 | **Chỉ báo chiều Mua Spot + Short Perp** (basis khớp được > 0). Chiều ngược (perp < spot, cần bán/vay spot) bị bỏ qua mặc định — `BASIS_ALLOW_REVERSE=false`. Lý do: người dùng không short được spot coin nhỏ. *(bổ sung 2026-11-06)* |
| FR-4 | `BASIS_MIN_DEVIATION_PCT` (spec 004) mặc định nâng lên `0.01` (1%) cho tương xứng ngưỡng 2%. |

## 3. Tiêu chí chấp nhận
- AC-1: AGI-like: spot bid/ask 0.00335/0.00496, perp bid/ask 0.003914/0.003919 → **không** báo.
- AC-2: NIULAI-like: spot bid/ask 0.06082/0.06083, perp bid/ask 0.05464/0.05468 → báo, basis ≈ −10.1%.
- AC-3: RAVE-like: spot bid/ask 0.13094/0.13927, perp 0.1323/0.1324, last price lệch −4.6% → **không** báo.
- AC-4: Snapshot thiếu bid/ask → hành vi như cũ (dùng last price).
