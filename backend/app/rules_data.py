"""Danh mục quy tắc R01–R24. Nhóm = phụ lục hồ sơ (PL1 phần móng, PL2 cột + dây, PL3 cắt–đóng điện/hiện trường, PL4 thanh toán/duyệt).
Ngữ nghĩa các rule R02–R06, R08–R11 theo bản thiết kế giao diện (PDF); engine thực thi ở services/rules.py."""
RULES: list[tuple[str, str, str, str]] = [
    ("R01", "Vị trí cột phải có loại móng gán mã thư viện", "Chặn", "PL1"),
    ("R02", "Công tác chỉ bắt đầu khi công tác tiên quyết đã nghiệm thu", "Chặn", "PL1"),
    ("R03", "Vật liệu từ nhà cung cấp chưa được chủ đầu tư chấp thuận", "Chặn", "PL1"),
    ("R04", "Lô vật liệu đã dùng chưa có kết quả thí nghiệm", "Chặn", "PL1"),
    ("R05", "Mẫu bê tông đến hạn nén chưa có kết quả", "Nhắc việc", "PL1"),
    ("R06", "Ngày nghiệm thu sớm hơn ngày hoàn thành công tác", "Chặn", "PL1"),
    ("R07", "Khối lượng đào móng thực tế lệch >5% so với công thức", "Cảnh báo", "PL1"),
    ("R08", "Biên bản đào móng chưa kèm bảng chiết tính", "Cảnh báo", "PL1"),
    ("R09", "Đề xuất vật tư vượt định mức còn lại", "Cảnh báo", "PL2"),
    ("R10", "Cần đặt hàng trước hạn lead-time của vật tư", "Nhắc việc", "PL2"),
    ("R11", "Đợt giao hàng thiếu ảnh phương tiện giao hàng", "Cảnh báo", "PL1"),
    ("R12", "Lô vật liệu đã dùng thiếu chứng chỉ CO/CQ", "Chặn", "PL1"),
    ("R13", "Biên bản chưa đủ chữ ký đúng chuỗi duyệt", "Chặn", "PL4"),
    ("R14", "Phiếu điều chỉnh đang chờ duyệt", "Nhắc việc", "PL4"),
    ("R15", "Giá khoán cao hơn giá hợp đồng", "Cảnh báo", "PL4"),
    ("R16", "Nhật ký thi công bỏ trống quá 2 ngày", "Nhắc việc", "PL3"),
    ("R17", "Vị trí cột vướng GPMB chưa có biên bản bàn giao mặt bằng", "Cảnh báo", "PL3"),
    ("R18", "Hạn đền bù GPMB sắp đến (≤7 ngày)", "Nhắc việc", "PL3"),
    ("R19", "Hồ sơ đệ trình thiếu bản vẽ hoàn công", "Chặn", "PL4"),
    ("R20", "Đệ trình quá hạn phản hồi của chủ đầu tư", "Cảnh báo", "PL4"),
    ("R21", "Thí nghiệm vật liệu hết hiệu lực hiệu chuẩn", "Chặn", "PL1"),
    ("R22", "Mẫu biên bản chưa cập nhật theo văn bản pháp luật mới", "Nhắc việc", "PL4"),
    ("R23", "Khối lượng thanh toán vượt khối lượng nghiệm thu", "Chặn", "PL4"),
    ("R24", "Đề xuất AI (đối soát 3 nguồn) chưa được người có thẩm quyền xác nhận", "Cảnh báo", "PL4"),
]
MUC = {ma: muc for ma, _, muc, _ in RULES}
NHOM = {ma: nhom for ma, _, _, nhom in RULES}
