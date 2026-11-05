# Tasks: 001-bingx-arb-alert

Ký hiệu: `[x]` xong · `[ ]` chưa · `[P]` có thể làm song song.

## Phase 1 — Setup
- [x] T001 Tạo cấu trúc thư mục, `requirements.txt`, `.env.example`, `.gitignore`
- [x] T002 `app/config.py` — Settings đọc `.env` (FR-7, FR-8, Constitution IV)

## Phase 2 — Core (logic thuần, test trước)
- [x] T003 [P] `app/models.py` — MarketSnapshot, Opportunity, OpportunityType
- [x] T004 [P] `tests/test_detector.py` — AC-1, AC-2, AC-3
- [x] T005 `app/core/detector.py` — filter_symbols, detect_funding, detect_basis (FR-2, FR-3)
- [x] T006 [P] `tests/test_dedup.py` — AC-4
- [x] T007 `app/core/dedup.py` — AlertDeduplicator (FR-5)
- [x] T008 `app/core/formatter.py` — tin Telegram HTML, gộp/chia tin (FR-4)

## Phase 3 — Clients (I/O)
- [x] T009 [P] `app/clients/bingx.py` — 3 endpoint public, join symbol (NFR-1)
- [x] T010 [P] `app/clients/telegram.py` — sendMessage, bỏ qua nếu chưa cấu hình (FR-8)

## Phase 4 — Service & API
- [x] T011 `app/services/scanner.py` — run_once / run_forever, bắt lỗi (FR-1, NFR-2)
- [x] T012 `app/api/routes.py` — các endpoint FR-6
- [x] T013 `app/main.py` — lifespan khởi động scanner

## Phase 5 — Hoàn thiện
- [x] T014 `README.md` — hướng dẫn tạo bot Telegram, lấy chat_id, chạy
- [ ] T015 Chạy thật với BingX, kiểm tra AC-5 bằng `POST /test-alert` (cần token của người dùng)

## Backlog (feature sau → tạo spec 002, 003…)
- Lưu lịch sử vào SQLite, biểu đồ funding.
- ~~Lệnh Telegram `/status`, `/set_threshold`~~ → đã làm ở spec 002.
- Trừ phí giao dịch / phí vay khi tính lợi nhuận ròng.
- So sánh chênh lệch liên sàn.
