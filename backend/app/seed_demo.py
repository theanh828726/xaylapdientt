"""Nạp DỮ LIỆU DEMO (không phải dữ liệu thật của khách hàng) theo kịch bản trong bản thiết kế giao diện (PDF):
dự án di chuyển ĐZ trung, hạ thế GPMB cao tốc Bắc–Nam (Hà Trung, Thanh Hóa), Lộ 471 · 22 kV · 64 vị trí · 3,9 km,
"hôm nay" là 14/10/2026. Các con số trên màn hình (12/64 vị trí đủ hồ sơ móng, 3 lỗi chặn, 5 mẫu chờ nén…) đều
được TÍNH từ dữ liệu này, không gõ cứng.

    python -m app.seed_demo           # nạp nếu chưa có
    python -m app.seed_demo --reset   # xoá dữ liệu demo cũ rồi nạp lại

Từ chối chạy khi ENV=production. Mật khẩu tài khoản demo lấy từ SEED_DEMO_PASSWORD.
Toạ độ tuyến/cột là toạ độ giả định quanh Hà Trung (Thanh Hóa) chỉ để minh hoạ bản đồ thật.
"""
import asyncio
import math
import sys
from datetime import date, datetime, timedelta, timezone

from geoalchemy2 import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import SessionLocal
from .models import (BaoCaoHienTruong, BuocDuyet, BuocTrangThai, CapKho, CongTac, CongTacMa, CongTacTT, DeXuatDong,
                     DeXuatVatTu, DoiSoat, DoiSoatHangMuc, DoiTuongDuyet, DongBo, DotGiaoHang, DuAn, GiaoHangTT, Kho,
                     LoVatLieu, MaCauKien, MauBeTong, NguoiDung, PhieuDieuChinh, PhieuLoai, ThanhVienDuAn, ThongBao,
                     TrangThaiDuyet, Tuyen, VatTuViTri, ViTriCot)
from .rbac import CHUOI_DUYET, Role
from .security import hash_password
from .services.cong_tac import CATALOG
from .services.ref_data import ensure_reference_data

DOMAIN = "demo.tuyenso.local"
VN = timezone(timedelta(hours=7))
HOM_NAY = date(2026, 10, 14)

# (khoá, họ tên, vai trò, đơn vị, chỉ dự án 1?)
USERS = [
    ("giamdoc", "Giám đốc (demo)", Role.giam_doc, None, False),
    ("chihuytruong", "Hoàng Văn Lực", Role.chi_huy_truong, None, False),
    ("kythuat", "Đỗ Minh Khôi", Role.ky_thuat, None, False),
    ("ketoan", "Kế toán (demo)", Role.ke_toan, None, False),
    ("kehoach", "Trần Thu Hà", Role.phong_ke_hoach, None, False),
    ("phogiamdoc", "Phạm Quốc Bảo", Role.pho_giam_doc, None, False),
    ("chutich", "Chủ tịch HĐTV", Role.chu_tich, None, False),
    ("tam", "Lê Văn Tâm", Role.ky_thuat, "Tổ 3", True),
    ("khoa", "Đặng Văn Khoa", Role.ky_thuat, "Tổ 2", True),
    ("son", "Võ Thanh Sơn", Role.ky_thuat, "Tổ 1", True),
]


def vn(y, mo, d, h=0, mi=0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=VN)


def d(m: int, dd: int) -> date:
    return date(2026, m, dd)


def pt(lon: float, lat: float) -> WKTElement:
    return WKTElement(f"POINT({lon:.6f} {lat:.6f})", srid=4326)


def line(coords: list[tuple[float, float]]) -> WKTElement:
    return WKTElement("LINESTRING(" + ", ".join(f"{x:.6f} {y:.6f}" for x, y in coords) + ")", srid=4326)


# ---------- hình học tuyến (Hà Trung, Thanh Hóa – giả định) ----------
ANCHORS = [(1, 0.0), (44, 2.272), (45, 2.340), (46, 2.412), (48, 2.550), (64, 3.900)]


def km_of(k: int) -> float:
    for (k0, s0), (k1, s1) in zip(ANCHORS, ANCHORS[1:]):
        if k0 <= k <= k1:
            return s0 + (s1 - s0) * (k - k0) / (k1 - k0)
    raise ValueError(k)


def pos(s: float, lat_off: float = 0.0) -> tuple[float, float]:
    return (105.8300 + s * 0.0072 + 0.0010 * math.sin(s * 1.7), 19.9500 + s * 0.0058 + 0.0008 * math.cos(s * 2.1) + lat_off)


async def xoa_demo(s: AsyncSession) -> None:
    ids = (await s.scalars(select(DuAn.id).where(DuAn.ma.like("DEMO-%")))).all()
    if ids:
        # buoc_duyet tham chiếu đa hình (không FK) nên phải xoá tay trước khi dự án bị cascade.
        dx = (await s.scalars(select(DeXuatVatTu.id).where(DeXuatVatTu.du_an_id.in_(ids)))).all()
        pdc = (await s.scalars(select(PhieuDieuChinh.id).where(PhieuDieuChinh.du_an_id.in_(ids)))).all()
        await s.execute(delete(BuocDuyet).where(BuocDuyet.doi_tuong_id.in_([*dx, *pdc])))
        await s.execute(delete(DuAn).where(DuAn.id.in_(ids)))
    await s.execute(delete(NguoiDung).where(NguoiDung.email.like(f"%@{DOMAIN}")))
    await s.commit()


C = CongTacMa
TT = CongTacTT


