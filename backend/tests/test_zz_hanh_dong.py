"""Các hành động ghi của QA/QC, đối soát và duyệt. Chạy sau cùng (tên zz) vì làm đổi số liệu dự án 1."""
import io
import re
import zipfile

from docx import Document

from .test_bao_cao_cong_tac import cong_tac_id
from .test_tai_lieu import DOCX, doc_text

KHOANG = {"tu": "2026-10-07", "den": "2026-10-14"}


async def vi_pham(client, H, who="kythuat", **p):
    return (await client.get("/api/quy-tac/vi-pham", params=p, headers=H[who])).json()


async def test_gan_ket_qua_thi_nghiem_het_r04(client, H):
    lo = next(v for v in await vi_pham(client, H) if v["ma"] == "R04")
    assert (await client.post(f"/api/lo-vat-lieu/{lo['doiTuongId']}/ket-qua", headers=H["ketoan"], json={"ketQua": "dat"})).status_code == 403
    assert (await client.post(f"/api/lo-vat-lieu/{lo['doiTuongId']}/ket-qua", headers=H["kythuat"], json={"ketQua": "nhap_bay"})).status_code == 422
    r = await client.post(f"/api/lo-vat-lieu/{lo['doiTuongId']}/ket-qua", headers=H["kythuat"], json={"ketQua": "dat", "ghiChu": "Phòng LAS trả KQ 15/10"})
    assert r.status_code == 200 and r.json()["ketQua"] == "dat"
    assert not any(v["ma"] == "R04" for v in await vi_pham(client, H))                                   # hết lỗi chặn
    d = (await client.get("/api/qaqc/tong-quan", params=KHOANG, headers=H["kehoach"])).json()
    assert d["thongKe"]["loiChan"]["n"] == 2
    assert (await client.post(f"/api/lo-vat-lieu/{lo['doiTuongId']}/ket-qua", headers=H["kythuat"], json={"ketQua": "dat"})).status_code == 409


async def test_soan_de_trinh_nha_cung_cap(client, H):
    lo = next(v for v in await vi_pham(client, H) if v["ma"] == "R03")
    assert (await client.post(f"/api/lo-vat-lieu/{lo['doiTuongId']}/de-trinh", headers=H["ketoan"])).status_code == 403
    r = await client.post(f"/api/lo-vat-lieu/{lo['doiTuongId']}/de-trinh", headers=H["kythuat"])
    assert r.status_code == 200 and r.headers["content-type"] == DOCX
    t = doc_text(r.content)
    for can in ("ĐỀ TRÌNH CHẤP THUẬN NHÀ CUNG CẤP", "Cát vàng", "CV-0212", "nhà cung cấp thứ hai", "VT 46", "17/10/2026", "Đỗ Minh Khôi"):
        assert can in t, can
    assert any(v["ma"] == "R03" for v in await vi_pham(client, H))                                       # đề trình chưa làm hết lỗi


async def test_mo_phieu_dieu_chinh_r06_va_ap_dung_khi_duyet(client, H):
    ct = await cong_tac_id("VT38", "dung_cot", "DEMO-LO471")
    assert (await client.post(f"/api/cong-tac/{ct}/mo-phieu-dieu-chinh", headers=H["ketoan"])).status_code == 403
    r = await client.post(f"/api/cong-tac/{ct}/mo-phieu-dieu-chinh", headers=H["kythuat"])
    assert r.status_code == 201 and r.json()["ma"].startswith("PĐC-")
    ph = next(p for p in (await client.get("/api/phieu-dieu-chinh", headers=H["kythuat"])).json() if p["ma"] == r.json()["ma"])
    assert ph["tieuDe"] == "VT 38 · đổi ngày nghiệm thu dựng cột 10/10 → 11/10" and ph["viTri"] == "VT38"
    assert ph["tacDong"] == ["BBNT lắp xà", "BBNT kéo dây", "Nhật ký ngày 11/10"] and ph["buocHienTai"] == "Bước 2/5 – Chỉ huy trưởng"
    for who in ("chihuytruong", "kehoach", "phogiamdoc", "chutich"):
        assert (await client.post(f"/api/duyet/phieu_dc/{ph['id']}", headers=H[who], json={"quyetDinh": "duyet"})).status_code == 200
    assert not any(v["ma"] == "R06" for v in await vi_pham(client, H))                                  # duyệt xong tự sửa ngày nghiệm thu
    assert (await client.post(f"/api/cong-tac/{ct}/mo-phieu-dieu-chinh", headers=H["kythuat"])).status_code == 409   # không còn vi phạm
    cots = {c["ten"]: c for c in (await client.get("/api/vi-tri-cot", headers=H["kythuat"])).json()}
    assert cots["VT38"]["canhBaoMuc"] is None


