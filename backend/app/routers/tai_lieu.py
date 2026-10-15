import io
import re
import unicodedata
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import Ctx, access
from ..models import (BienBan, CongTac, CongTacMa, DeXuatVatTu, DoiTuongDuyet, DuAn, LoVatLieu, MauBieu, PhieuDieuChinh)
from ..rbac import P, ROLE_LABEL
from ..services import audit, docs, duyet, qaqc, rules, storage
from ..services import cong_tac as ct
from ..services.foundation import chiet_tinh, khoi_luong_ho_mong
from ..services.format import VN, dmy, nguoi_label, so_vn, tien

router = APIRouter(tags=["bieu-mau-bien-ban"])
TT_DUYET = {"cho_duyet": "Đang chờ duyệt", "da_duyet": "Đã duyệt", "tu_choi": "Bị từ chối"}
TT_BUOC = {"xong": "Đã duyệt", "dang": "Đang chờ", "cho": "Chờ", "tu_choi": "Từ chối"}


def ascii_slug(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D").replace("–", "-").replace("—", "-")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-") or "tai-lieu"


def docx_response(data: bytes, ten_file: str, mime: str = docs.DOCX_MIME) -> Response:
    ten = ascii_slug(ten_file)
    return Response(data, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename=\"{ten}\"; filename*=UTF-8''{quote(ten_file)}", "X-Content-Type-Options": "nosniff"})


async def mau_dang_dung(s: AsyncSession, du_an_id: uuid.UUID, loai: str) -> MauBieu | None:
    return await s.scalar(select(MauBieu).where(MauBieu.du_an_id == du_an_id, MauBieu.loai == loai, MauBieu.dang_dung.is_(True))
                          .order_by(MauBieu.phien_ban.desc()).limit(1))


async def lay_mau(s: AsyncSession, du_an_id: uuid.UUID, loai: str) -> tuple[bytes, str]:
    row = await mau_dang_dung(s, du_an_id, loai)
    if row is None:
        return docs.mac_dinh(loai), "mac-dinh"
    return await storage.get(row.object_key), f"du-an-v{row.phien_ban}"


def _loai(loai: str) -> str:
    if loai not in docs.LOAI:
        raise HTTPException(404, "Không có loại mẫu biểu này")
    return loai


async def _du_an(s: AsyncSession, ctx: Ctx) -> DuAn:
    return await s.get(DuAn, ctx.du_an_id)


async def _khoa_du_an(s: AsyncSession, du_an_id: uuid.UUID) -> None:
    await s.execute(select(DuAn.id).where(DuAn.id == du_an_id).with_for_update())  # tuần tự hoá cấp số/phiên bản


