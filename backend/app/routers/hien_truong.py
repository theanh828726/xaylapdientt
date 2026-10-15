import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import (AnhHienTruong, BaoCaoHienTruong, CongTac, CongTacMa, CongTacTT, DongBo, NguoiDung, ThanhVienDuAn, ViTriCot)
from ..rbac import P
from ..services import cong_tac as ct
from ..services.foundation import khoi_luong_ho_mong
from ..services.format import VN, ngay_gio, nguoi_label

router = APIRouter(tags=["hien-truong"])
MAY_THI_CONG = ["Máy đào 0,8 m³", "Máy bơm nước", "Máy trộn bê tông", "Cẩu 5 tấn", "Máy kéo dây"]
ANH_TOI_THIEU = 3


def _bc_out(b: BaoCaoHienTruong, anh_tai_len: int = 0) -> dict:
    # anh = số ảnh khai báo (so_anh) + ảnh đã tải lên kho lưu trữ
    return {"id": str(b.id), "viTri": b.vi_tri.ten, "viTriId": str(b.vi_tri_id), "ngay": ngay_gio(b.ngay), "ngayIso": b.ngay.isoformat(),
            "noiDung": b.noi_dung, "anh": b.so_anh + anh_tai_len, "dongBo": b.dong_bo.value, "nguoi": nguoi_label(b.nguoi),
            "congTacMa": b.cong_tac_ma.value if b.cong_tac_ma else None,
            "congTac": ct.DEF[b.cong_tac_ma].ten_dai if b.cong_tac_ma else None,
            "khoiLuong": float(b.khoi_luong) if b.khoi_luong is not None else None, "thoiTiet": b.thoi_tiet, "toDoi": b.to_doi,
            "nhanLuc": b.nhan_luc, "mayThiCong": b.may_thi_cong or []}


