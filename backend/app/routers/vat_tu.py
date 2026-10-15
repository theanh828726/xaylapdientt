import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import (DeXuatDong, DeXuatVatTu, DotGiaoHang, DoiTuongDuyet, DuAn, MaCauKien, NguoiDung, PhieuDieuChinh, PhieuLoai,
                      ThanhVienDuAn, ThongBao, TrangThaiDuyet, ViTriCot)
from ..rbac import P, ROLE_LABEL, Role
from ..services import audit, duyet, rules
from ..services.format import VN, nguoi_label, so_vn

router = APIRouter(tags=["vat-tu-duyet"])
Camel = ConfigDict(populate_by_name=True)
LOAI_TEN = {"de_xuat": "ĐỀ XUẤT VẬT TƯ", "dieu_chinh": "PHIẾU ĐIỀU CHỈNH", "nghiem_thu_dk": "NGHIỆM THU CÓ ĐIỀU KIỆN"}


# ---------- Đề xuất vật tư ----------
def _dong_out(r: DeXuatDong, d: DeXuatVatTu) -> dict:
    con_lai = r.theo_dinh_muc - r.da_de_xuat
    vuot = r.de_xuat - con_lai
    cb = None
    if vuot > 0:
        cb = f"R09 · vượt định mức {so_vn(vuot)} {r.dvt}" + (" · có lý do của kỹ thuật" if d.ly_do_vuot else "")
    return {"maCK": r.ma_ck, "ten": r.ten, "dvt": r.dvt, "moTa": r.mo_ta, "theoDinhMuc": float(r.theo_dinh_muc),
            "daDeXuat": float(r.da_de_xuat), "conLai": float(con_lai), "tonKho": float(r.ton_kho) if r.ton_kho is not None else None,
            "deXuat": float(r.de_xuat), "quyDoi": r.quy_doi, "canhBao": cb, "hdSoLuong": float(r.hd_so_luong) if r.hd_so_luong is not None else None}


def _doi_chieu(d: DeXuatVatTu) -> dict:
    """Đối chiếu số lượng thiết kế với phụ lục khối lượng hợp đồng (dòng nào có hd_so_luong)."""
    co_hd = [r for r in d.dong if r.hd_so_luong is not None]
    lech = [r for r in co_hd if r.hd_so_luong != r.theo_dinh_muc]
    ghi = None
    if lech:
        r = lech[0]
        pct = f"{(float(r.theo_dinh_muc) - float(r.hd_so_luong)) / float(r.hd_so_luong) * 100:+.1f}".replace(".", ",")
        ten = f"{r.ten.split()[0]} {r.ma_ck}" if r.ma_ck and r.ma_ck != "—" else r.ten
        ghi = f"{ten}: hợp đồng {so_vn(r.hd_so_luong)} {r.dvt}, thiết kế {so_vn(r.theo_dinh_muc)} {r.dvt} ({pct}%)"
    return {"khop": len(co_hd) - len(lech), "tong": len(d.dong), "ghiChu": ghi}


def _dx_out(d: DeXuatVatTu, steps: list, ctx: Ctx) -> dict:
    return {
        "id": str(d.id), "ma": d.ma, "doan": d.doan, "congTrinh": d.cong_trinh, "nguoiLap": nguoi_label(d.nguoi_lap),
        "nguoiLapTen": d.nguoi_lap.ho_ten, "ngayLap": d.ngay_lap.isoformat(), "canHang": d.can_hang.isoformat() if d.can_hang else None,
        "giaoTai": d.giao_tai, "lanDeXuat": d.lan_de_xuat, "lyDoVuot": d.ly_do_vuot,
        "dong": [_dong_out(r, d) for r in d.dong], "chuoiDuyet": [duyet.buoc_out(b) for b in steps], "doiChieu": _doi_chieu(d),
        # Ẩn giá ngay ở backend: không đủ quyền thì trường không có trong JSON.
        **({"giaHopDong": d.gia_hop_dong} if ctx.co(P.gia_hop_dong_xem) and d.gia_hop_dong is not None else {}),
        **({"giaKhoan": d.gia_khoan} if ctx.co(P.gia_khoan_xem) and d.gia_khoan is not None else {}),
        "trangThai": d.trang_thai.value, "buocHienTai": duyet.nhan_buoc(steps), "vaiTroTiep": duyet.vai_tro_tiep(steps),
        "coTheDuyet": duyet.co_the_duyet(d.trang_thai, steps, ctx.user, ctx.perms),
    }


