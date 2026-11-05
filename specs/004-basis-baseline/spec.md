# Feature Spec: So sánh với lịch sử 24h (Basis Baseline)

- **ID**: 004-basis-baseline
- **Phụ thuộc**: 001
- **Trạng thái**: Implemented (v1)
- **Ngày**: 2026-11-06

## 1. Vấn đề
Spec 001 báo BASIS chỉ dựa trên `|basis| ≥ BASIS_MIN_PCT`. Nhưng nhiều coin có **basis lệch
thường trực** (do funding, chi phí vay, thanh khoản) — ví dụ một coin luôn có perp thấp hơn spot 0.5%
suốt 24h. Báo những coin đó là **nhiễu**: chênh lệch đó không phải cơ hội, nó "đó giờ vẫn vậy".

Dữ liệu thực (2026-11-06): basis 24h của BTC dao động −0.06%…+0.01%, của WLD −0.50%…+0.21% —
mỗi coin có mức "bình thường" khác nhau.

## 2. Định nghĩa
- **Chuỗi basis 24h**: với mỗi nến `BASELINE_INTERVAL` (mặc định 15m) trong `BASELINE_HOURS` (24h)
  gần nhất, `basis_t = (perp_close_t − spot_close_t) / spot_close_t`, ghép spot & perp theo thời gian mở nến.
  Bỏ nến cuối cùng (đang chạy) khỏi baseline.
- **Baseline** = trung vị (median) chuỗi basis.
- **Độ biến động** σ = 1.4826 × MAD (median absolute deviation) — robust, không bị chính cú spike làm méo.
- **Độ lệch** `dev = basis_hiện_tại − baseline`, **z** = `dev / σ`.

## 3. Yêu cầu chức năng
| ID | Yêu cầu |
|----|---------|
| FR-1 | Coin vượt `BASIS_MIN_PCT` (spec 001) là *ứng viên*. Chỉ ứng viên mới tải lịch sử (tiết kiệm request). |
| FR-2 | Ứng viên chỉ được **báo** khi: `|dev| ≥ BASIS_MIN_DEVIATION_PCT` (mặc định 0.3%) **và** `|z| ≥ BASIS_MIN_ZSCORE` (mặc định 3). σ = 0 → chỉ xét điều kiện dev. |
| FR-3 | Ứng viên không đạt FR-2 → xếp vào **basis_structural** (lệch thường trực), không báo, vẫn xem được ở `/opportunities`. |
| FR-4 | Không lấy được lịch sử (lỗi mạng, coin mới < 12 nến) → **vẫn báo** nhưng ghi rõ "⚠️ chưa có dữ liệu 24h" (fail-safe: thà báo thừa còn hơn bỏ sót). |
| FR-5 | Tin alert BASIS hiển thị: basis **đúng 24h trước**, trung vị 24h, khoảng min–max 24h, độ lệch so với trung vị và z-score. (Lọc dùng trung vị chứ không dùng điểm 24h trước, vì 1 điểm đơn lẻ có thể trùng spike.) |
| FR-6 | Tin alert FUNDING hiển thị funding **trung bình các kỳ trong 24h** (lấy từ lịch sử funding) để biết funding cao ổn định hay chỉ vừa vọt lên. Không lọc FUNDING theo lịch sử (funding cao ổn định là *tốt* cho chiến lược). |
| FR-7 | Cache baseline mỗi symbol `BASELINE_CACHE_MINUTES` (mặc định 15) — tránh gọi lại mỗi chu kỳ. Tối đa 2 symbol tải lịch sử đồng thời. BingX trả `code=100410` ("thử lại sau") hoặc HTTP 429 → tự thử lại tối đa 3 lần (0.5s, 1s, 2s). |
| FR-8 | Tắt toàn bộ tính năng bằng `BASIS_BASELINE_ENABLED=false` → hành vi như spec 001. |

## 4. Ngoài phạm vi
- Lưu lịch sử basis vào DB, vẽ biểu đồ.
- Baseline cho funding dùng để lọc.

## 5. Tiêu chí chấp nhận
- AC-1: Chuỗi basis luôn ≈ −0.5%, hiện tại −0.55% → **không** báo (structural).
- AC-2: Chuỗi basis ≈ −0.1% (σ nhỏ), hiện tại −0.56% → **báo**, hiển thị dev ≈ −0.46%.
- AC-3: Lấy lịch sử lỗi → vẫn báo, có cảnh báo "chưa có dữ liệu 24h".
- AC-4: Ghép nến spot/perp lệch thời gian → chỉ dùng các mốc có ở cả 2 phía.