# ---------------- Quản lý mẫu biểu ----------------
@router.get("/mau-bieu")
async def list_mau_bieu(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    out = []
    for loai, meta in docs.LOAI.items():
        row = await mau_dang_dung(s, ctx.du_an_id, loai)
        out.append({"loai": loai, "ten": meta["ten"], "nguon": "du-an" if row else "mac-dinh",
                    "phienBan": row.phien_ban if row else 0, "tenFile": row.ten_file if row else f"{loai}.docx",
                    "ghiChu": row.ghi_chu if row else None, "capNhat": row.created_at.isoformat() if row else None,
                    "bien": [{"ten": t, "moTa": m} for t, m in meta["bien"]]})
    return out


@router.get("/mau-bieu/{loai}/tai-ve")
async def tai_mau_ve(loai: str, nguon: str = "hien-tai", ctx: Ctx = Depends(access(P.du_an_quan_ly)), s: AsyncSession = Depends(get_session)):
    """Tải mẫu về để chỉnh bằng Word (nguon=hien-tai | mac-dinh)."""
    _loai(loai)
    if nguon == "mac-dinh":
        return docx_response(docs.mac_dinh(loai), f"{loai}-mac-dinh.docx")
    if nguon != "hien-tai":
        raise HTTPException(422, "nguon phải là hien-tai hoặc mac-dinh")
    data, tag = await lay_mau(s, ctx.du_an_id, loai)
    return docx_response(data, f"{loai}-{tag}.docx")


@router.put("/mau-bieu/{loai}")
async def tai_mau_len(loai: str, file: UploadFile, ghi_chu: str | None = Form(default=None, alias="ghiChu", max_length=300),
                      ctx: Ctx = Depends(access(P.du_an_quan_ly)), s: AsyncSession = Depends(get_session)):
    """Thay mẫu của dự án bằng bản .docx đã chỉnh. Mẫu bị từ chối nếu không render được bằng dữ liệu mẫu."""
    _loai(loai)
    data = await file.read(docs.MAX_MAU + 1)
    try:
        await docs.kiem_tra_mau(data, loai)
    except docs.MauError as e:
        raise HTTPException(422, str(e))
    await _khoa_du_an(s, ctx.du_an_id)
    n = (await s.scalar(select(func.coalesce(func.max(MauBieu.phien_ban), 0)).where(MauBieu.du_an_id == ctx.du_an_id, MauBieu.loai == loai))) + 1
    key = f"{ctx.du_an_id}/mau/{loai}/v{n}-{uuid.uuid4().hex[:8]}.docx"
    await storage.put(key, data, docs.DOCX_MIME)
    s.add(MauBieu(du_an_id=ctx.du_an_id, loai=loai, phien_ban=n, ten_file=ascii_slug(file.filename or f"{loai}.docx")[:200],
                  object_key=key, ghi_chu=ghi_chu, nguoi_id=ctx.user.id))
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="tai_mau", bang="mau_bieu", doi_tuong_id=loai,
              sau={"phien_ban": n, "kich_thuoc": len(data)})
    await s.commit()
    return {"loai": loai, "phienBan": n}


@router.delete("/mau-bieu/{loai}", status_code=204)
async def dung_lai_mau_mac_dinh(loai: str, ctx: Ctx = Depends(access(P.du_an_quan_ly)), s: AsyncSession = Depends(get_session)):
    """Quay về mẫu mặc định. Các phiên bản đã tải lên vẫn được lưu (chỉ ngừng áp dụng)."""
    _loai(loai)
    await s.execute(update(MauBieu).where(MauBieu.du_an_id == ctx.du_an_id, MauBieu.loai == loai).values(dang_dung=False))
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="dung_mau_mac_dinh", bang="mau_bieu", doi_tuong_id=loai)
    await s.commit()


# ---------------- Biên bản nghiệm thu theo công tác ----------------
def _bb_out(b: BienBan, message: str = "") -> dict:
    return {"id": str(b.id), "doiTuongId": str(b.doi_tuong_id), "loai": b.loai, "so": b.so, "tenFile": b.ten_file, "mauNguon": b.mau_nguon,
            "congTacIds": b.cong_tac_ids or [], "message": message, "taoLuc": b.created_at.isoformat() if b.created_at else None}


def _ngay_ctx(ctx: Ctx, da: DuAn, now: datetime) -> dict:
    return {"du_an": {"ten": da.ten, "chu_dau_tu": da.chu_dau_tu or ""}, "ngay": docs.ngay_ctx(now),
            "nguoi_lap": {"ho_ten": ctx.user.ho_ten, "chuc_danh": ROLE_LABEL[ctx.user.vai_tro]}}


def _vt_info(vt) -> dict:
    r = chiet_tinh(float(vt.a), float(vt.b), float(vt.h), float(vt.k))
    return {"ten": rules.vt_hien(vt.ten), "km": ct.km_text(vt.km), "loai_mong": vt.loai_mong,
            "khoi_luong": so_vn(r["V"], 1, co_dinh=True), "a": so_vn(vt.a, 2), "b": so_vn(vt.b, 2), "h": so_vn(vt.h, 2), "k": so_vn(vt.k, 2),
            "s_day": so_vn(r["S1"], 1, co_dinh=True), "s_mieng": so_vn(r["S2"], 1, co_dinh=True), "v": so_vn(r["V"], 1, co_dinh=True), "_v": r["V"]}


