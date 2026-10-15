from datetime import date, datetime, timedelta, timezone

from ..models import NguoiDung
from ..rbac import ROLE_LABEL

VN = timezone(timedelta(hours=7))  # Việt Nam không có DST


def ngay_gio(dt: datetime) -> str:
    return dt.astimezone(VN).strftime("%Y-%m-%d %H:%M")


def gio_ngan(dt: datetime) -> str:
    return dt.astimezone(VN).strftime("%d/%m %H:%M")


def ngay(d: date) -> str:
    return d.isoformat()


def nguoi_label(u: NguoiDung) -> str:
    return f"{u.don_vi or ROLE_LABEL[u.vai_tro]} – {u.ho_ten}"


def so_vn(x, chu_so: int = 3, co_dinh: bool = False) -> str:
    """Quy ước Việt Nam (dấu . ngăn nghìn, dấu , thập phân). Mặc định bỏ số 0 thừa (1200 → '1.200');
    co_dinh=True giữ nguyên số chữ số thập phân (62 → '62,0' khi chu_so=1)."""
    t = f"{float(x):,.{chu_so}f}"
    if not co_dinh and "." in t:
        t = t.rstrip("0").rstrip(".")
    return t.replace(",", "§").replace(".", ",").replace("§", ".")


def tien(x: int) -> str:
    return f"{x:,}".replace(",", ".") + " đ"


def dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")
