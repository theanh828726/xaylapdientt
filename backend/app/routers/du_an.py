from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import CapKho, DuAn, Kho, ThanhVienDuAn
from ..rbac import P
from ..services import audit

router = APIRouter(prefix="/du-an", tags=["du-an"])


class DuAnIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ma: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    ten: str = Field(min_length=2, max_length=200)
    chu_dau_tu: str | None = Field(default=None, alias="chuDauTu", max_length=200)


@router.get("")
async def list_du_an(ctx: Ctx = Depends(access(scoped=False)), s: AsyncSession = Depends(get_session)):
    rows = await s.scalars(select(DuAn).join(ThanhVienDuAn, ThanhVienDuAn.du_an_id == DuAn.id)
                           .where(ThanhVienDuAn.nguoi_dung_id == ctx.user.id).order_by(DuAn.created_at, DuAn.ma))
    return [{"id": str(d.id), "ma": d.ma, "ten": d.ten, "chuDauTu": d.chu_dau_tu} for d in rows]


@router.get("/tat-ca")
async def list_tat_ca_du_an(ctx: Ctx = Depends(access(P.nguoi_dung_quan_ly, scoped=False)),
                            s: AsyncSession = Depends(get_session)):
    """Mọi dự án trong hệ thống, để quản trị viên gán người dùng vào dự án."""
    rows = await s.scalars(select(DuAn).order_by(DuAn.created_at, DuAn.ma))
    return [{"id": str(d.id), "ma": d.ma, "ten": d.ten, "chuDauTu": d.chu_dau_tu} for d in rows]


@router.post("", status_code=201)
async def tao_du_an(body: DuAnIn, ctx: Ctx = Depends(access(P.du_an_quan_ly, scoped=False)),
                    s: AsyncSession = Depends(get_session)):
    da = DuAn(ma=body.ma, ten=body.ten.strip(), chu_dau_tu=body.chu_dau_tu)
    s.add(da)
    try:
        await s.flush()
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "Mã dự án đã tồn tại")
    s.add(ThanhVienDuAn(du_an_id=da.id, nguoi_dung_id=ctx.user.id))
    s.add(Kho(du_an_id=da.id, ten=da.ten, cap=CapKho.cong_truong))
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=da.id, hanh_dong="tao", bang="du_an", doi_tuong_id=da.id,
              sau={"ma": da.ma, "ten": da.ten})
    await s.commit()
    return {"id": str(da.id), "ma": da.ma, "ten": da.ten, "chuDauTu": da.chu_dau_tu}
