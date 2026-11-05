"""Telegram Bot API client (spec 001 FR-4/FR-8, spec 002)."""
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, default_chat_id: str = "", timeout: float = 15.0):
        self.enabled = bool(token)
        self.default_chat_id = default_chat_id
        self._http = httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{token}", timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def call(self, method: str, timeout: float | None = None, **payload: Any) -> Any | None:
        """Gọi Bot API; trả `result` hoặc None nếu lỗi (không raise — Constitution VI)."""
        if not self.enabled:
            return None
        try:
            r = await self._http.post(f"/{method}", json=payload, timeout=timeout or self._http.timeout)
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("Telegram %s lỗi mạng: %s", method, e)
            return None
        if not body.get("ok"):
            log.warning("Telegram %s lỗi: %s", method, body.get("description"))
            return None
        return body.get("result")

    async def send(self, text: str, chat_id: str | int | None = None, silent: bool = False) -> int | None:
        """Gửi tin HTML; trả message_id hoặc None."""
        target = chat_id or self.default_chat_id
        if not self.enabled or not target:
            log.info("[Telegram chưa có chat đích] %s", text[:200])
            return None
        res = await self.call(
            "sendMessage", chat_id=target, text=text, parse_mode="HTML",
            disable_web_page_preview=True, disable_notification=silent,
        )
        return res.get("message_id") if res else None

    async def edit(self, chat_id: str | int, message_id: int, text: str) -> bool:
        res = await self.call(
            "editMessageText", chat_id=chat_id, message_id=message_id, text=text,
            parse_mode="HTML", disable_web_page_preview=True,
        )
        return res is not None

    async def pin(self, chat_id: str | int, message_id: int) -> bool:
        res = await self.call("pinChatMessage", chat_id=chat_id, message_id=message_id, disable_notification=True)
        return res is not None

    async def unpin(self, chat_id: str | int, message_id: int) -> bool:
        return await self.call("unpinChatMessage", chat_id=chat_id, message_id=message_id) is not None

    async def delete(self, chat_id: str | int, message_id: int) -> bool:
        return await self.call("deleteMessage", chat_id=chat_id, message_id=message_id) is not None

    async def get_chat(self, chat_id: str | int) -> dict | None:
        return await self.call("getChat", chat_id=chat_id)

    async def get_me(self) -> dict | None:
        return await self.call("getMe")

    async def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict] | None:
        """Long-polling; trả None nếu lỗi. `timeout` của Bot API trùng tên timeout HTTP nên gọi riêng."""
        if not self.enabled:
            return None
        try:
            r = await self._http.post(
                "/getUpdates",
                json={"offset": offset, "timeout": timeout, "allowed_updates": ["message", "my_chat_member"]},
                timeout=timeout + 10,
            )
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("getUpdates lỗi mạng: %s", e)
            return None
        if not body.get("ok"):
            log.warning("getUpdates lỗi: %s", body.get("description"))
            return None
        return body.get("result", [])

    async def set_commands(self, commands: list[tuple[str, str]]) -> None:
        await self.call(
            "setMyCommands",
            commands=[{"command": c, "description": d} for c, d in commands],
            scope={"type": "all_private_chats"},
        )
