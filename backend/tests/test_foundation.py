from app.services.foundation import khoi_luong_ho_mong


def test_cong_thuc_ho_mong_theo_claude_md():
    # A=2.5, B=3.2, h=2.8, K=0.5 → 62.0 m³ (MT-7a-14-2,8)
    assert round(khoi_luong_ho_mong(2.5, 3.2, 2.8, 0.5), 1) == 62.0
