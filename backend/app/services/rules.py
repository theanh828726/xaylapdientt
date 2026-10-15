"""Rule engine: đánh giá dữ liệu dự án và trả về các vi phạm/nhắc việc đang mở.

Chỉ triển khai rule mà dữ liệu hiện có đủ để kết luận; phần còn lại nằm trong KHONG_CO_DU_LIEU kèm lý do và không
bao giờ báo vi phạm giả. Engine chỉ BÁO CÁO. Việc chặn thao tác thật hiện nằm ở: sinh biên bản (bỏ qua công tác bị
Chặn) và khoá công tác tiên quyết khi gửi báo cáo hiện trường (R02).

Mỗi ViPham là một bản ghi nguyên tử gắn với (vị trí, công tác). Cờ `an` = không hiển thị trong danh sách chung
(chỉ dùng cho ma trận / cảnh báo trong panel vị trí / tính toán chặn); các dòng tổng hợp thì hiển thị.
"""
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (BaoCaoHienTruong, BuocDuyet, BuocTrangThai, CongTac, CongTacMa, CongTacTT, DeXuatVatTu, DoiSoat,
                      DoiTuongDuyet, DotGiaoHang, LoVatLieu, MauBeTong, PhieuDieuChinh, PhieuLoai, TrangThaiDuyet,
                      ViTriCot, VatTuViTri)
from ..rbac import P, Role
from ..rules_data import MUC, NHOM
from . import cong_tac as ct
from .format import VN, so_vn
from .foundation import khoi_luong_ho_mong

KHONG_CO_DU_LIEU: dict[str, str] = {
    "R13": "chưa có thực thể chữ ký trên biên bản",
    "R18": "chưa có dữ liệu hạn đền bù GPMB",
    "R19": "chưa có hồ sơ đệ trình và bản vẽ hoàn công",
    "R20": "chưa có dữ liệu đệ trình và phản hồi chủ đầu tư",
    "R21": "chưa có dữ liệu hiệu chuẩn thiết bị thí nghiệm",
    "R22": "chưa có danh mục văn bản pháp luật để so mẫu biên bản",
    "R23": "chưa có khối lượng thanh toán",
}
TEN_NGAN = {CongTacMa.xa_su: "lắp xà", CongTacMa.keo_day: "kéo dây", CongTacMa.dung_cot: "dựng cột",
            CongTacMa.lap_mong: "lắp móng", CongTacMa.bt_mong: "đổ BT móng"}


@dataclass
class ViPham:
    ma: str
    loai: str          # vi_tri_cot | cong_tac | lo_vat_lieu | de_xuat | dot_giao_hang | phieu_dieu_chinh | doi_soat | du_an | mau_be_tong
    doi_tuong_id: str
    ten: str
    thong_bao: str
    vi_tri: str | None = None            # tên cột ("VT46") nếu gắn với vị trí
    cong_tac: CongTacMa | None = None
    chi_tiet: str | None = None
    hanh_dong: str | None = None         # gan_ket_qua | soan_de_trinh | mo_phieu_dieu_chinh | sinh_chiet_tinh | nhac_ky_thuat | xem_lich | ...
    an: bool = False
    moc: str | None = None               # ngày liên quan (ISO)

    @property
    def muc(self) -> str:
        return MUC[self.ma]

    @property
    def nhom(self) -> str:
        return NHOM[self.ma]


def vt_hien(ten: str) -> str:
    return re.sub(r"^VT(\d+)", r"VT \1", ten)


def dai_vt(ds: list[str]) -> str:
    """['VT46','VT47'] → 'VT 46–47'; ['VT46','VT49'] → 'VT 46, VT 49'."""
    so = sorted(int(re.sub(r"\D", "", x)) for x in ds)
    if len(so) > 1 and so == list(range(so[0], so[-1] + 1)):
        return f"VT {so[0]}–{so[-1]}"
    return ", ".join(f"VT {n}" for n in so)


