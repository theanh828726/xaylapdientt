from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import RuleDef
from ..services import rules

router = APIRouter(tags=["rule-engine"])
THU_TU_MUC = {"Chặn": 0, "Cảnh báo": 1, "Nhắc việc": 2}


def vp_out(v: rules.ViPham) -> dict:
    return {"ma": v.ma, "muc": v.muc, "nhom": v.nhom, "loai": v.loai, "doiTuongId": v.doi_tuong_id, "ten": v.ten, "thongBao": v.thong_bao,
            "chiTiet": v.chi_tiet, "hanhDong": v.hanh_dong, "viTri": v.vi_tri, "congTac": v.cong_tac.value if v.cong_tac else None, "moc": v.moc}


@router.get("/quy-tac")
async def list_rules(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Danh mục R01–R24 kèm số vi phạm đang mở của dự án hiện tại."""
    dem = Counter(v.ma for v in rules.hien_thi(rules.loc_theo_quyen(await rules.danh_gia(s, ctx.du_an_id), ctx.perms)))
    rows = await s.scalars(select(RuleDef).order_by(RuleDef.ma))
    return [{"ma": r.ma, "ten": r.ten, "muc": r.muc.value, "nhom": r.module, "moTa": r.mo_ta,
             "trienKhai": r.ma not in rules.KHONG_CO_DU_LIEU, "lyDoChuaCo": rules.KHONG_CO_DU_LIEU.get(r.ma),
             "soViPham": dem.get(r.ma, 0)} for r in rows]


@router.get("/quy-tac/vi-pham")
async def list_vi_pham(nhom: str | None = Query(default=None, pattern=r"^PL[1-4]$"), ctx: Ctx = Depends(access()),
                       s: AsyncSession = Depends(get_session)):
    """Các vi phạm/nhắc việc đang mở (Chặn trước, rồi Cảnh báo, Nhắc việc; cùng mức thì mới nhất trước)."""
    ds = rules.hien_thi(rules.loc_theo_quyen(await rules.danh_gia(s, ctx.du_an_id), ctx.perms))
    if nhom:
        ds = [v for v in ds if v.nhom == nhom]
    ds.sort(key=lambda v: (THU_TU_MUC[v.muc], v.ma))
    ds.sort(key=lambda v: (THU_TU_MUC[v.muc], -int((v.moc or "0").replace("-", ""))))
    return [vp_out(v) for v in ds]
