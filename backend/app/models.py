"""Schema PostgreSQL/PostGIS. Tên bảng/cột tiếng Việt không dấu, khớp thuật ngữ trong src/types.ts."""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .rbac import Role

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = sa.MetaData(naming_convention=NAMING)


def pg_enum(cls: type[enum.Enum], name: str) -> sa.Enum:
    return sa.Enum(cls, name=name, native_enum=False, length=32, create_constraint=True,
                   validate_strings=True, values_callable=lambda e: [m.value for m in e])


class CongTacMa(enum.StrEnum):
    """Công tác thi công theo từng vị trí cột, đúng thứ tự (PL1: móng, PL2: cột + dây)."""
    dao_mong = "dao_mong"
    bt_lot = "bt_lot"
    thep_de = "thep_de"
    bt_mong = "bt_mong"
    lap_mong = "lap_mong"
    dung_cot = "dung_cot"
    xa_su = "xa_su"
    keo_day = "keo_day"


class CongTacTT(enum.StrEnum):
    chua_lam = "chua_lam"
    dang_lam = "dang_lam"
    cho_nghiem_thu = "cho_nghiem_thu"
    da_nghiem_thu = "da_nghiem_thu"


class PhieuLoai(enum.StrEnum):
    dieu_chinh = "dieu_chinh"
    nghiem_thu_dk = "nghiem_thu_dk"     # nghiệm thu có điều kiện


class TrangThaiDuyet(enum.StrEnum):
    cho_duyet = "cho_duyet"
    da_duyet = "da_duyet"
    tu_choi = "tu_choi"


class BuocTrangThai(enum.StrEnum):
    xong = "xong"
    dang = "dang"
    cho = "cho"
    tu_choi = "tu_choi"


class DoiTuongDuyet(enum.StrEnum):
    de_xuat = "de_xuat"
    phieu_dc = "phieu_dc"


class GiaoHangTT(enum.StrEnum):
    da_giao = "da_giao"
    tren_duong = "tren_duong"
    cho_giao = "cho_giao"


class DongBo(enum.StrEnum):
    da_dong_bo = "da_dong_bo"
    cho_dong_bo = "cho_dong_bo"


class QuyetDinhDoiSoat(enum.StrEnum):
    chap_nhan = "chap_nhan"
    hoi_tvgs = "hoi_tvgs"
    da_tao_phieu = "da_tao_phieu"


class CapKho(enum.StrEnum):
    cong_ty = "Công ty"
    cong_truong = "Công trường"
    to_doi = "Tổ đội"


class MucRule(enum.StrEnum):
    chan = "Chặn"
    canh_bao = "Cảnh báo"
    nhac_viec = "Nhắc việc"


UUID_PK = dict(primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()"))


class Stamped:
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())


def du_an_fk() -> Mapped[uuid.UUID]:
    return mapped_column(sa.ForeignKey("du_an.id", ondelete="CASCADE"), index=True)


# ---------- Người dùng, dự án, phân quyền ----------
class DuAn(Base, Stamped):
    __tablename__ = "du_an"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    ma: Mapped[str] = mapped_column(sa.String(40), unique=True)
    ten: Mapped[str] = mapped_column(sa.String(200))
    chu_dau_tu: Mapped[str | None] = mapped_column(sa.String(200))


class NguoiDung(Base, Stamped):
    __tablename__ = "nguoi_dung"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    email: Mapped[str] = mapped_column(sa.String(254), unique=True)  # luôn lưu chữ thường
    mat_khau_hash: Mapped[str] = mapped_column(sa.String(255))
    ho_ten: Mapped[str] = mapped_column(sa.String(120))
    vai_tro: Mapped[Role] = mapped_column(pg_enum(Role, "vai_tro"))
    don_vi: Mapped[str | None] = mapped_column(sa.String(120))  # ví dụ "Tổ đội 2"
    active: Mapped[bool] = mapped_column(server_default=sa.true())


