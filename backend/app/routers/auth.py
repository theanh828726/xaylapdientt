import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..deps import Ctx, access, perms_of
from ..models import DuAn, NguoiDung, RefreshToken, ThanhVienDuAn
from ..rbac import ROLE_LABEL
from ..security import create_access_token, hash_refresh, new_refresh_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "refresh_token"
_fails: dict[str, list[float]] = defaultdict(list)


class LoginIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    email: str
    mat_khau: str = Field(alias="matKhau")


def _throttle(key: str) -> None:
    now = time.monotonic()
    _fails[key] = [t for t in _fails[key] if now - t < 60]
    if len(_fails[key]) >= 5:
        raise HTTPException(429, "Đăng nhập sai quá nhiều lần, thử lại sau 1 phút")


async def payload(s: AsyncSession, user: NguoiDung) -> dict:
    perms = sorted(await perms_of(s, user.vai_tro))
    projects = (await s.scalars(select(DuAn).join(ThanhVienDuAn, ThanhVienDuAn.du_an_id == DuAn.id)
                                .where(ThanhVienDuAn.nguoi_dung_id == user.id).order_by(DuAn.created_at, DuAn.ma))).all()
    return {
        "user": {"id": str(user.id), "email": user.email, "hoTen": user.ho_ten, "vaiTro": user.vai_tro.value,
                 "vaiTroTen": ROLE_LABEL[user.vai_tro], "donVi": user.don_vi},
        "quyen": perms,
        "duAn": [{"id": str(p.id), "ma": p.ma, "ten": p.ten} for p in projects],
    }


async def _phat_hanh(s: AsyncSession, response: Response, user: NguoiDung) -> dict:
    raw, h = new_refresh_token()
    s.add(RefreshToken(nguoi_dung_id=user.id, token_hash=h,
                       expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_ttl_days)))
    await s.commit()
    response.set_cookie(COOKIE, raw, max_age=settings.refresh_ttl_days * 86400, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/api/auth")
    return {"accessToken": create_access_token(user.id, user.vai_tro.value), **await payload(s, user)}


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response, s: AsyncSession = Depends(get_session)):
    email = body.email.strip().lower()
    key = f"{request.client.host if request.client else '-'}:{email}"
    _throttle(key)
    user = await s.scalar(select(NguoiDung).where(NguoiDung.email == email))
    if not verify_password(body.mat_khau, user.mat_khau_hash if user else None) or not user or not user.active:
        _fails[key].append(time.monotonic())
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return await _phat_hanh(s, response, user)


@router.post("/refresh")
async def refresh(response: Response, s: AsyncSession = Depends(get_session),
                  refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(401, "Không có phiên đăng nhập")
    row = await s.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh(refresh_token))
                         .with_for_update())
    now = datetime.now(timezone.utc)
    if row is None:
        raise HTTPException(401, "Phiên đăng nhập không hợp lệ")
    if row.revoked_at is not None:
        # Token đã xoay vòng bị dùng lại → nghi bị lộ, thu hồi toàn bộ phiên của người này.
        await s.execute(update(RefreshToken).where(RefreshToken.nguoi_dung_id == row.nguoi_dung_id,
                                                   RefreshToken.revoked_at.is_(None)).values(revoked_at=now))
        await s.commit()
        raise HTTPException(401, "Phiên đăng nhập không hợp lệ")
    user = await s.get(NguoiDung, row.nguoi_dung_id)
    if row.expires_at < now or user is None or not user.active:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn")
    row.revoked_at = now
    return await _phat_hanh(s, response, user)


@router.post("/logout", status_code=204)
async def logout(response: Response, s: AsyncSession = Depends(get_session),
                 refresh_token: str | None = Cookie(default=None)):
    if refresh_token:
        await s.execute(update(RefreshToken).where(RefreshToken.token_hash == hash_refresh(refresh_token),
                                                   RefreshToken.revoked_at.is_(None))
                        .values(revoked_at=datetime.now(timezone.utc)))
        await s.commit()
    response.delete_cookie(COOKIE, path="/api/auth")


@router.get("/me")
async def me(ctx: Ctx = Depends(access(scoped=False)), s: AsyncSession = Depends(get_session)):
    return await payload(s, ctx.user)
