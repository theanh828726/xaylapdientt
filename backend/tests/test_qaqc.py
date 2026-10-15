"""Màn hình Hồ sơ QA/QC: mọi con số phải khớp thiết kế và được TÍNH từ dữ liệu seed."""
KHOANG = {"tu": "2026-10-07", "den": "2026-10-14"}


async def tong_quan(client, H, nhom="PL1", who="kehoach"):
    r = await client.get("/api/qaqc/tong-quan", params={"nhom": nhom, **KHOANG}, headers=H[who])
    assert r.status_code == 200, r.text
    return r.json()


async def test_thong_ke_khop_thiet_ke(client, H):
    d = await tong_quan(client, H)
    assert d["thongKe"]["duHoSoMong"] == {"du": 12, "tong": 64}
    assert d["thongKe"]["bienBanSanSang"] == {"n": 18, "tu": "2026-10-07", "den": "2026-10-14"}
    assert d["thongKe"]["loiChan"] == {"n": 3}
    assert d["thongKe"]["mauChoNen"] == {"n": 5, "ganNhat": {"tuoi": 7, "ngay": "2026-10-16"}}
    assert d["nhom"] == "PL1" and d["nhomTen"] == "Phần móng" and d["soQuyTac"] == 17


async def test_kiem_tra_logic_ho_so_pl1(client, H):
    d = await tong_quan(client, H)
    kt = d["kiemTra"]
    assert [(v["muc"], v["ma"]) for v in kt][:3] == [("Chặn", "R04"), ("Chặn", "R03"), ("Chặn", "R06")]
    assert {v["ma"] for v in kt} == {"R03", "R04", "R06", "R08", "R11", "R05"}
    assert [v["muc"] for v in kt] == ["Chặn"] * 3 + ["Cảnh báo"] * 2 + ["Nhắc việc"]
    r04 = next(v for v in kt if v["ma"] == "R04")
    assert r04["ten"] == "Xi măng lô XM-1009 chưa có kết quả thí nghiệm" and r04["hanhDong"] == "gan_ket_qua"
    assert r04["chiTiet"] == "Đã đổ bê tông lót tại VT 46 ngày 13/10 · BB lấy mẫu 08/10, phòng LAS chưa trả kết quả"
    r03 = next(v for v in kt if v["ma"] == "R03")
    assert r03["ten"] == "Cát vàng nhà cung cấp thứ hai chưa được chủ đầu tư chấp thuận" and r03["hanhDong"] == "soan_de_trinh"
    assert r03["chiTiet"] == "Đã giao 12/10 · đã dùng tại VT 46 · cần văn bản chấp thuận trước ngày 17/10"
    r06 = next(v for v in kt if v["ma"] == "R06")
    assert r06["ten"] == "VT 38: ngày nghiệm thu dựng cột (10/10) sớm hơn ngày hoàn thành (11/10)"
    assert r06["chiTiet"] == "Sửa sẽ ảnh hưởng 3 biên bản phía sau: lắp xà, kéo dây, nhật ký 11/10" and r06["hanhDong"] == "mo_phieu_dieu_chinh"
    r08 = next(v for v in kt if v["ma"] == "R08")
    assert r08["ten"] == "2 biên bản đào móng VT 46–47 chưa kèm bảng chiết tính" and r08["chiTiet"].startswith("Thư viện đã có mã MT-8a-20-3,7")
    r11 = next(v for v in kt if v["ma"] == "R11")
    assert r11["ten"] == "Đợt giao 2 của PO-0388 (thép D16) thiếu ảnh phương tiện giao hàng"
    assert r11["chiTiet"] == "Nhận 13/10 tại Kho công trường Hà Trung · 1,8 / 3,0 tấn" and r11["hanhDong"] == "nhac_ky_thuat"
    r05 = next(v for v in kt if v["ma"] == "R05")
    assert r05["ten"] == "5 mẫu bê tông đến hạn nén: 3 mẫu 7 ngày (16/10), 2 mẫu 28 ngày (30/10)" and r05["hanhDong"] == "xem_lich"


