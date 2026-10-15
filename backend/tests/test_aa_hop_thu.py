"""Hộp thư phê duyệt (mobile): Chờ tôi / Đang ở cấp khác / Đã xử lý."""


async def hop_thu(client, H, who, tab):
    r = await client.get("/api/duyet/hop-thu", params={"tab": tab}, headers=H[who])
    assert r.status_code == 200, r.text
    return r.json()


async def test_pho_giam_doc_3_cho_5_cap_khac(client, H):
    cho = await hop_thu(client, H, "phogiamdoc", "cho_toi")
    assert cho["dem"]["choToi"] == 3 and cho["dem"]["capKhac"] == 5
    assert {i["ma"] for i in cho["items"]} == {"ĐX-0411", "PĐC-021", "NTĐK-007"}
    assert {i["nhan"] for i in cho["items"]} == {"ĐỀ XUẤT VẬT TƯ", "PHIẾU ĐIỀU CHỈNH", "NGHIỆM THU CÓ ĐIỀU KIỆN"}
    khac = await hop_thu(client, H, "phogiamdoc", "cap_khac")
    assert {i["ma"] for i in khac["items"]} == {"ĐX-0412", "ĐX-0413", "ĐX-0414", "PĐC-020", "NTĐK-006"}
    assert all(i["coTheDuyet"] is False for i in khac["items"])


async def test_the_phieu_dieu_chinh_day_du_thong_tin(client, H):
    p = next(i for i in (await hop_thu(client, H, "phogiamdoc", "cho_toi"))["items"] if i["ma"] == "PĐC-021")
    assert p["tieuDe"] == "VT 38 · đổi ngày nghiệm thu dựng cột 10/10 → 11/10" and p["doiTuong"] == "phieu_dc" and p["gio"] == "09:48"
    assert [(c["ngan"], c["trangThai"]) for c in p["chuoi"]] == [("Kỹ thuật", "xong"), ("CHT", "xong"), ("P.KH", "xong"), ("PGĐ", "dang"), ("Chủ tịch", "cho")]
    assert p["chiTiet"]["lyDo"] == "tổ đội báo hoàn thành ngày 11/10, biên bản ghi nhầm ngày."
    assert p["chiTiet"]["tacDong"] == ["BBNT lắp xà, sứ", "BBNT kéo dây", "Nhật ký ngày 11/10"] and p["chiTiet"]["sauDieuChinh"] == "không còn vi phạm quy tắc"


async def test_the_de_xuat_canh_bao_r09(client, H):
    d = next(i for i in (await hop_thu(client, H, "phogiamdoc", "cap_khac"))["items"] if i["ma"] == "ĐX-0412")
    assert d["canhBao"]["ma"] == "R09" and "thép tròn D ≤ 10 vượt 40 kg" in d["canhBao"]["noiDung"]
    assert "ván khuôn VT 46 hỏng do mưa" in d["canhBao"]["noiDung"] and d["lienKet"] == "/de-xuat/ĐX-0412"
    assert next(i for i in (await hop_thu(client, H, "phogiamdoc", "cho_toi"))["items"] if i["ma"] == "ĐX-0411")["canhBao"] is None


async def test_da_xu_ly_va_vai_tro_khac(client, H):
    assert "ĐX-0410" in {i["ma"] for i in (await hop_thu(client, H, "phogiamdoc", "da_xu_ly"))["items"]}
    kh = await hop_thu(client, H, "kehoach", "cho_toi")
    assert {i["ma"] for i in kh["items"]} == {"ĐX-0412", "NTĐK-006"}              # đến lượt Phòng Kế hoạch
    assert (await hop_thu(client, H, "ketoan", "cho_toi"))["items"] == []        # Kế toán không có bước duyệt
    r = await client.get("/api/duyet/hop-thu", params={"tab": "khac"}, headers=H["kehoach"])
    assert r.status_code == 422
    assert (await client.get("/api/duyet/hop-thu")).status_code == 401
