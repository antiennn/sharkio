from datetime import datetime, timezone

import pytest

from app.core.commands import parse_command, parse_set
from app.core.formatter import format_dashboard
from app.state import StateStore


def test_parse_command_strips_botname():
    assert parse_command("/set@SharkBot funding 0.05") == ("set", ["funding", "0.05"])
    assert parse_command("/STATUS") == ("status", [])
    assert parse_command("hello") is None
    assert parse_command(None) is None


def test_ac2_set_funding_percent():
    key, val = parse_set(["funding", "0.03"])
    assert key == "funding_min_rate"
    assert val == pytest.approx(0.0003)
    assert parse_set(["basis", "0,5%"]) == ("basis_min_pct", pytest.approx(0.005))
    assert parse_set(["volume", "300000"]) == ("min_quote_volume_usdt", 300000)


@pytest.mark.parametrize(
    "args", [["funding", "abc"], ["foo", "1"], ["funding"], ["cooldown", "-5"], ["funding", "99"]]
)
def test_ac3_set_invalid(args):
    with pytest.raises(ValueError):
        parse_set(args)


def test_state_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    s = StateStore(str(p))
    s.state.overrides["funding_min_rate"] = 0.0003
    s.state.dashboard_message_id = 42
    s.set_channel("-1001", "My channel")  # đổi channel -> reset dashboard id
    s2 = StateStore(str(p))
    assert s2.state.channel_id == "-1001"
    assert s2.state.overrides == {"funding_min_rate": 0.0003}
    assert s2.state.dashboard_message_id is None


def test_dashboard_empty_and_paused():
    text = format_dashboard([], [], datetime(2026, 1, 1, tzinfo=timezone.utc), paused=True)
    assert "tạm dừng" in text and "00:00:00 UTC" in text
