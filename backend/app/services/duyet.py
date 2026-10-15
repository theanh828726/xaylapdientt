"""Chuỗi duyệt Kỹ thuật → CHT → P.KH → PGĐ → Chủ tịch, dùng chung cho đề xuất vật tư và phiếu điều chỉnh."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import Ctx
from ..models import (BuocDuyet, BuocTrangThai, DeXuatVatTu, DoiTuongDuyet, NguoiDung, PhieuDieuChinh,
                      ThanhVienDuAn, TrangThaiDuyet)
from ..rbac import BUOC_GOI_Y, CHUOI_DUYET, P, ROLE_LABEL, ROLE_SHORT, Role
from . import audit
from .format import gio_ngan


async def tao_chuoi(s: AsyncSession, loai: DoiTuongDuyet, doi_tuong_id: uuid.UUID, du_an_id: uuid.UUID,
                    nguoi_lap: NguoiDung) -> None:
    """Tạo các bước duyệt. Nếu người lập chính là vai trò bước 1 thì bước 1 coi như xong."""
    thanh_vien = (await s.scalars(
        select(NguoiDung).join(ThanhVienDuAn, ThanhVienDuAn.nguoi_dung_id == NguoiDung.id)
        .where(ThanhVienDuAn.du_an_id == du_an_id, NguoiDung.active.is_(True)).order_by(NguoiDung.created_at))).all()
    now = datetime.now(timezone.utc)
    dang_gan = False
    for i, vai_tro in enumerate(CHUOI_DUYET, start=1):
        phu_trach = nguoi_lap if (i == 1 and nguoi_lap.vai_tro == vai_tro) else next(
            (u for u in thanh_vien if u.vai_tro == vai_tro), None)
        xong = i == 1 and nguoi_lap.vai_tro == vai_tro
        if xong:
            tt = BuocTrangThai.xong
        elif not dang_gan:
            tt, dang_gan = BuocTrangThai.dang, True
        else:
            tt = BuocTrangThai.cho
        s.add(BuocDuyet(doi_tuong=loai, doi_tuong_id=doi_tuong_id, thu_tu=i, vai_tro=vai_tro,
                        nguoi_phu_trach_id=phu_trach.id if phu_trach else None,
                        nguoi_duyet_id=nguoi_lap.id if xong else None, trang_thai=tt,
                        thoi_gian=now if xong else None))


async def chuoi_cua(s: AsyncSession, loai: DoiTuongDuyet, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[BuocDuyet]]:
    out: dict[uuid.UUID, list[BuocDuyet]] = {i: [] for i in ids}
    if ids:
        rows = await s.scalars(select(BuocDuyet).where(BuocDuyet.doi_tuong == loai, BuocDuyet.doi_tuong_id.in_(ids))
                               .order_by(BuocDuyet.thu_tu))
        for b in rows:
            out[b.doi_tuong_id].append(b)
    return out


def buoc_out(b: BuocDuyet) -> dict:
    nguoi = b.nguoi_duyet or b.nguoi_phu_trach
    return {"vaiTro": ROLE_LABEL[b.vai_tro], "vaiTroNgan": ROLE_SHORT[b.vai_tro], "vaiTroMa": b.vai_tro.value,
            "nguoi": nguoi.ho_ten if nguoi else "Chưa phân công", "trangThai": b.trang_thai.value,
            "thoiGian": gio_ngan(b.thoi_gian) if b.thoi_gian else None, "thoiGianIso": b.thoi_gian.isoformat() if b.thoi_gian else None,
            "lyDo": b.ly_do, "goiY": BUOC_GOI_Y.get(b.vai_tro)}


def buoc_hien_tai(steps: list[BuocDuyet]) -> BuocDuyet | None:
    return next((b for b in steps if b.trang_thai == BuocTrangThai.dang), None)


def nhan_buoc(steps: list[BuocDuyet]) -> str | None:
    cur = buoc_hien_tai(steps)
    return f"Bước {cur.thu_tu}/{len(steps)} – {ROLE_LABEL[cur.vai_tro]}" if cur else None


def vai_tro_tiep(steps: list[BuocDuyet]) -> str | None:
    """Vai trò (viết tắt) của bước kế tiếp sau bước hiện tại, để ghi nhãn nút 'Duyệt, chuyển PGĐ'."""
    cur = buoc_hien_tai(steps)
    nxt = next((b for b in steps if cur and b.thu_tu == cur.thu_tu + 1), None)
    return ROLE_SHORT[nxt.vai_tro] if nxt else None


def co_the_duyet(trang_thai: TrangThaiDuyet, steps: list[BuocDuyet], user: NguoiDung, perms: frozenset[str]) -> bool:
    cur = buoc_hien_tai(steps)
    if trang_thai != TrangThaiDuyet.cho_duyet or cur is None or str(P.duyet_thuc_hien) not in perms:
        return False
    return cur.vai_tro == user.vai_tro or str(P.duyet_moi_buoc) in perms


async def quyet_dinh(s: AsyncSession, ctx: Ctx, loai: DoiTuongDuyet, item_id: uuid.UUID, duyet: bool,
                     ly_do: str | None) -> tuple[TrangThaiDuyet, str | None]:
    model = DeXuatVatTu if loai == DoiTuongDuyet.de_xuat else PhieuDieuChinh
    # Khoá hàng cha để hai người duyệt cùng lúc không làm lệch chuỗi.
    parent = await s.scalar(select(model).where(model.id == item_id, model.du_an_id == ctx.du_an_id).with_for_update(of=model))
    if parent is None:
        raise HTTPException(404, "Không tìm thấy hồ sơ cần duyệt")
    if parent.trang_thai != TrangThaiDuyet.cho_duyet:
        raise HTTPException(409, "Hồ sơ đã được xử lý xong, không thể duyệt thêm")
    steps = (await chuoi_cua(s, loai, [item_id]))[item_id]
    cur = buoc_hien_tai(steps)
    if cur is None:
        raise HTTPException(409, "Hồ sơ không còn bước nào đang chờ duyệt")
    if not (cur.vai_tro == ctx.user.vai_tro or ctx.co(P.duyet_moi_buoc)):
        raise HTTPException(403, f"Bước hiện tại thuộc vai trò {ROLE_LABEL[cur.vai_tro]}, không phải của bạn")
    ly_do = (ly_do or "").strip() or None
    if not duyet and not ly_do:
        raise HTTPException(422, "Từ chối phải ghi lý do")

    truoc = {"buoc": cur.thu_tu, "trang_thai": cur.trang_thai.value}
    cur.nguoi_duyet_id, cur.thoi_gian, cur.ly_do = ctx.user.id, datetime.now(timezone.utc), ly_do
    if duyet:
        cur.trang_thai = BuocTrangThai.xong
        nxt = next((b for b in steps if b.thu_tu == cur.thu_tu + 1), None)
        if nxt:
            nxt.trang_thai = BuocTrangThai.dang
        else:
            parent.trang_thai = TrangThaiDuyet.da_duyet
            if isinstance(parent, PhieuDieuChinh) and parent.ap_dung:
                await ap_dung_phieu(s, parent)
    else:
        cur.trang_thai = BuocTrangThai.tu_choi
        parent.trang_thai = TrangThaiDuyet.tu_choi
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="duyet" if duyet else "tu_choi",
              bang=loai.value, doi_tuong_id=item_id, truoc=truoc,
              sau={"buoc": cur.thu_tu, "trang_thai": cur.trang_thai.value, "ly_do": ly_do})
    await s.commit()
    return parent.trang_thai, nhan_buoc(steps)


async def ap_dung_phieu(s: AsyncSession, p: PhieuDieuChinh) -> None:
    """Phiếu điều chỉnh duyệt xong thì áp dụng thật vào dữ liệu."""
    from datetime import date
    from ..models import CongTac
    a = p.ap_dung or {}
    if a.get("loai") == "sua_ngay_nghiem_thu":
        x = await s.get(CongTac, uuid.UUID(a["cong_tac_id"]))
        if x is not None:
            x.ngay_nghiem_thu = date.fromisoformat(a["ngay"])