async def nap(s: AsyncSession) -> None:
    pw = settings.seed_demo_password
    if len(pw) < 10:
        raise SystemExit("Đặt SEED_DEMO_PASSWORD (>= 10 ký tự) trong .env trước khi seed demo")
    await ensure_reference_data(s)

    # Dự án chính tạo trước → là dự án mặc định (xếp theo created_at).
    da1 = DuAn(ma="DEMO-LO471", ten="Di chuyển ĐZ trung, hạ thế GPMB cao tốc Bắc–Nam · Hà Trung, Thanh Hóa",
               chu_dau_tu="Ban QLDA giao thông (demo)", created_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    da2 = DuAn(ma="DEMO-BL110", ten="ĐZ 110kV Nghi Sơn – Tĩnh Gia (demo)", chu_dau_tu="Chủ đầu tư (demo)")
    s.add_all([da1, da2])
    hashed = hash_password(pw)
    u: dict[str, NguoiDung] = {}
    for key, ten, vai_tro, don_vi, _ in USERS:
        u[key] = NguoiDung(email=f"{key}@{DOMAIN}", mat_khau_hash=hashed, ho_ten=ten, vai_tro=vai_tro, don_vi=don_vi)
        s.add(u[key])
    await s.flush()
    for key, *_, chi_da1 in USERS:
        s.add(ThanhVienDuAn(du_an_id=da1.id, nguoi_dung_id=u[key].id))
        if not chi_da1:
            s.add(ThanhVienDuAn(du_an_id=da2.id, nguoi_dung_id=u[key].id))
    theo_vai_tro = {r: next(x for k, x in u.items() if x.vai_tro == r and x.don_vi is None) for r in CHUOI_DUYET}

    # ================= Dự án 1: Lộ 471 · 22 kV · 64 vị trí · 3,9 km =================
    poles = list(range(1, 65))
    coords = [pos(km_of(k)) for k in poles]
    t_main = Tuyen(du_an_id=da1.id, ma="L471", ten="Lộ 471 · 22 kV", cap_dien_ap="22 kV", loai="moi", nguon="demo", geom=line(coords))
    t_ha = Tuyen(du_an_id=da1.id, ma="HT04", ten="Hạ thế 0,4 kV", cap_dien_ap="0,4 kV", loai="moi", nguon="demo",
                 geom=line([pos(s_, -0.00035) for s_ in [2.0 + i * 0.1 for i in range(11)]]))
    t_cu = Tuyen(du_an_id=da1.id, ma="CU", ten="Tuyến cũ (thu hồi)", cap_dien_ap="22 kV", loai="cu", nguon="demo",
                 geom=line([pos(s_, 0.00075) for s_ in [1.4 + i * 0.12 for i in range(20)]]))
    s.add_all([t_main, t_ha, t_cu])
    await s.flush()

    neo = {1, 8, 16, 24, 31, 38, 45, 52, 58, 64}
    cot: dict[str, ViTriCot] = {}
    for k, xy in zip(poles, coords):
        n = k in neo
        mong8a = n or k in (46, 47)          # móng MT-8a dùng cả cho 2 vị trí đỡ VT46–47 (nền đất yếu)
        km = km_of(k)
        truoc = (km - km_of(k - 1)) * 1000 if k > 1 else None
        sau = (km_of(k + 1) - km) * 1000 if k < 64 else None
        cot[f"VT{k}"] = ViTriCot(
            du_an_id=da1.id, tuyen_id=t_main.id, ten=f"VT{k}", km=round(km, 3),
            loai_mong="MT-8a-20-3,7" if mong8a else "MT-7a-14-2,8",
            a=3.0 if mong8a else 2.5, b=3.0 if mong8a else 3.2, h=3.6 if mong8a else 2.8, k=0.75 if mong8a else 0.5,
            kieu_cot="Néo góc" if n else "Đỡ thẳng",
            cot_ma="LT-20-14" if n else "LT-14-13", cot_ma_npc="NPC.I-20-190-14" if n else "NPC.I-14-190-13",
            xa_ma="XN-22-3N" if n else "XĐ-22-1N", tiep_dia_ma="RC-4", cap_dat="Cấp II" if mong8a else "Cấp I",
            khoang_truoc=round(truoc) if truoc else None, khoang_sau=round(sau) if sau else None,
            vuong_gpmb=(k == 55), geom=pt(*xy))
        s.add(cot[f"VT{k}"])
    await s.flush()

    # ---------- công tác theo vị trí ----------
    spec: dict[tuple[str, CongTacMa], dict] = {}

    def ct(vt: int, ma: CongTacMa, tt: CongTacTT, hoan: date | None = None, nt: date | None = None, *, bb: bool = False,
           chiet_tinh: bool = False, to_doi: str | None = None, kl: float | None = None, ghi_chu: str | None = None):
        spec[(f"VT{vt}", ma)] = dict(trang_thai=tt, ngay_hoan_thanh=hoan, ngay_nghiem_thu=nt, da_co_bien_ban=bb,
                                     co_chiet_tinh=chiet_tinh, to_doi=to_doi, khoi_luong=kl, ghi_chu=ghi_chu)

    def chuoi_cu(vt: int, den: CongTacMa, bat_dau: date):
        """Chuỗi công tác đã nghiệm thu và đã có biên bản từ trước (lịch sử), mỗi công tác cách nhau 2 ngày."""
        x = bat_dau
        for m in [C.dao_mong, C.bt_lot, C.thep_de, C.bt_mong, C.lap_mong, C.dung_cot, C.xa_su, C.keo_day]:
            ct(vt, m, TT.da_nghiem_thu, x, x + timedelta(days=1), bb=True, chiet_tinh=(m == C.dao_mong),
               to_doi="Tổ 3" if m in (C.dao_mong, C.bt_lot, C.thep_de, C.bt_mong, C.lap_mong) else "Tổ 2")
            x += timedelta(days=2)
            if m == den:
                break

    for i, vt in enumerate([33, 34, 35]):
        chuoi_cu(vt, C.keo_day, d(9, 1) + timedelta(days=2 * i))
    for i, vt in enumerate([36, 37]):                               # móng, cột, xà đã có biên bản; kéo dây mới xong 13/10
        chuoi_cu(vt, C.xa_su, d(9, 8) + timedelta(days=2 * i))
        ct(vt, C.keo_day, TT.cho_nghiem_thu, d(10, 13), to_doi="Tổ 2")
    # VT38: móng cũ; dựng cột nghiệm thu 10/10 nhưng hoàn thành 11/10 (R06)
    chuoi_cu(38, C.lap_mong, d(9, 14))
    ct(38, C.dung_cot, TT.da_nghiem_thu, d(10, 11), d(10, 10), to_doi="Tổ 2")
    ct(38, C.xa_su, TT.cho_nghiem_thu, d(10, 12), to_doi="Tổ 2")
    ct(38, C.keo_day, TT.cho_nghiem_thu, d(10, 13), to_doi="Tổ 2")
    chuoi_cu(39, C.lap_mong, d(9, 16))
    ct(39, C.dung_cot, TT.da_nghiem_thu, d(10, 8), d(10, 9), to_doi="Tổ 2")
    ct(39, C.xa_su, TT.da_nghiem_thu, d(10, 9), d(10, 10), to_doi="Tổ 2")
    chuoi_cu(40, C.lap_mong, d(9, 18))
    ct(40, C.dung_cot, TT.da_nghiem_thu, d(10, 8), d(10, 9), to_doi="Tổ 2")
    ct(40, C.xa_su, TT.cho_nghiem_thu, d(10, 9), to_doi="Tổ 2")
    chuoi_cu(41, C.bt_mong, d(9, 20))
    ct(41, C.lap_mong, TT.da_nghiem_thu, d(10, 7), d(10, 8), to_doi="Tổ 3")
    ct(41, C.dung_cot, TT.cho_nghiem_thu, d(10, 12), to_doi="Tổ 2")
    for i, vt in enumerate([42, 43, 44]):
        chuoi_cu(vt, C.bt_mong, d(9, 22) + timedelta(days=2 * i))
        ct(vt, C.lap_mong, TT.da_nghiem_thu, d(10, 7), d(10, 8), to_doi="Tổ 3")
    # VT45: đúng như panel trong thiết kế
    ct(45, C.dao_mong, TT.da_nghiem_thu, d(10, 2), d(10, 3), bb=True, chiet_tinh=True, to_doi="Tổ 3 · Lê Văn Tâm", kl=143.6,
       ghi_chu="Tổ 3 · Lê Văn Tâm · 143,6 m³ · nắng")
    ct(45, C.bt_lot, TT.da_nghiem_thu, d(10, 4), d(10, 5), bb=True, to_doi="Tổ 3", ghi_chu="Tổ 3 · 1,2 m³ · mẫu L-0045")
    ct(45, C.thep_de, TT.da_nghiem_thu, d(10, 7), d(10, 8), bb=True, to_doi="Tổ 3", ghi_chu="Thép lô T-0917 · KQ kéo đạt 20/09")
    ct(45, C.bt_mong, TT.cho_nghiem_thu, d(10, 9), to_doi="Tổ 3", ghi_chu="KL theo mã MT-8a · BB lấy mẫu M-0045")
    ct(45, C.dung_cot, TT.chua_lam, ghi_chu="Kế hoạch tuần 43")
    # VT46, VT47: đang thi công móng, chưa kèm bảng chiết tính
    ct(46, C.dao_mong, TT.cho_nghiem_thu, d(10, 11), to_doi="Tổ 3", kl=142.0)
    ct(46, C.bt_lot, TT.cho_nghiem_thu, d(10, 13), to_doi="Tổ 3")
    ct(47, C.dao_mong, TT.cho_nghiem_thu, d(10, 12), to_doi="Tổ 3", kl=141.5)

    for k in poles:
        for dd in CATALOG:
            x = spec.get((f"VT{k}", dd.ma), dict(trang_thai=TT.chua_lam))
            s.add(CongTac(du_an_id=da1.id, vi_tri_id=cot[f"VT{k}"].id, ma=dd.ma, **x))

    # ---------- lô vật liệu, mẫu bê tông, vật tư theo vị trí ----------
    s.add_all([
        LoVatLieu(du_an_id=da1.id, ma="XM-1009", ten_vat_lieu="Xi măng", nha_cung_cap="Xi măng Nghi Sơn", ngay_giao=d(10, 5),
                  ngay_dung=d(10, 13), dung_tai=["VT46"], cong_tac_ma=C.bt_lot, ngay_lay_mau=d(10, 8),
                  phong_thi_nghiem="phòng LAS", ket_qua_thi_nghiem=None),
        LoVatLieu(du_an_id=da1.id, ma="CV-0212", ten_vat_lieu="Cát vàng", nha_cung_cap="nhà cung cấp thứ hai", ngay_giao=d(10, 12),
                  ngay_dung=d(10, 13), dung_tai=["VT46"], cong_tac_ma=C.bt_lot, ngay_lay_mau=d(10, 9),
                  phong_thi_nghiem="phòng LAS", ket_qua_thi_nghiem="dat", ncc_chap_thuan=False, han_chap_thuan=d(10, 17)),
        LoVatLieu(du_an_id=da1.id, ma="XM-0951", ten_vat_lieu="Xi măng", nha_cung_cap="Xi măng Nghi Sơn", ngay_giao=d(9, 28),
                  ngay_dung=d(10, 4), dung_tai=["VT45"], cong_tac_ma=C.bt_lot, ngay_lay_mau=d(9, 29),
                  phong_thi_nghiem="phòng LAS", ket_qua_thi_nghiem="dat"),
        LoVatLieu(du_an_id=da1.id, ma="T-0917", ten_vat_lieu="Thép tròn", nha_cung_cap="Thép Hòa Phát", ngay_giao=d(9, 15),
                  ngay_dung=d(10, 7), dung_tai=["VT45"], cong_tac_ma=C.thep_de, ngay_lay_mau=d(9, 18),
                  phong_thi_nghiem="phòng LAS", ket_qua_thi_nghiem="dat", ghi_chu_thi_nghiem="KQ kéo đạt 20/09"),
    ])
    for i, ma_mau in enumerate(["M-0045-1", "M-0045-2", "M-0045-3"]):
        s.add(MauBeTong(du_an_id=da1.id, vi_tri_id=cot["VT45"].id, cong_tac_ma=C.bt_mong, ma_mau=ma_mau, ngay_duc=d(10, 9), tuoi_ngay=7, han_nen=d(10, 16)))
    for vt, ma_mau in [("VT42", "M-0042-28"), ("VT43", "M-0043-28")]:
        s.add(MauBeTong(du_an_id=da1.id, vi_tri_id=cot[vt].id, cong_tac_ma=C.bt_mong, ma_mau=ma_mau, ngay_duc=d(10, 2), tuoi_ngay=28, han_nen=d(10, 30)))
    s.add(MauBeTong(du_an_id=da1.id, vi_tri_id=cot["VT44"].id, cong_tac_ma=C.bt_mong, ma_mau="M-0044-7", ngay_duc=d(9, 28), tuoi_ngay=7,
                    han_nen=d(10, 5), ket_qua_mpa=19.6))

    def vat_tu(vt: int, xi_mang: float, thep: float, da_cap_cot: float, can_truoc: date | None):
        c = cot[f"VT{vt}"]
        s.add_all([
            VatTuViTri(du_an_id=da1.id, vi_tri_id=c.id, thu_tu=1, ten="Xi măng PC40", dvt="tấn", dinh_muc=xi_mang, da_cap=xi_mang),
            VatTuViTri(du_an_id=da1.id, vi_tri_id=c.id, thu_tu=2, ten="Thép tròn D ≤ 18", dvt="tấn", dinh_muc=thep, da_cap=thep),
            VatTuViTri(du_an_id=da1.id, vi_tri_id=c.id, thu_tu=3, ten=f"Cột {c.cot_ma}", dvt="cột", dinh_muc=1, da_cap=da_cap_cot,
                       can_truoc_ngay=can_truoc, lead_time_ngay=10 if can_truoc else None),
        ])

    vat_tu(45, 3.22, 0.61, 0, d(10, 18))
    for vt in range(33, 45):
        vat_tu(vt, 3.22 if vt in neo else 1.9, 0.61 if vt in neo else 0.35, 1, None)
    for vt in range(46, 52):
        vat_tu(vt, 3.22 if vt in neo else 1.9, 0.61 if vt in neo else 0.35, 0, d(11, 5))

    # ---------- thư viện mã cấu kiện & kho ----------
    ck = {}
    for ma, ten, dvt, dm_, ton in [
        ("LT-20-14", "Cột BTLT 20 m", "cột", 3, 0), ("LT-14-13", "Cột BTLT 14 m", "cột", 5, 0), ("XN-22-3N", "Xà néo góc 22 kV", "bộ", 2, 0),
        ("RC-4", "Tiếp địa", "bộ", 8, 1), ("AC-95/16", "Dây nhôm lõi thép", "m", 3660, 0), ("M20x80", "Bu lông mạ kẽm", "cái", 64, 12),
    ]:
        ck[ma] = MaCauKien(du_an_id=da1.id, ma=ma, ten=ten, dvt=dvt, dinh_muc=dm_, ton_kho=ton)
        s.add(ck[ma])
    await s.flush()

    # ---------- đề xuất vật tư ----------
    def de_xuat(ma, doan, cong_trinh, nguoi, ngay, can_hang, lan, dong, *, gia=(1_284_500_000, 1_102_300_000), ly_do_vuot=None, tt=TrangThaiDuyet.cho_duyet):
        dx = DeXuatVatTu(du_an_id=da1.id, ma=ma, doan=doan, cong_trinh=cong_trinh, nguoi_lap_id=nguoi.id, ngay_lap=ngay, can_hang=can_hang,
                         giao_tai="Kho công trường Hà Trung", lan_de_xuat=lan, gia_hop_dong=gia[0], gia_khoan=gia[1],
                         ly_do_vuot=ly_do_vuot, trang_thai=tt)
        dx.nguoi_lap = nguoi
        dx.dong = [DeXuatDong(thu_tu=i, ma_cau_kien_id=ck[r[0]].id if r[0] in ck else None, ma_ck=r[0] or "—", ten=r[1], dvt=r[2], mo_ta=r[3],
                              theo_dinh_muc=r[4], da_de_xuat=r[5], ton_kho=r[6], de_xuat=r[7], quy_doi=r[8], hd_so_luong=r[9])
                   for i, r in enumerate(dong, start=1)]
        s.add(dx)
        return dx

    dx12 = de_xuat("ĐX-0412", "VT 41–48", "Lộ 471 · VT 41–48 · 9 dòng vật tư cho móng và dựng cột", u["kythuat"], d(10, 14), d(10, 21), 3, [
        ("LT-20-14", "Cột BTLT 20 m", "cột", "LT-20-14 · NPC.I-20-190-14", 3, 0, 0, 3, "3 cột\nLead-time 10 ngày · đặt trước 11/10 · trễ", 3),
        ("LT-14-13", "Cột BTLT 14 m", "cột", "LT-14-13 · NPC.I-14-190-13", 5, 0, 0, 5, "5 cột", 5),
        ("XN-22-3N", "Xà néo góc 22 kV", "bộ", "XN-22-3N", 2, 0, 0, 2, "2 bộ", 2),
        ("RC-4", "Tiếp địa", "bộ", "RC-4", 8, 4, 1, 3, "3 bộ (đã trừ 1 tồn)", 8),
        ("", "Bê tông M150, đá 2×4", "m³", "trộn tại chỗ · móng MT-7a, MT-8a", 62.4, 34.8, None, 18.6, "Xi măng PC40 5,17 t\nCát vàng 8,72 m³ · Đá 2×4 16,3 m³", 62.4),
        ("", "Thép tròn D ≤ 10", "kg", "đai móng, ván khuôn", 420, 280, 0, 180, "25 cây D10 × 11,7 m", 420),
        ("", "Thép tròn D ≤ 18", "kg", "cốt thép đế, cổ móng", 2440, 1830, 120, 490, "27 cây D16 × 11,7 m", 2440),
        ("AC-95/16", "Dây nhôm lõi thép", "m", "AC-95/16", 3660, 0, 0, 1200, "Đợt 1 / 3 theo tiến độ kéo dây", 3600),
        ("M20x80", "Bu lông mạ kẽm", "cái", "M20×80", 64, 32, 12, 20, "20 cái", 64),
    ], ly_do_vuot="ván khuôn VT 46 hỏng do mưa ngày 12/10, cần làm lại đai.")
    dx11 = de_xuat("ĐX-0411", "VT 33–40", "Lộ 471 · VT 33–40 · 6 dòng vật tư cho dựng cột và kéo dây", u["kythuat"], d(10, 12), d(10, 19), 2, [
        ("LT-14-13", "Cột BTLT 14 m", "cột", "LT-14-13", 6, 0, 0, 6, "6 cột", 6),
        ("XN-22-3N", "Xà néo góc 22 kV", "bộ", "XN-22-3N", 3, 0, 0, 3, "3 bộ", 3),
        ("AC-95/16", "Dây nhôm lõi thép", "m", "AC-95/16", 3660, 1200, 0, 1200, "Đợt 2 / 3 theo tiến độ kéo dây", 3600),
    ])
    dx13 = de_xuat("ĐX-0413", "VT 49–56", "Lộ 471 · VT 49–56 · 2 dòng vật tư cho móng", u["kythuat"], d(10, 14), d(10, 28), 1, [
        ("RC-4", "Tiếp địa", "bộ", "RC-4", 8, 0, 0, 8, "8 bộ", 8),
        ("M20x80", "Bu lông mạ kẽm", "cái", "M20×80", 64, 0, 0, 32, "32 cái", 64),
    ])
    dx14 = de_xuat("ĐX-0414", "VT 57–64", "Lộ 471 · VT 57–64 · 2 dòng vật tư cho móng", u["kythuat"], d(10, 9), d(10, 30), 1, [
        ("RC-4", "Tiếp địa", "bộ", "RC-4", 8, 0, 0, 8, "8 bộ", 8),
        ("XN-22-3N", "Xà néo góc 22 kV", "bộ", "XN-22-3N", 4, 0, 0, 4, "4 bộ", 4),
    ])
    dx10 = de_xuat("ĐX-0410", "VT 33–36", "Lộ 471 · VT 33–36 · 2 dòng vật tư cho dựng cột", u["kythuat"], d(9, 28), d(10, 5), 1, [
        ("LT-14-13", "Cột BTLT 14 m", "cột", "LT-14-13", 4, 0, 0, 4, "4 cột", 4),
        ("XN-22-3N", "Xà néo góc 22 kV", "bộ", "XN-22-3N", 2, 0, 0, 2, "2 bộ", 2),
    ], tt=TrangThaiDuyet.da_duyet)

    def phieu(ma, loai, tieu_de, ly_do, ngay, vt, tac_dong, sau, nguoi):
        p = PhieuDieuChinh(du_an_id=da1.id, ma=ma, loai=loai, tieu_de=tieu_de, ly_do=ly_do, ngay=ngay, nguoi_lap_id=nguoi.id,
                           vi_tri_id=cot[vt].id if vt else None, tac_dong=tac_dong, sau_dieu_chinh=sau, trang_thai=TrangThaiDuyet.cho_duyet)
        s.add(p)
        return p

    p21 = phieu("PĐC-021", PhieuLoai.dieu_chinh, "VT 38 · đổi ngày nghiệm thu dựng cột 10/10 → 11/10",
                "tổ đội báo hoàn thành ngày 11/10, biên bản ghi nhầm ngày.", d(10, 14), "VT38",
                ["BBNT lắp xà, sứ", "BBNT kéo dây", "Nhật ký ngày 11/10"], "không còn vi phạm quy tắc", u["kythuat"])
    p20 = phieu("PĐC-020", PhieuLoai.dieu_chinh, "VT 41 · đổi tổ đội thi công dựng cột",
                "Tổ 2 điều sang đoạn VT 49–56, Tổ 1 thay thế.", d(10, 13), "VT41", ["Nhật ký ngày 12/10"], "không còn vi phạm quy tắc", u["kythuat"])
    n7 = phieu("NTĐK-007", PhieuLoai.nghiem_thu_dk, "VT 45 · nghiệm thu BT móng ngày 15/10, trước khi có kết quả nén 7 ngày",
               "tiến độ lắp móng; chấp nhận nghiệm thu có điều kiện, bổ sung kết quả nén 7 ngày (dự kiến 16/10) trong 48 giờ.", d(10, 14), "VT45",
               ["BBNT bê tông móng (có điều kiện)"], "bổ sung kết quả nén trước 18/10", u["kythuat"])
    n6 = phieu("NTĐK-006", PhieuLoai.nghiem_thu_dk, "VT 44 · nghiệm thu thép đế trước khi có kết quả kéo thép",
               "tiến độ; kết quả kéo thép lô T-0917 dự kiến 12/10.", d(10, 10), "VT44", ["BBNT cốt thép đế móng (có điều kiện)"],
               "bổ sung kết quả kéo thép", u["kythuat"])
    await s.flush()
    ct38 = await s.scalar(select(CongTac).where(CongTac.vi_tri_id == cot["VT38"].id, CongTac.ma == C.dung_cot))
    p21.ap_dung = {"loai": "sua_ngay_nghiem_thu", "cong_tac_id": str(ct38.id), "ngay": "2026-10-11"}

    def chuoi(loai, oid, so_xong: int, moc: list[datetime], ghi: dict[int, str] | None = None):
        ghi = ghi or {}
        for i, r in enumerate(CHUOI_DUYET):
            ng = theo_vai_tro[r]
            if i < so_xong:
                s.add(BuocDuyet(doi_tuong=loai, doi_tuong_id=oid, thu_tu=i + 1, vai_tro=r, nguoi_phu_trach_id=ng.id, nguoi_duyet_id=ng.id,
                                trang_thai=BuocTrangThai.xong, thoi_gian=moc[i], ly_do=ghi.get(i)))
            else:
                s.add(BuocDuyet(doi_tuong=loai, doi_tuong_id=oid, thu_tu=i + 1, vai_tro=r, nguoi_phu_trach_id=ng.id,
                                trang_thai=BuocTrangThai.dang if i == so_xong else BuocTrangThai.cho))

    DX, PH = DoiTuongDuyet.de_xuat, DoiTuongDuyet.phieu_dc
    chuoi(DX, dx12.id, 2, [vn(2026, 10, 14, 8, 12), vn(2026, 10, 14, 9, 30)], {1: "Đã kiểm tồn kho"})
    chuoi(DX, dx11.id, 3, [vn(2026, 10, 12, 8, 40), vn(2026, 10, 12, 14, 5), vn(2026, 10, 13, 9, 0)])
    chuoi(DX, dx13.id, 1, [vn(2026, 10, 14, 7, 55)])
    chuoi(DX, dx14.id, 4, [vn(2026, 10, 9, 8, 0), vn(2026, 10, 9, 10, 0), vn(2026, 10, 10, 9, 0), vn(2026, 10, 12, 16, 0)])
    chuoi(DX, dx10.id, 5, [vn(2026, 9, 28, 8, 0), vn(2026, 9, 28, 15, 0), vn(2026, 9, 29, 9, 0), vn(2026, 9, 30, 10, 0), vn(2026, 10, 1, 9, 0)])
    dx10.trang_thai = TrangThaiDuyet.da_duyet
    chuoi(PH, p21.id, 3, [vn(2026, 10, 14, 7, 30), vn(2026, 10, 14, 8, 40), vn(2026, 10, 14, 9, 48)])
    chuoi(PH, p20.id, 1, [vn(2026, 10, 13, 16, 0)])
    chuoi(PH, n7.id, 3, [vn(2026, 10, 14, 6, 50), vn(2026, 10, 14, 7, 20), vn(2026, 10, 14, 8, 30)])
    chuoi(PH, n6.id, 2, [vn(2026, 10, 10, 17, 0), vn(2026, 10, 11, 8, 0)])

    # ---------- giao hàng ----------
    for dot, po, ngay, tt, hang, ncc, nhan, sl_dat, sl_nhan, dvt, anh in [
        (1, "PO-0388", d(10, 8), GiaoHangTT.da_giao, "thép D16", "Thép Hòa Phát", d(10, 8), 3.0, 3.0, "tấn", True),
        (2, "PO-0388", d(10, 13), GiaoHangTT.da_giao, "thép D16", "Thép Hòa Phát", d(10, 13), 3.0, 1.8, "tấn", False),
        (3, "PO-0388", d(10, 22), GiaoHangTT.cho_giao, "thép D16", "Thép Hòa Phát", None, 3.0, None, "tấn", True),
        (1, "PO-0391", d(10, 18), GiaoHangTT.tren_duong, "cột LT-20-14", "Công ty bê tông ly tâm", None, 3, None, "cột", True),
    ]:
        s.add(DotGiaoHang(du_an_id=da1.id, po=po, dot=dot, ngay_du_kien=ngay, dia_diem="Kho công trường Hà Trung", trang_thai=tt, hang=hang,
                          nha_cung_cap=ncc, ngay_nhan=nhan, sl_dat=sl_dat, sl_nhan=sl_nhan, dvt=dvt, co_anh_phuong_tien=anh))

    # ---------- báo cáo hiện trường (nhật ký) ----------
    def bc(vt, ngay: datetime, ma, nd, anh, nguoi, to_doi, kl=None, nhan_luc=5, may=None, thoi_tiet="Nắng, 31°C", dong_bo=DongBo.da_dong_bo):
        s.add(BaoCaoHienTruong(du_an_id=da1.id, vi_tri_id=cot[vt].id, nguoi_id=nguoi.id, ngay=ngay, noi_dung=nd, so_anh=anh, dong_bo=dong_bo,
                               cong_tac_ma=ma, khoi_luong=kl, to_doi=to_doi, nhan_luc=nhan_luc, may_thi_cong=may or [], thoi_tiet=thoi_tiet))

    T3, T2 = "Tổ 3 · Lê Văn Tâm", "Tổ 2 · Đặng Văn Khoa"
    bc("VT45", vn(2026, 10, 2, 16, 0), C.dao_mong, "Đào hố móng đạt cao độ thiết kế.", 4, u["tam"], T3, 143.6, 6, ["Máy đào 0,8 m³"])
    bc("VT45", vn(2026, 10, 4, 16, 30), C.bt_lot, "Đổ bê tông lót M100, lấy mẫu L-0045.", 3, u["tam"], T3, 1.2, 5, ["Máy bơm nước"])
    bc("VT45", vn(2026, 10, 7, 16, 0), C.thep_de, "Lắp cốt thép, ván khuôn đế móng, thép lô T-0917.", 3, u["tam"], T3, None, 5)
    bc("VT45", vn(2026, 10, 9, 17, 0), C.bt_mong, "Đổ bê tông đúc móng M150, lấy mẫu M-0045 (3 tổ).", 4, u["tam"], T3, 18.6, 7, ["Máy bơm nước"])
    bc("VT46", vn(2026, 10, 11, 16, 0), C.dao_mong, "Đào hố móng VT 46.", 5, u["tam"], T3, 142.0, 6, ["Máy đào 0,8 m³"])
    bc("VT46", vn(2026, 10, 13, 16, 45), C.bt_lot, "Đổ bê tông lót M100 (xi măng lô XM-1009, cát vàng CV-0212).", 4, u["tam"], T3, 1.2, 5)
    bc("VT47", vn(2026, 10, 12, 16, 20), C.dao_mong, "Đào hố móng VT 47.", 5, u["tam"], T3, 141.5, 6, ["Máy đào 0,8 m³"])
    bc("VT41", vn(2026, 10, 12, 15, 0), C.dung_cot, "Dựng cột VT 41.", 3, u["khoa"], T2, None, 8)
    bc("VT38", vn(2026, 10, 11, 15, 30), C.dung_cot, "Dựng cột VT 38.", 3, u["khoa"], T2, None, 8)
    bc("VT38", vn(2026, 10, 12, 15, 30), C.xa_su, "Lắp xà, sứ VT 38.", 3, u["khoa"], T2, None, 6)
    bc("VT38", vn(2026, 10, 13, 15, 40), C.keo_day, "Kéo dây VT 36–38.", 3, u["khoa"], T2, None, 8)
    bc("VT47", vn(2026, 10, 14, 7, 55), C.dao_mong, "Hoàn thiện đáy hố móng VT 47, chờ nghiệm thu.", 2, u["tam"], T3, None, 5, dong_bo=DongBo.cho_dong_bo)

    # ---------- đối soát 3 nguồn theo hạng mục ----------
    def nguon3(hd, bv, cd):
        return [{"nhan": "HỢP ĐỒNG", "ten": hd[0], "mo_ta": hd[1]}, {"nhan": "BẢN VẼ + BẢNG KÊ", "ten": bv[0], "mo_ta": bv[1]},
                {"nhan": "CHỈ DẪN KỸ THUẬT", "ten": cd[0], "mo_ta": cd[1]}]

    chung_hd = ("Phụ lục khối lượng, gói thầu số 04", "PDF 24 trang · trích 312 dòng")
    chung_cd = ("Thuyết minh & chỉ dẫn kỹ thuật", "PDF scan 41 trang · OCR tiếng Việt")
    hm = {}
    for i, (ten, tieu_de, bv) in enumerate([
        ("Chuỗi néo 22 kV", "Chuỗi néo 22 kV · 14 vị trí néo", ("BV-ĐZ-08 chi tiết chuỗi cách điện", "PDF vector 6 trang · bảng kê 64 vị trí")),
        ("Dây dẫn AC-95/16", "Dây dẫn AC-95/16 · toàn tuyến", ("BV-ĐZ-02 mặt cắt dọc tuyến", "PDF vector 12 trang · bảng kê 64 vị trí")),
        ("Móng MT-7a, MT-8a", "Móng MT-7a, MT-8a · 64 vị trí", ("BV-ĐZ-05 móng cột", "PDF vector 8 trang · bảng kê 64 vị trí")),
        ("Xà XN-22-3N", "Xà XN-22-3N · 10 vị trí néo", ("BV-ĐZ-06 xà néo", "PDF vector 4 trang · bảng kê 10 vị trí")),
        ("Cột BTLT 14–20 m", "Cột BTLT 14–20 m · 64 vị trí", ("BV-ĐZ-04 cột bê tông ly tâm", "PDF vector 5 trang · bảng kê 64 vị trí")),
    ]):
        hm[ten] = DoiSoatHangMuc(du_an_id=da1.id, thu_tu=i, ten=ten, tieu_de=tieu_de, nguon=nguon3(chung_hd, bv, chung_cd))
        s.add(hm[ten])
    await s.flush()

    def row(h, i, thong_so, hd, bv, cd, kl, tin_cay, ai, trich, bang_chung=None):
        s.add(DoiSoat(du_an_id=da1.id, hang_muc_id=hm[h].id, thu_tu=i, thong_so=thong_so, hop_dong=hd, ban_ve=bv, chi_dan=cd, ket_luan=kl,
                      tin_cay=tin_cay, ai_de_xuat=ai, trich_dan=trich, bang_chung=bang_chung or []))

    row("Chuỗi néo 22 kV", 0, "Loại bát sứ chuỗi néo", "“Bộ phụ kiện chuỗi néo”, không ghi loại", "Loại 210", "Loại 300", "lech", 0.94,
        "Bản vẽ ghi loại 210, chỉ dẫn kỹ thuật yêu cầu loại 300, hợp đồng không ghi loại: cần phiếu xử lý để thống nhất trước khi đặt hàng.",
        {"hd": "tr. 12, dòng 37", "bv": "BV-ĐZ-08, tr. 3", "cd": "mục 4.2, tr. 17"},
        [{"nguon": "Bản vẽ", "nhan": "[Ảnh trang BV-ĐZ-08, tr. 3]", "bbox": {"x": 0.28, "y": 0.34, "w": 0.34, "h": 0.28}, "tone": "bad",
          "chu_thich": "Bản vẽ: ký hiệu bát sứ loại 210 trong bảng vật liệu chuỗi néo"},
         {"nguon": "Chỉ dẫn kỹ thuật", "nhan": "[Ảnh trang chỉ dẫn KT, tr. 17]", "bbox": {"x": 0.12, "y": 0.42, "w": 0.7, "h": 0.12}, "tone": "ok",
          "chu_thich": "Chỉ dẫn kỹ thuật mục 4.2: chuỗi néo dùng bát sứ loại 300"}])
    row("Chuỗi néo 22 kV", 1, "Số bát sứ mỗi chuỗi", "—", "3", "3", "khop", 0.97, "Bản vẽ và chỉ dẫn kỹ thuật cùng ghi 3 bát/chuỗi.",
        {"bv": "BV-ĐZ-08, tr. 3", "cd": "mục 4.2, tr. 17"})
    row("Chuỗi néo 22 kV", 2, "Số bộ chuỗi néo", "42 bộ", "42 bộ", "—", "khop", None, "Tính từ bảng kê: 14 vị trí néo × 3 pha = 42 bộ.",
        {"hd": "tr. 12, dòng 37", "bv": "14 vị trí néo × 3 pha"})
    row("Chuỗi néo 22 kV", 3, "Chuỗi đỡ lèo", "Không có", "6 bộ", "Có yêu cầu", "thieu_hd", 0.88,
        "Hợp đồng không có chuỗi đỡ lèo nhưng bản vẽ (6 bộ) và chỉ dẫn kỹ thuật đều yêu cầu: cần lập phát sinh.",
        {"bv": "2 vị trí néo góc · BV-ĐZ-08, tr. 5", "cd": "mục 4.4, tr. 18"})
    row("Dây dẫn AC-95/16", 0, "Chiều dài dây dẫn", "3.600 m", "3.660 m", "3.660 m", "lech", 0.96,
        "Hợp đồng 3.600 m, bản vẽ và chỉ dẫn 3.660 m (+1,7%): đề nghị xác nhận khối lượng phát sinh 60 m.",
        {"hd": "tr. 14, dòng 52", "bv": "BV-ĐZ-02, tr. 2", "cd": "mục 5.1, tr. 22"})
    row("Móng MT-7a, MT-8a", 0, "Số lượng móng", "64", "64", "64", "khop", 0.99, "Khớp 3 nguồn.", {})
    row("Xà XN-22-3N", 0, "Số bộ xà néo", "10", "10", "10", "khop", 0.98, "Khớp 3 nguồn.", {})
    row("Cột BTLT 14–20 m", 0, "Số lượng cột", "64", "64", "64", "khop", 0.99, "Khớp 3 nguồn.", {})

    # ---------- kho ----------
    cty = Kho(du_an_id=da1.id, ten="Công ty TNHH Xây lắp điện Tuấn Thành", cap=CapKho.cong_ty, ton=18420)
    s.add(cty)
    await s.flush()
    ct1 = Kho(du_an_id=da1.id, parent_id=cty.id, ten="Kho công trường Hà Trung", cap=CapKho.cong_truong, ton=9620)
    ct2 = Kho(du_an_id=da1.id, parent_id=cty.id, ten="Công trường TBA 110kV Bến Lức", cap=CapKho.cong_truong, ton=5100)
    s.add_all([ct1, ct2])
    await s.flush()
    s.add_all([Kho(du_an_id=da1.id, parent_id=ct1.id, ten="Tổ 1", cap=CapKho.to_doi, ton=3210),
               Kho(du_an_id=da1.id, parent_id=ct1.id, ten="Tổ 2", cap=CapKho.to_doi, ton=2890),
               Kho(du_an_id=da1.id, parent_id=ct1.id, ten="Tổ 3", cap=CapKho.to_doi, ton=1980),
               Kho(du_an_id=da1.id, parent_id=ct2.id, ten="Tổ 4", cap=CapKho.to_doi, ton=2100)])

    # ---------- thông báo mẫu ----------
    s.add_all([
        ThongBao(du_an_id=da1.id, nguoi_nhan_id=u["kythuat"].id, tieu_de="Đợt giao 2 của PO-0388 thiếu ảnh phương tiện",
                 noi_dung="Nhận 13/10 tại kho Hà Trung · 1,8 / 3,0 tấn", lien_ket="/kho", nguoi_gui_id=u["kehoach"].id),
        ThongBao(du_an_id=da1.id, nguoi_nhan_id=u["kehoach"].id, tieu_de="ĐX-0412 chờ Phòng Kế hoạch duyệt",
                 noi_dung="Lộ 471 · VT 41–48 · 9 dòng vật tư", lien_ket="/de-xuat/ĐX-0412", nguoi_gui_id=u["chihuytruong"].id),
    ])

    # ================= Dự án 2: chỉ có tuyến + 6 cột (minh hoạ đa dự án / dữ liệu rỗng) =================
    coords2 = [(105.7400 - i * 0.0050, 19.4500 + i * 0.0030 + 0.0008 * math.sin(i * 1.3)) for i in range(6)]
    t2 = Tuyen(du_an_id=da2.id, ma="L110", ten="ĐZ 110kV Nghi Sơn – Tĩnh Gia (đoạn đầu)", cap_dien_ap="110 kV", loai="moi", nguon="demo", geom=line(coords2))
    s.add(t2)
    await s.flush()
    for i in range(6):
        c2 = ViTriCot(du_an_id=da2.id, tuyen_id=t2.id, ten=f"VT{i + 1}", km=round(i * 0.5, 3), loai_mong="MT-8a-20-3,7", a=3.0, b=3.0, h=3.6, k=0.75,
                      kieu_cot="Néo góc" if i in (0, 5) else "Đỡ thẳng", geom=pt(*coords2[i]))
        s.add(c2)
        await s.flush()
        for dd in CATALOG:
            tt = TT.dang_lam if (i == 0 and dd.ma == C.dao_mong) else TT.chua_lam
            s.add(CongTac(du_an_id=da2.id, vi_tri_id=c2.id, ma=dd.ma, trang_thai=tt))
    s.add(Kho(du_an_id=da2.id, ten=da2.ten, cap=CapKho.cong_truong, ton=0))
    await s.commit()


async def main() -> None:
    if settings.env == "production":
        raise SystemExit("Từ chối seed dữ liệu demo khi ENV=production")
    async with SessionLocal() as s:
        if "--reset" in sys.argv:
            await xoa_demo(s)
        elif await s.scalar(select(DuAn.id).where(DuAn.ma == "DEMO-LO471")):
            print("Dữ liệu demo đã có (dùng --reset để nạp lại).")
            return
        await nap(s)
    print(f"Đã nạp dữ liệu demo. Tài khoản: <{', '.join(k for k, *_ in USERS)}>@{DOMAIN} (mật khẩu = SEED_DEMO_PASSWORD).")


if __name__ == "__main__":
    asyncio.run(main())
