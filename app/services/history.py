"""Lấy & cache lịch sử 24h cho ứng viên (spec 004 FR-4, FR-6, FR-7)."""
import asyncio
import logging
import time
from statistics import mean

from app.config import Settings
from app.core.baseline import BasisBaseline, basis_series, compute_baseline

log = logging.getLogger(__name__)

_MISS = object()


class HistoryService:
    def __init__(self, settings: Settings, bingx, max_concurrency: int = 2):
        self.s = settings
        self.bingx = bingx
        self._sem = asyncio.Semaphore(max_concurrency)
        self._cache: dict[tuple[str, str], tuple[float, object]] = {}

    def _get_cached(self, key):
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < self.s.baseline_cache_minutes * 60:
            return hit[1]
        return _MISS

    def _put(self, key, value):
        self._cache[key] = (time.monotonic(), value)

    async def basis_baseline(self, symbol: str) -> BasisBaseline | None:
        key = ("basis", symbol)
        if (v := self._get_cached(key)) is not _MISS:
            return v
        try:
            async with self._sem:
                spot, perp = await asyncio.gather(
                    self.bingx.fetch_spot_closes(symbol, self.s.baseline_interval, self.s.baseline_limit),
                    self.bingx.fetch_perp_closes(symbol, self.s.baseline_interval, self.s.baseline_limit),
                )
        except Exception as e:  # FR-4: lỗi → None, không cache để lần sau thử lại
            log.warning("Không lấy được lịch sử basis %s: %s", symbol, e)
            return None
        base = compute_baseline(basis_series(spot, perp))
        self._put(key, base)
        return base

    async def funding_avg_24h(self, symbol: str) -> float | None:
        key = ("funding", symbol)
        if (v := self._get_cached(key)) is not _MISS:
            return v
        periods = max(1, round(24 / self.s.funding_interval_hours))
        try:
            async with self._sem:
                rows = await self.bingx.fetch_funding_history(symbol, periods)
        except Exception as e:
            log.warning("Không lấy được lịch sử funding %s: %s", symbol, e)
            return None
        avg = mean(r for _, r in rows[:periods]) if rows else None
        self._put(key, avg)
        return avg
