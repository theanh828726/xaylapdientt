# TuyếnSố – Quản lý xây lắp điện

Frontend React + Vite + TypeScript + Tailwind; backend FastAPI + PostgreSQL/PostGIS (`backend/`).

## Chạy local
```bash
cp .env.example .env            # rồi đổi POSTGRES_PASSWORD, DATABASE_URL, JWT_SECRET
docker compose up -d --build    # db (PostGIS 16) + minio + api :8000 (tự chạy alembic upgrade head)
docker compose exec api python -m app.seed_demo          # nạp dữ liệu DEMO (thêm --reset để nạp lại)
npm i && npm run dev            # http://localhost:5173 (Vite proxy /api -> :8000)
```
Tài khoản demo: `<vai-tro>@demo.tuyenso.local`, vai trò: giamdoc, chihuytruong, kythuat, ketoan, kehoach, phogiamdoc, chutich; tổ đội: tam, khoa, son. Dữ liệu demo neo ngày 14/10/2026 (trang QA/QC: chọn khoảng 07/10–14/10 để thấy đúng số liệu thiết kế). Mật khẩu = `SEED_DEMO_PASSWORD` trong `.env`. Seed từ chối chạy khi `ENV=production`.
API docs (dev): http://localhost:8000/api/docs

## Kiểm thử
```bash
docker compose run --rm --no-deps api pytest -q    # tạo DB riêng tuyenso_test, chạy migration thật + seed demo
npm run build && npm run lint
```

## Cấu trúc
- `src/api/` – lớp truy cập dữ liệu duy nhất, gọi backend qua `client.ts` (`http()`: token, refresh, header `X-Du-An`).
- `src/types.ts` – entity: ViTriCot, MaCauKien, DeXuatVatTu, DotGiaoHang, BaoCaoHienTruong, CongTac (kiêm nghiệm thu), PhieuDieuChinh.
- `backend/app/` – `models.py` (schema), `rbac.py` (vai trò + quyền mặc định), `routers/`, `services/` (chuỗi duyệt, công thức hố móng), `seed_demo.py`; migration ở `backend/alembic/`.
- Phân quyền theo bảng `role_permission` (sửa qua `PUT /api/phan-quyen/{vai_tro}`); nhiều dự án qua `thanh_vien_du_an`.
- Bản đồ: MapLibre (chunk riêng), nền OSM (`VITE_MAP_TILES_URL` đổi nguồn tile); GeoJSON từ `GET /api/ban-do/geojson`. Nhập KMZ/KML: nút trên trang Bản đồ hoặc `POST /api/ban-do/import-kmz` (giới hạn 20 MB, chặn DTD/entity).
- Rule engine: `backend/app/services/rules.py` (rule chưa có dữ liệu nguồn nằm trong `KHONG_CO_DU_LIEU`, kèm lý do). Quản trị người dùng/phân quyền: trang `/quan-tri` (cần quyền `nguoi_dung.quan_ly` / `phan_quyen.quan_ly`).
- Lưu trữ: ảnh/biên bản/mẫu biểu ở bucket S3 (`MINIO_*` trong `.env`). **Lưu ý:** MinIO không còn phát hành image community; `docker-compose.yml` dùng `bitnamilegacy/minio` (không được vá lỗi) chỉ cho dev. Production dùng S3 còn bảo trì (SeaweedFS, Garage hoặc S3 nhà cung cấp) – backend chỉ dùng API S3.
- Biểu mẫu .docx: mẫu mặc định ở `backend/app/templates/` (tạo lại: `docker compose run --rm -v ./backend:/app api python scripts/tao_mau_bieu.py`). Chỉnh mẫu: Quản trị → Biểu mẫu → tải về, sửa bằng Word (giữ thẻ `{{ }}`/`{% %}`), tải lên; có thể quay về mặc định. Mẫu mặc định cần đối chiếu biểu mẫu pháp lý hiện hành (TT 10/2021/TT-BXD) trước khi phát hành chính thức.
- Màn hình (theo PDF thiết kế): Bản đồ tuyến, Hồ sơ QA/QC, Đề xuất vật tư (+ chi tiết `/de-xuat/:ma`), Đối soát 3 nguồn, Phê duyệt (mobile), Báo cáo hiện trường (mobile, `/bao-cao`); đơn giản chờ thiết kế: Kho & giao nhận, Nhật ký thi công, Thu hồi tuyến cũ, Tổng quan, Tôi, Quản trị.

## Production
Dùng `requirements.txt` thay `requirements-dev.txt` trong `backend/Dockerfile`, đặt `ENV=production` (tắt /api/docs, từ chối seed), `COOKIE_SECURE=true`, chạy sau Nginx/HTTPS phục vụ cả frontend build và proxy `/api`.
