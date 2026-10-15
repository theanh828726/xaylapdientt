import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import CongTac, CongTacMa, CongTacTT, LoVatLieu, MauBeTong, PhieuLoai, ViTriCot
from ..rbac import P
from ..services import audit, qaqc, rules
from ..services import cong_tac as ct
from ..services.format import VN
from .quy_tac import THU_TU_MUC, vp_out
from .vat_tu import tao_phieu_noi_bo

router = APIRouter(tags=["qaqc"])


def _khoang(tu: date | None, den: date | None) -> tuple[date, date]:
    hom_nay = datetime.now(timezone.utc).astimezone(VN).date()
    den = den or hom_nay
    tu = tu or den - timedelta(days=7)
    if tu > den:
        raise HTTPException(422, "Từ ngày phải trước hoặc bằng đến ngày")
    if (den - tu).days > 366:
        raise HTTPException(422, "Khoảng ngày tối đa 1 năm")
    return tu, den


@router.get("/qaqc/tong-quan")
async def tong_quan(nhom: str = Query(default="PL1", pattern=r"^PL[1-4]$"), tu: date | None = None, den: date | None = None,
                    ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    tu, den = _khoang(tu, den)
    vp_all = rules.loc_theo_quyen(await rules.danh_gia(s, ctx.du_an_id), ctx.perms)
    vp = rules.hien_thi(vp_all)
    tong_cot = await s.scalar(select(func.count()).select_from(ViTriCot).where(ViTriCot.du_an_id == ctx.du_an_id))
    cts = (await s.scalars(select(CongTac).where(CongTac.du_an_id == ctx.du_an_id))).all()
    theo = defaultdict(dict)
    for c in cts:
        theo[c.vi_tri_id][c.ma] = c
    du_mong = sum(1 for m in theo.values() if all(k in m and m[k].trang_thai == CongTacTT.da_nghiem_thu for k in ct.MONG))
    ss = await qaqc.san_sang(s, ctx.du_an_id, tu, den, vp_all)
    mau = (await s.scalars(select(MauBeTong).where(MauBeTong.du_an_id == ctx.du_an_id, MauBeTong.ket_qua_mpa.is_(None))
                           .order_by(MauBeTong.han_nen))).all()
    chan = [v for v in vp if v.muc == "Chặn"]
    kiem_tra = sorted([v for v in vp if v.nhom == nhom], key=lambda v: (THU_TU_MUC[v.muc], -int((v.moc or "0").replace("-", ""))))
    return {
        "nhom": nhom, "nhomTen": ct.NHOM_TEN[nhom], "soQuyTac": 24 - len(rules.KHONG_CO_DU_LIEU),
        "chayLuc": datetime.now(timezone.utc).astimezone(VN).strftime("%H:%M"), "tu": tu.isoformat(), "den": den.isoformat(),
        "thongKe": {
            "duHoSoMong": {"du": du_mong, "tong": tong_cot},
            "bienBanSanSang": {"n": len(ss.items), "tu": tu.isoformat(), "den": den.isoformat()},
            "loiChan": {"n": len(chan)},
            "mauChoNen": {"n": len(mau), "ganNhat": {"tuoi": mau[0].tuoi_ngay, "ngay": mau[0].han_nen.isoformat()} if mau else None},
        },
        "kiemTra": [vp_out(v) for v in kiem_tra],
        "maTran": await qaqc.ma_tran(s, ctx.du_an_id, vp_all),
    }


@router.get("/qaqc/sinh-bien-ban/xem-truoc")
async def xem_truoc(tu: date | None = None, den: date | None = None, gop: str = Query(default="doan_ngay", pattern=r"^(vi_tri|doan_ngay)$"),
                    ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    tu, den = _khoang(tu, den)
    vp = rules.loc_theo_quyen(await rules.danh_gia(s, ctx.du_an_id), ctx.perms)
    ss = await qaqc.san_sang(s, ctx.du_an_id, tu, den, vp)
    nhom = qaqc.gop(ss.tao_duoc, gop)
    chan: dict[str, list[str]] = defaultdict(list)
    for c in ss.bi_chan:
        for ma in ss.chan[c.id]:
            if ma not in chan[c.vi_tri.ten]:
                chan[c.vi_tri.ten].append(ma)
    return {"tu": tu.isoformat(), "den": den.isoformat(), "gop": gop, "bienBan": len(nhom), "congTac": len(ss.tao_duoc),
            "kemGiayMoi": len(nhom), "kemChietTinh": len(nhom), "soNgayNhatKy": (den - tu).days + 1, "sanSang": len(ss.items),
            "biChan": {"n": len(ss.bi_chan), "ds": [{"viTri": rules.vt_hien(k), "ma": v} for k, v in chan.items()]},
            "danhSach": [{"nhan": f"{ct.DEF[g[0].ma].ten_dai} · {qaqc.nhan_vi_tri(g)} · {ct.dm(g[0].ngay_hoan_thanh)}", "soCongTac": len(g)} for g in nhom]}


@router.get("/qaqc/lich-nen")
async def lich_nen(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Lịch nén mẫu bê tông chưa có kết quả (R05)."""
    rows = (await s.scalars(select(MauBeTong).where(MauBeTong.du_an_id == ctx.du_an_id, MauBeTong.ket_qua_mpa.is_(None))
                            .order_by(MauBeTong.han_nen, MauBeTong.ma_mau))).all()
    return [{"id": str(m.id), "maMau": m.ma_mau, "viTri": m.vi_tri.ten, "congTac": ct.DEF[m.cong_tac_ma].ten_dai, "ngayDuc": m.ngay_duc.isoformat(),
             "tuoiNgay": m.tuoi_ngay, "hanNen": m.han_nen.isoformat()} for m in rows]


class KetQuaIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ket_qua: str = Field(alias="ketQua", pattern=r"^(dat|khong_dat)$")
    ghi_chu: str | None = Field(default=None, alias="ghiChu", max_length=300)


@router.post("/lo-vat-lieu/{lo_id}/ket-qua")
async def gan_ket_qua(lo_id: uuid.UUID, body: KetQuaIn, ctx: Ctx = Depends(access(P.nghiem_thu_xu_ly)), s: AsyncSession = Depends(get_session)):
    """'Gắn kết quả' thí nghiệm cho lô vật liệu (R04)."""
    lo = await s.scalar(select(LoVatLieu).where(LoVatLieu.id == lo_id, LoVatLieu.du_an_id == ctx.du_an_id).with_for_update())
    if lo is None:
        raise HTTPException(404, "Không tìm thấy lô vật liệu")
    if lo.ket_qua_thi_nghiem is not None:
        raise HTTPException(409, "Lô này đã có kết quả thí nghiệm")
    lo.ket_qua_thi_nghiem, lo.ghi_chu_thi_nghiem = body.ket_qua, body.ghi_chu
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="gan_ket_qua", bang="lo_vat_lieu", doi_tuong_id=lo.id,
              sau={"ket_qua": body.ket_qua})
    await s.commit()
    return {"id": str(lo.id), "ma": lo.ma, "ketQua": lo.ket_qua_thi_nghiem}


@router.post("/cong-tac/{ct_id}/mo-phieu-dieu-chinh", status_code=201)
async def mo_phieu_r06(ct_id: uuid.UUID, ctx: Ctx = Depends(access(P.de_xuat_lap)), s: AsyncSession = Depends(get_session)):
    """R06: mở phiếu điều chỉnh sửa ngày nghiệm thu = ngày hoàn thành; duyệt xong phiếu sẽ tự áp dụng vào công tác."""
    x = await s.scalar(select(CongTac).where(CongTac.id == ct_id, CongTac.du_an_id == ctx.du_an_id))
    if x is None:
        raise HTTPException(404, "Không tìm thấy công tác")
    if not (x.ngay_nghiem_thu and x.ngay_hoan_thanh and x.ngay_nghiem_thu < x.ngay_hoan_thanh):
        raise HTTPException(409, "Công tác này không vi phạm R06")
    vp = [v for v in await rules.danh_gia(s, ctx.du_an_id) if v.ma == "R06" and v.doi_tuong_id == str(x.id)]
    sau = (vp[0].chi_tiet or "").split(": ", 1)[-1].split(", ") if vp else []
    tac_dong = [f"BBNT {n}" for n in sau if not n.startswith("nhật ký")] + [f"Nhật ký ngày {ct.dm(x.ngay_hoan_thanh)}"]
    d = ct.DEF[x.ma]
    p = await tao_phieu_noi_bo(
        s, ctx, loai=PhieuLoai.dieu_chinh, vi_tri_id=x.vi_tri_id, tac_dong=tac_dong, sau="không còn vi phạm quy tắc",
        tieu_de=f"{rules.vt_hien(x.vi_tri.ten)} · đổi ngày nghiệm thu {d.ten.lower()} {ct.dm(x.ngay_nghiem_thu)} → {ct.dm(x.ngay_hoan_thanh)}",
        ly_do=f"Ngày nghiệm thu ({ct.dm(x.ngay_nghiem_thu)}) ghi sớm hơn ngày hoàn thành ({ct.dm(x.ngay_hoan_thanh)}) theo báo cáo hiện trường.")
    p.ap_dung = {"loai": "sua_ngay_nghiem_thu", "cong_tac_id": str(x.id), "ngay": x.ngay_hoan_thanh.isoformat()}
    await s.commit()
    return {"id": str(p.id), "ma": p.ma}
