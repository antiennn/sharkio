"""Bot quản lý channel: long-polling, tự nhận channel, lệnh admin (spec 002)."""
import asyncio
import logging
from datetime import datetime, timezone
from html import escape

from app.clients.telegram import TelegramNotifier
from app.config import Settings
from app.core.commands import parse_command, parse_set
from app.core.formatter import format_status
from app.services.scanner import Scanner
from app.state import StateStore

log = logging.getLogger(__name__)

COMMANDS = [
    ("status", "Trạng thái bot & ngưỡng"),
    ("top", "Top cơ hội hiện tại"),
    ("post", "Đăng top cơ hội lên channel"),
    ("scan", "Quét ngay"),
    ("pause", "Tạm dừng alert"),
    ("resume", "Tiếp tục alert"),
    ("set", "Đổi ngưỡng: /set funding 0.05"),
    ("reset", "Về ngưỡng mặc định (.env)"),
    ("dashboard", "Bật/tắt bảng tin: /dashboard on|off"),
    ("setchannel", "Đặt channel: /setchannel @ten"),
    ("help", "Hướng dẫn"),
]

HELP = """🦈 <b>Sharkio — quản lý channel</b>

<b>Kết nối channel:</b> thêm bot làm <b>Admin</b> của channel (quyền Đăng, Sửa, Ghim tin) → bot tự nhận.
Hoặc dùng <code>/setchannel @ten_channel</code>

<b>Lệnh:</b>
/status — trạng thái
/top — xem top cơ hội (gửi riêng cho bạn)
/post — đăng top cơ hội lên channel
/scan — quét ngay
/pause · /resume — tạm dừng / tiếp tục alert
/set funding 0.05 — funding tối thiểu 0.05%/kỳ
/set basis 0.5 — basis tối thiểu 0.5%
/set volume 300000 — volume 24h tối thiểu (USDT)
/set cooldown 30 — phút giữa 2 alert cùng coin
/reset — về ngưỡng trong .env
/dashboard on|off — bảng tin ghim trong channel"""