class ThanhVienDuAn(Base):
    __tablename__ = "thanh_vien_du_an"
    du_an_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("du_an.id", ondelete="CASCADE"), primary_key=True)
    nguoi_dung_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permission"
    vai_tro: Mapped[Role] = mapped_column(pg_enum(Role, "vai_tro"), primary_key=True)
    quyen: Mapped[str] = mapped_column(sa.String(60), primary_key=True)


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    nguoi_dung_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(sa.String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())


class DangNhapThatBai(Base):
    """Mỗi lần đăng nhập sai (dùng chung giữa các worker, sống qua khởi động lại). `email_hash` = sha256 của email chuẩn hóa."""
    __tablename__ = "dang_nhap_that_bai"
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(sa.String(64))
    email_hash: Mapped[str] = mapped_column(sa.String(64))
    luc: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    __table_args__ = (sa.Index("ix_dnt_ip_luc", "ip", "luc"), sa.Index("ix_dnt_email_luc", "email_hash", "luc"))


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    du_an_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("du_an.id", ondelete="SET NULL"), index=True)
    nguoi_dung_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    hanh_dong: Mapped[str] = mapped_column(sa.String(60))
    bang: Mapped[str] = mapped_column(sa.String(60))
    doi_tuong_id: Mapped[str | None] = mapped_column(sa.String(64))
    truoc: Mapped[Any | None] = mapped_column(JSONB)
    sau: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())


class RuleDef(Base):
    __tablename__ = "rule_def"
    ma: Mapped[str] = mapped_column(sa.String(8), primary_key=True)
    ten: Mapped[str] = mapped_column(sa.String(300))
    muc: Mapped[MucRule] = mapped_column(pg_enum(MucRule, "muc_rule"))
    module: Mapped[str] = mapped_column(sa.String(8))
    mo_ta: Mapped[str] = mapped_column(sa.String(500), server_default="")


# ---------- Nghiệp vụ: 7 entity trung tâm ----------
class Tuyen(Base, Stamped):
    __tablename__ = "tuyen"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    ma: Mapped[str] = mapped_column(sa.String(40), server_default="")
    ten: Mapped[str] = mapped_column(sa.String(200))
    cap_dien_ap: Mapped[str | None] = mapped_column(sa.String(20))       # "22 kV", "0,4 kV"
    loai: Mapped[str] = mapped_column(sa.String(10), server_default="moi")  # moi | cu (tuyến cũ chờ thu hồi)
    nguon: Mapped[str] = mapped_column(sa.String(20), server_default="demo")  # demo | kmz | nhap_tay
    geom: Mapped[Any] = mapped_column(Geometry("LINESTRING", srid=4326))


class ViTriCot(Base, Stamped):
    __tablename__ = "vi_tri_cot"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "ten"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    tuyen_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("tuyen.id", ondelete="SET NULL"))
    ten: Mapped[str] = mapped_column(sa.String(40))  # VT45
    km: Mapped[Decimal] = mapped_column(sa.Numeric(8, 3))  # km 2.340 hiển thị "Km 2+340"
    loai_mong: Mapped[str] = mapped_column(sa.String(60))  # MT-8a-20-3,7
    a: Mapped[Decimal] = mapped_column(sa.Numeric(8, 3))
    b: Mapped[Decimal] = mapped_column(sa.Numeric(8, 3))
    h: Mapped[Decimal] = mapped_column(sa.Numeric(8, 3))
    k: Mapped[Decimal] = mapped_column(sa.Numeric(8, 3))
    kieu_cot: Mapped[str | None] = mapped_column(sa.String(40))          # Néo góc, Đỡ thẳng…
    cot_ma: Mapped[str | None] = mapped_column(sa.String(60))            # LT-20-14
    cot_ma_npc: Mapped[str | None] = mapped_column(sa.String(80))        # NPC.I-20-190-14
    xa_ma: Mapped[str | None] = mapped_column(sa.String(40))             # XN-22-3N
    tiep_dia_ma: Mapped[str | None] = mapped_column(sa.String(40))       # RC-4
    cap_dat: Mapped[str | None] = mapped_column(sa.String(20))           # Cấp II
    khoang_truoc: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 1))
    khoang_sau: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 1))
    vuong_gpmb: Mapped[bool] = mapped_column(server_default=sa.false())
    geom: Mapped[Any | None] = mapped_column(Geometry("POINT", srid=4326))


