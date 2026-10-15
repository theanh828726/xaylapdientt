from .conftest import new_id

DX = {"congTrinh": "ĐZ test chuỗi duyệt", "dong": [{"maCK": "LT-20-14", "deXuat": 2, "theoDinhMuc": 2}]}


async def tao(client, H):
    r = await client.post("/api/de-xuat-vat-tu", headers=H["kythuat"], json=DX)
    assert r.status_code == 201, r.text
    return r.json()


async def duyet(client, H, who, id_, quyet="duyet", ly_do=None, loai="de_xuat"):
    body = {"quyetDinh": quyet, **({"lyDo": ly_do} if ly_do else {})}
    return await client.post(f"/api/duyet/{loai}/{id_}", headers=H[who], json=body)


async def tim(client, H, who, id_):
    return next(x for x in (await client.get("/api/de-xuat-vat-tu", headers=H[who])).json() if x["id"] == id_)


async def test_tao_de_xuat_khoi_tao_chuoi_5_buoc(client, H):
    d = await tao(client, H)
    assert d["ma"].startswith("ĐX-") and d["trangThai"] == "cho_duyet"
    assert [b["trangThai"] for b in d["chuoiDuyet"]] == ["xong", "dang", "cho", "cho", "cho"]
    assert [b["vaiTro"] for b in d["chuoiDuyet"]] == ["Kỹ thuật", "Chỉ huy trưởng", "Phòng Kế hoạch", "Phó Giám đốc", "Chủ tịch"]
    assert d["buocHienTai"] == "Bước 2/5 – Chỉ huy trưởng"
    assert d["dong"][0]["tonKho"] == 0 and d["dong"][0]["ten"] == "Cột BTLT 20 m"


async def test_di_het_chuoi_dung_thu_tu(client, H):
    d = await tao(client, H)
    # Sai vai trò / sai lượt / không có quyền duyệt
    assert (await duyet(client, H, "kythuat", d["id"])).status_code == 403
    assert (await duyet(client, H, "chutich", d["id"])).status_code == 403
    assert (await duyet(client, H, "ketoan", d["id"])).status_code == 403
    for who in ["chihuytruong", "kehoach", "phogiamdoc"]:
        r = await duyet(client, H, who, d["id"])
        assert r.status_code == 200 and r.json()["trangThai"] == "cho_duyet"
    r = await duyet(client, H, "chutich", d["id"])
    assert r.status_code == 200 and r.json()["trangThai"] == "da_duyet" and r.json()["buocHienTai"] is None
    assert (await duyet(client, H, "giamdoc", d["id"])).status_code == 409  # đã xong
    got = await tim(client, H, "giamdoc", d["id"])
    assert got["trangThai"] == "da_duyet" and all(b["trangThai"] == "xong" for b in got["chuoiDuyet"])


async def test_tu_choi_phai_co_ly_do_va_dung_chuoi(client, H):
    d = await tao(client, H)
    assert (await duyet(client, H, "chihuytruong", d["id"], "tu_choi")).status_code == 422
    r = await duyet(client, H, "chihuytruong", d["id"], "tu_choi", "Thiếu bản vẽ móng")
    assert r.status_code == 200 and r.json()["trangThai"] == "tu_choi"
    assert (await duyet(client, H, "kehoach", d["id"])).status_code == 409
    got = await tim(client, H, "giamdoc", d["id"])
    assert got["chuoiDuyet"][1]["trangThai"] == "tu_choi" and got["chuoiDuyet"][1]["lyDo"] == "Thiếu bản vẽ móng"


async def test_giam_doc_duyet_thay_moi_buoc(client, H):
    d = await tao(client, H)
    assert (await duyet(client, H, "giamdoc", d["id"])).status_code == 200  # duyet.moi_buoc


async def test_co_the_duyet_theo_nguoi_dang_nhap(client, H):
    d = await tao(client, H)
    for who, expect in [("chihuytruong", True), ("kythuat", False), ("kehoach", False), ("giamdoc", True)]:
        got = await tim(client, H, who, d["id"])
        assert got["coTheDuyet"] is expect, who


async def test_phieu_dieu_chinh_cung_chuoi(client, H):
    r = await client.post("/api/phieu-dieu-chinh", headers=H["kythuat"], json={"lyDo": "Điều chỉnh vị trí VT50 do GPMB"})
    assert r.status_code == 201
    p = r.json()
    assert p["ma"].startswith("PĐC-") and p["buocHienTai"] == "Bước 2/5 – Chỉ huy trưởng"
    assert (await duyet(client, H, "chihuytruong", p["id"], loai="phieu_dc")).status_code == 200
    assert (await duyet(client, H, "chihuytruong", new_id(), loai="phieu_dc")).status_code == 404


async def test_ma_cau_kien_la_bi_tu_choi(client, H):
    r = await client.post("/api/de-xuat-vat-tu", headers=H["kythuat"],
                          json={"congTrinh": "x y z", "dong": [{"maCK": "KHONG-CO", "deXuat": 1, "theoDinhMuc": 1}]})
    assert r.status_code == 422