@router.get("/bao-cao-hien-truong")
async def list_bao_cao(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), tu: date | None = None,
                       den: date | None = None, vi_tri: str | None = Query(default=None, max_length=40),
                       ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Mới nhất trước, phân trang bằng limit/offset (tối đa 200 dòng/lần); lọc theo khoảng ngày và tên vị trí."""
    q = select(BaoCaoHienTruong).where(BaoCaoHienTruong.du_an_id == ctx.du_an_id)
    if tu:
        q = q.where(BaoCaoHienTruong.ngay >= datetime.combine(tu, datetime.min.time(), tzinfo=VN))
    if den:
        q = q.where(BaoCaoHienTruong.ngay < datetime.combine(den + timedelta(days=1), datetime.min.time(), tzinfo=VN))
    if vi_tri:
        q = q.where(BaoCaoHienTruong.vi_tri.has(ViTriCot.ten == vi_tri))
    rows = (await s.scalars(q.order_by(BaoCaoHienTruong.ngay.desc(), BaoCaoHienTruong.id).limit(limit).offset(offset))).all()
    ids = [b.id for b in rows]
    dem = dict((await s.execute(select(AnhHienTruong.bao_cao_id, func.count()).where(AnhHienTruong.du_an_id == ctx.du_an_id, AnhHienTruong.bao_cao_id.in_(ids))
                                .group_by(AnhHienTruong.bao_cao_id))).all()) if ids else {}
    return [_bc_out(b, dem.get(b.id, 0)) for b in rows]


class BaoCaoIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    vi_tri: str = Field(alias="viTri", min_length=1, max_length=40)
    noi_dung: str = Field(default="", alias="noiDung", max_length=4000)
    so_anh: int = Field(default=0, alias="soAnh", ge=0, le=100)
    client_id: uuid.UUID | None = Field(default=None, alias="clientId")
    ngay: datetime | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    cong_tac_ma: CongTacMa | None = Field(default=None, alias="congTacMa")
    khoi_luong: Decimal | None = Field(default=None, alias="khoiLuong", ge=0, max_digits=12, decimal_places=3)
    hoan_thanh: bool = Field(default=False, alias="hoanThanh")
    thoi_tiet: str | None = Field(default=None, alias="thoiTiet", max_length=60)
    to_doi: str | None = Field(default=None, alias="toDoi", max_length=120)
    nhan_luc: int | None = Field(default=None, alias="nhanLuc", ge=0, le=500)
    may_thi_cong: list[str] = Field(default_factory=list, alias="mayThiCong", max_length=20)


@router.post("/bao-cao-hien-truong", status_code=201)
async def tao_bao_cao(body: BaoCaoIn, response: Response, ctx: Ctx = Depends(access(P.bao_cao_gui)), s: AsyncSession = Depends(get_session)):
    """Idempotent theo clientId (thiết bị gửi lại báo cáo offline không tạo bản sao: trả 200 + bản đã có).
    Nếu báo cáo gắn với một công tác: kiểm tra công tác tiên quyết đã nghiệm thu (R02) và cập nhật tiến độ công tác."""
    if body.client_id is not None:
        cu = await s.scalar(select(BaoCaoHienTruong).where(BaoCaoHienTruong.client_id == body.client_id))
        if cu is not None:
            if cu.du_an_id != ctx.du_an_id or cu.nguoi_id != ctx.user.id:
                raise HTTPException(409, "clientId đã được dùng")
            response.status_code = 200
            return _bc_out(cu)
    cot = await s.scalar(select(ViTriCot).where(ViTriCot.du_an_id == ctx.du_an_id, ViTriCot.ten == body.vi_tri))
    if cot is None:
        raise HTTPException(422, f"Không có vị trí cột {body.vi_tri} trong dự án")
    now = datetime.now(timezone.utc)
    ngay = body.ngay or now
    if ngay.tzinfo is None:
        raise HTTPException(422, "ngay phải kèm múi giờ")
    if ngay > now + timedelta(minutes=5):
        raise HTTPException(422, "Thời điểm báo cáo nằm trong tương lai")
    noi_dung = body.noi_dung.strip()
    if body.cong_tac_ma is not None:
        m = {x.ma: x for x in (await s.scalars(select(CongTac).where(CongTac.vi_tri_id == cot.id).with_for_update(of=CongTac))).all()}
        x = m.get(body.cong_tac_ma)
        if x is None:
            raise HTTPException(422, "Vị trí này chưa có công tác đó")
        d = ct.DEF[body.cong_tac_ma]
        if ct.bi_khoa(m, body.cong_tac_ma):
            raise HTTPException(409, f"R02: công tác {d.ten_dai} chưa mở vì {ct.DEF[d.tien_quyet].ten_dai} chưa nghiệm thu")
        if x.trang_thai in ct.HOAN_THANH:
            raise HTTPException(409, f"Công tác {d.ten_dai} tại {cot.ten} đã hoàn thành, không báo cáo thêm")
        x.to_doi = body.to_doi or x.to_doi
        if body.khoi_luong is not None:
            x.khoi_luong = body.khoi_luong
        if body.hoan_thanh:
            x.trang_thai, x.ngay_hoan_thanh = CongTacTT.cho_nghiem_thu, ngay.astimezone(VN).date()
        else:
            x.trang_thai = CongTacTT.dang_lam
        noi_dung = noi_dung or f"{d.ten_dai} tại {cot.ten}" + (" – hoàn thành, chờ nghiệm thu" if body.hoan_thanh else " – đang thực hiện")
    if not noi_dung:
        raise HTTPException(422, "Nội dung báo cáo không được để trống")
    b = BaoCaoHienTruong(du_an_id=ctx.du_an_id, vi_tri_id=cot.id, nguoi_id=ctx.user.id, ngay=ngay, noi_dung=noi_dung, so_anh=body.so_anh,
                         dong_bo=DongBo.da_dong_bo, client_id=body.client_id, lat=body.lat, lon=body.lon, cong_tac_ma=body.cong_tac_ma,
                         khoi_luong=body.khoi_luong, thoi_tiet=body.thoi_tiet, to_doi=body.to_doi, nhan_luc=body.nhan_luc,
                         may_thi_cong=body.may_thi_cong)
    b.vi_tri, b.nguoi = cot, ctx.user
    s.add(b)
    try:
        await s.commit()
    except IntegrityError:  # hai request cùng clientId chạy song song
        await s.rollback()
        cu = await s.scalar(select(BaoCaoHienTruong).where(BaoCaoHienTruong.client_id == body.client_id))
        if cu is None:
            raise
        response.status_code = 200
        return _bc_out(cu)
    return _bc_out(b)


@router.get("/vi-tri-cot/{vt_id}/bao-cao-form")
async def form_bao_cao(vt_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Dữ liệu cho màn hình báo cáo hiện trường (mobile): công tác mở/khoá, khối lượng thiết kế, cảnh báo, tổ đội, máy thi công."""
    c = await s.scalar(select(ViTriCot).where(ViTriCot.id == vt_id, ViTriCot.du_an_id == ctx.du_an_id))
    if c is None:
        raise HTTPException(404, "Không tìm thấy vị trí cột")
    cts = (await s.scalars(select(CongTac).where(CongTac.vi_tri_id == c.id))).all()
    m = {x.ma: x for x in cts}
    cong_tac = []
    for d in ct.CATALOG:
        khoa = ct.bi_khoa(m, d.ma) or (d.ma in m and m[d.ma].trang_thai in ct.HOAN_THANH)
        cong_tac.append({"ma": d.ma.value, "ten": d.ten, "tenDai": d.ten_dai, "trangThai": m[d.ma].trang_thai.value if d.ma in m else "chua_lam",
                         "khoa": khoa, "lyDoKhoa": (f"Mở khi {ct.DEF[d.tien_quyet].ten_dai} đã nghiệm thu" if d.tien_quyet and ct.bi_khoa(m, d.ma)
                                                    else "Đã hoàn thành" if khoa else None)})
    mac_dinh = next((x["ma"] for x in cong_tac if not x["khoa"]), None)
    canh_bao = []
    dao = m.get(CongTacMa.dao_mong)
    if dao is not None and dao.trang_thai in (CongTacTT.chua_lam, CongTacTT.dang_lam):
        canh_bao.append(f"Chưa có BB bàn giao tim mốc {c.ten.replace('VT', 'VT ')}. Chụp ảnh mốc trước khi đào để hồ sơ không thiếu.")
    lon, lat = (await s.execute(select(func.ST_X(ViTriCot.geom), func.ST_Y(ViTriCot.geom)).where(ViTriCot.id == c.id))).one()
    to_doi = (await s.scalars(select(NguoiDung).join(ThanhVienDuAn, ThanhVienDuAn.nguoi_dung_id == NguoiDung.id)
                              .where(ThanhVienDuAn.du_an_id == ctx.du_an_id, NguoiDung.don_vi.like("Tổ%"), NguoiDung.active.is_(True))
                              .order_by(NguoiDung.don_vi))).all()
    return {
        "viTri": {"id": str(c.id), "ten": c.ten, "kmText": ct.km_text(c.km), "loaiMong": c.loai_mong, "lon": lon, "lat": lat},
        "congTac": cong_tac, "congTacMacDinh": mac_dinh,
        "khoiLuongThietKe": {"daoMong": round(khoi_luong_ho_mong(float(c.a), float(c.b), float(c.h), float(c.k)), 1), "dvt": "m³", "datCap": c.cap_dat},
        "canhBao": canh_bao, "toDoi": [f"{u.don_vi} · {u.ho_ten}" for u in to_doi], "mayThiCong": MAY_THI_CONG, "anhToiThieu": ANH_TOI_THIEU,
    }