class CongTac(Base, Stamped):
    """Tiến độ một công tác tại một vị trí cột; đồng thời là hồ sơ nghiệm thu của công tác đó (entity NghiemThu)."""
    __tablename__ = "cong_tac"
    __table_args__ = (sa.UniqueConstraint("vi_tri_id", "ma"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    vi_tri_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vi_tri_cot.id", ondelete="CASCADE"), index=True)
    ma: Mapped[CongTacMa] = mapped_column(pg_enum(CongTacMa, "cong_tac_ma"))
    trang_thai: Mapped[CongTacTT] = mapped_column(pg_enum(CongTacTT, "cong_tac_tt"), server_default="chua_lam")
    ngay_hoan_thanh: Mapped[date | None]
    ngay_nghiem_thu: Mapped[date | None]
    to_doi: Mapped[str | None] = mapped_column(sa.String(120))
    khoi_luong: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3))
    ghi_chu: Mapped[str | None] = mapped_column(sa.Text)
    co_chiet_tinh: Mapped[bool] = mapped_column(server_default=sa.false())   # đã có bảng chiết tính kèm biên bản (R08)
    da_co_bien_ban: Mapped[bool] = mapped_column(server_default=sa.false())
    vi_tri: Mapped[ViTriCot] = relationship(lazy="joined")


class MauBeTong(Base):
    __tablename__ = "mau_be_tong"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    vi_tri_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vi_tri_cot.id", ondelete="CASCADE"), index=True)
    cong_tac_ma: Mapped[CongTacMa] = mapped_column(pg_enum(CongTacMa, "cong_tac_ma"))
    ma_mau: Mapped[str] = mapped_column(sa.String(40))
    ngay_duc: Mapped[date]
    tuoi_ngay: Mapped[int] = mapped_column(sa.SmallInteger)            # 7 hoặc 28
    han_nen: Mapped[date]
    ket_qua_mpa: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 2))
    vi_tri: Mapped[ViTriCot] = relationship(lazy="joined")


class LoVatLieu(Base):
    """Lô vật liệu nhập về: chấp thuận nhà cung cấp, CO/CQ, thí nghiệm, nơi đã dùng (R03/R04/R12)."""
    __tablename__ = "lo_vat_lieu"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "ma"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    ma: Mapped[str] = mapped_column(sa.String(40))                     # XM-1009
    ten_vat_lieu: Mapped[str] = mapped_column(sa.String(120))
    nha_cung_cap: Mapped[str] = mapped_column(sa.String(160))
    ngay_giao: Mapped[date]
    ngay_dung: Mapped[date | None]
    dung_tai: Mapped[list[str]] = mapped_column(JSONB, server_default=sa.text("'[]'::jsonb"))  # ["VT46"]
    cong_tac_ma: Mapped[CongTacMa | None] = mapped_column(pg_enum(CongTacMa, "cong_tac_ma"))   # công tác đã dùng lô này
    co_cq: Mapped[bool] = mapped_column(server_default=sa.true())
    ncc_chap_thuan: Mapped[bool] = mapped_column(server_default=sa.true())
    han_chap_thuan: Mapped[date | None]
    ngay_lay_mau: Mapped[date | None]
    phong_thi_nghiem: Mapped[str | None] = mapped_column(sa.String(120))
    ket_qua_thi_nghiem: Mapped[str | None] = mapped_column(sa.String(20))   # dat | khong_dat | NULL = chưa có
    ghi_chu_thi_nghiem: Mapped[str | None] = mapped_column(sa.String(300))


