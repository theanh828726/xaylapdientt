import json
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from geoalchemy2 import WKTElement
from sqlalchemy import cast, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography

from ..db import get_session
from ..deps import Ctx, access
from ..models import (AnhHienTruong, BaoCaoHienTruong, CongTac, CongTacMa, CongTacTT, Kho, LoVatLieu, MaCauKien, MauBeTong,
                      Tuyen, VatTuViTri, ViTriCot)
from ..rbac import P
from ..schemas import KhoOut, MaCauKienOut
from ..services import audit, kmz, rules
from ..services import cong_tac as ct
from ..services.format import ngay_gio

router = APIRouter(tags=["cot-ban-do-kho"])
MUC_CHAN = "Chặn"


async def _nap(s: AsyncSession, ctx: Ctx):
    """Dữ liệu dùng chung cho danh sách/chi tiết vị trí: công tác theo cột và các vi phạm (đã lọc theo quyền)."""
    cts = (await s.scalars(select(CongTac).where(CongTac.du_an_id == ctx.du_an_id))).all()
    theo_cot: dict[uuid.UUID, dict[CongTacMa, CongTac]] = defaultdict(dict)
    for c in cts:
        theo_cot[c.vi_tri_id][c.ma] = c
    vp = rules.loc_theo_quyen(await rules.danh_gia(s, ctx.du_an_id), ctx.perms)
    theo_ten: dict[str, list[rules.ViPham]] = defaultdict(list)
    for v in vp:
        if v.vi_tri:
            theo_ten[v.vi_tri].append(v)
    return theo_cot, theo_ten


def _canh_bao_cot(vps: list[rules.ViPham]) -> tuple[str | None, list[str]]:
    """Mức cảnh báo cao nhất và danh sách câu cảnh báo của một cột (bỏ R02 là trạng thái chờ; bỏ trùng)."""
    ds, thay = [], set()
    for v in vps:
        if v.ma == "R02" or (v.ma, v.thong_bao) in thay:
            continue
        thay.add((v.ma, v.thong_bao))
        ds.append(v)
    if not ds:
        return None, []
    muc = "chan" if any(v.muc == MUC_CHAN for v in ds) else "canh_bao"
    return muc, [f"{v.ma}: {v.thong_bao}" for v in ds]


@router.get("/vi-tri-cot")
async def list_vi_tri_cot(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(ViTriCot, func.ST_X(ViTriCot.geom), func.ST_Y(ViTriCot.geom), Tuyen.ma)
                            .outerjoin(Tuyen, Tuyen.id == ViTriCot.tuyen_id)
                            .where(ViTriCot.du_an_id == ctx.du_an_id).order_by(ViTriCot.km, ViTriCot.ten))).all()
    theo_cot, theo_ten = await _nap(s, ctx)
    out = []
    for c, lon, lat, tuyen_ma in rows:
        m = theo_cot.get(c.id, {})
        muc, cb = _canh_bao_cot(theo_ten.get(c.ten, []))
        buoc = ct.buoc_thi_cong(m)
        out.append({
            "id": str(c.id), "ten": c.ten, "km": float(c.km), "kmText": ct.km_text(c.km), "loaiMong": c.loai_mong,
            "kieuCot": c.kieu_cot, "buoc": buoc, "buocTen": ct.BUOC[buoc], "tienDo": ct.tien_do(m), "vuongGpmb": c.vuong_gpmb,
            "canhBaoMuc": muc, "canhBao": cb, "lon": lon, "lat": lat, "tuyenMa": tuyen_ma,
        })
    return out