@router.get("/de-xuat-vat-tu")
async def list_de_xuat(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = (await s.scalars(select(DeXuatVatTu).where(DeXuatVatTu.du_an_id == ctx.du_an_id)
                            .order_by(DeXuatVatTu.ngay_lap.desc(), DeXuatVatTu.ma.desc()))).all()
    chuoi = await duyet.chuoi_cua(s, DoiTuongDuyet.de_xuat, [d.id for d in rows])
    return [_dx_out(d, chuoi[d.id], ctx) for d in rows]


class DongIn(BaseModel):
    model_config = Camel
    ma_ck: str = Field(alias="maCK", min_length=1, max_length=40)
    de_xuat: Decimal = Field(alias="deXuat", gt=0, max_digits=14, decimal_places=3)
    theo_dinh_muc: Decimal = Field(alias="theoDinhMuc", ge=0, max_digits=14, decimal_places=3)


class DeXuatIn(BaseModel):
    model_config = Camel
    cong_trinh: str = Field(alias="congTrinh", min_length=3, max_length=300)
    dong: list[DongIn] = Field(min_length=1, max_length=200)
    gia_hop_dong: int | None = Field(default=None, alias="giaHopDong", ge=0)
    gia_khoan: int | None = Field(default=None, alias="giaKhoan", ge=0)
    doan: str | None = Field(default=None, max_length=100)
    can_hang: date | None = Field(default=None, alias="canHang")
    ly_do_vuot: str | None = Field(default=None, alias="lyDoVuot", max_length=2000)


async def _so_tiep_theo(s: AsyncSession, model, du_an_id: uuid.UUID) -> int:
    # Khoá dòng dự án để hai người lập cùng lúc không sinh trùng mã.
    await s.execute(select(DuAn.id).where(DuAn.id == du_an_id).with_for_update())
    codes = (await s.scalars(select(model.ma).where(model.du_an_id == du_an_id))).all()
    nums = [int("".join(ch for ch in c if ch.isdigit()) or 0) for c in codes]
    return (max(nums) if nums else 0) + 1


@router.post("/de-xuat-vat-tu", status_code=201)
async def tao_de_xuat(body: DeXuatIn, ctx: Ctx = Depends(access(P.de_xuat_lap)), s: AsyncSession = Depends(get_session)):
    if body.gia_hop_dong is not None and not ctx.co(P.gia_hop_dong_xem):
        raise HTTPException(403, "Không có quyền nhập giá hợp đồng")
    if body.gia_khoan is not None and not ctx.co(P.gia_khoan_xem):
        raise HTTPException(403, "Không có quyền nhập giá khoán")
    kho = {m.ma: m for m in (await s.scalars(select(MaCauKien).where(MaCauKien.du_an_id == ctx.du_an_id))).all()}
    thieu = sorted({r.ma_ck for r in body.dong if r.ma_ck not in kho})
    if thieu:
        raise HTTPException(422, f"Mã cấu kiện không có trong thư viện dự án: {', '.join(thieu)}")
    n = await _so_tiep_theo(s, DeXuatVatTu, ctx.du_an_id)
    hom_nay = datetime.now(timezone.utc).astimezone(VN).date()
    d = DeXuatVatTu(du_an_id=ctx.du_an_id, ma=f"ĐX-{n:04d}", cong_trinh=body.cong_trinh.strip(), nguoi_lap_id=ctx.user.id, ngay_lap=hom_nay,
                    gia_hop_dong=body.gia_hop_dong, gia_khoan=body.gia_khoan, trang_thai=TrangThaiDuyet.cho_duyet, doan=body.doan,
                    can_hang=body.can_hang, ly_do_vuot=body.ly_do_vuot, giao_tai=None, lan_de_xuat=1)
    d.nguoi_lap = ctx.user
    d.dong = [DeXuatDong(thu_tu=i, ma_cau_kien_id=kho[r.ma_ck].id, ma_ck=r.ma_ck, ten=kho[r.ma_ck].ten, dvt=kho[r.ma_ck].dvt,
                         theo_dinh_muc=r.theo_dinh_muc, de_xuat=r.de_xuat, ton_kho=kho[r.ma_ck].ton_kho, da_de_xuat=0)
              for i, r in enumerate(body.dong, start=1)]
    s.add(d)
    await s.flush()
    await duyet.tao_chuoi(s, DoiTuongDuyet.de_xuat, d.id, ctx.du_an_id, ctx.user)
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="tao", bang="de_xuat_vat_tu", doi_tuong_id=d.id,
              sau={"ma": d.ma, "so_dong": len(d.dong)})
    await s.commit()
    steps = (await duyet.chuoi_cua(s, DoiTuongDuyet.de_xuat, [d.id]))[d.id]
    return _dx_out(d, steps, ctx)


