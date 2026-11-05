# Implementation Plan: 001-bingx-arb-alert

## Tech stack
- Python 3.11+ · FastAPI · Uvicorn · httpx (async) · pydantic-settings · pytest
- Scheduler: `asyncio` background task khởi chạy trong `lifespan` của FastAPI (không cần Celery/APScheduler).

## Nguồn dữ liệu BingX (public, không ký)
| Mục đích | Endpoint | Trường dùng |
|---------|----------|-------------|
| Giá + volume Spot | `GET /openApi/spot/v1/ticker/24hr?timestamp=` | `symbol`, `lastPrice`, `quoteVolume` |
| Giá + volume Perp | `GET /openApi/swap/v2/quote/ticker` | `symbol`, `lastPrice`, `quoteVolume` |
| Funding Perp | `GET /openApi/swap/v2/quote/premiumIndex` | `symbol`, `markPrice`, `lastFundingRate`, `nextFundingTime` |

Base URL: `https://open-api.bingx.com`. Symbol 2 bên cùng định dạng `BTC-USDT` → join trực tiếp.
→ 3 request / chu kỳ (NFR-1).

## Kiến trúc
```
app/
├── main.py              # FastAPI app + lifespan (start/stop scanner loop)
├── config.py            # Settings (pydantic-settings, đọc .env)
├── models.py            # MarketSnapshot, Opportunity, OpportunityType
├── api/routes.py        # /health /opportunities /scan /test-alert /config
├── clients/
│   ├── bingx.py         # BingXClient: fetch_snapshots() -> list[MarketSnapshot]
│   └── telegram.py      # TelegramNotifier: send(text)
├── core/                # LOGIC THUẦN (Constitution III)
│   ├── detector.py      # detect_funding(), detect_basis(), filter_liquidity()
│   ├── dedup.py         # AlertDeduplicator (cooldown + escalation 50%)
│   └── formatter.py     # format_message(list[Opportunity]) -> HTML text
└── services/scanner.py  # Scanner: run_once(), run_forever()
tests/
├── test_detector.py     # AC-1, AC-2, AC-3
└── test_dedup.py        # AC-4
```

## Luồng một chu kỳ
1. `BingXClient.fetch_snapshots()` gọi song song 3 endpoint → join theo symbol → `MarketSnapshot`
   (spot_price, perp_price, funding_rate, next_funding_time, spot_vol, perp_vol). Perp không có spot vẫn giữ (spot=None).
2. `filter_symbols()` áp whitelist/blacklist + thanh khoản.
3. `detect_funding()` + `detect_basis()` → `list[Opportunity]`, sắp theo độ lớn giảm dần.
4. `AlertDeduplicator.filter_new()` → chỉ giữ cơ hội cần báo.
5. `format_message()` → `TelegramNotifier.send()` (parse_mode=HTML, chia tin nếu > 4096 ký tự).
6. Lưu kết quả vào `Scanner.last_result` để `/opportunities` trả về.

## Quyết định thiết kế
- **Giá perp cho basis** dùng `lastPrice` (sát giá khớp thực tế hơn markPrice). markPrice chỉ để tham khảo.
- **Funding interval** BingX không trả trong premiumIndex → cấu hình `FUNDING_INTERVAL_HOURS` (mặc định 8).
- **Dedup key** = `(type, symbol, chiều)`; giá trị so sánh = `|funding_rate|` hoặc `|basis|`.
- State giữ trong RAM; restart thì cooldown reset (chấp nhận được ở v1).

## Cấu hình (.env)
Xem `.env.example`. Tất cả có default trừ `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
