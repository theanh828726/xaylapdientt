import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import DoiSoat, DoiSoatHangMuc, PhieuDieuChinh, PhieuLoai, QuyetDinhDoiSoat
from ..rbac import P
from ..services import audit
from .vat_tu import tao_phieu_noi_bo

router = APIRouter(tags=["doi-soat"])
KET_LUAN_TEN = {"lech": "Lệch", "khop": "Khớp", "thieu_hd": "Thiếu trong HĐ", "thieu_bv": "Thiếu trong BV", "thieu_cd": "Thiếu trong CĐ"}
HANH_DONG = {"lech": "tao_phieu", "thieu_hd": "phat_sinh", "thieu_bv": "phat_sinh", "thieu_cd": "phat_sinh", "khop": "xac_nhan"}


def _row(d: DoiSoat, phieu: PhieuDieuChinh | None) -> dict:
    return {"id": str(d.id), "thongSo": d.thong_so, "hopDong": d.hop_dong, "banVe": d.ban_ve, "chiDan": d.chi_dan, "trichDan": d.trich_dan or {},
            "ketLuan": d.ket_luan, "ketLuanTen": KET_LUAN_TEN[d.ket_luan], "tinCay": float(d.tin_cay) if d.tin_cay is not None else None,
            "aiDeXuat": d.ai_de_xuat, "hanhDong": HANH_DONG[d.ket_luan], "quyetDinh": d.quyet_dinh.value if d.quyet_dinh else None,
            "phieu": {"id": str(phieu.id), "ma": phieu.ma} if phieu else None, "bangChung": d.bang_chung or []}


async def _hang_muc(s: AsyncSession, ctx: Ctx, hm_id: uuid.UUID) -> DoiSoatHangMuc:
    h = await s.scalar(select(DoiSoatHangMuc).where(DoiSoatHangMuc.id == hm_id, DoiSoatHangMuc.du_an_id == ctx.du_an_id))
    if h is None:
        raise HTTPException(404, "Không tìm thấy hạng mục đối soát")
    return h


@router.get("/doi-soat/hang-muc")
async def list_hang_muc(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    hms = (await s.scalars(select(DoiSoatHangMuc).where(DoiSoatHangMuc.du_an_id == ctx.du_an_id).order_by(DoiSoatHangMuc.thu_tu))).all()
    rows = (await s.scalars(select(DoiSoat).where(DoiSoat.du_an_id == ctx.du_an_id))).all()
    out = []
    for h in hms:
        con = [r for r in rows if r.hang_muc_id == h.id]
        out.append({"id": str(h.id), "ten": h.ten, "soCanXuLy": sum(1 for r in con if r.ket_luan != "khop" and r.quyet_dinh is None),
                    "soThongSo": len(con)})
    return out


@router.get("/doi-soat/hang-muc/{hm_id}")
async def chi_tiet_hang_muc(hm_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    h = await _hang_muc(s, ctx, hm_id)
    rows = (await s.scalars(select(DoiSoat).where(DoiSoat.hang_muc_id == h.id).order_by(DoiSoat.thu_tu))).all()
    phieu_ids = {r.phieu_id for r in rows if r.phieu_id}
    phieu = {p.id: p for p in (await s.scalars(select(PhieuDieuChinh).where(PhieuDieuChinh.id.in_(phieu_ids)))).all()} if phieu_ids else {}
    return {"id": str(h.id), "ten": h.ten, "tieuDe": h.tieu_de, "nguon": h.nguon,
            "soThongSo": len(rows), "soLech": sum(1 for r in rows if r.ket_luan == "lech"),
            "soThieu": sum(1 for r in rows if r.ket_luan.startswith("thieu")),
            "rows": [_row(r, phieu.get(r.phieu_id)) for r in rows]}


class QuyetDinhIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    quyet_dinh: QuyetDinhDoiSoat = Field(alias="quyetDinh")


async def _lay_dong(s: AsyncSession, ctx: Ctx, item_id: uuid.UUID) -> DoiSoat:
    d = await s.scalar(select(DoiSoat).where(DoiSoat.id == item_id, DoiSoat.du_an_id == ctx.du_an_id).with_for_update())
    if d is None:
        raise HTTPException(404, "Không tìm thấy thông số đối soát")
    if d.quyet_dinh is not None:
        raise HTTPException(409, "Thông số này đã có quyết định")
    return d


@router.post("/doi-soat/{item_id}/quyet-dinh")
async def quyet_dinh_doi_soat(item_id: uuid.UUID, body: QuyetDinhIn, ctx: Ctx = Depends(access(P.doi_soat_xac_nhan)),
                              s: AsyncSession = Depends(get_session)):
    """R24: đề xuất AI chỉ có hiệu lực khi người có thẩm quyền xác nhận; lưu người + thời điểm."""
    if body.quyet_dinh == QuyetDinhDoiSoat.da_tao_phieu:
        raise HTTPException(422, "Dùng /tao-phieu để tạo phiếu xử lý")
    d = await _lay_dong(s, ctx, item_id)
    d.quyet_dinh, d.nguoi_xac_nhan_id, d.xac_nhan_luc = body.quyet_dinh, ctx.user.id, datetime.now(timezone.utc)
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="xac_nhan_doi_soat", bang="doi_soat", doi_tuong_id=d.id,
              sau={"quyet_dinh": body.quyet_dinh.value})
    await s.commit()
    return _row(d, None)


@router.post("/doi-soat/{item_id}/tao-phieu", status_code=201)
async def tao_phieu_doi_soat(item_id: uuid.UUID, ctx: Ctx = Depends(access(P.doi_soat_xac_nhan, P.de_xuat_lap)),
                             s: AsyncSession = Depends(get_session)):
    """'Tạo phiếu xử lý' (thông số lệch) / 'Lập phát sinh' (thiếu trong một nguồn): mở phiếu điều chỉnh đi qua chuỗi duyệt."""
    d = await _lay_dong(s, ctx, item_id)
    if d.ket_luan == "khop":
        raise HTTPException(409, "Thông số đã khớp 3 nguồn, không cần phiếu")
    phat_sinh = d.ket_luan.startswith("thieu")
    p = await tao_phieu_noi_bo(s, ctx, ly_do=d.ai_de_xuat, tieu_de=f"{'Phát sinh' if phat_sinh else 'Xử lý đối soát'} · {d.thong_so}",
                               loai=PhieuLoai.dieu_chinh, vi_tri_id=None, tac_dong=[], sau="thống nhất 3 nguồn tài liệu")
    d.phieu_id, d.quyet_dinh, d.nguoi_xac_nhan_id, d.xac_nhan_luc = p.id, QuyetDinhDoiSoat.da_tao_phieu, ctx.user.id, datetime.now(timezone.utc)
    await s.commit()
    return _row(d, p)
