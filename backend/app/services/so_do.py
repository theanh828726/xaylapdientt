"""Chiếu toạ độ lon/lat của các vị trí cột lên khung sơ đồ SVG 820x320 của trang Bản đồ (giữ tỷ lệ, căn giữa)."""
import math

W, H, PAD_X, PAD_Y = 820.0, 320.0, 50.0, 40.0


def chieu(points: list[tuple[float, float] | None]) -> list[tuple[float, float]]:
    valid = [p for p in points if p is not None]
    if not valid:
        return [(PAD_X + i * 62.0, H / 2) for i in range(len(points))]
    lat0 = sum(p[1] for p in valid) / len(valid)
    kx = math.cos(math.radians(lat0))
    xs = [p[0] * kx for p in valid]
    ys = [p[1] for p in valid]
    dx, dy = (max(xs) - min(xs)) or 1e-9, (max(ys) - min(ys)) or 1e-9
    scale = min((W - 2 * PAD_X) / dx, (H - 2 * PAD_Y) / dy)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    out = []
    for i, p in enumerate(points):
        if p is None:
            out.append((PAD_X + i * 62.0, H / 2))
            continue
        out.append((round(W / 2 + (p[0] * kx - cx) * scale, 1), round(H / 2 - (p[1] - cy) * scale, 1)))
    return out
