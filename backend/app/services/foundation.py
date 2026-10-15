import math


def chiet_tinh(a: float, b: float, h: float, k: float) -> dict[str, float]:
    """A1=A+0.4, A2=A1+2Kh; S1=A1·B1 (đáy), S2=A2·B2 (miệng); V=h/3·(S1+S2+√(S1·S2)) (CLAUDE.md, trùng src/lib/foundation.ts)."""
    a1, b1 = a + 0.4, b + 0.4
    a2, b2 = a1 + 2 * k * h, b1 + 2 * k * h
    s1, s2 = a1 * b1, a2 * b2
    return {"A1": a1, "B1": b1, "A2": a2, "B2": b2, "S1": s1, "S2": s2, "V": (h / 3) * (s1 + s2 + math.sqrt(s1 * s2))}


def khoi_luong_ho_mong(a: float, b: float, h: float, k: float) -> float:
    return chiet_tinh(a, b, h, k)["V"]
