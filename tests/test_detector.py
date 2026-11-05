import pytest

from app.core.detector import detect_basis, detect_funding, filter_symbols, funding_apr
from app.models import MarketSnapshot, OpportunityType


def snap(symbol="BTC-USDT", spot=100.0, perp=100.0, funding=0.0, vol=1e7):
    return MarketSnapshot(
        symbol=symbol, spot_price=spot, perp_price=perp, funding_rate=funding,
        spot_quote_volume=vol, perp_quote_volume=vol,
    )


def test_ac1_basis_detected():
    opps = detect_basis([snap(spot=100, perp=101)], min_abs_basis=0.005)
    assert len(opps) == 1
    assert opps[0].type is OpportunityType.BASIS
    assert opps[0].value == pytest.approx(0.01)
    assert "Short Perp" in opps[0].action


def test_basis_negative_and_below_threshold():
    opps = detect_basis([snap(spot=100, perp=99), snap("ETH-USDT", spot=100, perp=100.1)], 0.005)
    assert [o.symbol for o in opps] == ["BTC-USDT"]
    assert opps[0].value < 0


def test_ac2_funding_apr():
    assert funding_apr(0.001, 8) == pytest.approx(1.095)
    opps = detect_funding([snap(funding=0.001)], min_rate=0.0005, interval_hours=8)
    assert opps[0].funding_apr == pytest.approx(1.095)


def test_ac3_funding_requires_spot():
    no_spot = MarketSnapshot(symbol="XYZ-USDT", perp_price=1.0, funding_rate=0.01)
    assert detect_funding([no_spot], 0.0005, 8) == []


def test_negative_funding_ignored():
    assert detect_funding([snap(funding=-0.002)], 0.0005, 8) == []


def test_filter_liquidity_and_lists():
    snaps = [snap("A-USDT"), snap("B-USDT", vol=10), snap("C-USDT")]
    assert [s.symbol for s in filter_symbols(snaps, 1e5)] == ["A-USDT", "C-USDT"]
    assert [s.symbol for s in filter_symbols(snaps, 1e5, blacklist={"C-USDT"})] == ["A-USDT"]
    assert [s.symbol for s in filter_symbols(snaps, 1e5, whitelist={"C-USDT"})] == ["C-USDT"]
