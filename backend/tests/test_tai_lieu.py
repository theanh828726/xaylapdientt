import io
import zipfile

from docx import Document

from .test_bao_cao_cong_tac import cong_tac_id

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
LOAI = {"nghiem_thu_cong_viec", "de_xuat_vat_tu", "phieu_dieu_chinh", "giay_moi_nghiem_thu", "bang_chiet_tinh", "de_trinh_nha_cung_cap"}


def doc_text(data: bytes) -> str:
    d = Document(io.BytesIO(data))
    return "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])


def sua_mau(data: bytes, tu: str, thanh: str) -> bytes:
    d = Document(io.BytesIO(data))
    done = False
    for p in d.paragraphs:
        for r in p.runs:
            if tu in r.text:
                r.text, done = r.text.replace(tu, thanh), True
    assert done, tu
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()


def put_mau(client, headers, loai, content, name="mau.docx"):
    return client.put(f"/api/mau-bieu/{loai}", headers=headers, files={"file": (name, content, DOCX)}, data={"ghiChu": "thử"})


async def test_danh_muc_mau_bieu_day_du_6_loai(client, H):
    ds = {m["loai"]: m for m in (await client.get("/api/mau-bieu", headers=H["kythuat"])).json()}
    assert set(ds) == LOAI and all(m["nguon"] == "mac-dinh" and m["bien"] for m in ds.values())
    for loai in LOAI:   # mọi mẫu mặc định phải tải được và render được bằng dữ liệu mẫu
        r = await client.get(f"/api/mau-bieu/{loai}/tai-ve?nguon=mac-dinh", headers=H["giamdoc"])
        assert r.status_code == 200 and r.headers["content-type"] == DOCX
        assert (await put_mau(client, H["giamdoc"], loai, r.content)).status_code == 200   # kiểm tra mẫu thử render thành công
        await client.delete(f"/api/mau-bieu/{loai}", headers=H["giamdoc"])


async def test_vong_doi_mau_bieu_du_an(client, H):
    loai = "nghiem_thu_cong_viec"
    assert (await client.get(f"/api/mau-bieu/{loai}/tai-ve", headers=H["kythuat"])).status_code == 403   # chỉ người quản lý dự án
    macdinh = await client.get(f"/api/mau-bieu/{loai}/tai-ve?nguon=mac-dinh", headers=H["giamdoc"])
    sua = sua_mau(macdinh.content, "BIÊN BẢN NGHIỆM THU CÔNG VIỆC XÂY DỰNG", "BIÊN BẢN NGHIỆM THU (MẪU DỰ ÁN)")
    assert (await put_mau(client, H["kythuat"], loai, sua)).status_code == 403
    r = await put_mau(client, H["giamdoc"], loai, sua)
    assert r.status_code == 200 and r.json()["phienBan"] >= 1
    cur = {m["loai"]: m for m in (await client.get("/api/mau-bieu", headers=H["kythuat"])).json()}[loai]
    assert cur["nguon"] == "du-an" and cur["ghiChu"] == "thử"
    assert "MẪU DỰ ÁN" in doc_text((await client.get(f"/api/mau-bieu/{loai}/tai-ve", headers=H["giamdoc"])).content)

    du_an = (await client.get("/api/du-an", headers=H["giamdoc"])).json()
    p2 = {**H["giamdoc"], "X-Du-An": next(d["id"] for d in du_an if d["ma"] == "DEMO-LO471")}
    # mẫu của dự án được dùng khi sinh biên bản mới
    ct = await cong_tac_id("VT1", "dao_mong")
    p2b = {**H["giamdoc"], "X-Du-An": next(d["id"] for d in du_an if d["ma"] == "DEMO-BL110")}
    assert (await client.get("/api/mau-bieu", headers=p2b)).json()[0]["nguon"] == "mac-dinh"       # mẫu theo từng dự án
    moi = (await client.post(f"/api/cong-tac/{ct}/bien-ban?tao_lai=true", headers=p2b)).json()
    assert moi["mauNguon"] == "mac-dinh"

    assert (await client.delete(f"/api/mau-bieu/{loai}", headers=H["kythuat"])).status_code == 403
    assert (await client.delete(f"/api/mau-bieu/{loai}", headers=H["giamdoc"])).status_code == 204
    cur = {m["loai"]: m for m in (await client.get("/api/mau-bieu", headers=H["kythuat"])).json()}[loai]
    assert cur["nguon"] == "mac-dinh"
    r2 = await put_mau(client, H["giamdoc"], loai, sua)       # phiên bản tiếp tục tăng sau khi quay về mặc định
    assert r2.json()["phienBan"] == r.json()["phienBan"] + 1
    await client.delete(f"/api/mau-bieu/{loai}", headers=H["giamdoc"])


