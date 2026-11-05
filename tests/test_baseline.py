"""Spec 004 AC-1..AC-4."""
import asyncio

import pytest

from app.config import Settings
from app.core.baseline import basis_series, compute_baseline, evaluate
from app.models import MarketSnapshot
from app.services.scanner import Scanner
from app.state import StateStore


def wobble(center, amp=0.0005, n=96):
    return [center + amp * ((i % 5) - 2) / 2 for i in range(n)]


def test_ac1_structural_not_anomaly():
    base = compute_baseline(wobble(-0.005))
    v = evaluate(-0.0055, base, min_deviation=0.003, min_z=3)
    assert not v.is_anomaly
    assert base.median == pytest.approx(-0.005)


def test_ac2_spike_is_anomaly():
    base = compute_baseline(wobble(-0.001))
    v = evaluate(-0.0056, base, 0.003, 3)
    assert v.is_anomaly
    assert v.deviation == pytest.approx(-0.0046)
    assert v.zscore < -3


def test_flat_history_sigma_zero_uses_deviation_only():
    base = compute_baseline([0.001] * 50)
    assert base.sigma == 0
    assert evaluate(0.006, base, 0.003, 3).is_anomaly
    assert not evaluate(0.002, base, 0.003, 3).is_anomaly


def test_ac4_series_aligns_timestamps():
    spot = {1: 100.0, 2: 100.0, 3: 100.0}
    perp = {2: 101.0, 3: 99.0, 4: 50.0}
    assert basis_series(spot, perp) == pytest.approx([0.01, -0.01])


def test_too_few_points():
    assert compute_baseline([0.01] * 5) is None


# --- tích hợp scanner (FR-3, FR-4 / AC-3) ---
class _TG:
    enabled = False

    async def send(self, *a, **k):
        return None


class _BingX:
    def __init__(self, history_ok=True):
        self.history_ok = history_ok

    async def fetch_snapshots(self):
        mk = lambda s, perp: MarketSnapshot(symbol=s, spot_price=100, perp_price=perp, funding_rate=0.0,
                                            spot_quote_volume=1e8, perp_quote_volume=1e8)
        return [mk("STRUCT-USDT", 99.45), mk("SPIKE-USDT", 99.44)]

    async def fetch_spot_closes(self, symbol, interval, limit):
        if not self.history_ok:
            raise RuntimeError("boom")
        return {t: 100.0 for t in range(limit)}

    async def fetch_perp_closes(self, symbol, interval, limit):
        center = 99.5 if symbol == "STRUCT-USDT" else 99.9
        return {t: center + 0.01 * ((t % 5) - 2) for t in range(limit)}

    async def fetch_funding_history(self, symbol, limit):
        return []


def _scan(tmp_path, history_ok=True):
    s = Settings(_env_file=None, state_file=str(tmp_path / "s.json"),
                 basis_min_pct=0.005, basis_min_deviation_pct=0.003, basis_allow_reverse=True)
    sc = Scanner(s, _BingX(history_ok), _TG(), StateStore(s.state_file))
    return asyncio.run(sc.run_once())


def test_scanner_splits_structural_and_anomaly(tmp_path):
    r = _scan(tmp_path)
    assert r.error is None
    assert [o.symbol for o in r.basis] == ["SPIKE-USDT"]
    assert [o.symbol for o in r.basis_structural] == ["STRUCT-USDT"]
    spike = r.basis[0]
    assert spike.basis_median_24h == pytest.approx(-0.001, abs=1e-4)
    assert spike.history_ok


def test_ac3_history_failure_still_alerts(tmp_path):
    r = _scan(tmp_path, history_ok=False)
    assert {o.symbol for o in r.basis} == {"STRUCT-USDT", "SPIKE-USDT"}
    assert all(o.history_ok is False for o in r.basis)
