"""Huy hiệu menu/chuông (/tong-quan/dem) và xuất chiết tính theo vị trí."""


async def test_dem_pho_giam_doc(client, H):
    r = await client.get("/api/tong-quan/dem", headers=H["phogiamdoc"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["choToi"] == 3 and len(d["choToiItems"]) == 3
    assert {i["ma"] for i in d["choToiItems"]} == {"ĐX-0411", "PĐC-021", "NTĐK-007"}
    assert d["loiChan"] >= 0 and d["chuaDoc"] >= 0


async def test_dem_can_dang_nhap(client):
    assert (await client.get("/api/tong-quan/dem")).status_code == 401


async def test_dem_ky_thuat_thay_loi_chan(client, H):
    d = (await client.get("/api/tong-quan/dem", headers=H["kythuat"])).json()
    assert d["loiChan"] == 3 and d["choToi"] == len(d["choToiItems"])


async def test_chiet_tinh_vi_tri(client, H):
    ds = (await client.get("/api/vi-tri-cot", headers=H["kythuat"])).json()
    vt = next(p for p in ds if p["ten"] == "VT45")
    r = await client.get(f"/api/vi-tri-cot/{vt['id']}/chiet-tinh", headers=H["kythuat"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert r.content[:2] == b"PK"


async def test_chiet_tinh_vi_tri_khong_ton_tai(client, H):
    r = await client.get("/api/vi-tri-cot/00000000-0000-0000-0000-000000000000/chiet-tinh", headers=H["kythuat"])
    assert r.status_code == 404
