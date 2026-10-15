# Triển khai TuyếnSố lên VPS (HTTPS, sao lưu)

## 1. Chuẩn bị
- VPS Linux có Docker + Docker Compose v2.24 trở lên, tên miền trỏ về IP máy chủ.
- `cp .env.example .env`, rồi đặt: mật khẩu DB và MinIO mạnh, `JWT_SECRET` ≥ 32 ký tự ngẫu nhiên, `ENV=production`, `COOKIE_SECURE=true`. **Không** đặt `SEED_DEMO_PASSWORD` và không chạy seed demo trên máy thật (seed tự từ chối khi `ENV=production`).
- Build frontend: `npm ci && npm run build` (ra thư mục `dist/`).

## 2. Chứng chỉ TLS
Sửa `tuyenso.example.vn` trong `deploy/nginx.conf` thành tên miền thật. Lấy chứng chỉ Let's Encrypt (ví dụ):
```bash
sudo certbot certonly --standalone -d tuyenso.example.vn      # chạy trước khi bật nginx; cổng 80 phải trống
sudo cp /etc/letsencrypt/live/tuyenso.example.vn/{fullchain,privkey}.pem deploy/certs/
```
Gia hạn: lặp lại hai lệnh trên mỗi ~60 ngày (hoặc dùng hook `--deploy-hook` của certbot để chép lại và chạy `docker compose restart nginx`). Thư mục `deploy/certs/` đã được git bỏ qua, không commit khoá riêng.

## 3. Chạy
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Bản này: chỉ nginx mở cổng 80/443; api và MinIO console không mở ra ngoài; HSTS, CSP, giới hạn tốc độ (đăng nhập 10 lần/phút/IP, API 20 yêu cầu/giây/IP); cookie phiên `Secure`.
**Chưa chạy thử đầu cuối với tên miền thật.** Cấu hình nginx đã kiểm cú pháp (`nginx -t`) nhưng cần thử thật: đăng nhập, tải ảnh, bản đồ (nếu đổi nguồn tile, thêm tên miền tile vào `img-src` và `connect-src` của CSP).

## 4. Sao lưu và khôi phục
```bash
./scripts/sao_luu.sh                       # tạo backups/<ngày-giờ>/ gồm db.dump, minio.tar, SHA256SUMS; xoá bản quá 14 ngày
./scripts/khoi_phuc.sh backups/<thư mục>   # GHI ĐÈ dữ liệu hiện tại (hỏi xác nhận)
```
Cron mỗi ngày 02:00: `0 2 * * * cd /opt/tuyenso && ./scripts/sao_luu.sh >> backups/sao_luu.log 2>&1`.
- Đã kiểm thử: sao lưu rồi khôi phục vào một DB tạm, số dòng các bảng khớp với DB gốc.
- Bản sao nằm cùng máy chủ chưa đủ an toàn: chép `backups/` sang nơi khác (máy khác, ổ khác, kho đám mây). Nên thử khôi phục định kỳ (mỗi quý một lần).
- Kiểm thử khôi phục không đụng DB thật: `DB_TARGET=tuyenso_khoi_phuc_thu ./scripts/khoi_phuc.sh <thư mục> --chi-db`.

## 5. Còn lại trước khi coi là production
- **MinIO:** `docker-compose.yml` vẫn dùng image `bitnamilegacy/minio` (không còn được vá). Backend chỉ dùng API S3 nên đổi sang SeaweedFS, Garage hoặc S3 của nhà cung cấp mà không sửa mã; cần cập nhật các biến `MINIO_*` và chạy lại `kho_tar.py nhap` để nạp ảnh cũ.
- Tài khoản MinIO riêng cho ứng dụng thay vì tài khoản root.
- Giám sát (uptime, dung lượng ổ đĩa) và cảnh báo khi sao lưu thất bại.
