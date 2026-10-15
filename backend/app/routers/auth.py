import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..deps import Ctx, access, perms_of
from ..models import DangNhapThatBai, DuAn, NguoiDung, RefreshToken, ThanhVienDuAn
from ..rbac import ROLE_LABEL
from ..security import create_access_token, hash_refresh, new_refresh_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "refresh_token"
# Giới hạn đăng nhập sai (đếm trong DB, dùng chung giữa các worker): cặp IP+email 5/phút, một email 10/15 phút, một IP 30/5 phút.
GIOI_HAN = ((60, 5, "cap"), (900, 10, "email"), (300, 30, "ip"))


class LoginIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    email: str
    mat_khau: str = Field(alias="matKhau")


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()


def _ip(request: Request) -> str:
    return (request.client.host if request.client else "-")[:64]


async def _throttle(s: AsyncSession, ip: str, eh: str) -> None:
    now = datetime.now(timezone.utc)
    for giay, toi_da, loai in GIOI_HAN:
        q = select(func.count()).select_from(DangNhapThatBai).where(DangNhapThatBai.luc > now - timedelta(seconds=giay))
        if loai in ("cap", "ip"):
            q = q.where(DangNhapThatBai.ip == ip)
        if loai in ("cap", "email"):
            q = q.where(DangNhapThatBai.email_hash == eh)
        if (await s.scalar(q) or 0) >= toi_da:
            raise HTTPException(429, f"Đăng nhập sai quá nhiều lần, thử lại sau {max(1, giay // 60)} phút")


async def _ghi_that_bai(s: AsyncSession, ip: str, eh: str) -> None:
    s.add(DangNhapThatBai(ip=ip, email_hash=eh))
    await s.execute(delete(DangNhapThatBai).where(DangNhapThatBai.luc < datetime.now(timezone.utc) - timedelta(days=1)))
    await s.commit()


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
    ip, eh = _ip(request), _hash_email(email)
    await _throttle(s, ip, eh)
    user = await s.scalar(select(NguoiDung).where(NguoiDung.email == email))
    if not verify_password(body.mat_khau, user.mat_khau_hash if user else None) or not user or not user.active:
        await _ghi_that_bai(s, ip, eh)
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