def ctx_bb(ctx: Ctx, da: DuAn, now: datetime, so: str, nhom: list[CongTac]) -> dict:
    d = ct.DEF[nhom[0].ma]
    ngay_ht = sorted({c.ngay_hoan_thanh for c in nhom})
    ds = []
    for i, c in enumerate(nhom, start=1):
        v = _vt_info(c.vi_tri)
        ds.append({"stt": i, "ten": v["ten"], "km": v["km"], "loai_mong": v["loai_mong"], "khoi_luong": v["khoi_luong"]})
    return {"so": so, **_ngay_ctx(ctx, da, now), "hang_muc": d.ten_dai, "phu_luc": f"{d.nhom} · {ct.NHOM_TEN[d.nhom]}",
            "vi_tri_text": qaqc.nhan_vi_tri(nhom), "danh_sach": ds,
            "ngay_hoan_thanh": dmy(ngay_ht[0]) if len(ngay_ht) == 1 else f"{dmy(ngay_ht[0])} – {dmy(ngay_ht[-1])}",
            "thanh_phan": [{"ho_ten": ctx.user.ho_ten, "chuc_danh": ROLE_LABEL[ctx.user.vai_tro], "don_vi": ctx.user.don_vi or "Nhà thầu thi công"},
                           {"ho_ten": "", "chuc_danh": "Đại diện tư vấn giám sát", "don_vi": ""},
                           {"ho_ten": "", "chuc_danh": "Đại diện chủ đầu tư", "don_vi": da.chu_dau_tu or ""}]}


def ctx_gm(ctx: Ctx, da: DuAn, now: datetime, so: str, nhom: list[CongTac]) -> dict:
    return {"so": so, **_ngay_ctx(ctx, da, now), "cong_viec": ct.DEF[nhom[0].ma].ten_dai, "vi_tri_text": qaqc.nhan_vi_tri(nhom),
            "ngay_nghiem_thu": dmy(now.astimezone(VN).date() + timedelta(days=1))}


def ctx_chiet_tinh(ctx: Ctx, da: DuAn, now: datetime, so: str, nhom: list[CongTac]) -> dict:
    info = [_vt_info(c.vi_tri) for c in nhom]
    return {"so": so, **_ngay_ctx(ctx, da, now), "cong_viec": ct.DEF[nhom[0].ma].ten_dai, "tong_v": so_vn(sum(i["_v"] for i in info), 1, co_dinh=True),
            "rows": [{"stt": k, "vi_tri": i["ten"], "loai_mong": i["loai_mong"], **{x: i[x] for x in ("a", "b", "h", "k", "s_day", "s_mieng", "v")}}
                     for k, i in enumerate(info, start=1)]}


async def _so_tiep(s: AsyncSession, du_an_id: uuid.UUID, tien_to: str) -> int:
    so_cu = (await s.scalars(select(BienBan.so).where(BienBan.du_an_id == du_an_id, BienBan.so.like(f"{tien_to}%")))).all()
    return max((int(x.rsplit("-", 1)[1]) for x in so_cu), default=0) + 1


async def _luu(s: AsyncSession, ctx: Ctx, loai: str, so: str, data: bytes, nguon: str, nhom: list[CongTac], ten_goi: str) -> BienBan:
    key = f"{ctx.du_an_id}/bien-ban/{uuid.uuid4()}.docx"
    await storage.put(key, data, docs.DOCX_MIME)
    b = BienBan(du_an_id=ctx.du_an_id, loai=loai, doi_tuong_id=nhom[0].id, so=so, ten_file=f"{so}_{ascii_slug(ten_goi)}.docx", object_key=key,
                mau_nguon=nguon, nguoi_id=ctx.user.id, cong_tac_ids=[str(c.id) for c in nhom])
    s.add(b)
    return b


