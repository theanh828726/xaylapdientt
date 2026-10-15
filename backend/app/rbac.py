"""Vai trò, quyền và bộ quyền mặc định. Quyền thực tế nằm trong bảng role_permission (sửa được qua API)."""
import enum


class Role(enum.StrEnum):
    giam_doc = "giam_doc"
    chi_huy_truong = "chi_huy_truong"
    ky_thuat = "ky_thuat"
    ke_toan = "ke_toan"
    phong_ke_hoach = "phong_ke_hoach"
    pho_giam_doc = "pho_giam_doc"
    chu_tich = "chu_tich"


ROLE_LABEL: dict[Role, str] = {
    Role.giam_doc: "Giám đốc",
    Role.chi_huy_truong: "Chỉ huy trưởng",
    Role.ky_thuat: "Kỹ thuật",
    Role.ke_toan: "Kế toán",
    Role.phong_ke_hoach: "Phòng Kế hoạch",
    Role.pho_giam_doc: "Phó Giám đốc",
    Role.chu_tich: "Chủ tịch",
}

ROLE_SHORT: dict[Role, str] = {
    Role.giam_doc: "GĐ", Role.chi_huy_truong: "CHT", Role.ky_thuat: "Kỹ thuật", Role.ke_toan: "Kế toán",
    Role.phong_ke_hoach: "P.KH", Role.pho_giam_doc: "PGĐ", Role.chu_tich: "Chủ tịch",
}
# Gợi ý việc của từng bước (hiện ở luồng duyệt khi chưa đến lượt)
BUOC_GOI_Y: dict[Role, str] = {
    Role.ky_thuat: "Lập từ định mức mã cấu kiện",
    Role.chi_huy_truong: "Kiểm tồn kho, tiến độ hiện trường",
    Role.phong_ke_hoach: "Đối chiếu hợp đồng, bảng kê",
    Role.pho_giam_doc: "Đối chiếu chỉ dẫn kỹ thuật, tồn kho kế toán",
    Role.chu_tich: "Duyệt cuối → kế toán vật tư lập chào giá",
}

# Chuỗi duyệt: Kỹ thuật → CHT → P.KH → PGĐ → Chủ tịch (CLAUDE.md)
CHUOI_DUYET: list[Role] = [
    Role.ky_thuat, Role.chi_huy_truong, Role.phong_ke_hoach, Role.pho_giam_doc, Role.chu_tich,
]


class P(enum.StrEnum):
    gia_hop_dong_xem = "gia_hop_dong.xem"
    gia_khoan_xem = "gia_khoan.xem"
    de_xuat_lap = "de_xuat.lap"
    duyet_thuc_hien = "duyet.thuc_hien"
    duyet_moi_buoc = "duyet.moi_buoc"
    bao_cao_gui = "bao_cao.gui"
    nghiem_thu_xu_ly = "nghiem_thu.xu_ly"
    doi_soat_xac_nhan = "doi_soat.xac_nhan"
    nguoi_dung_quan_ly = "nguoi_dung.quan_ly"
    phan_quyen_quan_ly = "phan_quyen.quan_ly"
    du_an_quan_ly = "du_an.quan_ly"


PERM_MOTA: dict[P, str] = {
    P.gia_hop_dong_xem: "Xem giá hợp đồng",
    P.gia_khoan_xem: "Xem giá khoán",
    P.de_xuat_lap: "Lập đề xuất vật tư / phiếu điều chỉnh",
    P.duyet_thuc_hien: "Duyệt / từ chối bước của vai trò mình",
    P.duyet_moi_buoc: "Duyệt thay mọi bước trong chuỗi duyệt",
    P.bao_cao_gui: "Gửi báo cáo hiện trường",
    P.nghiem_thu_xu_ly: "Xử lý nghiệm thu, sinh biên bản",
    P.doi_soat_xac_nhan: "Xác nhận đề xuất AI ở đối soát 3 nguồn",
    P.nguoi_dung_quan_ly: "Quản lý người dùng",
    P.phan_quyen_quan_ly: "Chỉnh ma trận phân quyền",
    P.du_an_quan_ly: "Tạo / quản lý dự án",
}

_R = Role
DEFAULT_PERMS: dict[Role, set[P]] = {
    _R.giam_doc: set(P),
    _R.chi_huy_truong: {P.gia_khoan_xem, P.de_xuat_lap, P.duyet_thuc_hien, P.bao_cao_gui, P.nghiem_thu_xu_ly, P.doi_soat_xac_nhan},
    _R.ky_thuat: {P.de_xuat_lap, P.duyet_thuc_hien, P.bao_cao_gui, P.nghiem_thu_xu_ly, P.doi_soat_xac_nhan},
    _R.ke_toan: {P.gia_hop_dong_xem, P.gia_khoan_xem},
    _R.phong_ke_hoach: {P.gia_hop_dong_xem, P.gia_khoan_xem, P.duyet_thuc_hien},
    _R.pho_giam_doc: {P.gia_hop_dong_xem, P.gia_khoan_xem, P.duyet_thuc_hien, P.doi_soat_xac_nhan},
    _R.chu_tich: {P.gia_hop_dong_xem, P.gia_khoan_xem, P.duyet_thuc_hien},
}
