"""Spec 003 AC-1..AC-4."""
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router
from app.config import Settings
from app.core.health import compute_status
from app.services.scanner import Scanner
from app.state import StateStore

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
I = 60


def test_ac1_starting():
    assert compute_status(T0 + timedelta(seconds=30), T0, None, I, False) == "starting"


def test_ac2_ok():
    assert compute_status(T0 + timedelta(seconds=70), T0, T0 + timedelta(seconds=60), I, False) == "ok"


def test_ac3_degraded():
    now = T0 + timedelta(seconds=200)
    assert compute_status(now, T0, now - timedelta(seconds=60), I, True) == "degraded"
    assert compute_status(now, T0, now - timedelta(seconds=150), I, False) == "degraded"


def test_ac4_down():
    now = T0 + timedelta(seconds=1000)
    assert compute_status(now, T0, now - timedelta(seconds=200), I, False) == "down"
    assert compute_status(now, T0, None, I, True) == "down"


class _TG:
    enabled = False


def _client(tmp_path) -> tuple[TestClient, Scanner]:
    s = Settings(_env_file=None, state_file=str(tmp_path / "s.json"))
    sc = Scanner(s, None, _TG(), StateStore(s.state_file))
    app = FastAPI()
    app.include_router(router)
    app.state.scanner, app.state.bot = sc, None
    return TestClient(app), sc


def test_endpoint_200_then_503(tmp_path):
    c, sc = _client(tmp_path)
    r = c.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "starting"
    assert r.json()["scan"]["interval_seconds"] == 60
    sc.stats.started_at -= timedelta(hours=1)  # giả lập treo lâu không quét được
    r = c.get("/health")
    assert r.status_code == 503 and r.json()["status"] == "down"
    assert c.get("/health/live").json() == {"alive": True}
