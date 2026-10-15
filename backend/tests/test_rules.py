from datetime import datetime, timedelta, timezone

from sqlalchemy import select

VN = timezone(timedelta(hours=7))


async def danh_gia(now):
    from app.db import SessionLocal
    from app.models import DuAn
    from app.services import rules
    async with SessionLocal() as s:
        da = await s.scalar(select(DuAn.id).where(DuAn.ma == "DEMO-LO471"))
        return await rules.danh_gia(s, da, now)


def tim(ds, ma, an=False):
    return [v for v in ds if v.ma == ma and v.an == an]


async def test_vi_pham_theo_du_lieu_seed():
    ds = await danh_gia(datetime(2026, 10, 14, 12, 0, tzinfo=VN))
    assert [v.vi_tri for v in tim(ds, "R06")] == ["VT38"] and tim(ds, "R06")[0].muc == "Chặn"
    assert [v.ma for v in ds if not v.an and v.muc == "Chặn"].count("R03") == 1
    assert sorted(v.ma for v in ds if not v.an and v.muc == "Chặn") == ["R03", "R04", "R06"]       # đúng 3 lỗi chặn
    assert len(tim(ds, "R05", an=True)) == 5 and len(tim(ds, "R05")) == 1                          # 5 mẫu chưa nén + dòng tổng hợp
    vt45 = [v for v in tim(ds, "R05", an=True) if v.vi_tri == "VT45"]
    assert len(vt45) == 3 and vt45[0].thong_bao.endswith("Lắp móng đang bị chặn đến khi có kết quả.")
    assert [v.vi_tri for v in tim(ds, "R02", an=True)] == ["VT45"]                                 # chờ tiên quyết, không phải lỗi
    assert [v.vi_tri for v in tim(ds, "R08", an=True)] == ["VT46", "VT47"] and len(tim(ds, "R08")) == 1
    assert tim(ds, "R11")[0].chi_tiet.endswith("1,8 / 3,0 tấn")
    assert tim(ds, "R10")[0].ten == "Cột LT-20-14 cần đặt trước 18/10 (lead-time 10 ngày)"
    assert "thép tròn D ≤ 10 vượt 40 kg" in tim(ds, "R09")[0].thong_bao
    assert [v.vi_tri for v in tim(ds, "R17")] == ["VT55"]
    assert {v.ma for v in ds}.isdisjoint({"R01", "R07", "R12", "R15", "R16"})                    # seed không vi phạm các rule này


async def test_rule_phu_thuoc_thoi_gian():
    assert tim(await danh_gia(datetime(2099, 1, 1, tzinfo=VN)), "R16")         # nhật ký bỏ trống quá 2 ngày
    assert not tim(await danh_gia(datetime(2026, 10, 14, 12, 0, tzinfo=VN)), "R16")  # báo cáo mới nhất 14/10 07:55


async def test_bi_chan_theo_vi_tri_cong_tac():
    from app.models import CongTacMa
    from app.services import rules
    r = rules.bi_chan(await danh_gia(datetime(2026, 10, 14, 12, 0, tzinfo=VN)))
    assert r[("VT38", CongTacMa.dung_cot)] == ["R06"] and set(r[("VT46", CongTacMa.bt_lot)]) == {"R03", "R04"}
    assert ("VT45", CongTacMa.lap_mong) not in r                        # R02 không phải lỗi chặn của biên bản


async def test_danh_muc_rule_va_so_vi_pham(client, H):
    rules = {r["ma"]: r for r in (await client.get("/api/quy-tac", headers=H["giamdoc"])).json()}
    assert len(rules) == 24 and rules["R04"]["nhom"] == "PL1" and rules["R09"]["nhom"] == "PL2"
    assert rules["R03"]["trienKhai"] is True and rules["R03"]["soViPham"] == 1 and rules["R03"]["muc"] == "Chặn"
    assert rules["R13"]["trienKhai"] is False and "lyDoChuaCo" in rules["R13"] and rules["R13"]["soViPham"] == 0
    assert {m for m, r in rules.items() if not r["trienKhai"]} == {"R13", "R18", "R19", "R20", "R21", "R22", "R23"}
    assert rules["R14"]["muc"] == "Nhắc việc"


async def test_vi_pham_sap_chan_truoc(client, H):
    ds = (await client.get("/api/quy-tac/vi-pham", headers=H["kythuat"])).json()
    muc = [v["muc"] for v in ds]
    assert muc == sorted(muc, key=["Chặn", "Cảnh báo", "Nhắc việc"].index) and muc[0] == "Chặn"
    assert (await client.get("/api/quy-tac/vi-pham")).status_code == 401
    pl1 = (await client.get("/api/quy-tac/vi-pham", params={"nhom": "PL1"}, headers=H["kythuat"])).json()
    assert pl1 and all(v["nhom"] == "PL1" for v in pl1)
    assert (await client.get("/api/quy-tac/vi-pham", params={"nhom": "PL9"}, headers=H["kythuat"])).status_code == 422


async def test_r15_chi_nguoi_xem_duoc_ca_hai_gia_moi_thay(client, H):
    r = await client.post("/api/de-xuat-vat-tu", headers=H["giamdoc"], json={
        "congTrinh": "Thử R15 giá khoán vượt", "giaHopDong": 1_000_000, "giaKhoan": 2_000_000,
        "dong": [{"maCK": "LT-20-14", "deXuat": 1, "theoDinhMuc": 1}]})
    assert r.status_code == 201

    async def r15(who):
        return [v for v in (await client.get("/api/quy-tac/vi-pham", headers=H[who])).json() if v["ma"] == "R15"]

    assert len(await r15("giamdoc")) == 1 and len(await r15("ketoan")) == 1
    assert await r15("chihuytruong") == [] and await r15("kythuat") == []   # không lộ quan hệ giá qua cảnh báo
