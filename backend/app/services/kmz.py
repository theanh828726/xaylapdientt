"""Đọc KMZ/KML: lấy đường dây (LineString) và vị trí cột (Point). KMZ chỉ cung cấp hình học;
thông số kỹ thuật (loại móng, A/B/h/K...) không có trong KMZ nên không bao giờ được suy đoán."""
import io
import math
import re
import zipfile
from dataclasses import dataclass

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

MAX_UPLOAD = 20 * 1024 * 1024      # file tải lên
MAX_KML = 50 * 1024 * 1024         # KML sau giải nén (chống zip bomb)
MAX_POINTS = 20000


class KmzError(ValueError):
    pass


@dataclass
class Line:
    ten: str
    coords: list[tuple[float, float]]  # (lon, lat)


@dataclass
class Point:
    ten: str
    lon: float
    lat: float


def chuan_hoa_ten(s: str) -> str:
    """'vt 45' / 'VT-45' → 'VT45' để khớp tên vị trí cột."""
    return re.sub(r"[\s_\-]+", "", s).upper()


def _kml_bytes(data: bytes) -> bytes:
    if data[:2] != b"PK":
        return data
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise KmzError("File KMZ không hợp lệ")
    kmls = [i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith(".kml")]
    if not kmls:
        raise KmzError("KMZ không chứa file .kml")
    info = next((i for i in kmls if i.filename.lower() == "doc.kml"), kmls[0])
    if info.file_size > MAX_KML:
        raise KmzError("File KML bên trong quá lớn")
    with z.open(info) as f:
        kml = f.read(MAX_KML + 1)  # đọc có chặn: file_size trong header có thể bị khai sai
    if len(kml) > MAX_KML:
        raise KmzError("File KML bên trong quá lớn")
    return kml


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _coords(text: str | None) -> list[tuple[float, float]]:
    out = []
    for tok in (text or "").split():
        parts = tok.split(",")
        if len(parts) < 2:
            raise KmzError(f"Toạ độ không hợp lệ: {tok[:40]}")
        try:
            lon, lat = float(parts[0]), float(parts[1])
        except ValueError:
            raise KmzError(f"Toạ độ không hợp lệ: {tok[:40]}")
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise KmzError(f"Toạ độ ngoài phạm vi: {tok[:40]}")
        out.append((lon, lat))
    return out


def parse(data: bytes) -> tuple[list[Line], list[Point]]:
    try:
        root = ET.fromstring(_kml_bytes(data), forbid_dtd=True)
    except (ET.ParseError, DefusedXmlException):
        raise KmzError("KML không hợp lệ hoặc chứa khai báo DTD/entity bị cấm")
    lines: list[Line] = []
    points: list[Point] = []
    total = 0
    for pm in (e for e in root.iter() if _local(e.tag) == "Placemark"):
        name = next((c.text or "" for c in pm if _local(c.tag) == "name"), "").strip()
        for g in pm.iter():
            kind = _local(g.tag)
            if kind not in ("LineString", "Point"):
                continue
            coords = _coords(next((c.text for c in g if _local(c.tag) == "coordinates"), None))
            total += len(coords)
            if total > MAX_POINTS:
                raise KmzError(f"Quá {MAX_POINTS} toạ độ")
            if kind == "LineString" and len(coords) >= 2:
                lines.append(Line(name or f"Tuyến {len(lines) + 1}", coords))
            elif kind == "Point" and len(coords) == 1 and name:
                points.append(Point(name, *coords[0]))
    if not lines and not points:
        raise KmzError("Không tìm thấy đường dây (LineString) hoặc vị trí cột (Point) nào trong file")
    return lines, points
