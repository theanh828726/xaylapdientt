import re


async def lay_cot(client, H, who="giamdoc"):
    return {c["ten"]: c for c in (await client.get("/api/vi-tri-cot", headers=H[who])).json()}


async def test_danh_sach_vi_tri_dung_hinh_dang(client, H):
    cot = await lay_cot(client, H)
    assert len(cot) == 64
    c = cot["VT45"]
    assert {"id", "ten", "km", "kmText", "loaiMong", "kieuCot", "buoc", "buocTen", "tienDo", "vuongGpmb", "canhBaoMuc", "canhBao", "lon", "lat"} <= set(c)
    assert c["kmText"] == "Km 2+340" and c["kieuCot"] == "Néo góc" and c["loaiMong"] == "MT-8a-20-3,7"
    assert 105 < c["lon"] < 106 and 19 < c["lat"] < 21                         # Hà Trung, Thanh Hóa
    assert c["buoc"] == "dang_thi_cong_mong" and c["canhBaoMuc"] == "canh_bao"


async def test_buoc_thi_cong_khop_chu_giai_ban_do(client, H):
    from collections import Counter
    cot = await lay_cot(client, H)
    dem = Counter(c["buoc"] for k, c in cot.items() if 33 <= int(k[2:]) <= 51)
    assert dem == {"da_keo_day": 6, "da_dung_cot": 3, "mong_da_nghiem_thu": 3, "dang_thi_cong_mong": 3, "chua_thi_cong": 4}
    assert cot["VT38"]["canhBaoMuc"] == "chan" and cot["VT46"]["canhBaoMuc"] == "chan"        # R06 / R03+R04
    assert cot["VT55"]["vuongGpmb"] is True


async def test_chi_tiet_vi_tri_45_theo_thiet_ke(client, H):
    vt = (await lay_cot(client, H))["VT45"]
    d = (await client.get(f"/api/vi-tri-cot/{vt['id']}", headers=H["giamdoc"])).json()
    assert d["doan"] == "Đoạn Km2 – Km3" and d["tuyen"]["ma"] == "L471"
    assert [c["text"] for c in d["chips"]] == ["Đang thi công móng", "Chờ kết quả nén 7 ngày"]
    assert d["thietKe"] == {"cot": "LT-20-14", "cotNpc": "NPC.I-20-190-14", "mong": "MT-8a-20-3,7", "xa": "XN-22-3N", "tiepDia": "RC-4",
                            "capDat": "Cấp II · K = 0,75", "khoangCach": "68 m / 72 m"}
    assert d["chietTinh"]["dienTichDay"] == 11.6 and abs(d["chietTinh"]["daoDat"] - 142.7) < 0.1
    assert [(r["trangThai"], r["ten"]) for r in d["lichSu"]] == [
        ("xong", "Đào móng"), ("xong", "Bê tông lót M100"), ("xong", "Cốt thép, ván khuôn đế móng"), ("dang", "Bê tông đúc móng M150"),
        ("chan", "Lắp móng"), ("chua", "Dựng cột · lắp xà sứ · kéo dây")]
    assert d["lichSu"][3]["nhan"] == "Chờ 16/10" and d["lichSu"][4]["ghiChu"] == "Bị chặn bởi R02 · cần NT bê tông móng"
    assert d["lichSu"][0]["ngay"] == "02/10" and d["lichSu"][0]["nhan"] == "NT 03/10"
    assert d["hoSo"]["dat"] == 6 and d["hoSo"]["tong"] == 9 and d["anh"]["tong"] == 14
    assert len(d["canhBao"]) == 1 and d["canhBao"][0]["ma"] == "R05" and "dự kiến 16/10" in d["canhBao"][0]["thongBao"]
    assert d["nhacVatTu"] == "Cần đặt trước 18/10 (lead-time 10 ngày)"
    assert [v["ten"] for v in d["vatTu"]] == ["Xi măng PC40", "Thép tròn D ≤ 18", "Cột LT-20-14"] and d["vatTu"][2]["daCap"] == 0