# ---------- Phiếu điều chỉnh / nghiệm thu có điều kiện ----------
def _pdc_out(p: PhieuDieuChinh, steps: list, ctx: Ctx, vi_tri: str | None) -> dict:
    return {"id": str(p.id), "ma": p.ma, "loai": p.loai.value, "loaiTen": LOAI_TEN[p.loai.value], "tieuDe": p.tieu_de or p.ly_do[:80],
            "lyDo": p.ly_do, "ngay": p.ngay.isoformat(), "trangThai": p.trang_thai.value, "viTri": vi_tri, "tacDong": p.tac_dong or [],
            "sauDieuChinh": p.sau_dieu_chinh, "chuoiDuyet": [duyet.buoc_out(b) for b in steps], "buocHienTai": duyet.nhan_buoc(steps),
            "coTheDuyet": duyet.co_the_duyet(p.trang_thai, steps, ctx.user, ctx.perms)}


async def _ten_cot(s: AsyncSession, ids: set[uuid.UUID | None]) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {c.id: c.ten for c in (await s.scalars(select(ViTriCot).where(ViTriCot.id.in_(ids)))).all()}


@router.get("/phieu-dieu-chinh")
async def list_phieu(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = (await s.scalars(select(PhieuDieuChinh).where(PhieuDieuChinh.du_an_id == ctx.du_an_id)
                            .order_by(PhieuDieuChinh.ngay.desc(), PhieuDieuChinh.ma.desc()))).all()
    chuoi = await duyet.chuoi_cua(s, DoiTuongDuyet.phieu_dc, [p.id for p in rows])
    ten = await _ten_cot(s, {p.vi_tri_id for p in rows})
    return [_pdc_out(p, chuoi[p.id], ctx, ten.get(p.vi_tri_id)) for p in rows]


class PhieuIn(BaseModel):
    model_config = Camel
    ly_do: str = Field(alias="lyDo", min_length=5, max_length=2000)
    tieu_de: str | None = Field(default=None, alias="tieuDe", max_length=200)
    loai: PhieuLoai = PhieuLoai.dieu_chinh
    vi_tri: str | None = Field(default=None, alias="viTri", max_length=40)
    tac_dong: list[str] = Field(default_factory=list, alias="tacDong", max_length=20)


async def tao_phieu_noi_bo(s: AsyncSession, ctx: Ctx, *, ly_do: str, tieu_de: str | None, loai: PhieuLoai, vi_tri_id: uuid.UUID | None,
                           tac_dong: list[str], sau: str | None = None) -> PhieuDieuChinh:
    """Tạo phiếu + chuỗi duyệt (dùng chung cho API tạo phiếu và các hành động của QA/QC, đối soát)."""
    tien_to = "NTĐK" if loai == PhieuLoai.nghiem_thu_dk else "PĐC"
    codes = (await s.scalars(select(PhieuDieuChinh.ma).where(PhieuDieuChinh.du_an_id == ctx.du_an_id, PhieuDieuChinh.loai == loai))).all()
    await s.execute(select(DuAn.id).where(DuAn.id == ctx.du_an_id).with_for_update())
    n = max([int("".join(ch for ch in c if ch.isdigit()) or 0) for c in codes], default=0) + 1
    p = PhieuDieuChinh(du_an_id=ctx.du_an_id, ma=f"{tien_to}-{n:03d}", loai=loai, tieu_de=tieu_de, ly_do=ly_do.strip(),
                       ngay=datetime.now(timezone.utc).astimezone(VN).date(), nguoi_lap_id=ctx.user.id, vi_tri_id=vi_tri_id,
                       tac_dong=tac_dong, sau_dieu_chinh=sau, trang_thai=TrangThaiDuyet.cho_duyet)
    s.add(p)
    await s.flush()
    await duyet.tao_chuoi(s, DoiTuongDuyet.phieu_dc, p.id, ctx.du_an_id, ctx.user)
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="tao", bang="phieu_dieu_chinh", doi_tuong_id=p.id, sau={"ma": p.ma})
    return p


@router.post("/phieu-dieu-chinh", status_code=201)
async def tao_phieu(body: PhieuIn, ctx: Ctx = Depends(access(P.de_xuat_lap)), s: AsyncSession = Depends(get_session)):
    vt_id = None
    if body.vi_tri:
        vt_id = await s.scalar(select(ViTriCot.id).where(ViTriCot.du_an_id == ctx.du_an_id, ViTriCot.ten == body.vi_tri))
        if vt_id is None:
            raise HTTPException(422, f"Không có vị trí cột {body.vi_tri} trong dự án")
    p = await tao_phieu_noi_bo(s, ctx, ly_do=body.ly_do, tieu_de=body.tieu_de, loai=body.loai, vi_tri_id=vt_id, tac_dong=body.tac_dong)
    await s.commit()
    steps = (await duyet.chuoi_cua(s, DoiTuongDuyet.phieu_dc, [p.id]))[p.id]
    return _pdc_out(p, steps, ctx, body.vi_tri)


