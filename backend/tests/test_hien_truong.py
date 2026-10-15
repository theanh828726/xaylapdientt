from datetime import datetime, timedelta, timezone

from .conftest import new_id


async def test_bao_cao_idempotent_theo_client_id(client, H):
    cid = new_id()
    body = {"viTri": "VT48", "noiDung": "Chuẩn bị mặt bằng VT48", "soAnh": 4, "clientId": cid}
    a = await client.post("/api/bao-cao-hien-truong", headers=H["khoa"], json=body)
    b = await client.post("/api/bao-cao-hien-truong", headers=H["khoa"], json=body)
    assert a.status_code == 201 and b.status_code == 200 and a.json()["id"] == b.json()["id"]
    assert a.json()["dongBo"] == "da_dong_bo" and a.json()["nguoi"] == "Tổ 2 – Đặng Văn Khoa"
    ds = (await client.get("/api/bao-cao-hien-truong", headers=H["khoa"])).json()
    assert sum(1 for x in ds if x["noiDung"] == "Chuẩn bị mặt bằng VT48") == 1
    # người khác không chiếm được clientId của người đã gửi
    assert (await client.post("/api/bao-cao-hien-truong", headers=H["son"], json=body)).status_code == 409


async def test_bao_cao_validate_va_quyen(client, H):
    ok = {"viTri": "VT41", "noiDung": "ok"}
    assert (await client.post("/api/bao-cao-hien-truong", headers=H["ketoan"], json=ok)).status_code == 403
    assert (await client.post("/api/bao-cao-hien-truong", headers=H["khoa"], json={**ok, "viTri": "VT999"})).status_code == 422
    assert (await client.post("/api/bao-cao-hien-truong", headers=H["khoa"], json={**ok, "noiDung": ""})).status_code == 422
    tuong_lai = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert (await client.post("/api/bao-cao-hien-truong", headers=H["khoa"], json={**ok, "ngay": tuong_lai})).status_code == 422
    khong_mui_gio = datetime(2026, 1, 1, 8, 0).isoformat()
    assert (await client.post("/api/bao-cao-hien-truong", headers=H["khoa"], json={**ok, "ngay": khong_mui_gio})).status_code == 422


async def test_nhat_ky_hien_thi_day_du_truong(client, H):
    ds = (await client.get("/api/bao-cao-hien-truong", headers=H["giamdoc"])).json()
    b = next(x for x in ds if x["viTri"] == "VT45" and x["congTacMa"] == "dao_mong")
    assert b["congTac"] == "Đào móng" and b["khoiLuong"] == 143.6 and b["toDoi"] == "Tổ 3 · Lê Văn Tâm" and b["anh"] == 4 and b["mayThiCong"] == ["Máy đào 0,8 m³"]
    assert b["thoiTiet"] == "Nắng, 31°C" and b["nguoi"] == "Tổ 3 – Lê Văn Tâm" and b["ngay"] == "2026-10-02 16:00"
    cho = next(x for x in ds if x["ngay"] == "2026-10-14 07:55")
    assert cho["dongBo"] == "cho_dong_bo" and cho["viTri"] == "VT47"     # báo cáo từ thiết bị còn chờ đồng bộ