async def _phat_hanh(s: AsyncSession, ctx: Ctx, da: DuAn, nhom: list[CongTac], *, kem: bool, now: datetime, dem: dict[str, int],
                     mau: dict[str, tuple[bytes, str]]) -> list[tuple[BienBan, bytes]]:
    """Phát hành một biên bản cho nhóm công tác (+ giấy mời + bảng chiết tính nếu kem). Trả về [(bản ghi, nội dung .docx)]."""
    nam = now.astimezone(VN).year
    ten_goi = qaqc.nhan_vi_tri(nhom)
    out = []
    plan = [("nghiem_thu_cong_viec", f"BB-NT-{nam}-", ctx_bb)]
    if kem:
        plan += [("giay_moi_nghiem_thu", f"GM-NT-{nam}-", ctx_gm), ("bang_chiet_tinh", f"CT-{nam}-", ctx_chiet_tinh)]
    for loai, tien_to, ham in plan:
        if tien_to not in dem:
            dem[tien_to] = await _so_tiep(s, ctx.du_an_id, tien_to)
        so = f"{tien_to}{dem[tien_to]:04d}"
        dem[tien_to] += 1
        if loai not in mau:
            mau[loai] = await lay_mau(s, ctx.du_an_id, loai)
        try:
            data = await docs.render(mau[loai][0], ham(ctx, da, now, so, nhom))
        except docs.MauError as e:
            raise HTTPException(422, f"Mẫu '{docs.LOAI[loai]['ten']}' của dự án bị lỗi, hãy sửa hoặc dùng lại mẫu mặc định. {e}")
        out.append((await _luu(s, ctx, loai, so, data, mau[loai][1], nhom, ten_goi), data))
    for c in nhom:
        c.da_co_bien_ban = True
        if kem and c.ma.value == "dao_mong":
            c.co_chiet_tinh = True
    return out


@router.post("/cong-tac/{ct_id}/bien-ban")
async def sinh_bien_ban(ct_id: uuid.UUID, response: Response, tao_lai: bool = False, ctx: Ctx = Depends(access(P.nghiem_thu_xu_ly)),
                        s: AsyncSession = Depends(get_session)):
    """Phát hành biên bản nghiệm thu cho MỘT công tác. Không phát hành khi công tác chưa xong hoặc đang bị rule Chặn
    (R03/R04/R06/R12…). Gọi lại trả biên bản đã phát hành; `?tao_lai=true` phát hành bản mới với số mới."""
    x = await s.scalar(select(CongTac).where(CongTac.id == ct_id, CongTac.du_an_id == ctx.du_an_id).with_for_update(of=CongTac))
    if x is None:
        raise HTTPException(404, "Không tìm thấy công tác")
    if x.trang_thai not in ct.HOAN_THANH:
        raise HTTPException(409, "Công tác chưa hoàn thành nên chưa thể lập biên bản nghiệm thu")
    chan = rules.bi_chan(await rules.danh_gia(s, ctx.du_an_id)).get((x.vi_tri.ten, x.ma))
    if chan:
        raise HTTPException(409, f"{', '.join(chan)}: công tác đang bị chặn bởi quy tắc, xử lý xong mới sinh được biên bản")
    await _khoa_du_an(s, ctx.du_an_id)
    if not tao_lai:
        cu = await s.scalar(select(BienBan).where(BienBan.du_an_id == ctx.du_an_id, BienBan.loai == "nghiem_thu_cong_viec",
                                                  BienBan.cong_tac_ids.contains([str(x.id)])).order_by(BienBan.created_at.desc()).limit(1))
        if cu is not None:
            return _bb_out(cu, f"Đã có biên bản {cu.so} (dùng ?tao_lai=true để phát hành bản mới)")
    da, now = await _du_an(s, ctx), datetime.now(timezone.utc)
    (b, _), = await _phat_hanh(s, ctx, da, [x], kem=False, now=now, dem={}, mau={})
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="sinh_bien_ban", bang="cong_tac", doi_tuong_id=x.id,
              sau={"so": b.so, "mau": b.mau_nguon, "vi_tri": x.vi_tri.ten})
    await s.commit()
    await s.refresh(b)
    response.status_code = 201
    return _bb_out(b, f"Đã phát hành biên bản {b.so} cho {rules.vt_hien(x.vi_tri.ten)} · {ct.DEF[x.ma].ten_dai} (mẫu: {b.mau_nguon})")


class SinhHangLoatIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    tu: date | None = None
    den: date | None = None
    gop: str = Field(default="doan_ngay", pattern=r"^(vi_tri|doan_ngay)$")


