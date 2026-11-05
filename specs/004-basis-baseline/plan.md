# Plan: 004-basis-baseline

## API BingX (đã kiểm tra thực tế 2026-11-06)
| Dữ liệu | Endpoint | Định dạng |
|---------|----------|-----------|
| Nến spot | `GET /openApi/spot/v2/market/kline?symbol&interval&limit` | list `[openTime, o, h, l, c, vol, closeTime, quoteVol]`, mới nhất trước |
| Nến perp | `GET /openApi/swap/v3/quote/klines?symbol&interval&limit` | list `{time, open, high, low, close, volume}`, mới nhất trước |
| Lịch sử funding | `GET /openApi/swap/v2/quote/fundingRate?symbol&limit` | list `{fundingRate, fundingTime}`, mới nhất trước |

`limit = BASELINE_HOURS × 60 / phút_mỗi_nến + 1` (24h/15m → 97).

## Thành phần
- `app/core/baseline.py` (thuần): `basis_series()`, `compute_baseline()`, `evaluate()` → `BasisBaseline`, `BaselineVerdict`.
- `app/clients/bingx.py`: `fetch_spot_closes()`, `fetch_perp_closes()`, `fetch_funding_history()`.
- `app/services/history.py`: `HistoryService` — cache TTL theo symbol, `asyncio.Semaphore(4)`,
  `basis_baseline(symbol)`, `funding_avg_24h(symbol)`; lỗi → `None`.
- `app/models.py`: thêm field ngữ cảnh 24h vào `Opportunity`.
- `app/services/scanner.py`: sau `detect_basis` → enrich + lọc; `ScanResult.basis_structural`.
- `app/core/formatter.py`: hiển thị ngữ cảnh 24h.

## Số request thêm
Chỉ cho ứng viên: 2 request/coin BASIS + 1 request/coin FUNDING, có cache 15 phút
→ thị trường bình thường gần như 0 request thêm.