class VatTuViTri(Base):
    """Định mức vật tư theo vị trí: định mức, đã cấp, hạn cần đặt hàng (lead-time) — R10."""
    __tablename__ = "vat_tu_vi_tri"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    vi_tri_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vi_tri_cot.id", ondelete="CASCADE"), index=True)
    thu_tu: Mapped[int] = mapped_column(sa.SmallInteger, server_default="0")
    ten: Mapped[str] = mapped_column(sa.String(120))
    dvt: Mapped[str] = mapped_column(sa.String(20))
    dinh_muc: Mapped[Decimal] = mapped_column(sa.Numeric(12, 3))
    da_cap: Mapped[Decimal] = mapped_column(sa.Numeric(12, 3), server_default="0")
    can_truoc_ngay: Mapped[date | None]
    lead_time_ngay: Mapped[int | None] = mapped_column(sa.SmallInteger)


class ThongBao(Base):
    __tablename__ = "thong_bao"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    nguoi_nhan_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="CASCADE"), index=True)
    vai_tro_nhan: Mapped[Role | None] = mapped_column(pg_enum(Role, "vai_tro"))
    tieu_de: Mapped[str] = mapped_column(sa.String(200))
    noi_dung: Mapped[str | None] = mapped_column(sa.String(500))
    lien_ket: Mapped[str | None] = mapped_column(sa.String(200))
    nguoi_gui_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    da_doc: Mapped[bool] = mapped_column(server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())


class MaCauKien(Base, Stamped):
    __tablename__ = "ma_cau_kien"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "ma"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    ma: Mapped[str] = mapped_column(sa.String(40))
    ten: Mapped[str] = mapped_column(sa.String(200))
    dvt: Mapped[str] = mapped_column(sa.String(20))
    dinh_muc: Mapped[Decimal] = mapped_column(sa.Numeric(14, 3))
    ton_kho: Mapped[Decimal] = mapped_column(sa.Numeric(14, 3), server_default="0")


class DeXuatVatTu(Base, Stamped):
    __tablename__ = "de_xuat_vat_tu"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "ma"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    ma: Mapped[str] = mapped_column(sa.String(40))
    cong_trinh: Mapped[str] = mapped_column(sa.String(300))
    nguoi_lap_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("nguoi_dung.id"))
    ngay_lap: Mapped[date]
    gia_hop_dong: Mapped[int | None] = mapped_column(sa.BigInteger)
    gia_khoan: Mapped[int | None] = mapped_column(sa.BigInteger)
    trang_thai: Mapped[TrangThaiDuyet] = mapped_column(pg_enum(TrangThaiDuyet, "trang_thai_duyet"),
                                                       server_default="cho_duyet")
    doan: Mapped[str | None] = mapped_column(sa.String(100))            # "VT 41–48"
    can_hang: Mapped[date | None]
    giao_tai: Mapped[str | None] = mapped_column(sa.String(200))
    lan_de_xuat: Mapped[int] = mapped_column(sa.SmallInteger, server_default="1")
    ly_do_vuot: Mapped[str | None] = mapped_column(sa.Text)            # giải trình của kỹ thuật khi vượt định mức
    nguoi_lap: Mapped[NguoiDung] = relationship(lazy="joined")
    dong: Mapped[list["DeXuatDong"]] = relationship(order_by="DeXuatDong.thu_tu", cascade="all, delete-orphan",
                                                    lazy="selectin")