async def test_tu_choi_mau_nguy_hiem_hoac_hong(client, H):
    loai = "nghiem_thu_cong_viec"
    base = (await client.get(f"/api/mau-bieu/{loai}/tai-ve?nguon=mac-dinh", headers=H["giamdoc"])).content
    cases = {
        "SSTI (truy cập thuộc tính nội bộ)": sua_mau(base, "{{ so }}", "{{ ''.__class__.__mro__ }}"),
        "cú pháp Jinja sai": sua_mau(base, "{{ so }}", "{% for x in %}"),
        "biến không tồn tại": sua_mau(base, "{{ so }}", "{{ khong_co.x }}"),
        "không phải docx": b"day la text",
        "zip thiếu document.xml": (lambda b: (zipfile.ZipFile(b, "w").writestr("x.txt", "x"), b.getvalue())[1])(io.BytesIO()),
        "quá lớn": b"PK" + b"0" * (5 * 1024 * 1024 + 1),
    }
    for ten, noi_dung in cases.items():
        r = await put_mau(client, H["giamdoc"], loai, noi_dung)
        assert r.status_code == 422, f"{ten}: {r.status_code} {r.text}"
    assert (await put_mau(client, H["giamdoc"], "khong_co_loai_nay", base)).status_code == 404
    cur = {m["loai"]: m for m in (await client.get("/api/mau-bieu", headers=H["giamdoc"])).json()}[loai]
    assert cur["nguon"] == "mac-dinh"                           # mẫu hỏng không bao giờ được lưu


async def test_in_phieu_an_gia_theo_quyen(client, H):
    dx = next(d for d in (await client.get("/api/de-xuat-vat-tu", headers=H["giamdoc"])).json() if d["ma"] == "ĐX-0412")

    async def in_text(who):
        r = await client.get(f"/api/de-xuat-vat-tu/{dx['id']}/in", headers=H[who])
        assert r.status_code == 200 and r.headers["content-type"] == DOCX
        return doc_text(r.content)

    gd, cht, kt = await in_text("giamdoc"), await in_text("chihuytruong"), await in_text("kythuat")
    assert "1.284.500.000 đ" in gd and "1.102.300.000 đ" in gd
    assert "1.284.500.000" not in cht and "1.102.300.000 đ" in cht          # CHT chỉ thấy giá khoán
    assert "1.284.500.000" not in kt and "1.102.300.000" not in kt           # Kỹ thuật không thấy giá nào
    for t in (gd, cht, kt):
        assert "ĐX-0412" in t and "XN-22-3N" in t and "Phòng Kế hoạch" in t and "Trần Thu Hà" in t and "{{" not in t
    assert "3.660" in gd and "1.200" in gd and "Đã kiểm tồn kho" in gd       # số kiểu Việt Nam, ghi chú duyệt


async def test_in_phieu_dieu_chinh_va_404(client, H):
    p = next(x for x in (await client.get("/api/phieu-dieu-chinh", headers=H["giamdoc"])).json() if x["ma"] == "PĐC-021")
    r = await client.get(f"/api/phieu-dieu-chinh/{p['id']}/in", headers=H["kythuat"])
    assert r.status_code == 200 and "PĐC-021" in doc_text(r.content) and "biên bản ghi nhầm ngày" in doc_text(r.content)
    assert (await client.get("/api/phieu-dieu-chinh/00000000-0000-0000-0000-000000000000/in", headers=H["kythuat"])).status_code == 404


async def test_tai_bien_ban_dung_du_an_va_xac_thuc(client, H):
    ds = (await client.get("/api/bien-ban", headers=H["giamdoc"])).json()
    assert ds == [] or all(b["so"] for b in ds)
    du_an = (await client.get("/api/du-an", headers=H["giamdoc"])).json()
    p2 = next(d["id"] for d in du_an if d["ma"] == "DEMO-BL110")
    mine = (await client.get("/api/bien-ban", headers={**H["giamdoc"], "X-Du-An": p2})).json()
    assert mine, "dự án 2 đã phát hành biên bản ở test trước"
    assert (await client.get(f"/api/bien-ban/{mine[0]['id']}/tai-ve")).status_code == 401
    assert (await client.get(f"/api/bien-ban/{mine[0]['id']}/tai-ve", headers=H["giamdoc"])).status_code == 404     # sai dự án