def _lich_su(c: ViTriCot, m: dict[CongTacMa, CongTac], mau: list[MauBeTong]) -> list[dict]:
    han = {x.cong_tac_ma: x for x in mau if x.ket_qua_mpa is None}
    nhom = [[CongTacMa.dao_mong], [CongTacMa.bt_lot], [CongTacMa.thep_de], [CongTacMa.bt_mong], [CongTacMa.lap_mong],
            [CongTacMa.dung_cot, CongTacMa.xa_su, CongTacMa.keo_day]]
    out = []
    for g in nhom:
        x = m.get(g[0])
        d0 = ct.DEF[g[0]]
        if len(g) > 1:                                   # gộp "Dựng cột · lắp xà sứ · kéo dây"
            ten = "Dựng cột · lắp xà sứ · kéo dây"
            moc = [m[k] for k in g if k in m and m[k].trang_thai in ct.HOAN_THANH]
            x = moc[-1] if moc else m.get(g[0])
        else:
            ten = d0.ten_dai
        st, nhan, ngay = "chua", "—", None
        sub = (x.ghi_chu if x and x.ghi_chu else "") or ""
        if x is not None:
            if x.trang_thai == CongTacTT.da_nghiem_thu:
                st, nhan, ngay = "xong", f"NT {ct.dm(x.ngay_nghiem_thu)}", ct.dm(x.ngay_hoan_thanh)
            elif x.trang_thai == CongTacTT.cho_nghiem_thu:
                mau_x = han.get(x.ma)
                st, nhan, ngay = "dang", f"Chờ {ct.dm(mau_x.han_nen)}" if mau_x else "Chờ NT", ct.dm(x.ngay_hoan_thanh)
            elif x.trang_thai == CongTacTT.dang_lam:
                st, nhan, ngay = "dang", "Đang làm", ct.dm(x.ngay_hoan_thanh)
            elif ct.gating_r02(m, x.ma):
                tq = ct.DEF[x.ma].tien_quyet
                st, sub = "chan", f"Bị chặn bởi R02 · cần NT {ct.DEF[tq].ten_dai.lower().replace('bê tông đúc móng m150', 'bê tông móng')}"
        out.append({"ma": g[0].value, "ten": ten, "ghiChu": sub, "ngay": ngay, "nhan": nhan, "trangThai": st})
    return out


def _ho_so(m: dict[CongTacMa, CongTac]) -> dict:
    def xong(ma: CongTacMa) -> bool:
        return ma in m and m[ma].trang_thai == CongTacTT.da_nghiem_thu

    muc = [{"ten": f"Biên bản nghiệm thu {ct.DEF[ma].ten.lower()}", "ok": xong(ma) and m[ma].da_co_bien_ban} for ma in ct.MONG]
    muc += [{"ten": "Kết quả thí nghiệm xi măng", "ok": xong(CongTacMa.bt_lot)},
            {"ten": "Kết quả kéo thép", "ok": xong(CongTacMa.thep_de)},
            {"ten": "Kết quả nén mẫu bê tông", "ok": xong(CongTacMa.bt_mong)},
            {"ten": "Bảng chiết tính móng", "ok": CongTacMa.dao_mong in m and m[CongTacMa.dao_mong].co_chiet_tinh}]
    return {"dat": sum(1 for x in muc if x["ok"]), "tong": len(muc), "muc": muc}