class DeXuatDong(Base):
    __tablename__ = "de_xuat_dong"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    de_xuat_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("de_xuat_vat_tu.id", ondelete="CASCADE"), index=True)
    thu_tu: Mapped[int] = mapped_column(sa.SmallInteger)
    ma_cau_kien_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("ma_cau_kien.id", ondelete="SET NULL"))
    ma_ck: Mapped[str] = mapped_column(sa.String(40))
    ten: Mapped[str] = mapped_column(sa.String(200))
    dvt: Mapped[str] = mapped_column(sa.String(20))
    theo_dinh_muc: Mapped[Decimal] = mapped_column(sa.Numeric(14, 3))
    de_xuat: Mapped[Decimal] = mapped_column(sa.Numeric(14, 3))
    ton_kho: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 3))  # tồn kho công trường tại thời điểm lập (NULL = không quản lý tồn)
    da_de_xuat: Mapped[Decimal] = mapped_column(sa.Numeric(14, 3), server_default="0")  # đã đề xuất ở các lần trước
    mo_ta: Mapped[str | None] = mapped_column(sa.String(200))          # dòng phụ: mã NPC, "trộn tại chỗ"…
    quy_doi: Mapped[str | None] = mapped_column(sa.Text)               # quy đổi để mua: "Xi măng PC40 5,17 t · Cát vàng …"
    hd_so_luong: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 3))  # số lượng theo hợp đồng (để đối chiếu)


class PhieuDieuChinh(Base, Stamped):
    __tablename__ = "phieu_dieu_chinh"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "ma"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    ma: Mapped[str] = mapped_column(sa.String(40))
    ly_do: Mapped[str] = mapped_column(sa.Text)
    ngay: Mapped[date]
    nguoi_lap_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id"))
    trang_thai: Mapped[TrangThaiDuyet] = mapped_column(pg_enum(TrangThaiDuyet, "trang_thai_duyet"),
                                                       server_default="cho_duyet")
    loai: Mapped[PhieuLoai] = mapped_column(pg_enum(PhieuLoai, "phieu_loai"), server_default="dieu_chinh")
    tieu_de: Mapped[str | None] = mapped_column(sa.String(200))
    vi_tri_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("vi_tri_cot.id", ondelete="SET NULL"))
    tac_dong: Mapped[list[str]] = mapped_column(JSONB, server_default=sa.text("'[]'::jsonb"))   # văn bản bị ảnh hưởng
    sau_dieu_chinh: Mapped[str | None] = mapped_column(sa.Text)
    ap_dung: Mapped[dict | None] = mapped_column(JSONB)               # hành động tự áp dụng khi duyệt xong, vd {"loai":"sua_ngay_nghiem_thu",…}


class BuocDuyet(Base):
    """Chuỗi duyệt dùng chung cho đề xuất vật tư và phiếu điều chỉnh (đối tượng đa hình)."""
    __tablename__ = "buoc_duyet"
    __table_args__ = (
        sa.UniqueConstraint("doi_tuong", "doi_tuong_id", "thu_tu"),
        sa.Index("ix_buoc_duyet_doi_tuong", "doi_tuong", "doi_tuong_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    doi_tuong: Mapped[DoiTuongDuyet] = mapped_column(pg_enum(DoiTuongDuyet, "doi_tuong_duyet"))
    doi_tuong_id: Mapped[uuid.UUID]
    thu_tu: Mapped[int] = mapped_column(sa.SmallInteger)
    vai_tro: Mapped[Role] = mapped_column(pg_enum(Role, "vai_tro"))
    nguoi_phu_trach_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    nguoi_duyet_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    trang_thai: Mapped[BuocTrangThai] = mapped_column(pg_enum(BuocTrangThai, "buoc_trang_thai"))
    thoi_gian: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    ly_do: Mapped[str | None] = mapped_column(sa.Text)
    nguoi_phu_trach: Mapped[NguoiDung | None] = relationship(foreign_keys=[nguoi_phu_trach_id], lazy="joined")
    nguoi_duyet: Mapped[NguoiDung | None] = relationship(foreign_keys=[nguoi_duyet_id], lazy="joined")


class DotGiaoHang(Base, Stamped):
    __tablename__ = "dot_giao_hang"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    po: Mapped[str] = mapped_column(sa.String(40))
    dot: Mapped[int] = mapped_column(sa.SmallInteger)
    ngay_du_kien: Mapped[date]
    dia_diem: Mapped[str] = mapped_column(sa.String(200))
    trang_thai: Mapped[GiaoHangTT] = mapped_column(pg_enum(GiaoHangTT, "giao_hang_tt"))
    hang: Mapped[str] = mapped_column(sa.Text)
    nha_cung_cap: Mapped[str | None] = mapped_column(sa.String(160))
    ngay_nhan: Mapped[date | None]
    sl_dat: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3))
    sl_nhan: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3))
    dvt: Mapped[str | None] = mapped_column(sa.String(20))
    co_anh_phuong_tien: Mapped[bool] = mapped_column(server_default=sa.true())   # R11


