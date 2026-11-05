# Plan: 005-smallcap-executable-basis

- Ticker spot `/openApi/spot/v1/ticker/24hr` và perp `/openApi/swap/v2/quote/ticker` **đã có sẵn**
  `bidPrice, bidQty, askPrice, askQty` → không tốn thêm request.
- `app/models.py`: `MarketSnapshot` thêm `spot_bid/ask(+qty)`, `perp_bid/ask(+qty)`;
  property `exec_basis` và `exec_depth_usdt`. `Opportunity` thêm `basis_last`, `depth_usdt`,
  `spot_quote_volume`, `perp_quote_volume`.
- `app/core/detector.py`: `detect_basis` dùng `exec_basis` (fallback `basis`).
- `app/clients/bingx.py`: parse bid/ask.
- `app/config.py`, `.env`, `.env.example`: default mới (FR-1, FR-4).
- `app/core/formatter.py`: FR-3.
- Baseline (spec 004) vẫn tính bằng giá đóng nến → so sánh `exec_basis` với trung vị lịch sử.
