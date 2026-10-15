import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from .conftest import PW


@pytest_asyncio.fixture(loop_scope="session")
async def fresh():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def dang_nhap(c, who="giamdoc", pw=PW):
    return await c.post("/api/auth/login", json={"email": f"{who}@demo.tuyenso.local", "matKhau": pw})


async def test_sai_mat_khau_va_email_la_cung_thong_bao(fresh):
    a = await dang_nhap(fresh, pw="sai-mat-khau-123")
    b = await fresh.post("/api/auth/login", json={"email": "khong-co@demo.tuyenso.local", "matKhau": PW})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


async def test_me_va_quyen(fresh):
    r = await dang_nhap(fresh, "ketoan")
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["vaiTro"] == "ke_toan" and body["user"]["vaiTroTen"] == "Kế toán"
    assert "gia_hop_dong.xem" in body["quyen"] and "duyet.thuc_hien" not in body["quyen"]
    assert len(body["duAn"]) == 2
    me = await fresh.get("/api/auth/me", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me.status_code == 200 and me.json()["user"]["email"] == "ketoan@demo.tuyenso.local"


async def test_khong_token_hoac_token_gia_bi_401(fresh):
    assert (await fresh.get("/api/vi-tri-cot")).status_code == 401
    assert (await fresh.get("/api/vi-tri-cot", headers={"Authorization": "Bearer abc.def.ghi"})).status_code == 401


async def test_refresh_xoay_vong_va_phat_hien_dung_lai(fresh):
    await dang_nhap(fresh, "chutich")
    cu = fresh.cookies.get("refresh_token")
    assert cu
    r = await fresh.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json()["accessToken"]
    moi = fresh.cookies.get("refresh_token")
    assert moi and moi != cu
    # dùng lại token cũ → 401 và toàn bộ phiên bị thu hồi (kể cả token mới)
    dung_lai = await fresh.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={cu}"})
    assert dung_lai.status_code == 401
    r2 = await fresh.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={moi}"})
    assert r2.status_code == 401


async def test_logout_thu_hoi_refresh(fresh):
    await dang_nhap(fresh, "kehoach")
    tok = fresh.cookies.get("refresh_token")
    assert (await fresh.post("/api/auth/logout")).status_code == 204
    r = await fresh.post("/api/auth/refresh", headers={"Cookie": f"refresh_token={tok}"})
    assert r.status_code == 401


async def test_gioi_han_dang_nhap_sai(fresh):
    # Email riêng để không khoá tài khoản demo mà các test khác dùng.
    codes = [(await dang_nhap(fresh, "khong-co-throttle", pw=f"sai-mat-khau-{i}")).status_code for i in range(7)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