async def test_cac_tab_phu_luc_loc_theo_nhom(client, H):
    pl2 = await tong_quan(client, H, "PL2")
    assert {v["ma"] for v in pl2["kiemTra"]} == {"R09", "R10"}
    r09 = next(v for v in pl2["kiemTra"] if v["ma"] == "R09")
    assert r09["thongBao"] == "1 dòng vượt định mức: thép tròn D ≤ 10 vượt 40 kg" and r09["chiTiet"].startswith("Lý do của kỹ thuật: ván khuôn VT 46")
    assert next(v for v in pl2["kiemTra"] if v["ma"] == "R10")["ten"] == "Cột LT-20-14 cần đặt trước 18/10 (lead-time 10 ngày)"
    assert {v["ma"] for v in (await tong_quan(client, H, "PL3"))["kiemTra"]} == {"R17"}
    pl4 = {v["ma"] for v in (await tong_quan(client, H, "PL4"))["kiemTra"]}
    assert {"R14", "R24"} <= pl4


async def test_ma_tran_vi_tri_x_cong_tac(client, H):
    m = (await tong_quan(client, H))["maTran"]
    assert [c["ten"] for c in m["cot"]] == ["Đào móng", "BT lót", "Thép đế", "BT móng", "Lắp móng", "Dựng cột", "Xà, sứ", "Kéo dây"]
    rows = {r["viTri"]: r["cells"] for r in m["rows"]}
    assert list(rows)[0] == "VT36" and "VT47" in rows and "VT33" not in rows and "VT48" not in rows   # xong + đã có biên bản thì rời ma trận
    st = lambda vt: {k: (c["state"], c.get("ma"), c.get("nhan")) for k, c in rows[vt].items() if c}
    assert st("VT38")["dung_cot"] == ("chan", ["R06"], None) and st("VT38")["xa_su"][0] == "cho" and st("VT38")["lap_mong"][0] == "nt"
    assert st("VT39")["xa_su"][0] == "nt" and "keo_day" not in st("VT39")
    assert st("VT41")["dung_cot"][0] == "cho"
    assert st("VT45") == {"dao_mong": ("nt", None, None), "bt_lot": ("nt", None, None), "thep_de": ("nt", None, None),
                          "bt_mong": ("cho", None, "chờ nén"), "lap_mong": ("chan", ["R02"], None)}
    assert st("VT46") == {"dao_mong": ("thieu", ["R08"], None), "bt_lot": ("chan", ["R04", "R03"], None)}
    assert st("VT47") == {"dao_mong": ("thieu", ["R08"], None)}


async def test_xem_truoc_sinh_bien_ban_gop_theo_doan_ngay(client, H):
    r = await client.get("/api/qaqc/sinh-bien-ban/xem-truoc", params={**KHOANG, "gop": "doan_ngay"}, headers=H["kehoach"])
    d = r.json()
    assert (d["bienBan"], d["kemGiayMoi"], d["kemChietTinh"], d["congTac"], d["sanSang"], d["soNgayNhatKy"]) == (9, 9, 9, 16, 18, 8)
    assert d["biChan"]["n"] == 2 and {(x["viTri"], tuple(x["ma"])) for x in d["biChan"]["ds"]} == {("VT 38", ("R06",)), ("VT 46", ("R04", "R03"))}
    assert len(d["danhSach"]) == 9 and sum(x["soCongTac"] for x in d["danhSach"]) == 16
    tung = (await client.get("/api/qaqc/sinh-bien-ban/xem-truoc", params={**KHOANG, "gop": "vi_tri"}, headers=H["kehoach"])).json()
    assert tung["bienBan"] == 16                                              # từng vị trí: mỗi công tác một biên bản


async def test_khoang_ngay_hop_le(client, H):
    r = await client.get("/api/qaqc/tong-quan", params={"tu": "2026-10-14", "den": "2026-10-07"}, headers=H["kehoach"])
    assert r.status_code == 422
    r = await client.get("/api/qaqc/sinh-bien-ban/xem-truoc", params={"tu": "2024-01-01", "den": "2026-10-14"}, headers=H["kehoach"])
    assert r.status_code == 422
    assert (await client.get("/api/qaqc/tong-quan")).status_code == 401


async def test_lich_nen_mau_be_tong(client, H):
    ds = (await client.get("/api/qaqc/lich-nen", headers=H["kehoach"])).json()
    assert len(ds) == 5 and [x["hanNen"] for x in ds] == ["2026-10-16"] * 3 + ["2026-10-30"] * 2
    assert {x["viTri"] for x in ds[:3]} == {"VT45"} and {x["tuoiNgay"] for x in ds[3:]} == {28}