async def danh_gia(s: AsyncSession, du_an_id: uuid.UUID, now: datetime | None = None) -> list[ViPham]:
    now = now or datetime.now(timezone.utc)
    hom_nay: date = now.astimezone(VN).date()
    out: list[ViPham] = []

    cot = (await s.scalars(select(ViTriCot).where(ViTriCot.du_an_id == du_an_id).order_by(ViTriCot.km))).all()
    cts = (await s.scalars(select(CongTac).where(CongTac.du_an_id == du_an_id))).all()
    theo_cot: dict[uuid.UUID, dict[CongTacMa, CongTac]] = defaultdict(dict)
    for c in cts:
        theo_cot[c.vi_tri_id][c.ma] = c
    cot_theo_id = {c.id: c for c in cot}
    cot_theo_ten = {c.ten: c for c in cot}
    bao_cao = (await s.scalars(select(BaoCaoHienTruong).where(BaoCaoHienTruong.du_an_id == du_an_id))).all()
    lo = (await s.scalars(select(LoVatLieu).where(LoVatLieu.du_an_id == du_an_id))).all()
    mau = (await s.scalars(select(MauBeTong).where(MauBeTong.du_an_id == du_an_id, MauBeTong.ket_qua_mpa.is_(None)))).all()
    de_xuat = (await s.scalars(select(DeXuatVatTu).where(DeXuatVatTu.du_an_id == du_an_id,
                                                        DeXuatVatTu.trang_thai == TrangThaiDuyet.cho_duyet))).all()
    tat_ca_dx = (await s.scalars(select(DeXuatVatTu).where(DeXuatVatTu.du_an_id == du_an_id))).all()
    giao = (await s.scalars(select(DotGiaoHang).where(DotGiaoHang.du_an_id == du_an_id))).all()
    doi_soat = (await s.scalars(select(DoiSoat).where(DoiSoat.du_an_id == du_an_id))).all()
    phieu = (await s.scalars(select(PhieuDieuChinh).where(
        PhieuDieuChinh.du_an_id == du_an_id, PhieuDieuChinh.trang_thai == TrangThaiDuyet.cho_duyet,
        PhieuDieuChinh.loai == PhieuLoai.dieu_chinh))).all()
    vat_tu = (await s.scalars(select(VatTuViTri).where(VatTuViTri.du_an_id == du_an_id))).all()

    # --- theo vị trí / công tác ---
    for c in cot:
        v = dict(loai="vi_tri_cot", doi_tuong_id=str(c.id), ten=vt_hien(c.ten), vi_tri=c.ten)
        if not (c.loai_mong or "").strip():                                                       # R01
            out.append(ViPham("R01", thong_bao="Chưa gán loại móng", **v))
        if c.vuong_gpmb:                                                                          # R17
            out.append(ViPham("R17", thong_bao="Vướng GPMB, cần biên bản bàn giao mặt bằng", **v))
        m = theo_cot.get(c.id, {})
        for i, d in enumerate(ct.CATALOG):
            x = m.get(d.ma)
            if x is None:
                continue
            cv = dict(loai="cong_tac", doi_tuong_id=str(x.id), vi_tri=c.ten, cong_tac=d.ma)
            if ct.gating_r02(m, d.ma):                                                            # R02: đang chờ tiên quyết
                tq = ct.DEF[d.tien_quyet]
                out.append(ViPham("R02", ten=f"{vt_hien(c.ten)} · {d.ten}", an=True,
                                  thong_bao=f"{d.ten_dai} đang bị chặn bởi R02 · cần nghiệm thu {tq.ten_dai.lower()}", **cv))
            if x.ngay_nghiem_thu and x.ngay_hoan_thanh and x.ngay_nghiem_thu < x.ngay_hoan_thanh:   # R06
                sau = [TEN_NGAN.get(k.ma, k.ten.lower()) for k in ct.CATALOG[i + 1:]
                       if k.ma in m and m[k.ma].trang_thai in ct.HOAN_THANH]
                sau.append(f"nhật ký {ct.dm(x.ngay_hoan_thanh)}")
                out.append(ViPham("R06", ten=f"{vt_hien(c.ten)}: ngày nghiệm thu {d.ten.lower()} ({ct.dm(x.ngay_nghiem_thu)}) "
                                            f"sớm hơn ngày hoàn thành ({ct.dm(x.ngay_hoan_thanh)})",
                                  thong_bao="Ngày nghiệm thu không thể trước ngày hoàn thành công tác",
                                  chi_tiet=f"Sửa sẽ ảnh hưởng {len(sau)} biên bản phía sau: {', '.join(sau)}",
                                  hanh_dong="mo_phieu_dieu_chinh", moc=x.ngay_hoan_thanh.isoformat(), **cv))
            if d.ma == CongTacMa.dao_mong and x.trang_thai in ct.HOAN_THANH:
                if not x.co_chiet_tinh:                                                           # R08 (nguyên tử, ẩn)
                    out.append(ViPham("R08", ten=f"{vt_hien(c.ten)} · biên bản đào móng", an=True,
                                      thong_bao="Biên bản đào móng chưa kèm bảng chiết tính",
                                      moc=(x.ngay_hoan_thanh or hom_nay).isoformat(), **cv))
                if x.khoi_luong is not None:                                                      # R07
                    v_tk = khoi_luong_ho_mong(float(c.a), float(c.b), float(c.h), float(c.k))
                    lech = abs(float(x.khoi_luong) - v_tk) / v_tk
                    if lech > 0.05:
                        out.append(ViPham("R07", ten=f"{vt_hien(c.ten)} · đào móng",
                                          thong_bao=f"Khối lượng thực tế {float(x.khoi_luong):g} m³ lệch {lech:.0%} "
                                                    f"so với công thức {v_tk:.1f} m³", **cv))

    r08 = [v for v in out if v.ma == "R08"]                                                       # R08 tổng hợp
    if r08:
        poles = sorted({v.vi_tri for v in r08})
        loai = sorted({cot_theo_ten[p].loai_mong for p in poles})
        out.append(ViPham("R08", "du_an", str(du_an_id), f"{len(r08)} biên bản đào móng {dai_vt(poles)} chưa kèm bảng chiết tính",
                          f"{len(r08)} biên bản đào móng chưa kèm bảng chiết tính",
                          chi_tiet=f"Thư viện đã có mã {', '.join(loai)} · có thể sinh tự động", hanh_dong="sinh_chiet_tinh",
                          moc=max(v.moc for v in r08)))

    # --- lô vật liệu (R03, R04, R12) ---
    for l in lo:
        if l.ngay_dung is None:
            continue
        tai = l.dung_tai or []
        dau = vt_hien(tai[0]) if tai else "công trường"
        verb = {CongTacMa.bt_lot: "Đã đổ bê tông lót", CongTacMa.bt_mong: "Đã đổ bê tông móng"}.get(l.cong_tac_ma, "Đã dùng")
        base = dict(loai="lo_vat_lieu", doi_tuong_id=str(l.id), cong_tac=l.cong_tac_ma)
        loi_chinh: list[ViPham] = []
        if not l.ncc_chap_thuan:
            loi_chinh.append(ViPham(
                "R03", ten=f"{l.ten_vat_lieu} {l.nha_cung_cap} chưa được chủ đầu tư chấp thuận",
                thong_bao="Nhà cung cấp chưa được chủ đầu tư chấp thuận",
                chi_tiet=f"Đã giao {ct.dm(l.ngay_giao)} · đã dùng tại {', '.join(vt_hien(x) for x in tai) or '—'}"
                         f" · cần văn bản chấp thuận trước ngày {ct.dm(l.han_chap_thuan)}",
                vi_tri=tai[0] if tai else None, hanh_dong="soan_de_trinh", moc=l.ngay_giao.isoformat(), **base))
        if l.ket_qua_thi_nghiem is None:
            loi_chinh.append(ViPham(
                "R04", ten=f"{l.ten_vat_lieu} lô {l.ma} chưa có kết quả thí nghiệm",
                thong_bao="Lô vật liệu đã dùng nhưng chưa có kết quả thí nghiệm",
                chi_tiet=f"{verb} tại {dau} ngày {ct.dm(l.ngay_dung)} · BB lấy mẫu {ct.dm(l.ngay_lay_mau)}, "
                         f"{l.phong_thi_nghiem or 'phòng thí nghiệm'} chưa trả kết quả",
                vi_tri=tai[0] if tai else None, hanh_dong="gan_ket_qua", moc=l.ngay_dung.isoformat(), **base))
        if not l.co_cq:
            loi_chinh.append(ViPham("R12", ten=f"{l.ten_vat_lieu} lô {l.ma} thiếu chứng chỉ CO/CQ",
                                    thong_bao="Lô vật liệu đã dùng nhưng thiếu CO/CQ", vi_tri=tai[0] if tai else None,
                                    moc=l.ngay_dung.isoformat(), **base))
        out.extend(loi_chinh)
        for v in loi_chinh:       # bản ẩn theo từng vị trí để ma trận / chặn biên bản biết ô nào bị ảnh hưởng
            for p in tai:
                out.append(ViPham(v.ma, v.loai, v.doi_tuong_id, f"{vt_hien(p)} · {v.ten}", v.thong_bao, vi_tri=p,
                                  cong_tac=v.cong_tac, an=True))

    # --- mẫu bê tông (R05) ---
    if mau:
        for x in mau:
            c = x.vi_tri
            d = ct.DEF[x.cong_tac_ma]
            nxt = next((k for k in ct.CATALOG if k.tien_quyet == d.ma), None)
            chan = f" {nxt.ten_dai} đang bị chặn đến khi có kết quả." if nxt and ct.gating_r02(theo_cot.get(c.id, {}), nxt.ma) else ""
            out.append(ViPham("R05", "mau_be_tong", str(x.id), vt_hien(c.ten), an=True, vi_tri=c.ten, cong_tac=x.cong_tac_ma,
                              thong_bao=f"Chưa nghiệm thu được {d.ten}. Mẫu đúc {ct.dm(x.ngay_duc)}, kết quả nén {x.tuoi_ngay} ngày "
                                        f"dự kiến {ct.dm(x.han_nen)}.{chan}", moc=x.han_nen.isoformat()))
        tuoi: dict[int, list[MauBeTong]] = defaultdict(list)
        for x in mau:
            tuoi[x.tuoi_ngay].append(x)
        mo_ta = ", ".join(f"{len(v)} mẫu {k} ngày ({ct.dm(min(i.han_nen for i in v))})" for k, v in sorted(tuoi.items()))
        out.append(ViPham("R05", "du_an", str(du_an_id), f"{len(mau)} mẫu bê tông đến hạn nén: {mo_ta}",
                          f"{len(mau)} mẫu bê tông chưa có kết quả nén", chi_tiet="Lịch nén theo tuổi mẫu 7 và 28 ngày",
                          hanh_dong="xem_lich", moc=min(x.han_nen for x in mau).isoformat()))

    # --- nhật ký (R16) ---
    if any(c.trang_thai == CongTacTT.dang_lam or (c.trang_thai in ct.HOAN_THANH and not c.da_co_bien_ban) for c in cts):
        moi_nhat = max((b.ngay for b in bao_cao), default=None)
        if moi_nhat is None or now - moi_nhat > timedelta(days=2):
            out.append(ViPham("R16", "du_an", str(du_an_id), "Nhật ký thi công",
                              "Có công tác đang thi công nhưng không có báo cáo/nhật ký trong hơn 2 ngày"))

    # --- đề xuất vật tư (R09) và giá (R15) ---
    for d in de_xuat:
        vuot = [(r, r.de_xuat - (r.theo_dinh_muc - r.da_de_xuat)) for r in d.dong if r.de_xuat > (r.theo_dinh_muc - r.da_de_xuat)]
        if vuot:
            r, x = vuot[0]
            ten = r.ten[0].lower() + r.ten[1:]
            out.append(ViPham("R09", "de_xuat", str(d.id), f"{d.ma} · {len(vuot)} dòng vượt định mức",
                              f"{len(vuot)} dòng vượt định mức: {ten} vượt {float(x):g} {r.dvt}",
                              chi_tiet=f"Lý do của kỹ thuật: {d.ly_do_vuot}" if d.ly_do_vuot else None, hanh_dong="xem_de_xuat"))
    for d in tat_ca_dx:
        if d.gia_khoan is not None and d.gia_hop_dong is not None and d.gia_khoan > d.gia_hop_dong:
            out.append(ViPham("R15", "de_xuat", str(d.id), d.ma, "Giá khoán cao hơn giá hợp đồng"))

    # --- lead-time vật tư (R10) ---
    r10: dict[str, list[tuple[VatTuViTri, str]]] = defaultdict(list)
    for v in vat_tu:
        if v.can_truoc_ngay and v.da_cap < v.dinh_muc and (v.can_truoc_ngay - hom_nay).days <= 7:
            c = cot_theo_id[v.vi_tri_id]
            out.append(ViPham("R10", "vi_tri_cot", str(c.id), f"{vt_hien(c.ten)} · {v.ten}", an=True, vi_tri=c.ten,
                              thong_bao=f"Cần đặt trước {ct.dm(v.can_truoc_ngay)} (lead-time {v.lead_time_ngay} ngày)",
                              moc=v.can_truoc_ngay.isoformat()))
            r10[v.ten].append((v, c.ten))
    for ten, ds in r10.items():
        han = min(v.can_truoc_ngay for v, _ in ds)
        out.append(ViPham("R10", "du_an", str(du_an_id), f"{ten} cần đặt trước {ct.dm(han)} (lead-time {ds[0][0].lead_time_ngay} ngày)",
                          f"{len(ds)} vị trí cần đặt {ten}", chi_tiet=dai_vt([p for _, p in ds]), hanh_dong="xem_vat_tu",
                          moc=han.isoformat()))

    # --- giao hàng (R11) ---
    for g in giao:
        if g.ngay_nhan is not None and not g.co_anh_phuong_tien:
            sl = f" · {so_vn(g.sl_nhan, 1, True)} / {so_vn(g.sl_dat, 1, True)} {g.dvt}" if g.sl_dat is not None and g.sl_nhan is not None else ""
            out.append(ViPham("R11", "dot_giao_hang", str(g.id), f"Đợt giao {g.dot} của {g.po} ({g.hang}) thiếu ảnh phương tiện giao hàng",
                              "Đợt giao đã nhận nhưng thiếu ảnh phương tiện giao hàng",
                              chi_tiet=f"Nhận {ct.dm(g.ngay_nhan)} tại {g.dia_diem}{sl}", hanh_dong="nhac_ky_thuat",
                              moc=g.ngay_nhan.isoformat()))

    # --- đối soát AI (R24) và phiếu điều chỉnh (R14) ---
    for d in doi_soat:
        if d.ket_luan != "khop" and d.quyet_dinh is None:
            out.append(ViPham("R24", "doi_soat", str(d.id), d.thong_so, "Đề xuất AI chưa được người có thẩm quyền xác nhận",
                              hanh_dong="xem_doi_soat"))
    for p in phieu:
        out.append(ViPham("R14", "phieu_dieu_chinh", str(p.id), f"{p.ma}: {p.tieu_de or p.ly_do[:70]}",
                          "Phiếu điều chỉnh đang chờ duyệt", hanh_dong="xem_phieu"))
    return out


def hien_thi(ds: list[ViPham]) -> list[ViPham]:
    return [v for v in ds if not v.an]


def loc_theo_quyen(vi_pham: list[ViPham], perms: frozenset[str]) -> list[ViPham]:
    """R15 so sánh hai loại giá nên chỉ người xem được cả hai mới thấy (không lộ giá qua cảnh báo)."""
    can_gia = {str(P.gia_hop_dong_xem), str(P.gia_khoan_xem)} <= perms
    return [v for v in vi_pham if v.ma != "R15" or can_gia]


def bi_chan(ds: list[ViPham]) -> dict[tuple[str, CongTacMa], list[str]]:
    """(vị trí, công tác) → các mã rule Chặn đang áp dụng (không gồm R02: đó là chờ tiên quyết, không phải lỗi)."""
    r: dict[tuple[str, CongTacMa], list[str]] = defaultdict(list)
    for v in ds:
        if v.muc == "Chặn" and v.vi_tri and v.cong_tac and v.ma != "R02" and v.ma not in r[(v.vi_tri, v.cong_tac)]:
            r[(v.vi_tri, v.cong_tac)].append(v.ma)
    return r
