"""Spec 005 AC-1..AC-4 — số liệu lấy từ BingX thật ngày 2026-11-06."""
import pytest

from app.config import Settings
from app.core.detector import detect_basis
from app.models import MarketSnapshot


def book(last_spot, last_perp, sb, sa, pb, pa, qty=1e6):
    return MarketSnapshot(
        symbol="X-USDT", spot_price=last_spot, perp_price=last_perp,
        spot_quote_volume=5e4, perp_quote_volume=7e5,
        spot_bid=sb, spot_ask=sa, perp_bid=pb, perp_ask=pa,
        spot_bid_qty=qty, spot_ask_qty=qty, perp_bid_qty=qty, perp_ask_qty=qty,
    )


def test_ac1_agi_fake_wide_spread():
    s = book(0.0032, 0.003917, 0.00335, 0.00496, 0.003914, 0.003919)
    assert s.basis > 0.2                    # last price nói +22%
    assert detect_basis([s], 0.02) == []    # nhưng không khớp được


def test_ac2_niulai_real():
    s = book(0.06083, 0.05462, 0.06082, 0.06083, 0.05464, 0.05468, qty=10_000)
    opps = detect_basis([s], 0.02, round_trip_fee=0.003)
    assert len(opps) == 1
    o = opps[0]
    assert o.value == pytest.approx((0.05468 - 0.06082) / 0.06082)   # ≈ −10.1%
    assert o.spot_price == 0.06082 and o.perp_price == 0.05468       # bán spot bid, mua perp ask
    assert o.net_after_fees == pytest.approx(abs(o.value) - 0.003)
    assert o.depth_usdt == pytest.approx(min(0.06082, 0.05468) * 10_000)


def test_ac3_rave_last_price_misleading():
    s = book(0.1385, 0.13213, 0.13094, 0.13927, 0.1323, 0.1324)
    assert s.basis < -0.04
    assert detect_basis([s], 0.02) == []


def test_ac4_no_book_falls_back_to_last():
    s = MarketSnapshot(symbol="Y-USDT", spot_price=100, perp_price=103,
                       spot_quote_volume=1e5, perp_quote_volume=1e5)
    assert detect_basis([s], 0.02)[0].value == pytest.approx(0.03)


def test_fr6_reverse_direction_skipped():
    neg = book(0.06083, 0.05462, 0.06082, 0.06083, 0.05464, 0.05468)
    pos = MarketSnapshot(symbol="P-USDT", spot_price=100, perp_price=103,
                         spot_quote_volume=1e5, perp_quote_volume=1e5)
    opps = detect_basis([neg, pos], 0.02, allow_reverse=False)
    assert [o.symbol for o in opps] == ["P-USDT"]
    assert "Mua Spot" in opps[0].action
    assert Settings(_env_file=None).basis_allow_reverse is False


def test_defaults_spec005():
    s = Settings(_env_file=None)
    assert s.basis_min_pct == 0.02
    assert s.min_quote_volume_usdt == 10_000
    assert s.round_trip_fee == pytest.approx(0.003)
