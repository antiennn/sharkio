"""BingX public market data client (plan.md — 3 request / chu kỳ)."""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.models import MarketSnapshot

log = logging.getLogger(__name__)

SPOT_TICKER = "/openApi/spot/v1/ticker/24hr"
SWAP_TICKER = "/openApi/swap/v2/quote/ticker"
SWAP_PREMIUM = "/openApi/swap/v2/quote/premiumIndex"
RATE_LIMIT_CODES = {"100410", "100429"}
SPOT_KLINE ="/openApi/spot/v2/market/kline"
SWAP_KLINE = "/openApi/swap/v3/quote/klines"
SWAP_FUNDING_HIST = "/openApi/swap/v2/quote/fundingRate"


class BingXError(RuntimeError):
    pass


def _f(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


class BingXClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, params: dict | None = None, retries: int = 3) -> list[dict]:
        for attempt in range(retries + 1):
            q = {**(params or {}), "timestamp": int(time.time() * 1000)}
            r = await self._http.get(path, params=q)
            if r.status_code == 429 and attempt < retries:
                await asyncio.sleep(0.5 * 2**attempt)
                continue
            r.raise_for_status()
            body = r.json()
            code = body.get("code")
            if str(code) in RATE_LIMIT_CODES and attempt < retries:  # "请稍后重试" — thử lại
                await asyncio.sleep(0.5 * 2**attempt)
                continue
            break
        if body.get("code") not in (0, "0", None):
            raise BingXError(f"{path}: code={body.get('code')} msg={body.get('msg')}")
        data = body.get("data")
        if isinstance(data, dict):  # phòng khi API bọc thêm 1 lớp
            data = data.get("symbols") or data.get("tickers") or [data]
        return data or []

    # --- lịch sử (spec 004) ---
    async def fetch_spot_closes(self, symbol: str, interval: str, limit: int) -> dict[int, float]:
        rows = await self._get(SPOT_KLINE, {"symbol": symbol, "interval": interval, "limit": limit})
        return {int(k[0]): float(k[4]) for k in rows if len(k) > 4}

    async def fetch_perp_closes(self, symbol: str, interval: str, limit: int) -> dict[int, float]:
        rows = await self._get(SWAP_KLINE, {"symbol": symbol, "interval": interval, "limit": limit})
        return {int(k["time"]): float(k["close"]) for k in rows if "time" in k}

    async def fetch_funding_history(self, symbol: str, limit: int) -> list[tuple[int, float]]:
        rows = await self._get(SWAP_FUNDING_HIST, {"symbol": symbol, "limit": limit})
        return [(int(r["fundingTime"]), float(r["fundingRate"])) for r in rows if "fundingRate" in r]

    async def fetch_snapshots(self) -> list[MarketSnapshot]:
        spot, swap, premium = await asyncio.gather(
            self._get(SPOT_TICKER), self._get(SWAP_TICKER), self._get(SWAP_PREMIUM)
        )

        spot_map = {d["symbol"]: d for d in spot if d.get("symbol")}
        prem_map = {d["symbol"]: d for d in premium if d.get("symbol")}

        out: list[MarketSnapshot] = []
        for t in swap:
            sym = t.get("symbol")
            perp_price = _f(t.get("lastPrice"))
            if not sym or not sym.endswith("-USDT") or not perp_price:
                continue
            p = prem_map.get(sym, {})
            s = spot_map.get(sym, {})
            nft = _f(p.get("nextFundingTime"))
            out.append(
                MarketSnapshot(
                    symbol=sym,
                    perp_price=perp_price,
                    mark_price=_f(p.get("markPrice")),
                    funding_rate=_f(p.get("lastFundingRate")),
                    next_funding_time=datetime.fromtimestamp(nft / 1000, tz=timezone.utc) if nft else None,
                    perp_quote_volume=_f(t.get("quoteVolume")) or 0.0,
                    spot_price=_f(s.get("lastPrice")),
                    spot_quote_volume=_f(s.get("quoteVolume")) or 0.0,
                    spot_bid=_f(s.get("bidPrice")),
                    spot_bid_qty=_f(s.get("bidQty")),
                    spot_ask=_f(s.get("askPrice")),
                    spot_ask_qty=_f(s.get("askQty")),
                    perp_bid=_f(t.get("bidPrice")),
                    perp_bid_qty=_f(t.get("bidQty")),
                    perp_ask=_f(t.get("askPrice")),
                    perp_ask_qty=_f(t.get("askQty")),
                )
            )
        log.debug("Fetched %d perp, %d spot, %d joined", len(swap), len(spot), len(out))
        return out