class BaoCaoHienTruong(Base, Stamped):
    __tablename__ = "bao_cao_hien_truong"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    vi_tri_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("vi_tri_cot.id", ondelete="CASCADE"), index=True)
    nguoi_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("nguoi_dung.id"))
    ngay: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    noi_dung: Mapped[str] = mapped_column(sa.Text)
    so_anh: Mapped[int] = mapped_column(sa.SmallInteger, server_default="0")
    dong_bo: Mapped[DongBo] = mapped_column(pg_enum(DongBo, "dong_bo"))
    client_id: Mapped[uuid.UUID | None] = mapped_column(unique=True)  # id do thiết bị sinh → đồng bộ offline không trùng
    lat: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 6))
    lon: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 6))
    cong_tac_ma: Mapped[CongTacMa | None] = mapped_column(pg_enum(CongTacMa, "cong_tac_ma"))
    khoi_luong: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3))
    thoi_tiet: Mapped[str | None] = mapped_column(sa.String(60))
    to_doi: Mapped[str | None] = mapped_column(sa.String(120))
    nhan_luc: Mapped[int | None] = mapped_column(sa.SmallInteger)
    may_thi_cong: Mapped[list[str]] = mapped_column(JSONB, server_default=sa.text("'[]'::jsonb"))
    vi_tri: Mapped[ViTriCot] = relationship(lazy="joined")
    nguoi: Mapped[NguoiDung] = relationship(lazy="joined")


# ---------- Phụ trợ ----------
class DoiSoatHangMuc(Base, Stamped):
    """Hạng mục đối soát (Chuỗi néo 22 kV, Dây dẫn AC-95/16…) và ba nguồn tài liệu của nó."""
    __tablename__ = "doi_soat_hang_muc"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    thu_tu: Mapped[int] = mapped_column(sa.SmallInteger, server_default="0")
    ten: Mapped[str] = mapped_column(sa.String(120))
    tieu_de: Mapped[str] = mapped_column(sa.String(200))                # "Chuỗi néo 22 kV · 14 vị trí néo"
    nguon: Mapped[list[dict]] = mapped_column(JSONB, server_default=sa.text("'[]'::jsonb"))  # 3 nguồn: ten, mo_ta, chi_tiet


