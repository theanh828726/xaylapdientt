# TuyếnSố – Phần mềm quản lý xây lắp điện có AI hỗ trợ
Khách hàng: Công ty TNHH Xây lắp điện Tuấn Thành (dự án riêng, hạ tầng VPS). Chủ dự án: Ngô Thế Anh.
Giao tiếp: tiếng Việt (xưng "em"/gọi "anh"), thuật ngữ kỹ thuật giữ tiếng Anh. Output production-ready, không placeholder.

## Hiện trạng
Giao diện bám file thiết kế `TuyếnSố — Thiết kế giao diện.pdf` (6 màn: Bản đồ tuyến, Hồ sơ QA/QC, Báo cáo hiện trường mobile, Phê duyệt mobile, Đề xuất vật tư, Đối soát 3 nguồn) – PDF là nguồn chuẩn, thắng mọi mock cũ. Kho & giao nhận, Nhật ký thi công, Thu hồi tuyến cũ, Tổng quan mobile, Tôi chưa có thiết kế: làm đơn giản, cùng ngôn ngữ hình ảnh; khi có thiết kế thì thay.
React + Vite + TS + Tailwind 3 (`src/pages/`) + backend FastAPI/PostgreSQL-PostGIS trong `backend/` (Docker Compose). Dữ liệu là DEMO (`python -m app.seed_demo --reset`, neo ngày 14/10/2026; 64 cột VT1–64 quanh Hà Trung, Thanh Hóa) – KHÔNG phải dữ liệu thật.
Mọi truy cập dữ liệu CHỈ qua `src/api/` → `client.ts` `http()` (JWT access trong bộ nhớ + refresh cookie HttpOnly, header `X-Du-An`).
Mô hình: công tác theo vị trí (`cong_tac`: đào móng, BT lót, thép đế, BT móng, lắp móng [PL1]; dựng cột, xà sứ, kéo dây [PL2]; trạng thái chưa làm/đang làm/chờ nghiệm thu/đã nghiệm thu; "bước thi công" trên bản đồ suy ra từ đây), lô vật liệu, mẫu bê tông, vật tư theo vị trí (lead-time), phiếu điều chỉnh + nghiệm thu có điều kiện dùng chung chuỗi duyệt 5 bước, đối soát theo hạng mục, thông báo theo người dùng.
Đăng nhập thật; 7 vai trò; quyền cấu hình ở `role_permission`; giá bị bỏ khỏi JSON ở backend khi thiếu quyền. Nhiều dự án. Bản đồ MapLibre + import KMZ/KML. Rule engine R01–R24 (chặn/cảnh báo/nhắc việc; 7 rule R13, R18–R23 chưa có dữ liệu nguồn nên `trienKhai=false`). Ảnh hiện trường ở MinIO/S3. Biên bản/giấy mời/chiết tính .docx sinh bằng docxtpl từ mẫu theo dự án (mẫu mặc định CHƯA đối chiếu biểu mẫu pháp lý – chờ Tuấn Thành). Báo cáo hiện trường mobile-web có hàng đợi offline IndexedDB (`src/lib/offline.ts`, idempotent theo `clientId`).
Vận hành (2026-10-15): đã có git, `scripts/sao_luu.sh` + `khoi_phuc.sh` (đã thử khôi phục), `docker-compose.prod.yml` + `deploy/nginx.conf` (HTTPS, HSTS, CSP, giới hạn tốc độ; mới kiểm cú pháp, chưa chạy với tên miền thật; xem `docs/TRIEN_KHAI.md`), chống dò mật khẩu đếm trong DB (bảng `dang_nhap_that_bai`), `rules.danh_gia` có đệm TTL 5 s xoá khi commit, nhật ký thi công phân trang (limit ≤ 200), màn Đối soát gắn nhãn "Dữ liệu minh họa". Chưa làm: đổi MinIO bản cũ (`bitnamilegacy`) sang S3 còn bảo trì. Chưa có: mobile Expo + SQLite, AI service (PDF/OCR; nút "Chạy lại AI trích xuất" đang tắt), Zalo OA, xuất PDF biên bản (LibreOffice), nhập "bảng kê", form tạo đề xuất vật tư trên giao diện.

## Nguyên tắc nghiệp vụ
- Trục dữ liệu trung tâm: **vị trí cột** (VT45...). Entity: ViTriCot, MaCauKien, DeXuatVatTu, DotGiaoHang, BaoCaoHienTruong, CongTac (kiêm nghiệm thu), PhieuDieuChinh.
- AI đề xuất, người có thẩm quyền duyệt (rule R24). Rule engine R01–R24, mức Chặn/Cảnh báo/Nhắc việc.
- Đối soát 3 nguồn: Hợp đồng – Bản vẽ – Chỉ dẫn kỹ thuật.
- Chuỗi duyệt: Kỹ thuật → CHT → P.KH → PGĐ → Chủ tịch. Giá hợp đồng/giá khoán ẩn theo vai trò (`src/lib/role.tsx`).
- Khối lượng hố móng (`src/lib/foundation.ts`): A1=A+0.4, B1=B+0.4, A2=A1+2Kh, B2=B1+2Kh, S1=A1·B1, S2=A2·B2, V=h/3·(S1+S2+√(S1·S2)). Kiểm chứng: A=2.5,B=3.2,h=2.8,K=0.5 → 62.0 m³ (MT-7a-14-2,8).
- Biểu mẫu biên bản phải cấu hình theo dự án (TT 10/2021/TT-BXD; NĐ 207/2026/NĐ-CP – kiểm tra hiệu lực).

## Lộ trình kỹ thuật (đã chốt)
Backend FastAPI/NestJS + PostgreSQL/PostGIS + MinIO; bản đồ MapLibre GL + KMZ (togeojson); mobile Expo + SQLite offline; sinh biên bản bằng docxtemplater/Carbone; AI service Python (PyMuPDF, PaddleOCR, LLM→JSON); Zalo OA.
Bước (1) backend + auth/vai trò và (2) map thật + import KMZ đã xong (chưa thử với KMZ thật của khách). (3) rule engine và UI quản trị đã xong ở mức dữ liệu hiện có. MinIO + sinh .docx đã xong. Còn lại: (4) mobile Expo (báo cáo hiện trường đã idempotent theo `clientId`).

## Lệnh
`docker compose up -d --build` · `docker compose exec api python -m app.seed_demo` · `npm i` · `npm run dev` · `npm run build` (phải xanh trước khi bàn giao; kiểm tra bằng trình duyệt cả desktop 1366 và mobile 390) · `docker compose run --rm --no-deps api pytest -q` (100 test). Chi tiết: README.md.
Chờ tài liệu thật từ Tuấn Thành (định mức, mẫu biểu, KMZ) – chưa dùng dữ liệu thật cho đến khi có.