@router.get("/vi-tri-cot/{vt_id}")
async def chi_tiet_vi_tri(vt_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    c = await s.scalar(select(ViTriCot).where(ViTriCot.id == vt_id, ViTriCot.du_an_id == ctx.du_an_id))
    if c is None:
        raise HTTPException(404, "Không tìm thấy vị trí cột")
    theo_cot, theo_ten = await _nap(s, ctx)
    m = theo_cot.get(c.id, {})
    mau = (await s.scalars(select(MauBeTong).where(MauBeTong.vi_tri_id == c.id).order_by(MauBeTong.han_nen))).all()
    vt = (await s.scalars(select(VatTuViTri).where(VatTuViTri.vi_tri_id == c.id).order_by(VatTuViTri.thu_tu))).all()
    tuyen = await s.get(Tuyen, c.tuyen_id) if c.tuyen_id else None
    bc = (await s.scalars(select(BaoCaoHienTruong).where(BaoCaoHienTruong.vi_tri_id == c.id))).all()
    so_tep = await s.scalar(select(func.count()).select_from(AnhHienTruong).where(AnhHienTruong.bao_cao_id.in_([b.id for b in bc]))) if bc else 0
    km0 = int(float(c.km))
    buoc = ct.buoc_thi_cong(m)
    chips = [{"text": ct.BUOC[buoc], "tone": "warn" if buoc == "dang_thi_cong_mong" else "ok" if buoc != "chua_thi_cong" else "idle"}]
    chua_nen = [x for x in mau if x.ket_qua_mpa is None]
    if chua_nen:
        chips.append({"text": f"Chờ kết quả nén {chua_nen[0].tuoi_ngay} ngày", "tone": "info"})
    if c.vuong_gpmb:
        chips.append({"text": "Vướng GPMB", "tone": "bad"})
    the = []
    for v in theo_ten.get(c.ten, []):
        if v.ma in ("R02", "R10") or any(x["ma"] == v.ma and x["thongBao"] == v.thong_bao for x in the):
            continue
        the.append({"ma": v.ma, "muc": v.muc, "thongBao": v.thong_bao, "chiTiet": v.chi_tiet})
    r10 = next((v for v in theo_ten.get(c.ten, []) if v.ma == "R10"), None)
    return {
        "id": str(c.id), "ten": c.ten, "kmText": ct.km_text(c.km), "kieuCot": c.kieu_cot,
        "tuyen": {"id": str(tuyen.id), "ma": tuyen.ma, "ten": tuyen.ten} if tuyen else None,
        "doan": f"Đoạn Km{km0} – Km{km0 + 1}", "chips": chips, "canhBao": the,
        "thietKe": {"cot": c.cot_ma, "cotNpc": c.cot_ma_npc, "mong": c.loai_mong, "xa": c.xa_ma, "tiepDia": c.tiep_dia_ma,
                    "capDat": f"{c.cap_dat} · K = {float(c.k):g}".replace(".", ",") if c.cap_dat else None,
                    "khoangCach": f"{float(c.khoang_truoc):g} m / {float(c.khoang_sau):g} m" if c.khoang_truoc and c.khoang_sau else None},
        "chietTinh": {**ct.tinh_mong(c), "ghiChu": f"Tính từ thư viện mã {c.loai_mong}"},
        "lichSu": _lich_su(c, m, mau),
        "vatTu": [{"ten": v.ten, "dvt": v.dvt, "dinhMuc": float(v.dinh_muc), "daCap": float(v.da_cap)} for v in vt],
        "nhacVatTu": r10.thong_bao if r10 else None,
        "hoSo": _ho_so(m),
        "anh": {"tong": sum(b.so_anh for b in bc) + so_tep, "tep": so_tep},
    }


@router.get("/vi-tri-cot/{vt_id}/anh")
async def anh_vi_tri(vt_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Ảnh của vị trí: tệp đã tải lên kho + số ảnh chỉ khai báo trong báo cáo (chưa có tệp)."""
    if await s.scalar(select(ViTriCot.id).where(ViTriCot.id == vt_id, ViTriCot.du_an_id == ctx.du_an_id)) is None:
        raise HTTPException(404, "Không tìm thấy vị trí cột")
    bc = (await s.scalars(select(BaoCaoHienTruong).where(BaoCaoHienTruong.vi_tri_id == vt_id, BaoCaoHienTruong.du_an_id == ctx.du_an_id)
                          .order_by(BaoCaoHienTruong.ngay.desc()))).all()
    anh = (await s.scalars(select(AnhHienTruong).where(AnhHienTruong.bao_cao_id.in_([b.id for b in bc])))).all() if bc else []
    return {"khaiBao": sum(b.so_anh for b in bc),
            "tep": [{"id": str(a.id), "baoCaoId": str(a.bao_cao_id), "tenFile": a.ten_file, "mime": a.mime} for a in anh]}


@router.get("/tuyen")
async def list_tuyen(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(Tuyen, func.ST_Length(cast(Tuyen.geom, Geography)) / 1000).where(Tuyen.du_an_id == ctx.du_an_id)
                            .order_by(Tuyen.loai.desc(), Tuyen.created_at))).all()
    dem = dict((await s.execute(select(ViTriCot.tuyen_id, func.count()).where(ViTriCot.du_an_id == ctx.du_an_id)
                                .group_by(ViTriCot.tuyen_id))).all())
    cap_nhat = await s.scalar(select(func.max(CongTac.updated_at)).where(CongTac.du_an_id == ctx.du_an_id))
    return [{"id": str(t.id), "ma": t.ma, "ten": t.ten, "capDienAp": t.cap_dien_ap, "loai": t.loai, "nguon": t.nguon,
             "soViTri": dem.get(t.id, 0), "chieuDaiKm": round(float(km), 2),
             "capNhat": ngay_gio(cap_nhat) if cap_nhat else None} for t, km in rows]


@router.get("/ban-do/geojson")
async def geojson(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """FeatureCollection: đường dây (LineString) + vị trí cột (Point) để vẽ bằng MapLibre GL."""
    features = []
    for t, g in (await s.execute(select(Tuyen, func.ST_AsGeoJSON(Tuyen.geom)).where(Tuyen.du_an_id == ctx.du_an_id))).all():
        features.append({"type": "Feature", "geometry": json.loads(g), "properties": {
            "loai": "tuyen", "id": str(t.id), "ten": t.ten, "ma": t.ma, "capDienAp": t.cap_dien_ap, "tuyenLoai": t.loai, "nguon": t.nguon}})
    for c, g in (await s.execute(select(ViTriCot, func.ST_AsGeoJSON(ViTriCot.geom))
                                 .where(ViTriCot.du_an_id == ctx.du_an_id, ViTriCot.geom.is_not(None)).order_by(ViTriCot.km))).all():
        features.append({"type": "Feature", "geometry": json.loads(g), "properties": {
            "loai": "cot", "id": str(c.id), "ten": c.ten, "km": float(c.km)}})
    return {"type": "FeatureCollection", "features": features}


@router.post("/ban-do/import-kmz")
async def import_kmz(file: UploadFile, ctx: Ctx = Depends(access(P.du_an_quan_ly)), s: AsyncSession = Depends(get_session)):
    """Nhập đường dây + toạ độ cột từ KMZ/KML. Tuyến nhập từ KMZ trước đó của dự án bị thay thế.
    Point chỉ cập nhật toạ độ cho vị trí cột ĐÃ CÓ (khớp theo tên); không tạo cột mới vì KMZ thiếu thông số móng."""
    data = await file.read(kmz.MAX_UPLOAD + 1)
    if len(data) > kmz.MAX_UPLOAD:
        raise HTTPException(413, "File quá lớn (tối đa 20 MB)")
    try:
        lines, points = kmz.parse(data)
    except kmz.KmzError as e:
        raise HTTPException(422, str(e))

    await s.execute(delete(Tuyen).where(Tuyen.du_an_id == ctx.du_an_id, Tuyen.nguon == "kmz"))
    tuyen = []
    for ln in lines:
        t = Tuyen(du_an_id=ctx.du_an_id, ma="KMZ", ten=ln.ten[:200], nguon="kmz", loai="moi",
                  geom=WKTElement("LINESTRING(" + ", ".join(f"{x:.7f} {y:.7f}" for x, y in ln.coords) + ")", srid=4326))
        s.add(t)
        tuyen.append(t)
    await s.flush()

    cot = {kmz.chuan_hoa_ten(c.ten): c for c in (await s.scalars(select(ViTriCot).where(ViTriCot.du_an_id == ctx.du_an_id))).all()}
    khop, khong_khop = 0, []
    for p in points:
        c = cot.get(kmz.chuan_hoa_ten(p.ten))
        if c is None:
            khong_khop.append(p.ten)
            continue
        c.geom = WKTElement(f"POINT({p.lon:.7f} {p.lat:.7f})", srid=4326)
        if len(tuyen) == 1:
            c.tuyen_id = tuyen[0].id
        khop += 1
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="import_kmz", bang="tuyen",
              sau={"file": (file.filename or "")[:120], "tuyen": len(tuyen), "cot_cap_nhat": khop, "khong_khop": len(khong_khop)})
    await s.commit()
    return {"tuyen": len(tuyen), "cotCapNhat": khop, "khongKhop": khong_khop[:200]}


@router.get("/ma-cau-kien", response_model=list[MaCauKienOut])
async def list_ma_cau_kien(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = await s.scalars(select(MaCauKien).where(MaCauKien.du_an_id == ctx.du_an_id).order_by(MaCauKien.ma))
    return [MaCauKienOut(id=str(m.id), ma=m.ma, ten=m.ten, dvt=m.dvt, dinh_muc=float(m.dinh_muc), ton_kho=float(m.ton_kho)) for m in rows]


@router.get("/kho", response_model=KhoOut, response_model_exclude_none=True)
async def get_kho(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = (await s.scalars(select(Kho).where(Kho.du_an_id == ctx.du_an_id).order_by(Kho.created_at, Kho.ten))).all()
    con_cua: dict = defaultdict(list)
    for k in rows:
        con_cua[k.parent_id].append(k)

    def dung(k: Kho) -> KhoOut:
        con = [dung(c) for c in con_cua.get(k.id, [])]
        return KhoOut(id=str(k.id), ten=k.ten, cap=k.cap.value, ton=float(k.ton), con=con or None)

    goc = con_cua.get(None, [])
    if not goc:
        return KhoOut(id="-", ten="Chưa có kho", cap="Công ty", ton=0)
    return dung(goc[0])
