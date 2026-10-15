from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import DeXuatVatTu, DoiSoatHangMuc, LoVatLieu, PhieuDieuChinh, ViTriCot
from ..services.rules import vt_hien

router = APIRouter(tags=["thong-bao-tim-kiem"])


def _like(q: str) -> str:
    # Thoát ký tự đại diện của LIKE để người dùng gõ % hoặc _ không khớp bừa
    bs = chr(92)
    return "%" + q.replace(bs, bs + bs).replace("%", bs + "%").replace("_", bs + "_") + "%"


@router.get("/tim-kiem")
async def tim_kiem(q: str = Query(min_length=2, max_length=60), ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Tìm nhanh vị trí cột, mã móng, đề xuất, phiếu, lô vật liệu, hạng mục đối soát của dự án đang chọn."""
    k = _like(q.strip())
    out = []
    for c in (await s.scalars(select(ViTriCot).where(ViTriCot.du_an_id == ctx.du_an_id, or_(
            ViTriCot.ten.ilike(k, escape=chr(92)), ViTriCot.loai_mong.ilike(k, escape=chr(92)), ViTriCot.cot_ma.ilike(k, escape=chr(92))))
            .order_by(ViTriCot.km).limit(8))).all():
        out.append({"loai": "Vị trí", "tieuDe": vt_hien(c.ten), "phu": f"{c.loai_mong} · {c.kieu_cot or ''}".strip(" ·"), "lienKet": f"/ban-do?vt={c.id}"})
    for d in (await s.scalars(select(DeXuatVatTu).where(DeXuatVatTu.du_an_id == ctx.du_an_id, or_(
            DeXuatVatTu.ma.ilike(k, escape=chr(92)), DeXuatVatTu.cong_trinh.ilike(k, escape=chr(92)))).limit(5))).all():
        out.append({"loai": "Đề xuất", "tieuDe": d.ma, "phu": d.cong_trinh, "lienKet": f"/de-xuat/{d.ma}"})
    for p in (await s.scalars(select(PhieuDieuChinh).where(PhieuDieuChinh.du_an_id == ctx.du_an_id, or_(
            PhieuDieuChinh.ma.ilike(k, escape=chr(92)), PhieuDieuChinh.tieu_de.ilike(k, escape=chr(92)))).limit(5))).all():
        out.append({"loai": "Phiếu", "tieuDe": p.ma, "phu": p.tieu_de or p.ly_do[:70], "lienKet": "/duyet"})
    for l in (await s.scalars(select(LoVatLieu).where(LoVatLieu.du_an_id == ctx.du_an_id, or_(
            LoVatLieu.ma.ilike(k, escape=chr(92)), LoVatLieu.ten_vat_lieu.ilike(k, escape=chr(92)))).limit(4))).all():
        out.append({"loai": "Lô vật liệu", "tieuDe": l.ma, "phu": f"{l.ten_vat_lieu} · {l.nha_cung_cap}", "lienKet": "/qaqc"})
    for h in (await s.scalars(select(DoiSoatHangMuc).where(DoiSoatHangMuc.du_an_id == ctx.du_an_id,
                                                           DoiSoatHangMuc.ten.ilike(k, escape=chr(92))).limit(4))).all():
        out.append({"loai": "Đối soát", "tieuDe": h.ten, "phu": h.tieu_de, "lienKet": f"/doi-soat?hm={h.id}"})
    return out[:20]
