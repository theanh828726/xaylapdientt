import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access, perms_of
from ..models import DuAn, NguoiDung, RefreshToken, RolePermission, ThanhVienDuAn
from ..rbac import P, PERM_MOTA, ROLE_LABEL, Role
from ..security import hash_password
from ..services import audit

router = APIRouter(tags=["quan-tri"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- Phân quyền ----------
@router.get("/phan-quyen")
async def xem_phan_quyen(ctx: Ctx = Depends(access(P.phan_quyen_quan_ly, scoped=False)),
                         s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(RolePermission.vai_tro, RolePermission.quyen))).all()
    ma_tran: dict[str, list[str]] = {r.value: [] for r in Role}
    for vai_tro, quyen in rows:
        ma_tran[vai_tro.value].append(quyen)
    return {
        "vaiTro": [{"ma": r.value, "ten": ROLE_LABEL[r]} for r in Role],
        "quyen": [{"ma": p.value, "moTa": PERM_MOTA[p]} for p in P],
        "maTran": {k: sorted(v) for k, v in ma_tran.items()},
    }


class QuyenIn(BaseModel):
    quyen: list[str]


@router.put("/phan-quyen/{vai_tro}")
async def sua_phan_quyen(vai_tro: Role, body: QuyenIn,
                         ctx: Ctx = Depends(access(P.phan_quyen_quan_ly, scoped=False)),
                         s: AsyncSession = Depends(get_session)):
    hop_le = {p.value for p in P}
    moi = set(body.quyen)
    if not moi <= hop_le:
        raise HTTPException(422, f"Quyền không hợp lệ: {', '.join(sorted(moi - hop_le))}")
    if vai_tro == Role.giam_doc and not {P.phan_quyen_quan_ly.value, P.nguoi_dung_quan_ly.value} <= moi:
        raise HTTPException(422, "Không được gỡ quyền quản trị của Giám đốc (tránh tự khoá hệ thống)")
    cu = set(await perms_of(s, vai_tro))
    await s.execute(delete(RolePermission).where(RolePermission.vai_tro == vai_tro))
    s.add_all(RolePermission(vai_tro=vai_tro, quyen=q) for q in moi)
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=None, hanh_dong="sua_phan_quyen", bang="role_permission",
              doi_tuong_id=vai_tro.value, truoc=sorted(cu), sau=sorted(moi))
    await s.commit()
    return {"vaiTro": vai_tro.value, "quyen": sorted(moi)}


# ---------- Người dùng ----------
class NguoiDungIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    email: str
    ho_ten: str = Field(alias="hoTen", min_length=2, max_length=120)
    vai_tro: Role = Field(alias="vaiTro")
    mat_khau: str = Field(alias="matKhau", min_length=10, max_length=128)
    don_vi: str | None = Field(default=None, alias="donVi", max_length=120)
    du_an_ids: list[uuid.UUID] = Field(default_factory=list, alias="duAnIds")


class NguoiDungPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ho_ten: str | None = Field(default=None, alias="hoTen", min_length=2, max_length=120)
    vai_tro: Role | None = Field(default=None, alias="vaiTro")
    mat_khau: str | None = Field(default=None, alias="matKhau", min_length=10, max_length=128)
    don_vi: str | None = Field(default=None, alias="donVi", max_length=120)
    active: bool | None = None
    du_an_ids: list[uuid.UUID] | None = Field(default=None, alias="duAnIds")


async def _out(s: AsyncSession, u: NguoiDung) -> dict:
    ids = (await s.scalars(select(ThanhVienDuAn.du_an_id).where(ThanhVienDuAn.nguoi_dung_id == u.id))).all()
    return {"id": str(u.id), "email": u.email, "hoTen": u.ho_ten, "vaiTro": u.vai_tro.value,
            "vaiTroTen": ROLE_LABEL[u.vai_tro], "donVi": u.don_vi, "active": u.active,
            "duAnIds": [str(i) for i in ids]}


async def _gan_du_an(s: AsyncSession, user_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
    co = set((await s.scalars(select(DuAn.id).where(DuAn.id.in_(ids)))).all()) if ids else set()
    if set(ids) - co:
        raise HTTPException(422, "Có dự án không tồn tại")
    await s.execute(delete(ThanhVienDuAn).where(ThanhVienDuAn.nguoi_dung_id == user_id))
    s.add_all(ThanhVienDuAn(du_an_id=i, nguoi_dung_id=user_id) for i in co)


@router.get("/nguoi-dung")
async def list_nguoi_dung(ctx: Ctx = Depends(access(P.nguoi_dung_quan_ly, scoped=False)),
                          s: AsyncSession = Depends(get_session)):
    users = (await s.scalars(select(NguoiDung).order_by(NguoiDung.ho_ten))).all()
    return [await _out(s, u) for u in users]


@router.post("/nguoi-dung", status_code=201)
async def tao_nguoi_dung(body: NguoiDungIn, ctx: Ctx = Depends(access(P.nguoi_dung_quan_ly, scoped=False)),
                         s: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(422, "Email không hợp lệ")
    u = NguoiDung(email=email, mat_khau_hash=hash_password(body.mat_khau), ho_ten=body.ho_ten.strip(),
                  vai_tro=body.vai_tro, don_vi=body.don_vi)
    s.add(u)
    try:
        await s.flush()
    except IntegrityError:
        await s.rollback()
        raise HTTPException(409, "Email đã tồn tại")
    await _gan_du_an(s, u.id, body.du_an_ids)
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=None, hanh_dong="tao", bang="nguoi_dung", doi_tuong_id=u.id,
              sau={"email": email, "vai_tro": u.vai_tro.value})
    await s.commit()
    return await _out(s, u)


@router.patch("/nguoi-dung/{user_id}")
async def sua_nguoi_dung(user_id: uuid.UUID, body: NguoiDungPatch,
                         ctx: Ctx = Depends(access(P.nguoi_dung_quan_ly, scoped=False)),
                         s: AsyncSession = Depends(get_session)):
    u = await s.get(NguoiDung, user_id)
    if u is None:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if u.id == ctx.user.id and ((body.vai_tro and body.vai_tro != u.vai_tro) or body.active is False):
        raise HTTPException(422, "Không tự đổi vai trò hoặc khoá chính mình")
    truoc = {"vai_tro": u.vai_tro.value, "active": u.active}
    if body.ho_ten is not None:
        u.ho_ten = body.ho_ten.strip()
    if body.vai_tro is not None:
        u.vai_tro = body.vai_tro
    if body.don_vi is not None:
        u.don_vi = body.don_vi or None
    if body.active is not None:
        u.active = body.active
    if body.mat_khau is not None:
        u.mat_khau_hash = hash_password(body.mat_khau)
    if body.du_an_ids is not None:
        await _gan_du_an(s, u.id, body.du_an_ids)
    if body.active is False or body.mat_khau is not None or body.vai_tro is not None:
        # đổi mật khẩu / khoá / đổi vai trò → buộc đăng nhập lại
        await s.execute(update(RefreshToken).where(RefreshToken.nguoi_dung_id == u.id,
                                                   RefreshToken.revoked_at.is_(None))
                        .values(revoked_at=datetime.now(timezone.utc)))
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=None, hanh_dong="sua", bang="nguoi_dung", doi_tuong_id=u.id,
              truoc=truoc, sau={"vai_tro": u.vai_tro.value, "active": u.active,
                                "doi_mat_khau": body.mat_khau is not None})
    await s.commit()
    return await _out(s, u)
