"""So sánh basis hiện tại với lịch sử 24h — hàm thuần (spec 004)."""
import statistics
from dataclasses import dataclass

MIN_POINTS = 12  # ít hơn → coi như chưa có lịch sử (FR-4)


@dataclass(frozen=True)
class BasisBaseline:
    median: float
    sigma: float      # 1.4826 × MAD
    low: float
    high: float
    n: int
    first: float      # basis của nến cũ nhất ≈ đúng 24h trước


@dataclass(frozen=True)
class BaselineVerdict:
    is_anomaly: bool
    deviation: float
    zscore: float | None   # None khi sigma = 0


def basis_series(spot_closes: dict[int, float], perp_closes: dict[int, float]) -> list[float]:
    """Ghép theo thời gian mở nến (chỉ mốc có ở cả 2 phía — AC-4), sắp tăng dần theo thời gian."""
    out = []
    for t in sorted(spot_closes.keys() & perp_closes.keys()):
        s = spot_closes[t]
        if s > 0:
            out.append((perp_closes[t] - s) / s)
    return out


def compute_baseline(series: list[float], drop_last: bool = True) -> BasisBaseline | None:
    pts = series[:-1] if drop_last and series else series  # nến cuối đang chạy
    if len(pts) < MIN_POINTS:
        return None
    med = statistics.median(pts)
    mad = statistics.median(abs(x - med) for x in pts)
    return BasisBaseline(
        median=med, sigma=1.4826 * mad, low=min(pts), high=max(pts), n=len(pts), first=pts[0]
    )


def evaluate(current: float, base: BasisBaseline, min_deviation: float, min_z: float) -> BaselineVerdict:
    dev = current - base.median
    z = dev / base.sigma if base.sigma > 0 else None
    ok = abs(dev) >= min_deviation and (z is None or abs(z) >= min_z)
    return BaselineVerdict(is_anomaly=ok, deviation=dev, zscore=z)