async def test_sinh_chiet_tinh_r08(client, H):
    assert (await client.post("/api/qaqc/sinh-chiet-tinh", headers=H["ketoan"])).status_code == 403
    r = await client.post("/api/qaqc/sinh-chiet-tinh", headers=H["kythuat"])
    assert r.status_code == 200 and r.headers["content-type"] == DOCX
    t = doc_text(r.content)
    assert "BẢNG CHIẾT TÍNH KHỐI LƯỢNG HỐ MÓNG" in t and "VT 46" in t and "VT 47" in t and "MT-8a-20-3,7" in t and "142,7" in t
    assert not any(v["ma"] == "R08" for v in await vi_pham(client, H))                                  # đã kèm chiết tính
    assert (await client.post("/api/qaqc/sinh-chiet-tinh", headers=H["kythuat"])).status_code == 409


async def test_nhac_ky_thuat_tao_thong_bao_cho_tung_nguoi(client, H):
    g = next(v for v in await vi_pham(client, H) if v["ma"] == "R11")
    assert (await client.post(f"/api/dot-giao-hang/{g['doiTuongId']}/nhac", headers=H["ketoan"])).status_code == 403
    assert (await client.post(f"/api/dot-giao-hang/{g['doiTuongId']}/nhac", headers=H["chihuytruong"])).status_code == 200
    for who in ("kythuat", "tam"):
        d = (await client.get("/api/thong-bao", headers=H[who])).json()
        assert any(n["tieuDe"].startswith("Bổ sung ảnh phương tiện giao hàng · PO-0388 đợt 2") for n in d["items"]), who
    assert not any("PO-0388" in n["tieuDe"] for n in (await client.get("/api/thong-bao", headers=H["chutich"])).json()["items"])  # chỉ gửi cho Kỹ thuật
    await client.post("/api/thong-bao/doc-tat-ca", headers=H["kythuat"])
    assert (await client.get("/api/thong-bao", headers=H["kythuat"])).json()["chuaDoc"] == 0


async def test_doi_soat_tao_phieu_xu_ly_va_xac_nhan(client, H):
    hm = {h["ten"]: h for h in (await client.get("/api/doi-soat/hang-muc", headers=H["kehoach"])).json()}
    d = (await client.get(f"/api/doi-soat/hang-muc/{hm['Chuỗi néo 22 kV']['id']}", headers=H["kehoach"])).json()
    rows = {r["thongSo"]: r for r in d["rows"]}
    lech, khop, thieu = rows["Loại bát sứ chuỗi néo"], rows["Số bát sứ mỗi chuỗi"], rows["Chuỗi đỡ lèo"]
    assert (await client.post(f"/api/doi-soat/{lech['id']}/tao-phieu", headers=H["ketoan"])).status_code == 403
    assert (await client.post(f"/api/doi-soat/{khop['id']}/tao-phieu", headers=H["kythuat"])).status_code == 409      # khớp thì không cần phiếu
    r = await client.post(f"/api/doi-soat/{lech['id']}/tao-phieu", headers=H["kythuat"])
    assert r.status_code == 201 and r.json()["quyetDinh"] == "da_tao_phieu" and r.json()["phieu"]["ma"].startswith("PĐC-")
    assert (await client.post(f"/api/doi-soat/{lech['id']}/tao-phieu", headers=H["kythuat"])).status_code == 409      # đã có quyết định
    ph = next(p for p in (await client.get("/api/phieu-dieu-chinh", headers=H["kythuat"])).json() if p["ma"] == r.json()["phieu"]["ma"])
    assert ph["tieuDe"] == "Xử lý đối soát · Loại bát sứ chuỗi néo" and "loại 210" in ph["lyDo"]
    ps = await client.post(f"/api/doi-soat/{thieu['id']}/tao-phieu", headers=H["kythuat"])
    assert ps.status_code == 201
    p2 = next(p for p in (await client.get("/api/phieu-dieu-chinh", headers=H["kythuat"])).json() if p["ma"] == ps.json()["phieu"]["ma"])
    assert p2["tieuDe"] == "Phát sinh · Chuỗi đỡ lèo"
    # xác nhận một dòng khớp (R24: người có thẩm quyền xác nhận); người không có quyền bị từ chối
    assert (await client.post(f"/api/doi-soat/{khop['id']}/quyet-dinh", headers=H["ketoan"], json={"quyetDinh": "chap_nhan"})).status_code == 403
    assert (await client.post(f"/api/doi-soat/{khop['id']}/quyet-dinh", headers=H["kythuat"], json={"quyetDinh": "da_tao_phieu"})).status_code == 422
    ok = await client.post(f"/api/doi-soat/{khop['id']}/quyet-dinh", headers=H["kythuat"], json={"quyetDinh": "chap_nhan"})
    assert ok.status_code == 200 and ok.json()["quyetDinh"] == "chap_nhan"
    hm2 = {h["ten"]: h for h in (await client.get("/api/doi-soat/hang-muc", headers=H["kehoach"])).json()}
    assert hm2["Chuỗi néo 22 kV"]["soCanXuLy"] == 0


