import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import DuAn, NguoiDung, RolePermission, ThanhVienDuAn
from .rbac import P, Role
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)
_401 = HTTPException(401, "Chưa đăng nhập hoặc phiên đã hết hạn", headers={"WWW-Authenticate": "Bearer"})


@dataclass
class Ctx:
    user: NguoiDung
    perms: frozenset[str]
    du_an_id: uuid.UUID | None

    def co(self, p: P) -> bool:
        return str(p) in self.perms


async def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                       s: AsyncSession = Depends(get_session)) -> NguoiDung:
    if creds is None:
        raise _401
    try:
        claims = decode_access_token(creds.credentials)
        user = await s.get(NguoiDung, uuid.UUID(claims["sub"]))
    except (jwt.PyJWTError, ValueError):
        raise _401
    if user is None or not user.active:
        raise _401
    return user


async def perms_of(s: AsyncSession, role: Role) -> frozenset[str]:
    rows = await s.scalars(select(RolePermission.quyen).where(RolePermission.vai_tro == role))
    return frozenset(rows)


async def resolve_project(s: AsyncSession, user: NguoiDung, header: str | None) -> uuid.UUID:
    if header:
        try:
            du_an_id = uuid.UUID(header)
        except ValueError:
            raise HTTPException(400, "X-Du-An không hợp lệ")
        ok = await s.scalar(select(ThanhVienDuAn.du_an_id).where(
            ThanhVienDuAn.du_an_id == du_an_id, ThanhVienDuAn.nguoi_dung_id == user.id))
        if ok is None:
            raise HTTPException(403, "Bạn không thuộc dự án này")
        return du_an_id
    first = await s.scalar(select(DuAn.id).join(ThanhVienDuAn, ThanhVienDuAn.du_an_id == DuAn.id)
                           .where(ThanhVienDuAn.nguoi_dung_id == user.id).order_by(DuAn.created_at, DuAn.ma).limit(1))
    if first is None:
        raise HTTPException(403, "Tài khoản chưa được gán dự án nào")
    return first


def access(*required: P, scoped: bool = True):
    """Dependency: đăng nhập + đủ quyền (+ xác định dự án hiện tại từ header X-Du-An)."""
    async def dep(request: Request, user: NguoiDung = Depends(current_user),
                  s: AsyncSession = Depends(get_session)) -> Ctx:
        granted = await perms_of(s, user.vai_tro)
        thieu = [p for p in required if str(p) not in granted]
        if thieu:
            raise HTTPException(403, f"Vai trò hiện tại không có quyền: {', '.join(map(str, thieu))}")
        du_an_id = await resolve_project(s, user, request.headers.get("X-Du-An")) if scoped else None
        return Ctx(user, granted, du_an_id)
    return dep
