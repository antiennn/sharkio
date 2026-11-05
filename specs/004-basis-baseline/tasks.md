# Tasks: 004-basis-baseline

- [x] T001 `tests/test_baseline.py` — AC-1, AC-2, AC-4 + scanner AC-3
- [x] T002 `app/core/baseline.py` — basis_series, compute_baseline, evaluate (FR-2)
- [x] T003 `app/config.py`, `.env.example` — BASIS_BASELINE_ENABLED, BASIS_MIN_DEVIATION_PCT, BASIS_MIN_ZSCORE, BASELINE_INTERVAL, BASELINE_HOURS, BASELINE_CACHE_MINUTES
- [x] T004 `app/clients/bingx.py` — kline spot/perp, funding history
- [x] T005 `app/services/history.py` — cache + semaphore (FR-7), fail → None (FR-4)
- [x] T006 `app/models.py`, `app/services/scanner.py` — enrich, lọc, basis_structural (FR-1, FR-3, FR-6, FR-8)
- [x] T007 `app/core/formatter.py` — hiển thị ngữ cảnh 24h (FR-5, FR-6)
- [x] T008 Restart server, kiểm tra với dữ liệu thật