async def test_duyet_voi_ghi_chu_va_tra_lai(client, H):
    dx = next(d for d in (await client.get("/api/de-xuat-vat-tu", headers=H["kehoach"])).json() if d["ma"] == "ĐX-0413")
    assert (await client.post(f"/api/duyet/de_xuat/{dx['id']}", headers=H["kehoach"], json={"quyetDinh": "duyet"})).status_code == 403   # đang ở CHT
    r = await client.post(f"/api/duyet/de_xuat/{dx['id']}", headers=H["chihuytruong"], json={"quyetDinh": "duyet", "lyDo": "Đồng ý, đủ tồn kho"})
    assert r.status_code == 200 and r.json()["buocHienTai"] == "Bước 3/5 – Phòng Kế hoạch"
    now = next(d for d in (await client.get("/api/de-xuat-vat-tu", headers=H["kehoach"])).json() if d["ma"] == "ĐX-0413")
    assert now["chuoiDuyet"][1]["lyDo"] == "Đồng ý, đủ tồn kho" and now["coTheDuyet"] is True and now["vaiTroTiep"] == "PGĐ"
    assert (await client.post(f"/api/duyet/de_xuat/{dx['id']}", headers=H["kehoach"], json={"quyetDinh": "tu_choi"})).status_code == 422   # trả lại phải có lý do
    tra = await client.post(f"/api/duyet/de_xuat/{dx['id']}", headers=H["kehoach"], json={"quyetDinh": "tu_choi", "lyDo": "Thiếu bảng kê"})
    assert tra.status_code == 200 and tra.json()["trangThai"] == "tu_choi"


async def test_sinh_bien_ban_hang_loat_gop_theo_doan_ngay(client, H):
    assert (await client.post("/api/qaqc/sinh-bien-ban", headers=H["ketoan"], json=KHOANG)).status_code == 403
    xt = (await client.get("/api/qaqc/sinh-bien-ban/xem-truoc", params={**KHOANG, "gop": "doan_ngay"}, headers=H["kythuat"])).json()
    soBB = xt["bienBan"]
    assert soBB >= 1
    r = await client.post("/api/qaqc/sinh-bien-ban", headers=H["kythuat"], json={**KHOANG, "gop": "doan_ngay"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip" and int(r.headers["x-so-bien-ban"]) == soBB
    z = zipfile.ZipFile(io.BytesIO(r.content))
    ten = z.namelist()
    assert len(ten) == 3 * soBB and len({n.split("_")[0] for n in ten}) == 3 * soBB                   # mỗi biên bản kèm giấy mời + chiết tính, số không trùng
    assert sum(n.startswith("BB-NT-") for n in ten) == soBB and sum(n.startswith("GM-NT-") for n in ten) == soBB and sum(n.startswith("CT-") for n in ten) == soBB
    textbb = [doc_text(z.read(n)) for n in ten if n.startswith("BB-NT-")]
    t = next(x for x in textbb if "Dựng cột" in x and "VT 39–40" in x)                                 # gộp VT39–40 cùng ngày dựng cột
    assert "VT 39" in t and "VT 40" in t and "Km 2+" in t and "{{" not in t and any("VT-39-40" in n for n in ten)
    ct = doc_text(z.read(next(n for n in ten if n.startswith("CT-"))))
    assert "BẢNG CHIẾT TÍNH" in ct and "Tổng khối lượng" in ct
    gm = doc_text(z.read(next(n for n in ten if n.startswith("GM-NT-"))))
    assert "GIẤY MỜI NGHIỆM THU" in gm and "{{" not in gm
    # sau khi sinh: hết công tác sẵn sàng (chỉ còn bị chặn), không phát hành trùng
    sau = (await client.get("/api/qaqc/sinh-bien-ban/xem-truoc", params=KHOANG, headers=H["kythuat"])).json()
    assert sau["bienBan"] == 0 and sau["sanSang"] == xt["biChan"]["n"]
    again = await client.post("/api/qaqc/sinh-bien-ban", headers=H["kythuat"], json=KHOANG)
    assert again.status_code == 409
    ds = (await client.get("/api/bien-ban", headers=H["kythuat"])).json()
    assert {b["loai"] for b in ds} >= {"nghiem_thu_cong_viec", "giay_moi_nghiem_thu", "bang_chiet_tinh"}
    one = next(b for b in ds if b["loai"] == "nghiem_thu_cong_viec" and len(b["congTacIds"]) > 1)
    dl = await client.get(f"/api/bien-ban/{one['id']}/tai-ve", headers=H["kythuat"])
    assert dl.status_code == 200 and re.match(r"BB-NT-\d{4}-\d{4}", one["so"])
    d = (await client.get("/api/qaqc/tong-quan", params=KHOANG, headers=H["kythuat"])).json()
    assert d["thongKe"]["bienBanSanSang"]["n"] == xt["biChan"]["n"]                                    # chỉ còn công tác bị chặn


async def test_sinh_bien_ban_hang_loat_theo_tung_vi_tri_khi_khong_con_gi(client, H):
    r = await client.post("/api/qaqc/sinh-bien-ban", headers=H["kythuat"], json={**KHOANG, "gop": "vi_tri"})
    assert r.status_code == 409 and "Không có công tác nào" in r.json()["detail"]
    assert (await client.post("/api/qaqc/sinh-bien-ban", headers=H["kythuat"], json={"tu": "2026-10-14", "den": "2026-10-07"})).status_code == 422
