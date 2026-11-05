"""Tính trạng thái sức khoẻ — hàm thuần (spec 003 FR-2)."""
from datetime import datetime


def compute_status(
    now: datetime,
    started_at: datetime,
    last_success: datetime | None,
    interval_s: float,
    last_failed: bool,
) -> str:
    if last_success is None:
        return "starting" if (now - started_at).total_seconds() < 3 * interval_s else "down"
    age = (now - last_success).total_seconds()
    if age > 3 * interval_s:
        return "down"
    if last_failed or age > 2 * interval_s:
        return "degraded"
    return "ok"
