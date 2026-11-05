# Tasks: 005-smallcap-executable-basis

- [x] T001 `tests/test_executable_basis.py` — AC-1..AC-4
- [x] T002 `app/models.py` — bid/ask, exec_basis, exec_depth_usdt
- [x] T003 `app/clients/bingx.py` — parse bid/ask
- [x] T004 `app/core/detector.py` — dùng exec_basis
- [x] T005 `app/config.py`, `.env`, `.env.example` — BASIS_MIN_PCT=0.02, MIN_QUOTE_VOLUME_USDT=10000, BASIS_MIN_DEVIATION_PCT=0.01
- [x] T006 `app/core/formatter.py` — hiển thị basis khớp được, volume, depth
- [x] T007 Restart server, kiểm tra thực tế
- [x] T008 FR-6: chỉ chiều Mua Spot + Short Perp (`BASIS_ALLOW_REVERSE=false`)
