import io
import zipfile

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
  <Placemark><name>Tuyến thử KMZ</name><LineString><coordinates>
    106.5000,10.7000,0 106.5100,10.7050,0 106.5200,10.7100,0</coordinates></LineString></Placemark>
  <Placemark><name>vt 1</name><Point><coordinates>106.5000,10.7000,0</coordinates></Point></Placemark>
  <Placemark><name>VT-2</name><Point><coordinates>106.5100,10.7050,0</coordinates></Point></Placemark>
  <Placemark><name>VT999</name><Point><coordinates>106.5200,10.7100,0</coordinates></Point></Placemark>
</Document></kml>"""


def kmz(kml: str, name: str = "doc.kml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, kml)
    return buf.getvalue()


async def p2(client, H):
    du_an = (await client.get("/api/du-an", headers=H["giamdoc"])).json()
    return {**H["giamdoc"], "X-Du-An": next(d["id"] for d in du_an if d["ma"] == "DEMO-BL110")}


def up(client, headers, content, name="tuyen.kmz"):
    return client.post("/api/ban-do/import-kmz", headers=headers, files={"file": (name, content)})


async def test_import_kmz_cap_nhat_toa_do_va_thay_the_tuyen_kmz(client, H):
    h = await p2(client, H)
    for _ in range(2):  # nhập hai lần: tuyến KMZ cũ bị thay, không nhân đôi
        r = await up(client, h, kmz(KML))
        assert r.status_code == 200, r.text
        assert r.json() == {"tuyen": 1, "cotCapNhat": 2, "khongKhop": ["VT999"]}
    fc = (await client.get("/api/ban-do/geojson", headers=h)).json()
    tuyen = [f for f in fc["features"] if f["properties"]["loai"] == "tuyen"]
    assert sorted(f["properties"]["nguon"] for f in tuyen) == ["demo", "kmz"]
    cot = {f["properties"]["ten"]: f["geometry"]["coordinates"] for f in fc["features"] if f["properties"]["loai"] == "cot"}
    assert cot["VT1"] == [106.5, 10.7] and cot["VT2"] == [106.51, 10.705]
    ds = (await client.get("/api/vi-tri-cot", headers=h)).json()
    assert len(ds) == 6 and {c["ten"]: (c["lon"], c["lat"]) for c in ds}["VT1"] == (106.5, 10.7)   # toạ độ lấy từ KMZ


async def test_import_kml_thuong_khong_nen_zip(client, H):
    r = await up(client, await p2(client, H), KML.encode(), "tuyen.kml")
    assert r.status_code == 200 and r.json()["cotCapNhat"] == 2


async def test_import_can_quyen(client, H):
    h = {**H["kythuat"]}
    assert (await up(client, h, kmz(KML))).status_code == 403


async def test_import_tu_choi_file_xau(client, H):
    h = await p2(client, H)
    assert (await up(client, h, b"khong phai kmz")).status_code == 422
    assert (await up(client, h, b"PK\x03\x04hong")).status_code == 422
    assert (await up(client, h, kmz("<kml/>", "readme.txt"))).status_code == 422          # không có .kml
    assert (await up(client, h, kmz("<kml><Document/></kml>"))).status_code == 422         # không có hình học
    bad = KML.replace("106.5000,10.7000,0 106.5100", "999,10.7,0 106.5100")
    assert (await up(client, h, kmz(bad))).status_code == 422                               # lon ngoài phạm vi
    bomb = '<?xml version="1.0"?><!DOCTYPE k [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><kml>&b;</kml>'
    assert (await up(client, h, kmz(bomb))).status_code == 422                              # entity/DTD bị cấm
    big = b"PK" + b"0" * (20 * 1024 * 1024 + 1)
    assert (await up(client, h, big)).status_code == 413


async def test_import_khong_dong_cham_du_an_khac(client, H):
    before = (await client.get("/api/ban-do/geojson", headers=H["giamdoc"])).json()
    await up(client, await p2(client, H), kmz(KML))
    after = (await client.get("/api/ban-do/geojson", headers=H["giamdoc"])).json()
    assert before == after
