"""Kiểm thử an ninh theo cả hệ thống: mọi route đều đòi đăng nhập, mọi route có {id} đều cách ly theo dự án,
và người thiếu quyền không chạm được các thao tác quản trị. Thêm route mới thiếu xác thực hoặc thiếu lọc dự án sẽ làm test đỏ."""
import re
import uuid

import pytest
from sqlalchemy import select

CONG_KHAI = {"/api/auth/login", "/api/auth/refresh", "/api/auth/logout", "/api/health"}
BO_QUA_PREFIX = ("/api/docs", "/api/openapi", "/api/redoc")
ZERO = "00000000-0000-0000-0000-000000000000"


def _routes():
    """Mọi (phương thức, đường dẫn) của API, lấy từ lược đồ OpenAPI (không phụ thuộc cách FastAPI lưu route nội bộ)."""
    from app.main import app
    for p, ops in sorted(app.openapi()["paths"].items()):
        if p in CONG_KHAI or p.startswith(BO_QUA_PREFIX):
            continue
        for m in sorted(ops):
            if m.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                yield m.upper(), p


def _dien(path: str, **gia_tri) -> str:
    def thay(m):
        ten = m.group(1)
        if ten in gia_tri:
            return gia_tri[ten]
        return {"loai": "de_xuat", "vai_tro": "ky_thuat"}.get(ten, ZERO)
    return re.sub(r"\{(\w+)\}", thay, path)


async def test_moi_route_deu_doi_dang_nhap(client):
    cac_route = list(_routes())
    assert len(cac_route) >= 50                         # đảm bảo vòng lặp thực sự quét được route
    loi = []
    for m, p in cac_route:
        r = await client.request(m, _dien(p), json={} if m in {"POST", "PUT", "PATCH"} else None)
        if r.status_code != 401:
            loi.append(f"{m} {p} -> {r.status_code}")
    assert not loi, "Route không đòi đăng nhập:\n" + "\n".join(loi)


async def _id_du_an_1():
    """Gom id của một đối tượng thật ở dự án 1 cho mọi loại có {id} trong đường dẫn."""
    from app.db import SessionLocal
    from app.models import (AnhHienTruong, BaoCaoHienTruong, BienBan, CongTac, DeXuatVatTu, DoiSoat, DoiSoatHangMuc,
                            DotGiaoHang, DuAn, LoVatLieu, PhieuDieuChinh, ViTriCot)
    async with SessionLocal() as s:
        da = await s.scalar(select(DuAn.id).where(DuAn.ma == "DEMO-LO471"))
        d = {}
        for ten, model in [("vt_id", ViTriCot), ("ct_id", CongTac), ("lo_id", LoVatLieu), ("bb_id", BienBan), ("hm_id", DoiSoatHangMuc),
                           ("item_id", DeXuatVatTu), ("bao_cao_id", BaoCaoHienTruong), ("anh_id", AnhHienTruong)]:
            d[ten] = await s.scalar(select(model.id).where(model.du_an_id == da).limit(1))
        d["doi_soat_id"] = await s.scalar(select(DoiSoat.id).where(DoiSoat.du_an_id == da).limit(1))
        d["phieu_id"] = await s.scalar(select(PhieuDieuChinh.id).where(PhieuDieuChinh.du_an_id == da).limit(1))
        d["giao_id"] = await s.scalar(select(DotGiaoHang.id).where(DotGiaoHang.du_an_id == da).limit(1))
        return {k: str(v) for k, v in d.items() if v is not None}


async def _du_an_2(client, H):
    return next(d["id"] for d in (await client.get("/api/du-an", headers=H["giamdoc"])).json() if d["ma"] == "DEMO-BL110")


def _gia_tri_theo_duong_dan(path: str, id_: dict) -> str | None:
    """Chọn id thật của dự án 1 cho từng tham số; trả None nếu chưa có dữ liệu loại đó (bỏ qua route)."""
    def thay(m):
        ten = m.group(1)
        if ten == "item_id":
            if "/doi-soat/" in path:
                return id_.get("doi_soat_id", ZERO)
            if "/dot-giao-hang/" in path:
                return id_.get("giao_id", ZERO)
            if "/phieu-dieu-chinh/" in path or path.startswith("/api/duyet/"):
                return id_.get("phieu_id", ZERO)
            return id_.get("item_id", ZERO)
        return id_.get(ten, {"loai": "de_xuat", "vai_tro": "ky_thuat"}.get(ten, ZERO))
    return re.sub(r"\{(\w+)\}", thay, path)


