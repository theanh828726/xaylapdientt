import struct
import zlib

from .conftest import new_id


def png(w=2, h=2) -> bytes:
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


async def tao_bao_cao(client, H, who="khoa", vi_tri="VT46"):
    r = await client.post("/api/bao-cao-hien-truong", headers=H[who], json={"viTri": vi_tri, "noiDung": "Báo cáo thử ảnh"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def up(client, headers, bc, content, name="a.png", **form):
    return client.post(f"/api/bao-cao-hien-truong/{bc}/anh", headers=headers, files={"file": (name, content)}, data=form)


async def test_tai_anh_len_va_tai_ve_dung_noi_dung(client, H):
    bc = await tao_bao_cao(client, H)
    data = png()
    r = await up(client, H["khoa"], bc, data, lat="10.6453", lon="106.5118", chupLuc="2026-10-14T08:00:00+07:00")
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["mime"] == "image/png" and a["kichThuoc"] == len(data) and a["lat"] == 10.6453
    dl = await client.get(f"/api/anh/{a['id']}", headers=H["khoa"])
    assert dl.status_code == 200 and dl.content == data and dl.headers["content-type"] == "image/png"
    assert dl.headers["x-content-type-options"] == "nosniff"
    ds = (await client.get(f"/api/bao-cao-hien-truong/{bc}/anh", headers=H["khoa"])).json()
    assert [x["id"] for x in ds] == [a["id"]]
    lst = (await client.get("/api/bao-cao-hien-truong", headers=H["khoa"])).json()
    assert next(b for b in lst if b["id"] == bc)["anh"] == 1          # số ảnh = khai báo (0) + đã tải lên (1)


async def test_idempotent_theo_client_id(client, H):
    bc = await tao_bao_cao(client, H)
    cid = new_id()
    a = await up(client, H["khoa"], bc, png(), clientId=cid)
    b = await up(client, H["khoa"], bc, png(), clientId=cid)
    assert a.status_code == 201 and b.status_code == 200 and a.json()["id"] == b.json()["id"]
    assert len((await client.get(f"/api/bao-cao-hien-truong/{bc}/anh", headers=H["khoa"])).json()) == 1
    bc2 = await tao_bao_cao(client, H, "son", "VT44")
    assert (await up(client, H["son"], bc2, png(), clientId=cid)).status_code == 409   # clientId không chiếm được


async def test_chi_nguoi_lap_hoac_quan_ly_duoc_them_anh(client, H):
    bc = await tao_bao_cao(client, H, "khoa")
    assert (await up(client, H["son"], bc, png())).status_code == 403
    assert (await up(client, H["ketoan"], bc, png())).status_code == 403
    assert (await up(client, H["giamdoc"], bc, png())).status_code == 201


async def test_tu_choi_file_khong_phai_anh(client, H):
    bc = await tao_bao_cao(client, H)
    assert (await up(client, H["khoa"], bc, b"day la van ban", "a.jpg")).status_code == 422    # đuôi .jpg nhưng nội dung không phải ảnh
    assert (await up(client, H["khoa"], bc, b"<svg onload=alert(1)></svg>", "a.svg")).status_code == 422
    assert (await up(client, H["khoa"], bc, png(), lat="123")).status_code == 422
    assert (await up(client, H["khoa"], bc, png(), chupLuc="2999-01-01T00:00:00+00:00")).status_code == 422
    assert (await up(client, H["khoa"], bc, png() + b"0" * (10 * 1024 * 1024))).status_code == 413


async def test_gioi_han_so_anh_moi_bao_cao(client, H):
    bc = await tao_bao_cao(client, H)
    for _ in range(30):
        assert (await up(client, H["khoa"], bc, png())).status_code == 201
    assert (await up(client, H["khoa"], bc, png())).status_code == 422


async def test_cach_ly_du_an_va_xac_thuc(client, H):
    bc = await tao_bao_cao(client, H)
    a = (await up(client, H["khoa"], bc, png())).json()
    p2 = next(d["id"] for d in (await client.get("/api/du-an", headers=H["giamdoc"])).json() if d["ma"] == "DEMO-BL110")
    assert (await client.get(f"/api/anh/{a['id']}", headers={**H["giamdoc"], "X-Du-An": p2})).status_code == 404
    assert (await client.get(f"/api/anh/{a['id']}")).status_code == 401
    assert (await client.get(f"/api/anh/{new_id()}", headers=H["khoa"])).status_code == 404