@router.post("/qaqc/sinh-bien-ban")
async def sinh_hang_loat(body: SinhHangLoatIn, ctx: Ctx = Depends(access(P.nghiem_thu_xu_ly)), s: AsyncSession = Depends(get_session)):
    """Sinh biên bản nghiệm thu hàng loạt cho các công tác đã xong trong khoảng ngày (bỏ qua công tác bị rule Chặn),
    kèm giấy mời nghiệm thu và bảng chiết tính cho mỗi biên bản. Trả về file ZIP chứa các .docx."""
    from .qaqc import _khoang
    tu, den = _khoang(body.tu, body.den)
    await _khoa_du_an(s, ctx.du_an_id)
    ss = await qaqc.san_sang(s, ctx.du_an_id, tu, den, await rules.danh_gia(s, ctx.du_an_id))
    nhom = qaqc.gop(ss.tao_duoc, body.gop)
    if not nhom:
        raise HTTPException(409, "Không có công tác nào đủ điều kiện sinh biên bản trong khoảng ngày này")
    for c in ss.tao_duoc:                      # khoá các dòng để hai người bấm cùng lúc không phát hành trùng
        await s.refresh(c, with_for_update={"of": CongTac})
    if any(c.da_co_bien_ban for c in ss.tao_duoc):
        raise HTTPException(409, "Có công tác vừa được người khác phát hành biên bản, hãy tải lại và thử lại")
    da, now, dem, mau = await _du_an(s, ctx), datetime.now(timezone.utc), {}, {}
    buf = io.BytesIO()
    n_bb = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for g in nhom:
            for b, data in await _phat_hanh(s, ctx, da, g, kem=True, now=now, dem=dem, mau=mau):
                z.writestr(b.ten_file, data)
            n_bb += 1
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="sinh_bien_ban_hang_loat", bang="cong_tac", doi_tuong_id=None,
              sau={"tu": tu.isoformat(), "den": den.isoformat(), "gop": body.gop, "bien_ban": n_bb, "cong_tac": len(ss.tao_duoc), "bi_chan": len(ss.bi_chan)})
    await s.commit()
    r = docx_response(buf.getvalue(), f"bien-ban-nghiem-thu-{tu:%Y%m%d}-{den:%Y%m%d}.zip", "application/zip")
    r.headers["X-So-Bien-Ban"] = str(n_bb)
    return r


