"""Sinh biên bản/phiếu .docx từ mẫu Word (docxtpl = Jinja trong .docx).

Mẫu mặc định nằm ở app/templates/ (tạo bằng scripts/tao_mau_bieu.py). Mỗi dự án có thể tải mẫu lên để thay thế;
mẫu do người dùng tải lên là Jinja không đáng tin nên luôn render trong SandboxedEnvironment và được thử render
bằng dữ liệu mẫu trước khi nhận.
"""
import asyncio
import io
import zipfile
from datetime import datetime
from pathlib import Path

from docxtpl import DocxTemplate
from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from .format import VN

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_MAU = 5 * 1024 * 1024
MAX_UNZIPPED = 30 * 1024 * 1024


class MauError(ValueError):
    pass


# ---- Danh mục mẫu và biến dùng được (hiển thị trong màn hình Biểu mẫu để người dùng tự chỉnh) ----
_CHUNG = [("du_an.ten", "Tên dự án/công trình"), ("du_an.chu_dau_tu", "Chủ đầu tư"), ("ngay.ngay / ngay.thang / ngay.nam", "Ngày, tháng, năm lập"),
          ("ngay.gio_phut", "Giờ:phút lập"), ("nguoi_lap.ho_ten / nguoi_lap.chuc_danh", "Người thao tác phát hành")]
LOAI: dict[str, dict] = {
    "nghiem_thu_cong_viec": {
        "ten": "Biên bản nghiệm thu công việc xây dựng (móng cột)",
        "bien": [*_CHUNG, ("so", "Số biên bản (BB-NT-năm-số thứ tự)"), ("hang_muc", "Hạng mục nghiệm thu"),
                 ("vi_tri.ten / vi_tri.km / vi_tri.loai_mong", "Vị trí cột, km, loại móng"),
                 ("vi_tri.khoi_luong", "Khối lượng hố móng theo công thức (m³)"), ("phu_luc", "Phụ lục hồ sơ đã có (vd PL1–PL6)"),
                 ("thanh_phan[]  (ho_ten, chuc_danh, don_vi)", "Thành phần nghiệm thu — lặp bằng {%tr for t in thanh_phan %}")],
    },
    "de_xuat_vat_tu": {
        "ten": "Phiếu đề xuất vật tư",
        "bien": [*_CHUNG, ("ma", "Mã đề xuất"), ("cong_trinh", "Công trình/đoạn tuyến"), ("nguoi_lap_ten", "Người lập đề xuất"),
                 ("ngay_lap", "Ngày lập đề xuất"), ("trang_thai", "Trạng thái duyệt"),
                 ("gia_hop_dong / gia_khoan", "Giá (hiện '—' nếu người in không có quyền xem giá)"),
                 ("dong[]  (stt, ma_ck, ten, dvt, theo_dinh_muc, de_xuat, ton_kho)", "Các dòng vật tư — {%tr for r in dong %}"),
                 ("chuoi_duyet[]  (stt, vai_tro, nguoi, trang_thai, thoi_gian, ly_do)", "Chuỗi phê duyệt — {%tr for b in chuoi_duyet %}")],
    },
    "phieu_dieu_chinh": {
        "ten": "Phiếu điều chỉnh thiết kế",
        "bien": [*_CHUNG, ("ma", "Mã phiếu"), ("ly_do", "Lý do điều chỉnh"), ("ngay_lap", "Ngày lập phiếu"), ("trang_thai", "Trạng thái duyệt"),
                 ("chuoi_duyet[]  (stt, vai_tro, nguoi, trang_thai, thoi_gian, ly_do)", "Chuỗi phê duyệt — {%tr for b in chuoi_duyet %}")],
    },
}

