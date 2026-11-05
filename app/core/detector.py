"""Logic phát hiện cơ hội — hàm thuần, không I/O (Constitution III). Spec mục 2, FR-2, FR-3, FR-7."""
from collections.abc import Iterable

from app.models import MarketSnapshot, Opportunity, OpportunityType


def funding_apr(rate: float, interval_hours: float) -> float:
    """APR ước tính = rate × số kỳ/ngày × 365."""
    return rate * (24 / interval_hours) * 365


def filter_symbols(
    snapshots: Iterable[MarketSnapshot],
    min_quote_volume: float,
    whitelist: set[str] | None = None,
    blacklist: set[str] | None = None,
) -> list[MarketSnapshot]:
    out = []
    for s in snapshots:
        if whitelist and s.symbol not in whitelist:
            continue
        if blacklist and s.symbol in blacklist:
            continue
        if not s.has_spot:
            continue  # cả 2 chiến lược đều cần spot
        if s.perp_quote_volume < min_quote_volume or s.spot_quote_volume < min_quote_volume:
            continue
        out.append(s)
    return out


def detect_funding(
    snapshots: Iterable[MarketSnapshot], min_rate: float, interval_hours: float
) -> list[Opportunity]:
    """Funding dương cao + có spot → Mua Spot / Short Perp."""
    out = []
    for s in snapshots:
        if not s.has_spot or s.funding_rate is None or s.funding_rate < min_rate:
            continue
        out.append(
            Opportunity(
                type=OpportunityType.FUNDING,
                symbol=s.symbol,
                value=s.funding_rate,
                spot_price=s.spot_price,
                perp_price=s.perp_price,
                funding_rate=s.funding_rate,
                funding_apr=funding_apr(s.funding_rate, interval_hours),
                basis=s.basis,
                next_funding_time=s.next_funding_time,
                action="Mua Spot + Short Perp (delta-neutral, thu funding)",
            )
        )
    return sorted(out, key=lambda o: o.value, reverse=True)


def detect_basis(
    snapshots: Iterable[MarketSnapshot],
    min_abs_basis: float,
    round_trip_fee: float = 0.0,
    allow_reverse: bool = True,
) -> list[Opportunity]:
    """|basis khớp được| ≥ ngưỡng (spec 005 FR-2: dùng bid/ask, fallback last price).
    allow_reverse=False → chỉ giữ perp > spot (Mua Spot + Short Perp, FR-6)."""
    out = []
    for s in snapshots:
        b = s.exec_basis
        if b is None or abs(b) < min_abs_basis:
            continue
        if b < 0 and not allow_reverse:
            continue
        action = (
            "Perp > Spot: Mua Spot (ask) + Short Perp (bid), chờ hội tụ"
            if b > 0
            else "Perp < Spot: Long Perp (ask) + Bán Spot (bid) — cần có sẵn coin hoặc vay margin"
        )
        spot_px, perp_px = s.exec_prices
        out.append(
            Opportunity(
                type=OpportunityType.BASIS,
                symbol=s.symbol,
                value=b,
                spot_price=spot_px,
                perp_price=perp_px,
                funding_rate=s.funding_rate,
                basis=b,
                basis_last=s.basis,
                depth_usdt=s.exec_depth_usdt,
                net_after_fees=abs(b) - round_trip_fee,
                spot_quote_volume=s.spot_quote_volume,
                perp_quote_volume=s.perp_quote_volume,
                next_funding_time=s.next_funding_time,
                action=action,
            )
        )
    return sorted(out, key=lambda o: abs(o.value), reverse=True)