THAM_SO_DOI_TUONG = ("vt_id", "ct_id", "lo_id", "bb_id", "hm_id", "item_id", "bao_cao_id", "anh_id")


async def test_moi_route_co_id_cach_ly_theo_du_an(client, H):
    """Dùng id thật của dự án 1 nhưng gửi X-Du-An = dự án 2 (giám đốc thuộc cả hai): không được thành công."""
    id_ = await _id_du_an_1()
    p2 = await _du_an_2(client, H)
    h2 = {**H["giamdoc"], "X-Du-An": p2}
    da_thu, ro_ri = 0, []
    for m, p in _routes():
        if not any("{" + t + "}" in p for t in THAM_SO_DOI_TUONG):
            continue
        duong = _gia_tri_theo_duong_dan(p, id_)
        if duong is None:
            continue
        r = await client.request(m, duong, headers=h2, json={"quyetDinh": "duyet"} if m == "POST" else None)
        da_thu += 1
        if 200 <= r.status_code < 300:
            ro_ri.append(f"{m} {p} -> {r.status_code}")
    assert da_thu >= 20
    assert not ro_ri, "Đối tượng của dự án khác vẫn truy cập được:\n" + "\n".join(ro_ri)


async def test_nguoi_khong_thuoc_du_an_bi_chan_o_moi_route(client, H):
    """Tổ đội trưởng chỉ thuộc dự án 1 gửi X-Du-An = dự án 2: mọi route có phạm vi dự án phải 403."""
    p2 = await _du_an_2(client, H)
    h = {**H["khoa"], "X-Du-An": p2}
    mien = {"/api/auth/me", "/api/du-an", "/api/phan-quyen", "/api/nguoi-dung"}
    sai = []
    for m, p in _routes():
        if p in mien or "/phan-quyen" in p or "/nguoi-dung" in p or p.startswith("/api/mau-bieu"):
            continue
        r = await client.request(m, _dien(p), headers=h, json={} if m in {"POST", "PUT", "PATCH"} else None)
        if r.status_code not in (403, 422):     # 422: lỗi tham số được báo trước khi kiểm tra dự án; vẫn không rò dữ liệu
            sai.append(f"{m} {p} -> {r.status_code}")
    assert not sai, "Người ngoài dự án không bị chặn:\n" + "\n".join(sai)


QUAN_TRI = [
    ("PUT", "/api/phan-quyen/ky_thuat", {"quyen": []}),
    ("PATCH", f"/api/nguoi-dung/{ZERO}", {"active": False}),
    ("POST", "/api/du-an", {"ma": "X", "ten": "X"}),
    ("PUT", "/api/mau-bieu/bien_ban_nghiem_thu", None),
    ("DELETE", "/api/mau-bieu/bien_ban_nghiem_thu", None),
]


@pytest.mark.parametrize("who", ["son", "khoa", "ketoan", "kythuat", "chihuytruong"])
@pytest.mark.parametrize("m,p,body", QUAN_TRI)
async def test_thao_tac_quan_tri_can_quyen(client, H, who, m, p, body):
    r = await client.request(m, p, headers=H[who], json=body)
    assert r.status_code in (403, 404, 422) and r.status_code != 200, f"{who} {m} {p} -> {r.status_code}"
    assert r.status_code != 404 or "mau-bieu" in p      # 404 chỉ chấp nhận khi loại mẫu không tồn tại


async def test_ketoan_khong_duyet_duoc(client, H):
    id_ = await _id_du_an_1()
    r = await client.post(f"/api/duyet/de_xuat/{id_['item_id']}", headers=H["ketoan"], json={"quyetDinh": "duyet"})
    assert r.status_code == 403


async def test_token_gia_hoac_het_han_bi_tu_choi(client):
    for tok in ["abc", "Bearer.x.y", "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0."]:      # cả token thuật toán "none"
        r = await client.get("/api/vi-tri-cot", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 401, tok
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    het_han = pyjwt.encode({"sub": str(uuid.uuid4()), "typ": "access", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                           settings.jwt_secret, algorithm="HS256")
    assert (await client.get("/api/vi-tri-cot", headers={"Authorization": f"Bearer {het_han}"})).status_code == 401
    refresh_dung_lam_access = pyjwt.encode({"sub": str(uuid.uuid4()), "typ": "refresh", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                                           settings.jwt_secret, algorithm="HS256")
    assert (await client.get("/api/vi-tri-cot", headers={"Authorization": f"Bearer {refresh_dung_lam_access}"})).status_code == 401
