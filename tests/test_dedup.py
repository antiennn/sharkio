from datetime import datetime, timedelta, timezone

from app.core.dedup import AlertDeduplicator
from app.core.formatter import format_messages
from app.models import Opportunity, OpportunityType

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def opp(value=0.01, symbol="BTC-USDT"):
    return Opportunity(
        type=OpportunityType.BASIS, symbol=symbol, value=value, basis=value,
        spot_price=100, perp_price=100 * (1 + value), action="x",
    )


def test_ac4_cooldown_blocks_repeat():
    d = AlertDeduplicator(cooldown_minutes=30)
    assert len(d.filter_new([opp()], T0)) == 1
    assert d.filter_new([opp()], T0 + timedelta(minutes=5)) == []
    assert len(d.filter_new([opp()], T0 + timedelta(minutes=31))) == 1


def test_ac4_escalation_resends():
    d = AlertDeduplicator(cooldown_minutes=30, escalation_ratio=1.5)
    d.filter_new([opp(0.01)], T0)
    assert d.filter_new([opp(0.014)], T0 + timedelta(minutes=1)) == []
    assert len(d.filter_new([opp(0.015)], T0 + timedelta(minutes=2))) == 1


def test_direction_change_is_new_alert():
    d = AlertDeduplicator(cooldown_minutes=30)
    d.filter_new([opp(0.01)], T0)
    assert len(d.filter_new([opp(-0.01)], T0 + timedelta(minutes=1))) == 1


def test_formatter_splits_long_messages():
    opps = [opp(0.01, f"COIN{i}-USDT") for i in range(60)]
    msgs = format_messages(opps, max_items=60)
    assert len(msgs) > 1
    assert all(len(m) <= 4096 for m in msgs)
