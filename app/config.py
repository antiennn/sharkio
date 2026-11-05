"""Settings đọc từ biến môi trường / .env (Constitution IV)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    scan_interval_seconds: int = 60
    min_quote_volume_usdt: float = 10_000     # spec 005: thấp để quét cả coin nhỏ

    funding_min_rate: float = 0.0005
    funding_interval_hours: float = 8

    basis_min_pct: float = 0.02               # spec 005: 2%
    basis_allow_reverse: bool = False         # spec 005 FR-6: chỉ Mua Spot + Short Perp
    spot_taker_fee: float = 0.001
    perp_taker_fee: float = 0.0005

    @property
    def round_trip_fee(self) -> float:
        """Mở + đóng cả 2 chân."""
        return 2 * (self.spot_taker_fee + self.perp_taker_fee)

    alert_cooldown_minutes: float = 30
    alert_escalation_ratio: float = 1.5
    max_alerts_per_message: int = 15

    symbol_whitelist: str = ""
    symbol_blacklist: str = ""

    bingx_base_url: str = "https://open-api.bingx.com"

    # --- 002: channel manager ---
    telegram_admin_ids: str = ""          # user id, cách nhau dấu phẩy
    telegram_polling: bool = True         # nhận lệnh qua getUpdates
    dashboard_enabled: bool = True
    dashboard_interval_minutes: float = 5
    state_file: str = "data/state.json"

    # --- 004: so với lịch sử 24h ---
    basis_baseline_enabled: bool = True
    basis_min_deviation_pct: float = 0.01    # lệch khỏi trung vị 24h tối thiểu (1%, spec 005)
    basis_min_zscore: float = 3.0
    baseline_interval: str = "15m"
    baseline_hours: float = 24
    baseline_cache_minutes: float = 15

    @property
    def baseline_limit(self) -> int:
        unit = {"m": 1, "h": 60}[self.baseline_interval[-1]]
        minutes = int(self.baseline_interval[:-1]) * unit
        return int(self.baseline_hours * 60 / minutes) + 1

    @property
    def admin_ids(self) -> set[int]:
        return {int(x) for x in self.telegram_admin_ids.replace(" ", "").split(",") if x.lstrip("-").isdigit()}

    @field_validator("symbol_whitelist", "symbol_blacklist", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return (v or "").strip()

    @staticmethod
    def _parse(raw: str) -> set[str]:
        return {s.strip().upper() for s in raw.split(",") if s.strip()}

    @property
    def whitelist(self) -> set[str]:
        return self._parse(self.symbol_whitelist)

    @property
    def blacklist(self) -> set[str]:
        return self._parse(self.symbol_blacklist)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