# ---------- Duyệt ----------
class QuyetDinhIn(BaseModel):
    model_config = Camel
    quyet_dinh: str = Field(alias="quyetDinh", pattern=r"^(duyet|tu_choi)$")
    ly_do: str | None = Field(default=None, alias="lyDo", max_length=2000)


@router.post("/duyet/{loai}/{item_id}")
async def duyet_buoc(loai: DoiTuongDuyet, item_id: uuid.UUID, body: QuyetDinhIn,
                     ctx: Ctx = Depends(access(P.duyet_thuc_hien)), s: AsyncSession = Depends(get_session)):
    trang_thai, buoc = await duyet.quyet_dinh(s, ctx, loai, item_id, body.quyet_dinh == "duyet", body.ly_do)
    return {"trangThai": trang_thai.value, "buocHienTai": buoc}


async def tinh_hop_thu(s: AsyncSession, ctx: Ctx) -> list[dict]:
    """Mọi hồ sơ cần duyệt của dự án kèm nhóm (chờ tôi / cấp khác / đã xử lý) theo người đang đăng nhập."""
    dxs = (await s.scalars(select(DeXuatVatTu).where(DeXuatVatTu.du_an_id == ctx.du_an_id))).all()
    pds = (await s.scalars(select(PhieuDieuChinh).where(PhieuDieuChinh.du_an_id == ctx.du_an_id))).all()
    c_dx = await duyet.chuoi_cua(s, DoiTuongDuyet.de_xuat, [d.id for d in dxs])
    c_pd = await duyet.chuoi_cua(s, DoiTuongDuyet.phieu_dc, [p.id for p in pds])
    r09 = {v.doi_tuong_id: v for v in rules.hien_thi(await rules.danh_gia(s, ctx.du_an_id)) if v.ma == "R09"}
    items: list[dict] = []

    def them(loai_key, obj, steps, nhan, tieu_de, lien_ket, canh_bao, chi_tiet):
        cho = obj.trang_thai == TrangThaiDuyet.cho_duyet
        toi = duyet.co_the_duyet(obj.trang_thai, steps, ctx.user, ctx.perms)
        da_xu_ly = (not cho) or any(b.nguoi_duyet_id == ctx.user.id and b.trang_thai in ("xong", "tu_choi") for b in steps)
        moc = max([b.thoi_gian for b in steps if b.thoi_gian] or [datetime.now(timezone.utc)])
        items.append({
            "loai": loai_key, "doiTuong": "de_xuat" if loai_key == "de_xuat" else "phieu_dc", "id": str(obj.id), "ma": obj.ma, "nhan": nhan,
            "gio": moc.astimezone(VN).strftime("%H:%M"), "moc": moc.isoformat(), "tieuDe": tieu_de, "lienKet": lien_ket,
            "chuoi": [{"vaiTro": ROLE_LABEL[b.vai_tro], "ngan": duyet.buoc_out(b)["vaiTroNgan"], "trangThai": b.trang_thai.value} for b in steps],
            "canhBao": canh_bao, "chiTiet": chi_tiet, "trangThai": obj.trang_thai.value, "coTheDuyet": toi,
            "_nhom": "cho_toi" if (cho and toi) else "cap_khac" if cho else "da_xu_ly", "_da": da_xu_ly})

    for d in dxs:
        v = r09.get(str(d.id))
        cb = {"ma": "R09", "noiDung": f"{v.thong_bao}." + (f" {v.chi_tiet}" if v.chi_tiet else "")} if v else None
        them("de_xuat", d, c_dx[d.id], LOAI_TEN["de_xuat"], d.cong_trinh, f"/de-xuat/{d.ma}", cb, None)
    for p in pds:
        them(p.loai.value, p, c_pd[p.id], LOAI_TEN[p.loai.value], p.tieu_de or p.ly_do[:80], f"/duyet#{p.ma}", None,
             {"lyDo": p.ly_do, "tacDong": p.tac_dong or [], "sauDieuChinh": p.sau_dieu_chinh})
    return items


