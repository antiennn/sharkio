"""Định dạng tin Telegram (HTML) — FR-4."""
from datetime import datetime, timezone
from html import escape

from app.models import Opportunity, OpportunityType

TELEGRAM_LIMIT = 4000  # Telegram giới hạn 4096 ký tự, chừa biên


def _fmt_price(p: float) -> str:
    return f"{p:,.2f}" if p >= 100 else f"{p:.6g}"


def _fmt_opp(o: Opportunity) -> str:
    sym = escape(o.symbol)
    url = f"https://bingx.com/en/perpetual/{o.symbol}"
    lines = []
    if o.type is OpportunityType.FUNDING:
        lines.append(f"💰 <b>FUNDING</b> <a href=\"{url}\">{sym}</a>")
        lines.append(f"Funding: <b>{o.funding_rate * 100:.4f}%</b>/kỳ · APR ~<b>{o.funding_apr * 100:.1f}%</b>")
        if o.funding_avg_24h is not None:
            trend = "ổn định" if o.funding_avg_24h >= o.funding_rate * 0.5 else "vừa tăng đột biến"
            lines.append(f"TB 24h: {o.funding_avg_24h * 100:.4f}%/kỳ ({trend})")
        if o.basis is not None:
            lines.append(f"Basis: {o.basis * 100:+.3f}%")
    else:
        icon = "📈" if o.value > 0 else "📉"
        lines.append(f"{icon} <b>BASIS</b> <a href=\"{url}\">{sym}</a>: <b>{o.value * 100:+.2f}%</b> (khớp được)")
        if o.net_after_fees is not None:
            lines.append(f"💵 Lãi ước tính sau phí: <b>{o.net_after_fees * 100:.2f}%</b>")
        extra = []
        if o.basis_last is not None:
            extra.append(f"theo giá khớp cuối {o.basis_last * 100:+.2f}%")
        if o.depth_usdt is not None:
            extra.append(f"vào được ngay ~${o.depth_usdt:,.0f}")
        if extra:
            lines.append(" · ".join(extra))
        if o.spot_quote_volume is not None:
            lines.append(f"Vol 24h: spot ${o.spot_quote_volume:,.0f} · perp ${o.perp_quote_volume:,.0f}")
        if o.history_ok:
            lines.append(
                f"24h trước: {o.basis_24h_ago * 100:+.3f}% · TB 24h: {o.basis_median_24h * 100:+.3f}% "
                f"(khoảng {o.basis_low_24h * 100:+.2f}% → {o.basis_high_24h * 100:+.2f}%)"
            )
            z = f" · z={o.basis_zscore:+.1f}" if o.basis_zscore is not None else ""
            lines.append(f"Lệch so với bình thường: <b>{o.basis_deviation * 100:+.3f}%</b>{z}")
        elif o.history_ok is False:
            lines.append("⚠️ <i>Chưa có dữ liệu 24h để so sánh</i>")
        if o.funding_rate is not None:
            lines.append(f"Funding: {o.funding_rate * 100:.4f}%")
    lines.append(f"Spot {_fmt_price(o.spot_price)} · Perp {_fmt_price(o.perp_price)}")
    if o.next_funding_time:
        lines.append(f"Funding kế: {o.next_funding_time.astimezone(timezone.utc):%H:%M} UTC")
    lines.append(f"➡️ {escape(o.action)}")
    return "\n".join(lines)


def format_dashboard(
    funding: list[Opportunity],
    basis: list[Opportunity],
    updated_at: datetime,
    paused: bool = False,
    eligible: int = 0,
    top_n: int = 10,
) -> str:
    """Tin ghim trong channel (spec 002 FR-3). Luôn chứa thời gian → không bị 'not modified'."""
    lines = ["📊 <b>BingX Arbitrage — Bảng tin</b>"]
    if paused:
        lines.append("⏸ <i>Alert đang tạm dừng</i>")
    lines.append("")
    lines.append("💰 <b>Top Funding</b> (Mua Spot + Short Perp)")
    if funding:
        for i, o in enumerate(funding[:top_n], 1):
            lines.append(
                f"{i}. <code>{escape(o.symbol)}</code> {o.funding_rate * 100:.4f}% · APR {o.funding_apr * 100:.0f}%"
            )
    else:
        lines.append("<i>Không có coin vượt ngưỡng</i>")
    lines.append("")
    lines.append("⚖️ <b>Top Basis</b> (Perp vs Spot)")
    if basis:
        for i, o in enumerate(basis[:top_n], 1):
            lines.append(f"{i}. <code>{escape(o.symbol)}</code> {o.value * 100:+.3f}%")
    else:
        lines.append("<i>Không có coin vượt ngưỡng</i>")
    lines.append("")
    lines.append(f"🔎 {eligible} cặp đủ thanh khoản · cập nhật {updated_at.astimezone(timezone.utc):%H:%M:%S} UTC")
    return "\n".join(lines)[:TELEGRAM_LIMIT]


def format_status(info: dict) -> str:
    """info: channel, paused, dashboard, funding_min_rate, basis_min_pct, min_quote_volume_usdt,
    alert_cooldown_minutes, last_scan, last_error, overrides(list[str])."""
    last = info.get("last_scan")
    lines = [
        "🦈 <b>Sharkio status</b>",
        f"Channel: {escape(str(info.get('channel') or 'chưa có'))}",
        f"Alert: {'⏸ tạm dừng' if info.get('paused') else '▶️ đang chạy'}",
        f"Dashboard: {'bật' if info.get('dashboard') else 'tắt'}",
        "",
        f"Funding min: {info['funding_min_rate'] * 100:.4f}%",
        f"Basis min: {info['basis_min_pct'] * 100:.3f}%",
        f"Volume min: {info['min_quote_volume_usdt']:,.0f} USDT",
        f"Cooldown: {info['alert_cooldown_minutes']:g} phút",
    ]
    if info.get("overrides"):
        lines.append(f"<i>Đã đổi qua Telegram: {', '.join(info['overrides'])}</i>")
    lines.append("")
    lines.append(f"Quét cuối: {last.astimezone(timezone.utc):%H:%M:%S} UTC" if last else "Quét cuối: chưa")
    if info.get("last_error"):
        lines.append(f"⚠️ Lỗi: {escape(info['last_error'])}")
    return "\n".join(lines)


def format_messages(opps: list[Opportunity], max_items: int = 15) -> list[str]:
    """Gộp cơ hội thành các tin ≤ giới hạn Telegram."""
    if not opps:
        return []
    shown = opps[:max_items]
    blocks = [_fmt_opp(o) for o in shown]
    if len(opps) > max_items:
        blocks.append(f"… và {len(opps) - max_items} cơ hội khác (xem /opportunities)")

    header = "🦈 <b>BingX Arbitrage Alert</b>\n"
    messages, cur = [], header
    for b in blocks:
        if len(cur) + len(b) + 2 > TELEGRAM_LIMIT:
            messages.append(cur.rstrip())
            cur = ""
        cur += "\n" + b + "\n"
    if cur.strip():
        messages.append(cur.rstrip())
    return messages
