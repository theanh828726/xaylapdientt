import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import DoiTuongDuyet, ThongBao
from ..services.format import ngay_gio

router = APIRouter(tags=["thong-bao-tim-kiem"])


@router.get("/thong-bao")
async def list_thong_bao(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = (await s.scalars(select(ThongBao).where(ThongBao.du_an_id == ctx.du_an_id, ThongBao.nguoi_nhan_id == ctx.user.id)
                            .order_by(ThongBao.created_at.desc()).limit(30))).all()
    return {"chuaDoc": sum(1 for r in rows if not r.da_doc),
            "items": [{"id": str(r.id), "tieuDe": r.tieu_de, "noiDung": r.noi_dung, "lienKet": r.lien_ket, "daDoc": r.da_doc,
                       "thoiGian": ngay_gio(r.created_at)} for r in rows]}


@router.post("/thong-bao/doc-tat-ca", status_code=204)
async def doc_tat_ca(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    await s.execute(update(ThongBao).where(ThongBao.du_an_id == ctx.du_an_id, ThongBao.nguoi_nhan_id == ctx.user.id,
                                           ThongBao.da_doc.is_(False)).values(da_doc=True))
    await s.commit()
