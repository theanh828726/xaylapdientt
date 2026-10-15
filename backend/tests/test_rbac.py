import pytest

from .conftest import new_id

DX = {"congTrinh": "ĐZ test phân quyền", "dong": [{"maCK": "LT-20-14", "deXuat": 2, "theoDinhMuc": 2}]}


@pytest.mark.parametrize("who,hop_dong,khoan", [
    ("giamdoc", True, True), ("ketoan", True, True), ("phogiamdoc", True, True),
    ("chihuytruong", False, True), ("kythuat", False, False),
])
async def test_gia_an_o_response(client, H, who, hop_dong, khoan):
    r = await client.get("/api/de-xuat-vat-tu", headers=H[who])
    assert r.status_code == 200
    d = next(x for x in r.json() if x["ma"] == "ĐX-0412")
    # Không đủ quyền thì trường không có trong JSON (không chỉ bị ẩn ở UI).
    assert ("giaHopDong" in d) is hop_dong and ("giaKhoan" in d) is khoan
    if hop_dong:
        assert d["giaHopDong"] == 1_284_500_000


async def test_nhap_gia_can_quyen_xem_gia(client, H):
    r = await client.post("/api/de-xuat-vat-tu", headers=H["kythuat"], json={**DX, "giaKhoan": 1000})
    assert r.status_code == 403


async def test_ke_toan_khong_duoc_lap_de_xuat_mac_dinh(client, H):
    assert (await client.post("/api/de-xuat-vat-tu", headers=H["ketoan"], json=DX)).status_code == 403


async def test_chinh_ma_tran_phan_quyen(client, H):
    # Chỉ người có phan_quyen.quan_ly mới xem/sửa ma trận.
    assert (await client.get("/api/phan-quyen", headers=H["kythuat"])).status_code == 403
    mt = (await client.get("/api/phan-quyen", headers=H["giamdoc"])).json()
    goc = mt["maTran"]["ke_toan"]
    try:
        r = await client.put("/api/phan-quyen/ke_toan", headers=H["giamdoc"], json={"quyen": goc + ["de_xuat.lap"]})
        assert r.status_code == 200
        # quyền có hiệu lực ngay (không cần đăng nhập lại)
        assert (await client.post("/api/de-xuat-vat-tu", headers=H["ketoan"], json=DX)).status_code == 201
    finally:
        await client.put("/api/phan-quyen/ke_toan", headers=H["giamdoc"], json={"quyen": goc})
    assert (await client.post("/api/de-xuat-vat-tu", headers=H["ketoan"], json=DX)).status_code == 403


async def test_khong_duoc_tu_khoa_giam_doc(client, H):
    r = await client.put("/api/phan-quyen/giam_doc", headers=H["giamdoc"], json={"quyen": ["gia_khoan.xem"]})
    assert r.status_code == 422
    r = await client.put("/api/phan-quyen/giam_doc", headers=H["giamdoc"], json={"quyen": ["khong.ton.tai"]})
    assert r.status_code == 422


async def test_quan_ly_nguoi_dung(client, H):
    assert (await client.get("/api/nguoi-dung", headers=H["chihuytruong"])).status_code == 403
    email = f"test-{new_id()[:8]}@demo.tuyenso.local"
    body = {"email": email, "hoTen": "Người thử", "vaiTro": "ke_toan", "matKhau": "MatKhauThu#12345", "duAnIds": []}
    r = await client.post("/api/nguoi-dung", headers=H["giamdoc"], json=body)
    assert r.status_code == 201 and r.json()["vaiTro"] == "ke_toan"
    assert (await client.post("/api/nguoi-dung", headers=H["giamdoc"], json=body)).status_code == 409
    assert (await client.post("/api/nguoi-dung", headers=H["giamdoc"], json={**body, "matKhau": "ngan"})).status_code == 422
    # người mới chưa gán dự án → không vào được dữ liệu dự án
    tok = (await client.post("/api/auth/login", json={"email": email, "matKhau": "MatKhauThu#12345"})).json()["accessToken"]
    assert (await client.get("/api/vi-tri-cot", headers={"Authorization": f"Bearer {tok}"})).status_code == 403
    # khoá tài khoản → token cũ hết tác dụng
    uid = r.json()["id"]
    assert (await client.patch(f"/api/nguoi-dung/{uid}", headers=H["giamdoc"], json={"active": False})).status_code == 200
    assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})).status_code == 401
    # không tự đổi vai trò của chính mình
    me = (await client.get("/api/auth/me", headers=H["giamdoc"])).json()["user"]["id"]
    assert (await client.patch(f"/api/nguoi-dung/{me}", headers=H["giamdoc"], json={"vaiTro": "ke_toan"})).status_code == 422
