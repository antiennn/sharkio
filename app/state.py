"""Trạng thái chạy được lưu ra file (spec 002 FR-6)."""
import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel

log = logging.getLogger(__name__)

OVERRIDABLE = ("funding_min_rate", "basis_min_pct", "min_quote_volume_usdt", "alert_cooldown_minutes")


class BotState(BaseModel):
    channel_id: str | None = None
    channel_title: str | None = None
    admin_ids: list[int] = []
    paused: bool = False
    dashboard_enabled: bool | None = None     # None = theo .env
    dashboard_message_id: int | None = None
    overrides: dict[str, float] = {}


class StateStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.state = self._load()

    def _load(self) -> BotState:
        if self.path.exists():
            try:
                return BotState.model_validate_json(self.path.read_text(encoding="utf-8"))
            except Exception:
                log.exception("State file hỏng, dùng state mặc định")
        return BotState()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def set_channel(self, chat_id: str | None, title: str | None = None) -> None:
        if chat_id != self.state.channel_id:
            self.state.dashboard_message_id = None
        self.state.channel_id = chat_id
        self.state.channel_title = title
        self.save()
