"""Đối soát 3 nguồn theo hạng mục (chỉ đọc; thao tác ghi nằm ở test_zz_hanh_dong để không đổi số liệu của test khác)."""


async def hang_muc(client, H, who="kehoach"):
    return {h["ten"]: h for h in (await client.get("/api/doi-soat/hang-muc", headers=H[who])).json()}


async def test_danh_sach_hang_muc_khop_thiet_ke(client, H):
    hm = await hang_muc(client, H)
    assert list(hm) == ["Chuỗi néo 22 kV", "Dây dẫn AC-95/16", "Móng MT-7a, MT-8a", "Xà XN-22-3N", "Cột BTLT 14–20 m"]   # 5 hạng mục
    assert [h["soCanXuLy"] for h in hm.values()] == [2, 1, 0, 0, 0]            # chuỗi néo: 1 lệch + 1 thiếu; dây: 1 lệch; còn lại khớp


async def test_chi_tiet_chuoi_neo(client, H):
    hm = await hang_muc(client, H)
    d = (await client.get(f"/api/doi-soat/hang-muc/{hm['Chuỗi néo 22 kV']['id']}", headers=H["kehoach"])).json()
    assert d["tieuDe"] == "Chuỗi néo 22 kV · 14 vị trí néo" and (d["soThongSo"], d["soLech"], d["soThieu"]) == (4, 1, 1)
    assert [n["nhan"] for n in d["nguon"]] == ["HỢP ĐỒNG", "BẢN VẼ + BẢNG KÊ", "CHỈ DẪN KỸ THUẬT"]
    assert d["nguon"][0]["ten"] == "Phụ lục khối lượng, gói thầu số 04" and d["nguon"][2]["mo_ta"] == "PDF scan 41 trang · OCR tiếng Việt"
    rows = {r["thongSo"]: r for r in d["rows"]}
    bat = rows["Loại bát sứ chuỗi néo"]
    assert (bat["banVe"], bat["chiDan"], bat["ketLuan"], bat["ketLuanTen"], bat["tinCay"], bat["hanhDong"]) == ("Loại 210", "Loại 300", "lech", "Lệch", 0.94, "tao_phieu")
    assert bat["trichDan"] == {"hd": "tr. 12, dòng 37", "bv": "BV-ĐZ-08, tr. 3", "cd": "mục 4.2, tr. 17"}
    assert [b["tone"] for b in bat["bangChung"]] == ["bad", "ok"] and bat["bangChung"][0]["nhan"] == "[Ảnh trang BV-ĐZ-08, tr. 3]"
    assert rows["Số bát sứ mỗi chuỗi"]["hanhDong"] == "xac_nhan" and rows["Số bát sứ mỗi chuỗi"]["tinCay"] == 0.97
    lo = rows["Chuỗi đỡ lèo"]
    assert (lo["ketLuanTen"], lo["hanhDong"], lo["hopDong"], lo["tinCay"]) == ("Thiếu trong HĐ", "phat_sinh", "Không có", 0.88)
    assert rows["Số bộ chuỗi néo"]["tinCay"] is None and "tinCay" in rows["Số bộ chuỗi néo"]


async def test_hang_muc_khong_ton_tai_hoac_khac_du_an(client, H):
    assert (await client.get("/api/doi-soat/hang-muc/00000000-0000-0000-0000-000000000000", headers=H["kehoach"])).status_code == 404
    hm = await hang_muc(client, H)
    p2 = next(d["id"] for d in (await client.get("/api/du-an", headers=H["giamdoc"])).json() if d["ma"] == "DEMO-BL110")
    assert (await client.get(f"/api/doi-soat/hang-muc/{hm['Xà XN-22-3N']['id']}", headers={**H["giamdoc"], "X-Du-An": p2})).status_code == 404
    assert (await client.get("/api/doi-soat/hang-muc")).status_code == 401