async def test_chi_tiet_vi_tri_khong_ton_tai_hoac_khac_du_an(client, H):
    assert (await client.get("/api/vi-tri-cot/00000000-0000-0000-0000-000000000000", headers=H["giamdoc"])).status_code == 404
    vt = (await lay_cot(client, H))["VT45"]
    p2 = next(d["id"] for d in (await client.get("/api/du-an", headers=H["giamdoc"])).json() if d["ma"] == "DEMO-BL110")
    assert (await client.get(f"/api/vi-tri-cot/{vt['id']}", headers={**H["giamdoc"], "X-Du-An": p2})).status_code == 404


async def test_tuyen_va_geojson_toa_do_that(client, H):
    ds = {t["ma"]: t for t in (await client.get("/api/tuyen", headers=H["giamdoc"])).json()}
    assert set(ds) == {"L471", "HT04", "CU"} and ds["L471"]["soViTri"] == 64 and ds["L471"]["capDienAp"] == "22 kV"
    assert 3.5 < ds["L471"]["chieuDaiKm"] < 4.5 and ds["CU"]["loai"] == "cu" and ds["L471"]["capNhat"]
    fc = (await client.get("/api/ban-do/geojson", headers=H["giamdoc"])).json()
    tuyen = [f for f in fc["features"] if f["properties"]["loai"] == "tuyen"]
    cot = [f for f in fc["features"] if f["properties"]["loai"] == "cot"]
    assert len(tuyen) == 3 and all(f["geometry"]["type"] == "LineString" for f in tuyen) and len(cot) == 64
    assert {f["properties"]["tuyenLoai"] for f in tuyen} == {"moi", "cu"}
    for f in cot:
        lon, lat = f["geometry"]["coordinates"]
        assert 105.0 < lon < 106.5 and 19.5 < lat < 20.5


async def test_phan_quyen_gia_dong_de_xuat_va_dinh_dang(client, H):
    dx = next(d for d in (await client.get("/api/de-xuat-vat-tu", headers=H["kehoach"])).json() if d["ma"] == "ĐX-0412")
    assert dx["doan"] == "VT 41–48" and dx["lanDeXuat"] == 3 and dx["canHang"] == "2026-10-21" and dx["giaoTai"] == "Kho công trường Hà Trung"
    assert len(dx["dong"]) == 9 and dx["nguoiLap"] == "Kỹ thuật – Đỗ Minh Khôi" and dx["coTheDuyet"] is True
    thep = next(r for r in dx["dong"] if r["ten"] == "Thép tròn D ≤ 10")
    assert (thep["theoDinhMuc"], thep["daDeXuat"], thep["conLai"], thep["deXuat"]) == (420, 280, 140, 180)
    assert thep["canhBao"] == "R09 · vượt định mức 40 kg · có lý do của kỹ thuật" and dx["lyDoVuot"].startswith("ván khuôn VT 46")
    assert next(r for r in dx["dong"] if r["ten"].startswith("Bê tông"))["tonKho"] is None
    assert dx["doiChieu"] == {"khop": 8, "tong": 9, "ghiChu": "Dây AC-95/16: hợp đồng 3.600 m, thiết kế 3.660 m (+1,7%)"}
    assert [b["vaiTroNgan"] for b in dx["chuoiDuyet"]] == ["Kỹ thuật", "CHT", "P.KH", "PGĐ", "Chủ tịch"]
    assert [b["nguoi"] for b in dx["chuoiDuyet"]][:3] == ["Đỗ Minh Khôi", "Hoàng Văn Lực", "Trần Thu Hà"]
    assert dx["chuoiDuyet"][1]["lyDo"] == "Đã kiểm tồn kho" and dx["chuoiDuyet"][3]["goiY"].startswith("Đối chiếu chỉ dẫn kỹ thuật")
    assert dx["vaiTroTiep"] == "PGĐ" and dx["buocHienTai"] == "Bước 3/5 – Phòng Kế hoạch"


async def test_kho_dang_cay_va_giao_hang(client, H):
    kho = (await client.get("/api/kho", headers=H["giamdoc"])).json()
    assert kho["cap"] == "Công ty" and kho["ton"] == 18420
    con = {c["ten"]: c for c in kho["con"]}
    assert set(con) == {"Kho công trường Hà Trung", "Công trường TBA 110kV Bến Lức"}
    assert sorted(t["ten"] for t in con["Kho công trường Hà Trung"]["con"]) == ["Tổ 1", "Tổ 2", "Tổ 3"]
    giao = (await client.get("/api/dot-giao-hang", headers=H["giamdoc"])).json()
    d2 = next(g for g in giao if g["po"] == "PO-0388" and g["dot"] == 2)
    assert d2["coAnhPhuongTien"] is False and (d2["slNhan"], d2["slDat"], d2["dvt"]) == (1.8, 3.0, "tấn")