@router.get("/duyet/hop-thu")
async def hop_thu(tab: str = Query("cho_toi", pattern=r"^(cho_toi|cap_khac|da_xu_ly)$"), ctx: Ctx = Depends(access()),
                  s: AsyncSession = Depends(get_session)):
    """Hộp thư phê duyệt của người đang đăng nhập: chờ tôi / đang ở cấp khác / đã xử lý."""
    items = await tinh_hop_thu(s, ctx)
    dem = {"choToi": sum(1 for i in items if i["_nhom"] == "cho_toi"), "capKhac": sum(1 for i in items if i["_nhom"] == "cap_khac"),
           "daXuLy": sum(1 for i in items if i["_da"])}
    chon = [i for i in items if i["_da"]] if tab == "da_xu_ly" else [i for i in items if i["_nhom"] == tab]
    chon.sort(key=lambda i: i["moc"], reverse=True)
    for i in chon:
        i.pop("_nhom"), i.pop("_da")
    return {"tab": tab, "dem": dem, "items": chon}


@router.get("/tong-quan/dem")
async def dem_huy_hieu(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Số hiện trên menu và chuông: lỗi đang chặn, hồ sơ chờ tôi duyệt, thông báo chưa đọc."""
    items = await tinh_hop_thu(s, ctx)
    chan = [v for v in rules.hien_thi(rules.loc_theo_quyen(await rules.danh_gia(s, ctx.du_an_id), ctx.perms)) if v.muc == "Chặn"]
    chua_doc = await s.scalar(select(func.count()).select_from(ThongBao).where(
        ThongBao.du_an_id == ctx.du_an_id, ThongBao.nguoi_nhan_id == ctx.user.id, ThongBao.da_doc.is_(False)))
    return {"loiChan": len(chan), "choToi": sum(1 for i in items if i["_nhom"] == "cho_toi"), "chuaDoc": chua_doc or 0,
            "choToiItems": [{"ma": i["ma"], "nhan": i["nhan"], "tieuDe": i["tieuDe"], "lienKet": i["lienKet"]} for i in items if i["_nhom"] == "cho_toi"][:6]}


# ---------- Giao hàng ----------
@router.get("/dot-giao-hang")
async def list_dot_giao_hang(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = await s.scalars(select(DotGiaoHang).where(DotGiaoHang.du_an_id == ctx.du_an_id).order_by(DotGiaoHang.po, DotGiaoHang.dot))
    return [{"id": str(r.id), "po": r.po, "dot": r.dot, "ngayDuKien": r.ngay_du_kien.isoformat(), "diaDiem": r.dia_diem,
             "trangThai": r.trang_thai.value, "hang": r.hang, "nhaCungCap": r.nha_cung_cap,
             "ngayNhan": r.ngay_nhan.isoformat() if r.ngay_nhan else None,
             "slDat": float(r.sl_dat) if r.sl_dat is not None else None, "slNhan": float(r.sl_nhan) if r.sl_nhan is not None else None,
             "dvt": r.dvt, "coAnhPhuongTien": r.co_anh_phuong_tien} for r in rows]


@router.post("/dot-giao-hang/{item_id}/nhac")
async def nhac_ky_thuat(item_id: uuid.UUID, ctx: Ctx = Depends(access(P.nghiem_thu_xu_ly)), s: AsyncSession = Depends(get_session)):
    """Nhắc kỹ thuật bổ sung ảnh phương tiện giao hàng (R11): tạo thông báo cho vai trò Kỹ thuật của dự án."""
    g = await s.scalar(select(DotGiaoHang).where(DotGiaoHang.id == item_id, DotGiaoHang.du_an_id == ctx.du_an_id))
    if g is None:
        raise HTTPException(404, "Không tìm thấy đợt giao hàng")
    nguoi = (await s.scalars(select(NguoiDung).join(ThanhVienDuAn, ThanhVienDuAn.nguoi_dung_id == NguoiDung.id).where(
        ThanhVienDuAn.du_an_id == ctx.du_an_id, NguoiDung.vai_tro == Role.ky_thuat, NguoiDung.active.is_(True)))).all()
    for u in nguoi:
        s.add(ThongBao(du_an_id=ctx.du_an_id, nguoi_nhan_id=u.id, tieu_de=f"Bổ sung ảnh phương tiện giao hàng · {g.po} đợt {g.dot}",
                       noi_dung=f"Nhận {g.ngay_nhan.strftime('%d/%m') if g.ngay_nhan else ''} tại {g.dia_diem}", lien_ket="/kho",
                       nguoi_gui_id=ctx.user.id))
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="nhac_ky_thuat", bang="dot_giao_hang", doi_tuong_id=g.id)
    await s.commit()
    return {"message": "Đã gửi nhắc cho bộ phận Kỹ thuật"}