_NGAY_MAU = {"ngay": "01", "thang": "01", "nam": "2026", "gio_phut": "08:00"}
MAU_THU: dict[str, dict] = {   # dữ liệu giả để thử render mẫu người dùng tải lên
    "nghiem_thu_cong_viec": {
        "so": "BB-NT-2026-0001", "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "Chủ đầu tư mẫu"}, "ngay": _NGAY_MAU,
        "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"}, "hang_muc": "Móng", "phu_luc": "PL1–PL6",
        "vi_tri": {"ten": "VT01", "km": "1,00", "loai_mong": "MT-7a", "khoi_luong": "62,0"},
        "thanh_phan": [{"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật", "don_vi": "Nhà thầu"}],
    },
    "de_xuat_vat_tu": {
        "ma": "ĐX-0001", "cong_trinh": "Công trình mẫu", "nguoi_lap_ten": "Kỹ thuật – Nguyễn Văn A", "ngay_lap": "01/01/2026",
        "trang_thai": "Đang chờ duyệt", "gia_hop_dong": "—", "gia_khoan": "—", "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "CĐT"},
        "ngay": _NGAY_MAU, "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"},
        "dong": [{"stt": 1, "ma_ck": "X", "ten": "Vật tư", "dvt": "bộ", "theo_dinh_muc": "1", "de_xuat": "1", "ton_kho": "1"}],
        "chuoi_duyet": [{"stt": 1, "vai_tro": "Kỹ thuật", "nguoi": "A", "trang_thai": "Đã duyệt", "thoi_gian": "01/01 08:00", "ly_do": ""}],
    },
    "phieu_dieu_chinh": {
        "ma": "ĐC-001", "ly_do": "Lý do mẫu", "ngay_lap": "01/01/2026", "trang_thai": "Đang chờ duyệt",
        "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "CĐT"}, "ngay": _NGAY_MAU,
        "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"},
        "chuoi_duyet": [{"stt": 1, "vai_tro": "Kỹ thuật", "nguoi": "A", "trang_thai": "Đã duyệt", "thoi_gian": "01/01 08:00", "ly_do": ""}],
    },
}


def ngay_ctx(now: datetime) -> dict:
    d = now.astimezone(VN)
    return {"ngay": f"{d.day:02d}", "thang": f"{d.month:02d}", "nam": str(d.year), "gio_phut": d.strftime("%H:%M")}


def mac_dinh(loai: str) -> bytes:
    return (TEMPLATES_DIR / f"{loai}.docx").read_bytes()


def _render(mau: bytes, ctx: dict) -> bytes:
    try:
        doc = DocxTemplate(io.BytesIO(mau))
        doc.render(ctx, jinja_env=SandboxedEnvironment(), autoescape=True)
        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()
    except TemplateError as e:                         # cú pháp sai, biến không tồn tại, vi phạm sandbox
        raise MauError(f"Mẫu không hợp lệ: {e}")
    except (zipfile.BadZipFile, KeyError) as e:
        raise MauError(f"File không phải mẫu Word (.docx) hợp lệ: {e}")


async def render(mau: bytes, ctx: dict) -> bytes:
    return await asyncio.to_thread(_render, mau, ctx)


async def kiem_tra_mau(data: bytes, loai: str) -> None:
    """Nhận mẫu tải lên chỉ khi: là .docx hợp lệ, không quá lớn và render được bằng dữ liệu mẫu."""
    if len(data) > MAX_MAU:
        raise MauError("Mẫu quá lớn (tối đa 5 MB)")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        if "word/document.xml" not in names:
            raise MauError("File không phải .docx (thiếu word/document.xml)")
        if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
            raise MauError("Nội dung giải nén của mẫu quá lớn")
    except zipfile.BadZipFile:
        raise MauError("File không phải .docx hợp lệ")
    await render(data, MAU_THU[loai])


