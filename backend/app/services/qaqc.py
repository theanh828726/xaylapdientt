"""Tính toán cho màn hình Hồ sơ QA/QC: biên bản sẵn sàng sinh, gộp biên bản, ma trận vị trí × công tác."""
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CongTac, CongTacMa, CongTacTT, MauBeTong, ViTriCot
from . import cong_tac as ct
from . import rules

THU_TU = {d.ma: i for i, d in enumerate(ct.CATALOG)}


@dataclass
class SanSang:
    items: list[CongTac]                       # công tác xong, chưa có biên bản, trong khoảng ngày (gồm cả bị chặn)
    chan: dict[uuid.UUID, list[str]]           # id công tác → mã rule Chặn đang áp dụng

    @property
    def tao_duoc(self) -> list[CongTac]:
        return [c for c in self.items if c.id not in self.chan]

    @property
    def bi_chan(self) -> list[CongTac]:
        return [c for c in self.items if c.id in self.chan]


async def san_sang(s: AsyncSession, du_an_id: uuid.UUID, tu: date, den: date, vp: list[rules.ViPham]) -> SanSang:
    cts = (await s.scalars(select(CongTac).where(
        CongTac.du_an_id == du_an_id, CongTac.da_co_bien_ban.is_(False), CongTac.trang_thai.in_(ct.HOAN_THANH),
        CongTac.ngay_hoan_thanh >= tu, CongTac.ngay_hoan_thanh <= den))).all()
    cts = sorted(cts, key=lambda c: (c.ngay_hoan_thanh, THU_TU[c.ma], c.vi_tri.km))
    r = rules.bi_chan(vp)
    return SanSang(cts, {c.id: r[(c.vi_tri.ten, c.ma)] for c in cts if (c.vi_tri.ten, c.ma) in r})


def gop(items: list[CongTac], kieu: str) -> list[list[CongTac]]:
    """kieu='vi_tri': mỗi công tác một biên bản; 'doan_ngay': gộp các vị trí cùng công tác, cùng ngày hoàn thành."""
    if kieu == "vi_tri":
        return [[c] for c in items]
    nhom: dict[tuple, list[CongTac]] = defaultdict(list)
    for c in items:
        nhom[(c.ma, c.ngay_hoan_thanh)].append(c)
    return list(nhom.values())


def nhan_vi_tri(ds: list[CongTac]) -> str:
    return rules.dai_vt([c.vi_tri.ten for c in ds])


async def ma_tran(s: AsyncSession, du_an_id: uuid.UUID, vp_tat_ca: list[rules.ViPham]) -> dict:
    cot = (await s.scalars(select(ViTriCot).where(ViTriCot.du_an_id == du_an_id).order_by(ViTriCot.km))).all()
    cts = (await s.scalars(select(CongTac).where(CongTac.du_an_id == du_an_id))).all()
    theo: dict[uuid.UUID, dict[CongTacMa, CongTac]] = defaultdict(dict)
    for c in cts:
        theo[c.vi_tri_id][c.ma] = c
    chan = rules.bi_chan(vp_tat_ca)
    r08 = {(v.vi_tri, v.cong_tac) for v in vp_tat_ca if v.ma == "R08" and v.an}
    chua_nen = {(m.vi_tri.ten, m.cong_tac_ma) for m in (await s.scalars(select(MauBeTong).where(MauBeTong.du_an_id == du_an_id,
                                                                                               MauBeTong.ket_qua_mpa.is_(None)))).all()}
    rows = []
    for c in cot:
        m = theo.get(c.id, {})
        if not any(x.trang_thai != CongTacTT.chua_lam for x in m.values()):
            continue
        if all(m[d.ma].trang_thai == CongTacTT.da_nghiem_thu and m[d.ma].da_co_bien_ban for d in ct.CATALOG if d.ma in m) and len(m) == len(ct.CATALOG):
            continue                                       # đã xong và đã phát hành đủ biên bản → không còn việc ở ma trận
        cells = {}
        for d in ct.CATALOG:
            x = m.get(d.ma)
            cell = None
            if (c.ten, d.ma) in chan:
                cell = {"state": "chan", "ma": chan[(c.ten, d.ma)]}
            elif ct.gating_r02(m, d.ma):
                cell = {"state": "chan", "ma": ["R02"]}
            elif x is not None and x.trang_thai == CongTacTT.da_nghiem_thu:
                cell = {"state": "nt"}
            elif x is not None and x.trang_thai == CongTacTT.cho_nghiem_thu:
                cell = ({"state": "thieu", "ma": ["R08"]} if (c.ten, d.ma) in r08
                        else {"state": "cho", "nhan": "chờ nén" if (c.ten, d.ma) in chua_nen else None})
            elif x is not None and x.trang_thai == CongTacTT.dang_lam:
                cell = {"state": "cho", "nhan": "đang làm"}
            cells[d.ma.value] = cell
        rows.append({"viTri": c.ten, "viTriHien": rules.vt_hien(c.ten), "id": str(c.id), "cells": cells})
    return {"cot": [{"ma": d.ma.value, "ten": d.ten, "nhom": d.nhom} for d in ct.CATALOG], "rows": rows}