class TelegramBot:
    def __init__(self, settings: Settings, telegram: TelegramNotifier, store: StateStore, scanner: Scanner):
        self.s = settings
        self.tg = telegram
        self.store = store
        self.scanner = scanner
        self._offset: int | None = None
        self.last_poll_ok_at: datetime | None = None

    # --- quyền ---
    @property
    def admins(self) -> set[int]:
        return self.s.admin_ids | set(self.store.state.admin_ids)

    def is_admin(self, uid: int | None) -> bool:
        return uid is not None and uid in self.admins

    async def notify_admins(self, text: str) -> None:
        for uid in self.admins:
            await self.tg.send(text, uid)

    # --- vòng polling ---
    async def run_forever(self) -> None:
        me = await self.tg.get_me()
        if me:
            log.info("Telegram bot @%s sẵn sàng", me.get("username"))
        await self.tg.set_commands(COMMANDS)
        while True:
            updates = await self.tg.get_updates(self._offset, timeout=30)
            if updates is None:
                await asyncio.sleep(3)  # lỗi mạng: tránh vòng lặp nóng
                continue
            self.last_poll_ok_at = datetime.now(timezone.utc)
            for u in updates:
                self._offset = u["update_id"] + 1
                try:
                    await self.handle(u)
                except Exception:
                    log.exception("Lỗi xử lý update %s", u.get("update_id"))

    async def handle(self, u: dict) -> None:
        if "my_chat_member" in u:
            await self._on_membership(u["my_chat_member"])
            return
        msg = u.get("message")
        if not msg or msg.get("chat", {}).get("type") != "private":
            return
        parsed = parse_command(msg.get("text"))
        if not parsed:
            return
        cmd, args = parsed
        uid = msg.get("from", {}).get("id")
        chat_id = msg["chat"]["id"]

        if cmd == "start" and not self.admins:
            self.store.state.admin_ids.append(uid)
            self.store.save()
            log.warning("User %s đã được nhận làm owner của bot", uid)
            await self.tg.send(f"✅ Bạn (id <code>{uid}</code>) đã trở thành <b>owner</b> của bot.", chat_id)

        if not self.is_admin(uid):
            await self.tg.send(f"⛔ Bạn không có quyền. Id của bạn: <code>{uid}</code>", chat_id)
            return

        handler = getattr(self, f"cmd_{cmd}", None)
        if handler is None:
            await self.tg.send("Lệnh không tồn tại. Gõ /help", chat_id)
            return
        await handler(chat_id, args)

    # --- sự kiện bot được thêm/gỡ khỏi channel (FR-1) ---
    async def _on_membership(self, m: dict) -> None:
        chat = m.get("chat", {})
        if chat.get("type") not in ("channel", "supergroup", "group"):
            return
        status = m.get("new_chat_member", {}).get("status")
        uid = m.get("from", {}).get("id")
        cid, title = str(chat["id"]), chat.get("title") or chat.get("username") or str(chat["id"])

        if status == "administrator":
            if not (self.is_admin(uid) or not self.admins):
                log.warning("User lạ %s thêm bot vào %s — bỏ qua", uid, title)
                return
            self.store.set_channel(cid, title)
            log.info("Đã nhận channel %s (%s)", title, cid)
            await self.tg.send(
                "🦈 <b>Sharkio</b> đã kết nối. Kênh sẽ nhận cảnh báo Funding arbitrage & Basis spot/perp từ BingX.",
                cid, silent=True,
            )
            await self.notify_admins(f"✅ Đã kết nối channel <b>{escape(title)}</b> (<code>{cid}</code>)")
            asyncio.create_task(self.scanner.run_once(force_dashboard=True))
        elif status in ("left", "kicked", "member", "restricted") and self.store.state.channel_id == cid:
            self.store.set_channel(None)
            await self.notify_admins(
                f"⚠️ Bot không còn là admin của <b>{escape(title)}</b> — đã ngắt kết nối channel."
            )

    # --- lệnh (FR-5) ---
    async def cmd_start(self, chat_id, args):
        await self.tg.send(HELP, chat_id)

    cmd_help = cmd_start

    async def cmd_status(self, chat_id, args):
        st, r = self.store.state, self.scanner.last_result
        channel = (
            f"{st.channel_title} ({st.channel_id})" if st.channel_id else (self.s.telegram_chat_id or None)
        )
        info = {
            **self.scanner.params(),
            "channel": channel,
            "paused": st.paused,
            "dashboard": self.scanner.dashboard_enabled,
            "last_scan": r.scanned_at,
            "last_error": r.error,
            "overrides": list(st.overrides),
        }
        await self.tg.send(format_status(info), chat_id)

    async def cmd_pause(self, chat_id, args):
        self.store.state.paused = True
        self.store.save()
        await self.tg.send("⏸ Đã tạm dừng alert (vẫn quét & cập nhật bảng tin).", chat_id)

    async def cmd_resume(self, chat_id, args):
        self.store.state.paused = False
        self.store.save()
        await self.tg.send("▶️ Đã tiếp tục alert.", chat_id)

    async def cmd_set(self, chat_id, args):
        try:
            key, val = parse_set(args)
        except ValueError as e:
            await self.tg.send(f"❌ {escape(str(e))}", chat_id)
            return
        self.store.state.overrides[key] = val
        self.store.save()
        self.scanner.apply_overrides()
        await self.tg.send(f"✅ Đã đặt <code>{key}</code> = {val:g}", chat_id)
        await self.cmd_status(chat_id, [])

    async def cmd_reset(self, chat_id, args):
        self.store.state.overrides.clear()
        self.store.save()
        self.scanner.apply_overrides()
        await self.tg.send("✅ Đã về ngưỡng mặc định trong .env", chat_id)

    async def cmd_top(self, chat_id, args):
        await self.scanner.post_top(chat_id)

    async def cmd_post(self, chat_id, args):
        target = self.scanner.target_chat
        if not target:
            await self.tg.send("❌ Chưa có channel. Thêm bot làm admin channel hoặc /setchannel", chat_id)
            return
        ok = await self.scanner.post_top(target)
        await self.tg.send("✅ Đã đăng lên channel" if ok else "❌ Đăng thất bại (bot có quyền đăng tin?)", chat_id)

    async def cmd_scan(self, chat_id, args):
        r = await self.scanner.run_once(force_dashboard=True)
        if r.error:
            await self.tg.send(f"❌ {escape(r.error)}", chat_id)
        else:
            await self.tg.send(
                f"🔎 {r.symbols_eligible}/{r.symbols_total} cặp · funding {len(r.funding)} · "
                f"basis {len(r.basis)} · đã báo {r.alerted}",
                chat_id,
            )

    async def cmd_dashboard(self, chat_id, args):
        if not args or args[0].lower() not in ("on", "off"):
            await self.tg.send("Cú pháp: /dashboard on|off", chat_id)
            return
        on = args[0].lower() == "on"
        self.store.state.dashboard_enabled = on
        self.store.save()
        if on:
            await self.scanner.run_once(force_dashboard=True)
        else:
            await self.scanner.remove_dashboard()
        await self.tg.send(f"Dashboard: {'bật' if on else 'tắt'}", chat_id)

    async def cmd_setchannel(self, chat_id, args):
        if not args:
            await self.tg.send("Cú pháp: /setchannel @ten_channel hoặc /setchannel -100xxxxxxxx", chat_id)
            return
        chat = await self.tg.get_chat(args[0])
        if not chat:
            await self.tg.send("❌ Không tìm thấy channel. Bot đã là admin của channel chưa?", chat_id)
            return
        cid, title = str(chat["id"]), chat.get("title") or args[0]
        self.store.set_channel(cid, title)
        ok = await self.tg.send("🦈 <b>Sharkio</b> đã kết nối channel này.", cid, silent=True)
        await self.tg.send(
            f"✅ Channel: <b>{escape(title)}</b> (<code>{cid}</code>)"
            + ("" if ok else "\n⚠️ Không đăng được tin — kiểm tra quyền admin của bot."),
            chat_id,
        )
        if ok:
            await self.scanner.run_once(force_dashboard=True)