@router.get("/cong-tac/{ct_id}/bien-ban")
async def list_bien_ban(ct_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = await s.scalars(select(BienBan).where(BienBan.du_an_id == ctx.du_an_id, BienBan.cong_tac_ids.contains([str(ct_id)]))
                           .order_by(BienBan.created_at))
    return [_bb_out(b) for b in rows]


@router.get("/bien-ban")
async def list_bien_ban_du_an(ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    rows = await s.scalars(select(BienBan).where(BienBan.du_an_id == ctx.du_an_id).order_by(BienBan.created_at.desc()).limit(500))
    return [_bb_out(b) for b in rows]


@router.get("/bien-ban/{bb_id}/tai-ve")
async def tai_bien_ban(bb_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    b = await s.scalar(select(BienBan).where(BienBan.id == bb_id, BienBan.du_an_id == ctx.du_an_id))
    if b is None:
        raise HTTPException(404, "Không tìm thấy biên bản")
    try:
        return docx_response(await storage.get(b.object_key), b.ten_file)
    except FileNotFoundError:
        raise HTTPException(404, "Tệp biên bản không còn trong kho lưu trữ")


# ---------------- Hành động từ màn hình QA/QC ----------------
@router.post("/lo-vat-lieu/{lo_id}/de-trinh")
async def soan_de_trinh(lo_id: uuid.UUID, ctx: Ctx = Depends(access(P.nghiem_thu_xu_ly)), s: AsyncSession = Depends(get_session)):
    """R03: soạn đề trình chấp thuận nhà cung cấp (.docx) từ dữ liệu lô vật liệu."""
    lo = await s.scalar(select(LoVatLieu).where(LoVatLieu.id == lo_id, LoVatLieu.du_an_id == ctx.du_an_id))
    if lo is None:
        raise HTTPException(404, "Không tìm thấy lô vật liệu")
    da, now = await _du_an(s, ctx), datetime.now(timezone.utc)
    context = {**_ngay_ctx(ctx, da, now), "vat_lieu": {
        "ten": lo.ten_vat_lieu, "ma": lo.ma, "nha_cung_cap": lo.nha_cung_cap, "ngay_giao": dmy(lo.ngay_giao),
        "dung_tai": ", ".join(rules.vt_hien(x) for x in lo.dung_tai or []) or "—", "han": dmy(lo.han_chap_thuan) if lo.han_chap_thuan else "—"}}
    mau, nguon = await lay_mau(s, ctx.du_an_id, "de_trinh_nha_cung_cap")
    try:
        data = await docs.render(mau, context)
    except docs.MauError as e:
        raise HTTPException(422, f"Mẫu của dự án bị lỗi, hãy sửa hoặc dùng lại mẫu mặc định. {e}")
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="soan_de_trinh", bang="lo_vat_lieu", doi_tuong_id=lo.id, sau={"mau": nguon})
    await s.commit()
    return docx_response(data, f"de-trinh-{lo.ma}.docx")


@router.post("/qaqc/sinh-chiet-tinh")
async def sinh_chiet_tinh(ctx: Ctx = Depends(access(P.nghiem_thu_xu_ly)), s: AsyncSession = Depends(get_session)):
    """R08: sinh bảng chiết tính cho mọi biên bản đào móng còn thiếu (một file .docx) và ghi nhận đã có chiết tính."""
    vp = await rules.danh_gia(s, ctx.du_an_id)
    ids = {v.doi_tuong_id for v in vp if v.ma == "R08" and v.an}
    if not ids:
        raise HTTPException(409, "Không có biên bản đào móng nào thiếu bảng chiết tính")
    cts = sorted((await s.scalars(select(CongTac).where(CongTac.id.in_([uuid.UUID(i) for i in ids])).with_for_update(of=CongTac))).all(),
                 key=lambda c: c.vi_tri.km)
    await _khoa_du_an(s, ctx.du_an_id)
    da, now = await _du_an(s, ctx), datetime.now(timezone.utc)
    so = f"CT-{now.astimezone(VN).year}-{await _so_tiep(s, ctx.du_an_id, f'CT-{now.astimezone(VN).year}-'):04d}"
    mau, nguon = await lay_mau(s, ctx.du_an_id, "bang_chiet_tinh")
    try:
        data = await docs.render(mau, ctx_chiet_tinh(ctx, da, now, so, cts))
    except docs.MauError as e:
        raise HTTPException(422, f"Mẫu của dự án bị lỗi, hãy sửa hoặc dùng lại mẫu mặc định. {e}")
    b = await _luu(s, ctx, "bang_chiet_tinh", so, data, nguon, cts, qaqc.nhan_vi_tri(cts))
    for c in cts:
        c.co_chiet_tinh = True
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="sinh_chiet_tinh", bang="cong_tac", doi_tuong_id=None,
              sau={"so": so, "cong_tac": len(cts)})
    await s.commit()
    return docx_response(data, b.ten_file)


@router.get("/vi-tri-cot/{vt_id}/chiet-tinh")
async def chiet_tinh_vi_tri(vt_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    """Xuất bảng chiết tính hố móng của một vị trí (sinh tại chỗ, không đánh số)."""
    x = await s.scalar(select(CongTac).where(CongTac.vi_tri_id == vt_id, CongTac.du_an_id == ctx.du_an_id, CongTac.ma == CongTacMa.dao_mong))
    if x is None:
        raise HTTPException(404, "Không tìm thấy vị trí cột")
    da, now = await _du_an(s, ctx), datetime.now(timezone.utc)
    so = f"CT-{x.vi_tri.ten}-{now.astimezone(VN):%Y%m%d}"
    mau, nguon = await lay_mau(s, ctx.du_an_id, "bang_chiet_tinh")
    try:
        data = await docs.render(mau, ctx_chiet_tinh(ctx, da, now, so, [x]))
    except docs.MauError as e:
        raise HTTPException(422, f"Mẫu của dự án bị lỗi, hãy sửa hoặc dùng lại mẫu mặc định. {e}")
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="xuat_chiet_tinh", bang="vi_tri_cot", doi_tuong_id=vt_id, sau={"mau": nguon})
    await s.commit()
    return docx_response(data, f"chiet-tinh-{x.vi_tri.ten}.docx")


# ---------------- In phiếu (sinh tại chỗ, không đánh số) ----------------
def _chuoi_ctx(steps) -> list[dict]:
    out = []
    for i, st in enumerate(steps, start=1):
        o = duyet.buoc_out(st)
        out.append({"stt": i, "vai_tro": o["vaiTro"], "nguoi": o["nguoi"], "trang_thai": TT_BUOC[o["trangThai"]],
                    "thoi_gian": o["thoiGian"] or "", "ly_do": o["lyDo"] or ""})
    return out


async def _in(s: AsyncSession, ctx: Ctx, loai: str, ten_file: str, context: dict, doi_tuong_id) -> Response:
    context |= _ngay_ctx(ctx, await _du_an(s, ctx), datetime.now(timezone.utc))
    mau, nguon = await lay_mau(s, ctx.du_an_id, loai)
    try:
        data = await docs.render(mau, context)
    except docs.MauError as e:
        raise HTTPException(422, f"Mẫu của dự án bị lỗi, hãy sửa hoặc dùng lại mẫu mặc định. {e}")
    audit.ghi(s, nguoi_id=ctx.user.id, du_an_id=ctx.du_an_id, hanh_dong="in_phieu", bang=loai, doi_tuong_id=doi_tuong_id, sau={"mau": nguon})
    await s.commit()
    return docx_response(data, ten_file)


@router.get("/de-xuat-vat-tu/{item_id}/in")
async def in_de_xuat(item_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    d = await s.scalar(select(DeXuatVatTu).where(DeXuatVatTu.id == item_id, DeXuatVatTu.du_an_id == ctx.du_an_id))
    if d is None:
        raise HTTPException(404, "Không tìm thấy đề xuất vật tư")
    steps = (await duyet.chuoi_cua(s, DoiTuongDuyet.de_xuat, [d.id]))[d.id]
    context = {
        "ma": d.ma, "cong_trinh": d.cong_trinh, "nguoi_lap_ten": nguoi_label(d.nguoi_lap), "ngay_lap": dmy(d.ngay_lap),
        "trang_thai": TT_DUYET[d.trang_thai.value],
        # Giá chỉ in khi người in có quyền xem (cùng quy tắc với API).
        "gia_hop_dong": tien(d.gia_hop_dong) if ctx.co(P.gia_hop_dong_xem) and d.gia_hop_dong is not None else "—",
        "gia_khoan": tien(d.gia_khoan) if ctx.co(P.gia_khoan_xem) and d.gia_khoan is not None else "—",
        "dong": [{"stt": i, "ma_ck": r.ma_ck, "ten": r.ten, "dvt": r.dvt, "theo_dinh_muc": so_vn(r.theo_dinh_muc), "de_xuat": so_vn(r.de_xuat),
                  "ton_kho": so_vn(r.ton_kho) if r.ton_kho is not None else "–"} for i, r in enumerate(d.dong, start=1)],
        "chuoi_duyet": _chuoi_ctx(steps),
    }
    return await _in(s, ctx, "de_xuat_vat_tu", f"{d.ma}.docx", context, d.id)


@router.get("/phieu-dieu-chinh/{item_id}/in")
async def in_phieu(item_id: uuid.UUID, ctx: Ctx = Depends(access()), s: AsyncSession = Depends(get_session)):
    p = await s.scalar(select(PhieuDieuChinh).where(PhieuDieuChinh.id == item_id, PhieuDieuChinh.du_an_id == ctx.du_an_id))
    if p is None:
        raise HTTPException(404, "Không tìm thấy phiếu điều chỉnh")
    steps = (await duyet.chuoi_cua(s, DoiTuongDuyet.phieu_dc, [p.id]))[p.id]
    context = {"ma": p.ma, "ly_do": p.ly_do, "ngay_lap": dmy(p.ngay), "trang_thai": TT_DUYET[p.trang_thai.value], "chuoi_duyet": _chuoi_ctx(steps)}
    return await _in(s, ctx, "phieu_dieu_chinh", f"{p.ma}.docx", context, p.id)
