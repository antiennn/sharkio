"""Chống spam alert (FR-5)."""
from datetime import datetime, timedelta, timezone

from app.models import Opportunity


class AlertDeduplicator:
    def __init__(self, cooldown_minutes: float, escalation_ratio: float = 1.5):
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.escalation_ratio = escalation_ratio
        self._sent: dict[tuple, tuple[datetime, float]] = {}

    def filter_new(self, opps: list[Opportunity], now: datetime | None = None) -> list[Opportunity]:
        """Trả về cơ hội cần báo và ghi nhận chúng là đã gửi."""
        now = now or datetime.now(timezone.utc)
        out = []
        for o in opps:
            mag = abs(o.value)
            prev = self._sent.get(o.key)
            if prev:
                sent_at, prev_mag = prev
                in_cooldown = now - sent_at < self.cooldown
                escalated = prev_mag > 0 and mag >= prev_mag * self.escalation_ratio
                if in_cooldown and not escalated:
                    continue
            self._sent[o.key] = (now, mag)
            out.append(o)
        return out