class DoiSoat(Base, Stamped):
    """Một thông số đối soát Hợp đồng – Bản vẽ – Chỉ dẫn kỹ thuật; quyết định lưu người xác nhận (rule R24)."""
    __tablename__ = "doi_soat"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    thong_so: Mapped[str] = mapped_column(sa.String(200))
    hop_dong: Mapped[str] = mapped_column(sa.String(120))
    ban_ve: Mapped[str] = mapped_column(sa.String(120))
    chi_dan: Mapped[str] = mapped_column(sa.String(120))
    ai_de_xuat: Mapped[str] = mapped_column(sa.Text)
    hang_muc_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("doi_soat_hang_muc.id", ondelete="CASCADE"), index=True)
    thu_tu: Mapped[int] = mapped_column(sa.SmallInteger, server_default="0")
    trich_dan: Mapped[dict] = mapped_column(JSONB, server_default=sa.text("'{}'::jsonb"))     # {hd, bv, cd}: "tr. 12, dòng 37"
    ket_luan: Mapped[str] = mapped_column(sa.String(20), server_default="khop")               # khop | lech | thieu_hd | thieu_bv | thieu_cd
    tin_cay: Mapped[Decimal | None] = mapped_column(sa.Numeric(3, 2))
    bang_chung: Mapped[list[dict]] = mapped_column(JSONB, server_default=sa.text("'[]'::jsonb"))  # vùng AI đọc được
    phieu_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("phieu_dieu_chinh.id", ondelete="SET NULL"))
    quyet_dinh: Mapped[QuyetDinhDoiSoat | None] = mapped_column(pg_enum(QuyetDinhDoiSoat, "quyet_dinh_doi_soat"))
    nguoi_xac_nhan_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class Kho(Base, Stamped):
    __tablename__ = "kho"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    parent_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("kho.id", ondelete="CASCADE"), index=True)
    ten: Mapped[str] = mapped_column(sa.String(200))
    cap: Mapped[CapKho] = mapped_column(pg_enum(CapKho, "cap_kho"))
    ton: Mapped[Decimal] = mapped_column(sa.Numeric(16, 3), server_default="0")


# ---------- Ảnh hiện trường, mẫu biểu, biên bản ----------
class AnhHienTruong(Base):
    __tablename__ = "anh_hien_truong"
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    bao_cao_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("bao_cao_hien_truong.id", ondelete="CASCADE"), index=True)
    nguoi_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("nguoi_dung.id"))
    client_id: Mapped[uuid.UUID | None] = mapped_column(unique=True)  # thiết bị gửi lại không tạo bản sao
    object_key: Mapped[str] = mapped_column(sa.String(300), unique=True)
    ten_file: Mapped[str] = mapped_column(sa.String(200))
    mime: Mapped[str] = mapped_column(sa.String(60))
    kich_thuoc: Mapped[int] = mapped_column(sa.Integer)
    sha256: Mapped[str] = mapped_column(sa.String(64))
    chup_luc: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    lat: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 6))
    lon: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 6))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())


class MauBieu(Base):
    """Mẫu biểu .docx (Jinja qua docxtpl). du_an_id NULL không dùng: mẫu mặc định nằm trong repo, mẫu dự án ở đây."""
    __tablename__ = "mau_bieu"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "loai", "phien_ban"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    loai: Mapped[str] = mapped_column(sa.String(40))
    phien_ban: Mapped[int] = mapped_column(sa.SmallInteger)
    ten_file: Mapped[str] = mapped_column(sa.String(200))
    object_key: Mapped[str] = mapped_column(sa.String(300), unique=True)
    ghi_chu: Mapped[str | None] = mapped_column(sa.String(300))
    dang_dung: Mapped[bool] = mapped_column(server_default=sa.true())
    nguoi_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())


class BienBan(Base):
    """Biên bản đã sinh (lưu file .docx để tải lại đúng bản đã phát hành)."""
    __tablename__ = "bien_ban"
    __table_args__ = (sa.UniqueConstraint("du_an_id", "so"),)
    id: Mapped[uuid.UUID] = mapped_column(**UUID_PK)
    du_an_id: Mapped[uuid.UUID] = du_an_fk()
    loai: Mapped[str] = mapped_column(sa.String(40))
    doi_tuong_id: Mapped[uuid.UUID] = mapped_column(index=True)   # id nghiem_thu
    so: Mapped[str] = mapped_column(sa.String(40))                # BB-NT-2026-0001
    ten_file: Mapped[str] = mapped_column(sa.String(200))
    object_key: Mapped[str] = mapped_column(sa.String(300), unique=True)
    mau_nguon: Mapped[str] = mapped_column(sa.String(60))         # "mac-dinh" hoặc "du-an-v2"
    cong_tac_ids: Mapped[list[str]] = mapped_column(JSONB, server_default=sa.text("'[]'::jsonb"))  # biên bản gộp nhiều công tác/vị trí
    nguoi_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("nguoi_dung.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
