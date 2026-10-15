"""Đệm rule engine, phân trang nhật ký, bộ đếm đăng nhập sai lưu trong DB."""
from sqlalchemy import func, select


async def test_dem_rule_engine_dung_lai_va_xoa_khi_commit():
    from app.db import SessionLocal
    from app.models import DuAn
    from app.services import rules
    async with SessionLocal() as s:
        da = await s.scalar(select(DuAn.id).where(DuAn.ma == "DEMO-LO471"))
        a = await rules.danh_gia(s, da)
        assert da in rules._dem
        b = await rules.danh_gia(s, da)
        assert [(v.ma, v.doi_tuong_id) for v in a] == [(v.ma, v.doi_tuong_id) for v in b]
        assert a is not b and rules._dem[da][1] is not b      # trả bản sao, không lộ danh sách đang đệm
        await s.commit()
        assert da not in rules._dem                           # có commit thì bỏ đệm


async def test_truyen_now_thi_khong_dung_dem():
    from datetime import datetime, timezone
    from app.db import SessionLocal
    from app.models import DuAn
    from app.services import rules
    async with SessionLocal() as s:
        da = await s.scalar(select(DuAn.id).where(DuAn.ma == "DEMO-LO471"))
        rules._dem.clear()
        await rules.danh_gia(s, da, datetime(2026, 10, 14, 12, tzinfo=timezone.utc))
        assert da not in rules._dem


async def test_phan_trang_bao_cao(client, H):
    h = H["kythuat"]
    tat_ca = (await client.get("/api/bao-cao-hien-truong", params={"limit": 200}, headers=h)).json()
    assert len(tat_ca) >= 3
    t1 = (await client.get("/api/bao-cao-hien-truong", params={"limit": 2}, headers=h)).json()
    t2 = (await client.get("/api/bao-cao-hien-truong", params={"limit": 2, "offset": 2}, headers=h)).json()
    assert len(t1) == 2 and [b["id"] for b in t1 + t2] == [b["id"] for b in tat_ca[:2 + len(t2)]]
    assert (await client.get("/api/bao-cao-hien-truong", params={"limit": 500}, headers=h)).status_code == 422
    assert (await client.get("/api/bao-cao-hien-truong", params={"offset": -1}, headers=h)).status_code == 422


async def test_loc_bao_cao_theo_ngay_va_vi_tri(client, H):
    h = H["kythuat"]
    tuong_lai = (await client.get("/api/bao-cao-hien-truong", params={"tu": "2099-01-01"}, headers=h)).json()
    assert tuong_lai == []
    qua_khu = (await client.get("/api/bao-cao-hien-truong", params={"den": "2000-01-01"}, headers=h)).json()
    assert qua_khu == []
    mot = (await client.get("/api/bao-cao-hien-truong", params={"vi_tri": "VT47"}, headers=h)).json()
    assert mot and all(b["viTri"] == "VT47" for b in mot)


async def test_dang_nhap_sai_duoc_ghi_vao_db_khong_luu_email(client):
    from app.db import SessionLocal
    from app.models import DangNhapThatBai
    async with SessionLocal() as s:
        truoc = await s.scalar(select(func.count()).select_from(DangNhapThatBai))
    r = await client.post("/api/auth/login", json={"email": "do-bo-nho@demo.tuyenso.local", "matKhau": "sai-mat-khau-123"})
    assert r.status_code == 401
    async with SessionLocal() as s:
        sau = await s.scalar(select(func.count()).select_from(DangNhapThatBai))
        mau = (await s.scalars(select(DangNhapThatBai).order_by(DangNhapThatBai.id.desc()).limit(1))).one()
    assert sau == truoc + 1
    assert "@" not in mau.email_hash and len(mau.email_hash) == 64   # chỉ lưu băm, không lưu email thô
