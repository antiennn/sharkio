from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class OpportunityType(str, Enum):
    FUNDING = "FUNDING"
    BASIS = "BASIS"


class MarketSnapshot(BaseModel):
    symbol: str                       # ví dụ BTC-USDT
    perp_price: float
    mark_price: float | None = None
    funding_rate: float | None = None
    next_funding_time: datetime | None = None
    perp_quote_volume: float = 0.0
    spot_price: float | None = None   # None nếu coin không có cặp spot
    spot_quote_volume: float = 0.0

    # sổ lệnh tốt nhất (spec 005); qty tính theo đơn vị coin
    spot_bid: float | None = None
    spot_bid_qty: float | None = None
    spot_ask: float | None = None
    spot_ask_qty: float | None = None
    perp_bid: float | None = None
    perp_bid_qty: float | None = None
    perp_ask: float | None = None
    perp_ask_qty: float | None = None

    @property
    def has_spot(self) -> bool:
        return self.spot_price is not None and self.spot_price > 0

    @property
    def basis(self) -> float | None:
        """Basis theo last price."""
        if not self.has_spot:
            return None
        return (self.perp_price - self.spot_price) / self.spot_price

    @property
    def has_book(self) -> bool:
        return all(x and x > 0 for x in (self.spot_bid, self.spot_ask, self.perp_bid, self.perp_ask))

    @property
    def exec_side(self) -> int:
        """+1: perp_bid > spot_ask (mua spot, short perp); −1: perp_ask < spot_bid; 0: không khớp được."""
        if not self.has_book:
            return 0
        if self.perp_bid > self.spot_ask:
            return 1
        if self.perp_ask < self.spot_bid:
            return -1
        return 0

    @property
    def exec_basis(self) -> float | None:
        """Basis khớp được bằng bid/ask (spec 005 FR-2); thiếu sổ lệnh → last price."""
        if not self.has_spot:
            return None
        if not self.has_book:
            return self.basis
        side = self.exec_side
        if side > 0:
            return (self.perp_bid - self.spot_ask) / self.spot_ask
        if side < 0:
            return (self.perp_ask - self.spot_bid) / self.spot_bid
        return 0.0

    @property
    def exec_prices(self) -> tuple[float, float]:
        """(giá spot, giá perp) thực sự dùng để vào lệnh."""
        side = self.exec_side
        if side > 0:
            return self.spot_ask, self.perp_bid
        if side < 0:
            return self.spot_bid, self.perp_ask
        return self.spot_price, self.perp_price

    @property
    def exec_depth_usdt(self) -> float | None:
        """USDT vào được ngay ở giá tốt nhất = min 2 phía."""
        side = self.exec_side
        if side > 0 and self.spot_ask_qty and self.perp_bid_qty:
            return min(self.spot_ask * self.spot_ask_qty, self.perp_bid * self.perp_bid_qty)
        if side < 0 and self.spot_bid_qty and self.perp_ask_qty:
            return min(self.spot_bid * self.spot_bid_qty, self.perp_ask * self.perp_ask_qty)
        return None


class Opportunity(BaseModel):
    type: OpportunityType
    symbol: str
    value: float                      # funding_rate (FUNDING) hoặc basis (BASIS)
    spot_price: float
    perp_price: float
    funding_rate: float | None = None
    funding_apr: float | None = None
    basis: float | None = None
    next_funding_time: datetime | None = None
    action: str

    # spec 005
    basis_last: float | None = None          # basis theo last price (tham khảo)
    depth_usdt: float | None = None          # USDT vào được ở giá tốt nhất
    net_after_fees: float | None = None      # |basis| − phí 2 chiều
    spot_quote_volume: float | None = None
    perp_quote_volume: float | None = None

    # ngữ cảnh 24h (spec 004); None = chưa có / không áp dụng
    history_ok: bool | None = None
    basis_median_24h: float | None = None
    basis_24h_ago: float | None = None
    basis_low_24h: float | None = None
    basis_high_24h: float | None = None
    basis_deviation: float | None = None
    basis_zscore: float | None = None
    funding_avg_24h: float | None = None

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.type.value, self.symbol, 1 if self.value >= 0 else -1)
