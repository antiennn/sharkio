"""Vòng quét định kỳ (spec 001 FR-1, NFR-2; spec 002 FR-3, FR-4)."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from app.clients.bingx import BingXClient
from app.clients.telegram import TelegramNotifier
from app.config import Settings
from app.core.baseline import evaluate
from app.core.dedup import AlertDeduplicator
from app.core.detector import detect_basis, detect_funding, filter_symbols
from app.core.formatter import format_dashboard, format_messages
from app.models import Opportunity
from app.services.history import HistoryService
from app.state import OVERRIDABLE, StateStore

log = logging.getLogger(__name__)


class ScanResult(BaseModel):
    scanned_at: datetime | None = None
    symbols_total: int = 0
    symbols_eligible: int = 0
    funding: list[Opportunity] = []
    basis: list[Opportunity] = []
    basis_structural: list[Opportunity] = []   # spec 004: lệch thường trực, không báo
    alerted: int = 0
    error: str | None = None


class ScanStats(BaseModel):
    """Số liệu cho /health (spec 003)."""
    started_at: datetime
    scans_total: int = 0
    scans_failed: int = 0
    consecutive_failures: int = 0
    last_success_at: datetime | None = None
    last_duration_ms: int | None = None
    alerts_total: int = 0
    next_scan_at: datetime | None = None
    last_dashboard_at: datetime | None = None


class Scanner:
    def __init__(self, settings: Settings, bingx: BingXClient, telegram: TelegramNotifier, store: StateStore):
        self.s = settings
        self.bingx = bingx
        self.telegram = telegram
        self.store = store
        self.history = HistoryService(settings, bingx)
        self.dedup = AlertDeduplicator(self.param("alert_cooldown_minutes"), settings.alert_escalation_ratio)
        self.last_result = ScanResult()
        self._last_dashboard: datetime | None = None
        self._lock = asyncio.Lock()
        self.stats = ScanStats(started_at=datetime.now(timezone.utc))

    # --- tham số hiệu lực (env + override từ Telegram) ---
    def param(self, key: str) -> float:
        return self.store.state.overrides.get(key, getattr(self.s, key))

    def params(self) -> dict[str, float]:
        return {k: self.param(k) for k in OVERRIDABLE}

    def apply_overrides(self) -> None:
        self.dedup.cooldown = timedelta(minutes=self.param("alert_cooldown_minutes"))

    @property
    def target_chat(self) -> str | None:
        return self.store.state.channel_id or self.s.telegram_chat_id or None

    @property
    def dashboard_enabled(self) -> bool:
        st = self.store.state.dashboard_enabled
        return self.s.dashboard_enabled if st is None else st

    # --- quét ---
    async def run_once(self, force_dashboard: bool = False) -> ScanResult:
        async with self._lock:
            result = ScanResult(scanned_at=datetime.now(timezone.utc))
            try:
                snaps = await self.bingx.fetch_snapshots()
                eligible = filter_symbols(
                    snaps, self.param("min_quote_volume_usdt"), self.s.whitelist, self.s.blacklist
                )
                result.symbols_total = len(snaps)
                result.symbols_eligible = len(eligible)
                result.funding = detect_funding(
                    eligible, self.param("funding_min_rate"), self.s.funding_interval_hours
                )
                candidates = detect_basis(
                    eligible, self.param("basis_min_pct"), self.s.round_trip_fee, self.s.basis_allow_reverse
                )
                if self.s.basis_baseline_enabled:
                    result.basis, result.basis_structural = await self._apply_baseline(candidates)
                    await self._enrich_funding(result.funding)
                else:
                    result.basis = candidates

                if not self.store.state.paused and self.target_chat:
                    new = self.dedup.filter_new(result.funding + result.basis)
                    for msg in format_messages(new, self.s.max_alerts_per_message):
                        await self.telegram.send(msg, self.target_chat)
                    result.alerted = len(new)
                log.info(
                    "Scan: %d/%d eligible, funding=%d basis=%d alerted=%d",
                    result.symbols_eligible, result.symbols_total,
                    len(result.funding), len(result.basis), result.alerted,
                )
            except Exception as e:  # Constitution VI
                log.exception("Scan failed")
                result.error = f"{type(e).__name__}: {e}"
            self.last_result = result

            st = self.stats
            st.scans_total += 1
            st.last_duration_ms = int((datetime.now(timezone.utc) - result.scanned_at).total_seconds() * 1000)
            st.alerts_total += result.alerted
            if result.error:
                st.scans_failed += 1
                st.consecutive_failures += 1
            else:
                st.consecutive_failures = 0
                st.last_success_at = result.scanned_at

            if result.error is None:
                try:
                    await self._maybe_update_dashboard(force_dashboard)
                except Exception:
                    log.exception("Dashboard update failed")
            return result

    # --- spec 004: so với lịch sử 24h của chính coin ---
    async def _apply_baseline(self, candidates: list[Opportunity]) -> tuple[list[Opportunity], list[Opportunity]]:
        bases = await asyncio.gather(*(self.history.basis_baseline(o.symbol) for o in candidates))
        anomalies, structural = [], []
        for o, base in zip(candidates, bases):
            if base is None:                      # FR-4: không có lịch sử → vẫn báo
                o.history_ok = False
                anomalies.append(o)
                continue
            v = evaluate(o.value, base, self.s.basis_min_deviation_pct, self.s.basis_min_zscore)
            o.history_ok = True
            o.basis_median_24h, o.basis_24h_ago = base.median, base.first
            o.basis_low_24h, o.basis_high_24h = base.low, base.high
            o.basis_deviation, o.basis_zscore = v.deviation, v.zscore
            (anomalies if v.is_anomaly else structural).append(o)
        if structural:
            log.info("Bỏ qua basis thường trực: %s", ", ".join(f"{o.symbol} {o.value * 100:+.2f}%" for o in structural))
        return anomalies, structural

    async def _enrich_funding(self, opps: list[Opportunity]) -> None:
        avgs = await asyncio.gather(*(self.history.funding_avg_24h(o.symbol) for o in opps))
        for o, avg in zip(opps, avgs):
            o.funding_avg_24h = avg

    async def post_top(self, chat_id: str | int, limit: int = 10) -> bool:
        """Gửi top cơ hội hiện tại, bỏ qua chống spam (lệnh /top, /post)."""
        r = self.last_result
        opps = r.funding[:limit] + r.basis[:limit]
        msgs = format_messages(opps, limit * 2)
        if not msgs:
            return await self.telegram.send("Hiện không có cơ hội nào vượt ngưỡng.", chat_id) is not None
        ok = True
        for m in msgs:
            ok = await self.telegram.send(m, chat_id) is not None and ok
        return ok

    # --- dashboard ghim (spec 002 FR-3) ---
    async def _maybe_update_dashboard(self, force: bool) -> None:
        chat = self.target_chat
        if not (self.dashboard_enabled and chat and self.telegram.enabled):
            return
        now = datetime.now(timezone.utc)
        due = self._last_dashboard is None or now - self._last_dashboard >= timedelta(
            minutes=self.s.dashboard_interval_minutes
        )
        if not (force or due):
            return
        r = self.last_result
        text = format_dashboard(r.funding, r.basis, now, self.store.state.paused, r.symbols_eligible)
        st = self.store.state
        if st.dashboard_message_id and await self.telegram.edit(chat, st.dashboard_message_id, text):
            self._last_dashboard = self.stats.last_dashboard_at = now
            return
        mid = await self.telegram.send(text, chat, silent=True)
        if mid:
            await self.telegram.pin(chat, mid)
            st.dashboard_message_id = mid
            self.store.save()
            self._last_dashboard = self.stats.last_dashboard_at = now

    async def remove_dashboard(self) -> bool:
        """Spec 002 FR-3b: gỡ ghim + xoá tin dashboard cũ."""
        st, chat = self.store.state, self.target_chat
        if not (st.dashboard_message_id and chat):
            return False
        await self.telegram.unpin(chat, st.dashboard_message_id)
        ok = await self.telegram.delete(chat, st.dashboard_message_id)
        log.info("Đã gỡ dashboard (message %s), xoá=%s", st.dashboard_message_id, ok)
        st.dashboard_message_id = None
        self.store.save()
        self._last_dashboard = None
        return ok

    async def run_forever(self) -> None:
        if not self.dashboard_enabled:
            try:
                await self.remove_dashboard()
            except Exception:
                log.exception("Gỡ dashboard thất bại")
        while True:
            await self.run_once()
            self.stats.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=self.s.scan_interval_seconds)
            await asyncio.sleep(self.s.scan_interval_seconds)
