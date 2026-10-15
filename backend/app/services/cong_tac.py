"""Danh mục công tác thi công và các giá trị suy ra từ tiến độ công tác (bước thi công, khoá công tác tiên quyết…)."""
from dataclasses import dataclass
from datetime import date

from ..models import CongTac, CongTacMa, CongTacTT, ViTriCot
from .foundation import chiet_tinh


@dataclass(frozen=True)
class Def:
    ma: CongTacMa
    ten: str          # nhãn ngắn (ma trận)
    ten_dai: str      # nhãn trong lịch sử thi công
    nhom: str         # phụ lục: PL1 móng, PL2 cột + dây
    tien_quyet: CongTacMa | None
    dong_tu: str      # "Đã đổ bê tông lót" — dùng trong câu thông báo


CATALOG: list[Def] = [
    Def(CongTacMa.dao_mong, "Đào móng", "Đào móng", "PL1", None, "Đã đào móng"),
    Def(CongTacMa.bt_lot, "BT lót", "Bê tông lót M100", "PL1", CongTacMa.dao_mong, "Đã đổ bê tông lót"),
    Def(CongTacMa.thep_de, "Thép đế", "Cốt thép, ván khuôn đế móng", "PL1", CongTacMa.bt_lot, "Đã lắp cốt thép đế móng"),
    Def(CongTacMa.bt_mong, "BT móng", "Bê tông đúc móng M150", "PL1", CongTacMa.thep_de, "Đã đổ bê tông móng"),
    Def(CongTacMa.lap_mong, "Lắp móng", "Lắp móng", "PL1", CongTacMa.bt_mong, "Đã lắp móng"),
    Def(CongTacMa.dung_cot, "Dựng cột", "Dựng cột", "PL2", CongTacMa.lap_mong, "Đã dựng cột"),
    Def(CongTacMa.xa_su, "Xà, sứ", "Lắp xà, sứ", "PL2", CongTacMa.dung_cot, "Đã lắp xà, sứ"),
    Def(CongTacMa.keo_day, "Kéo dây", "Kéo dây", "PL2", CongTacMa.xa_su, "Đã kéo dây"),
]
DEF = {d.ma: d for d in CATALOG}
MONG = [d.ma for d in CATALOG if d.nhom == "PL1"]
NHOM_TEN = {"PL1": "Phần móng", "PL2": "Cột + dây", "PL3": "Cắt – đóng điện", "PL4": "Thanh toán"}

# Bước thi công hiển thị trên bản đồ (từ xa nhất → ban đầu)
BUOC = {
    "da_keo_day": "Đã kéo dây",
    "da_dung_cot": "Đã dựng cột, lắp xà",
    "mong_da_nghiem_thu": "Móng đã nghiệm thu",
    "dang_thi_cong_mong": "Đang thi công móng",
    "chua_thi_cong": "Chưa thi công",
}
HOAN_THANH = (CongTacTT.cho_nghiem_thu, CongTacTT.da_nghiem_thu)


def theo_ma(cts: list[CongTac]) -> dict[CongTacMa, CongTac]:
    return {c.ma: c for c in cts}


def buoc_thi_cong(c: dict[CongTacMa, CongTac]) -> str:
    def xong(ma: CongTacMa) -> bool:
        return ma in c and c[ma].trang_thai in HOAN_THANH
    if xong(CongTacMa.keo_day):
        return "da_keo_day"
    if xong(CongTacMa.dung_cot) or xong(CongTacMa.xa_su):
        return "da_dung_cot"
    if all(m in c and c[m].trang_thai == CongTacTT.da_nghiem_thu for m in MONG):
        return "mong_da_nghiem_thu"
    if any(m in c and c[m].trang_thai != CongTacTT.chua_lam for m in MONG):
        return "dang_thi_cong_mong"
    return "chua_thi_cong"


def tien_do(c: dict[CongTacMa, CongTac]) -> int:
    xong = sum(1 for d in CATALOG if d.ma in c and c[d.ma].trang_thai == CongTacTT.da_nghiem_thu)
    return round(100 * xong / len(CATALOG))


def bi_khoa(c: dict[CongTacMa, CongTac], ma: CongTacMa) -> bool:
    """R02: công tác chỉ bắt đầu khi công tác tiên quyết đã nghiệm thu."""
    tq = DEF[ma].tien_quyet
    return tq is not None and (tq not in c or c[tq].trang_thai != CongTacTT.da_nghiem_thu)


# Công tác phải chờ kết quả/nghiệm thu công tác trước mới được làm (R02). Hiện áp dụng cho lắp móng: cần có kết quả nén bê tông.
GATING_CHO_NT = {CongTacMa.lap_mong}


def gating_r02(c: dict[CongTacMa, CongTac], ma: CongTacMa) -> bool:
    """Công tác chưa làm nhưng công tác tiên quyết đã đổ xong mà CHƯA nghiệm thu → hiện 'bị chặn bởi R02' (đang chờ)."""
    tq = DEF[ma].tien_quyet
    return (ma in GATING_CHO_NT and tq is not None and ma in c and c[ma].trang_thai == CongTacTT.chua_lam
            and tq in c and c[tq].trang_thai == CongTacTT.cho_nghiem_thu)


def tinh_mong(vt: ViTriCot) -> dict:
    a, b, h, k = float(vt.a), float(vt.b), float(vt.h), float(vt.k)
    r = chiet_tinh(a, b, h, k)
    return {"daoDat": round(r["V"], 1), "dienTichMieng": round(r["S2"], 1), "dienTichDay": round(r["S1"], 1)}


def km_text(km) -> str:
    """2.340 → 'Km 2+340'."""
    m = round(float(km) * 1000)
    return f"Km {m // 1000}+{m % 1000:03d}"


def dm(d: date | None) -> str:
    return d.strftime("%d/%m") if d else "—"
