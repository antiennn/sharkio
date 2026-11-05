# Sharkio Constitution

Nguyên tắc bất biến cho mọi feature trong repo này. Spec/plan/tasks phải tuân thủ.

## I. Spec trước, code sau
Mỗi feature có thư mục `specs/NNN-ten-feature/` gồm `spec.md` (WHAT/WHY), `plan.md` (HOW),
`tasks.md` (các bước). Không viết code cho hành vi chưa có trong spec. Đổi hành vi = sửa spec trước.

## II. Chỉ đọc, không giao dịch
Bot chỉ dùng **public market data** và gửi **cảnh báo**. Không đặt lệnh, không lưu API key sàn.

## III. Logic thuần, I/O tách biệt
Công thức tính (basis, funding APR, lọc) là hàm thuần trong `app/core/`, không gọi mạng → test được
offline. Client sàn / Telegram nằm ở `app/clients/`.

## IV. Cấu hình qua môi trường
Mọi ngưỡng, chu kỳ quét, token đều đọc từ biến môi trường / `.env`. Không hard-code secret.

## V. Test cho logic cốt lõi
Mỗi công thức và quy tắc chống spam phải có unit test (`pytest`).

## VI. Fail an toàn
Lỗi mạng/sàn không được làm chết vòng quét; log lỗi và thử lại ở chu kỳ sau.