async def test_cach_ly_du_an(client, H):
    du_an = (await client.get("/api/du-an", headers=H["giamdoc"])).json()
    assert [d["ma"] for d in du_an][:2] == ["DEMO-LO471", "DEMO-BL110"]
    p2 = next(d["id"] for d in du_an if d["ma"] == "DEMO-BL110")
    assert len((await client.get("/api/vi-tri-cot", headers=H["giamdoc"])).json()) == 64
    r = await client.get("/api/vi-tri-cot", headers={**H["giamdoc"], "X-Du-An": p2})
    assert len(r.json()) == 6
    assert (await client.get("/api/de-xuat-vat-tu", headers={**H["giamdoc"], "X-Du-An": p2})).json() == []
    # Tổ 2 chỉ thuộc dự án 1 → không vào được dự án 2, và header sai định dạng bị từ chối
    assert (await client.get("/api/vi-tri-cot", headers={**H["khoa"], "X-Du-An": p2})).status_code == 403
    assert (await client.get("/api/vi-tri-cot", headers={**H["khoa"], "X-Du-An": "khong-phai-uuid"})).status_code == 400


async def test_tao_du_an_can_quyen(client, H):
    body = {"ma": "TEST-DA", "ten": "Dự án thử nghiệm"}
    assert (await client.post("/api/du-an", headers=H["kythuat"], json=body)).status_code == 403
    r = await client.post("/api/du-an", headers=H["giamdoc"], json=body)
    assert r.status_code == 201
    assert (await client.post("/api/du-an", headers=H["giamdoc"], json=body)).status_code == 409
    assert (await client.get("/api/vi-tri-cot", headers={**H["giamdoc"], "X-Du-An": r.json()["id"]})).json() == []


async def test_danh_sach_tat_ca_du_an_cho_quan_tri(client, H):
    assert (await client.get("/api/du-an/tat-ca", headers=H["kythuat"])).status_code == 403
    r = await client.get("/api/du-an/tat-ca", headers=H["giamdoc"])
    assert r.status_code == 200 and {"DEMO-LO471", "DEMO-BL110"} <= {d["ma"] for d in r.json()}


async def test_tim_kiem(client, H):
    r = await client.get("/api/tim-kiem", params={"q": "VT45"}, headers=H["kythuat"])
    assert r.status_code == 200 and r.json()[0]["tieuDe"] == "VT 45" and r.json()[0]["lienKet"].startswith("/ban-do?vt=")
    r = await client.get("/api/tim-kiem", params={"q": "MT-8a"}, headers=H["kythuat"])
    assert any(x["tieuDe"] == "VT 45" for x in r.json())
    assert any(x["loai"] == "Đề xuất" and x["tieuDe"] == "ĐX-0412" for x in (await client.get("/api/tim-kiem", params={"q": "0412"}, headers=H["kythuat"])).json())
    assert any(x["loai"] == "Lô vật liệu" for x in (await client.get("/api/tim-kiem", params={"q": "XM-1009"}, headers=H["kythuat"])).json())
    assert (await client.get("/api/tim-kiem", params={"q": "%"}, headers=H["kythuat"])).status_code == 422       # quá ngắn
    assert (await client.get("/api/tim-kiem", params={"q": "%%"}, headers=H["kythuat"])).json() == []            # ký tự đại diện bị thoát
    assert (await client.get("/api/tim-kiem", params={"q": "VT45"})).status_code == 401


async def test_thong_bao_cua_toi(client, H):
    d = (await client.get("/api/thong-bao", headers=H["kehoach"])).json()
    assert d["chuaDoc"] >= 1 and any("ĐX-0412" in n["tieuDe"] for n in d["items"])
    assert not any("ĐX-0412" in n["tieuDe"] for n in (await client.get("/api/thong-bao", headers=H["chutich"])).json()["items"])  # chỉ của mình
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", d["items"][0]["thoiGian"])
