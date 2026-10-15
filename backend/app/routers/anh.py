import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import AnhHienTruong, BaoCaoHienTruong
from ..rbac import P
from ..services import audit, storage

router = APIRouter(tags=["anh-hien-truong"])
MAX_ANH = 10 * 1024 * 1024
MAX_ANH_MOI_BAO_CAO = 30


def nhan_dang(data: bytes) -> tuple[str, str] | None:
    """Nhận dạng ảnh theo chữ ký file (không tin Content-Type/đuôi file do client gửi)."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def _out(a: AnhHienTruong) -> dict:
    return {"id": str(a.id), "tenFile": a.ten_file, "mime": a.mime, "kichThuoc": a.kich_thuoc,
            "chupLuc": a.chup_luc.isoformat() if a.chup_luc else None,
            "lat": float(a.lat) if a.lat is not None else None, "lon": float(a.lon) if a.lon is not None else None}


async def _bao_cao(s: AsyncSession, ctx: Ctx, bao_cao_id: uuid.UUID) -> BaoCaoHienTruong:
    b = await s.scalar(select(BaoCaoHienTruong).where(BaoCaoHienTruong.id == bao_cao_id,
                                                      BaoCaoHienTruong.du_an_id == ctx.du_an_id))
    if b is None:
        raise HTTPException(404, "Không tìm thấy báo cáo hiện trường")
    return b


@router.post("/bao-cao-hien-truong/{bao_cao_id}/anh", status_code=201)
async def tai_anh_len(bao_cao_id: uuid.UUID, file: UploadFile, response: Response,
                      client_id: uuid.UUID | None = Form(default=None, alias="clientId"),
                      chup_luc: datetime | None = Form(default=None, alias="chupLuc"),
                      lat: float | None = Form(default=None, ge=-90, le=90), lon: float | None = Form(default=None, ge=-180, le=180),
                      ctx: Ctx = Depends(access(P.bao_cao_gui)), s: AsyncSession = Depends(get_session)):
    """Ảnh gắn vào báo cáo; chỉ người lập báo cáo (hoặc người quản lý dự án) được thêm. Idempotent theo clientId."""
    b = await _bao_cao(s, ctx, bao_cao_id)
    if b.nguoi_id != ctx.user.id and not ctx.co(P.du_an_quan_ly):
        raise HTTPException(403, "Chỉ người lập báo cáo mới được thêm ảnh")
    if client_id is not None:
        cu = await s.scalar(select(AnhHienTruong).where(AnhHienTruong.client_id == client_id))
        if cu is not None:
            if cu.bao_cao_id != b.id:
                raise HTTPException(409, "clientId đã được dùng")
            response.status_code = 200
            return _out(cu)
    data = await file.read(MAX_ANH + 1)
    if len(data) > MAX_ANH:
        raise HTTPException(413, "Ảnh quá lớn (tối đa 10 MB)")
    kind = nhan_dang(data)
    if kind is None:
        raise HTTPException(422, "Chỉ nhận ảnh JPEG, PNG hoặc WebP")
    if chup_luc is not None and chup_luc.tzinfo is None:
        raise HTTPException(422, "chupLuc phải kèm múi giờ")
    if chup_luc is not None and chup_luc > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(422, "Thời điểm chụp nằm trong tương lai")
    da_co = len((await s.scalars(select(AnhHienTruong.id).where(AnhHienTruong.bao_cao_id == b.id))).all())
    if da_co >= MAX_ANH_MOI_BAO_CAO:
        raise HTTPException(422, f"Mỗi báo cáo tối đa {MAX_ANH_MOI_BAO_CAO} ảnh")

    mime, ext = kind
    anh_id = uuid.uuid4()
    key = f"{ctx.du_an_id}/anh/{b.id}/{anh_id}.{ext}"
    await storage.put(key, data, mime)
    a = AnhHienTruong(id=anh_id, du_an_id=ctx.du_an_id, bao_cao_id=b.id, nguoi_id=ctx.user.id, client_id=client_id,
                      object_key=key, ten_file=f"{b.id.hex[:8]}-{anh_id.hex[:8]}.{ext}", mime=mime, kich_thuoc=len(data),
                      sha256=hashlib.sha256(data).hexdigest(), chup_luc=chup_luc, lat=lat, lon=lon)
    s.add(a)
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="tai_anh", bang="anh_hien_truong",
              doi_tuong_id=anh_id, sau={"bao_cao": str(b.id), "kich_thuoc": len(data)})
    try:
        await s.commit()
    except IntegrityError:  # hai request cùng clientId chạy song song
        await s.rollback()
        cu = await s.scalar(select(AnhHienTruong).where(AnhHienTruong.client_id == client_id)) if client_id else None
        if cu is None:
            raise
        response.status_code = 200
        return _out(cu)
    return _out(a)


@router.get("/bao-cao-hien-truong/{bao_cao_id}/anh")
async def list_anh(bao_cao_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    b = await _bao_cao(s, ctx, bao_cao_id)
    rows = await s.scalars(select(AnhHienTruong).where(AnhHienTruong.bao_cao_id == b.id).order_by(AnhHienTruong.created_at))
    return [_out(a) for a in rows]


@router.get("/anh/{anh_id}")
async def tai_anh_ve(anh_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Ảnh đi qua API (có xác thực + kiểm tra dự án) thay vì lộ MinIO ra ngoài."""
    a = await s.scalar(select(AnhHienTruong).where(AnhHienTruong.id == anh_id, AnhHienTruong.du_an_id == ctx.du_an_id))
    if a is None:
        raise HTTPException(404, "Không tìm thấy ảnh")
    try:
        data = await storage.get(a.object_key)
    except FileNotFoundError:
        raise HTTPException(404, "Tệp ảnh không còn trong kho lưu trữ")
    return Response(data, media_type=a.mime, headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})