# ---- Mở rộng theo thiết kế màn hình QA/QC: biên bản gộp nhiều vị trí, giấy mời, bảng chiết tính, đề trình nhà cung cấp ----
LOAI["nghiem_thu_cong_viec"] = {
    "ten": "Biên bản nghiệm thu công việc xây dựng",
    "bien": [*_CHUNG, ("so", "Số biên bản (BB-NT-năm-số thứ tự)"), ("hang_muc", "Công tác nghiệm thu (Đào móng, Dựng cột…)"),
             ("vi_tri_text", "Các vị trí nghiệm thu, vd 'VT 39–40'"), ("ngay_hoan_thanh", "Ngày hoàn thành công tác"),
             ("phu_luc", "Nhóm hồ sơ (PL1 · Phần móng…)"),
             ("danh_sach[]  (stt, ten, km, loai_mong, khoi_luong)", "Danh sách vị trí — lặp bằng {%tr for v in danh_sach %}"),
             ("thanh_phan[]  (ho_ten, chuc_danh, don_vi)", "Thành phần nghiệm thu — {%tr for t in thanh_phan %}")],
}
LOAI["giay_moi_nghiem_thu"] = {
    "ten": "Giấy mời nghiệm thu",
    "bien": [*_CHUNG, ("so", "Số giấy mời (GM-NT-năm-số thứ tự)"), ("cong_viec", "Công tác cần nghiệm thu"), ("vi_tri_text", "Các vị trí"),
             ("ngay_nghiem_thu", "Ngày nghiệm thu dự kiến")],
}
LOAI["bang_chiet_tinh"] = {
    "ten": "Bảng chiết tính khối lượng hố móng",
    "bien": [*_CHUNG, ("so", "Số bảng (CT-năm-số thứ tự)"), ("cong_viec", "Công tác kèm theo"),
             ("rows[]  (stt, vi_tri, loai_mong, a, b, h, k, s_day, s_mieng, v)", "Các vị trí — {%tr for r in rows %}"), ("tong_v", "Tổng khối lượng (m³)")],
}
LOAI["de_trinh_nha_cung_cap"] = {
    "ten": "Đề trình chấp thuận nhà cung cấp vật liệu",
    "bien": [*_CHUNG, ("vat_lieu.ten / vat_lieu.ma", "Vật liệu và mã lô"), ("vat_lieu.nha_cung_cap", "Nhà cung cấp"),
             ("vat_lieu.ngay_giao / vat_lieu.dung_tai", "Ngày giao và vị trí đã dùng"), ("vat_lieu.han", "Hạn cần có văn bản chấp thuận")],
}

MAU_THU["nghiem_thu_cong_viec"] = {
    "so": "BB-NT-2026-0001", "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "Chủ đầu tư mẫu"}, "ngay": _NGAY_MAU,
    "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"}, "hang_muc": "Đào móng", "phu_luc": "PL1 · Phần móng",
    "vi_tri_text": "VT 01–02", "ngay_hoan_thanh": "01/01/2026",
    "danh_sach": [{"stt": 1, "ten": "VT01", "km": "Km 0+100", "loai_mong": "MT-7a", "khoi_luong": "62,0"}],
    "thanh_phan": [{"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật", "don_vi": "Nhà thầu"}],
}
MAU_THU["giay_moi_nghiem_thu"] = {
    "so": "GM-NT-2026-0001", "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "CĐT"}, "ngay": _NGAY_MAU,
    "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"}, "cong_viec": "Đào móng", "vi_tri_text": "VT 01", "ngay_nghiem_thu": "02/01/2026",
}
MAU_THU["bang_chiet_tinh"] = {
    "so": "CT-2026-0001", "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "CĐT"}, "ngay": _NGAY_MAU,
    "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"}, "cong_viec": "Đào móng", "tong_v": "62,0",
    "rows": [{"stt": 1, "vi_tri": "VT01", "loai_mong": "MT-7a", "a": "2,5", "b": "3,2", "h": "2,8", "k": "0,5", "s_day": "11,6", "s_mieng": "78,0", "v": "62,0"}],
}
MAU_THU["de_trinh_nha_cung_cap"] = {
    "du_an": {"ten": "Dự án mẫu", "chu_dau_tu": "CĐT"}, "ngay": _NGAY_MAU, "nguoi_lap": {"ho_ten": "Nguyễn Văn A", "chuc_danh": "Kỹ thuật"},
    "vat_lieu": {"ten": "Cát vàng", "ma": "CV-0001", "nha_cung_cap": "Nhà cung cấp mẫu", "ngay_giao": "01/01/2026", "dung_tai": "VT 01", "han": "10/01/2026"},
}
