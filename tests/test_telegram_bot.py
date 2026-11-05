"""Test luồng bot với Telegram/BingX giả (spec 002 AC-1, AC-2, AC-4, AC-5, AC-6)."""
import asyncio

import pytest

from app.config import Settings
from app.models import MarketSnapshot
from app.services.scanner import Scanner
from app.services.telegram_bot import TelegramBot
from app.state import StateStore

OWNER, STRANGER, CHANNEL = 111, 999, -100123


class FakeTG:
    enabled = True

    def __init__(self):
        self.sent, self.edits, self.pins = [], [], []
        self.edit_ok = True
        self._mid = 0

    async def send(self, text, chat_id=None, silent=False):
        self._mid += 1
        self.sent.append((chat_id, text))
        return self._mid

    async def edit(self, chat_id, mid, text):
        self.edits.append((chat_id, mid))
        return self.edit_ok

    async def pin(self, chat_id, mid):
        self.pins.append((chat_id, mid))
        return True

    async def unpin(self, chat_id, mid):
        self.unpins = getattr(self, "unpins", []) + [mid]
        return True

    async def delete(self, chat_id, mid):
        self.deleted = getattr(self, "deleted", []) + [mid]
        return True

    async def get_chat(self, cid):
        return {"id": CHANNEL, "title": "Test"}

    def to(self, chat):
        return [t for c, t in self.sent if c == chat]


class FakeBingX:
    async def fetch_snapshots(self):
        return [MarketSnapshot(symbol="BTC-USDT", spot_price=100, perp_price=102, funding_rate=0.001,
                               spot_quote_volume=1e8, perp_quote_volume=1e8)]


@pytest.fixture
def env(tmp_path):
    s = Settings(_env_file=None, telegram_bot_token="x", telegram_admin_ids=str(OWNER),
                 state_file=str(tmp_path / "s.json"))
    store = StateStore(s.state_file)
    tg = FakeTG()
    sc = Scanner(s, FakeBingX(), tg, store)
    return s, store, tg, sc, TelegramBot(s, tg, store, sc)


def msg(uid, text):
    return {"update_id": 1, "message": {"from": {"id": uid}, "chat": {"id": uid, "type": "private"}, "text": text}}


def added(uid, status="administrator"):
    return {"update_id": 2, "my_chat_member": {
        "chat": {"id": CHANNEL, "type": "channel", "title": "Shark"},
        "from": {"id": uid}, "new_chat_member": {"status": status}}}


def run(coro):
    return asyncio.run(coro)


def test_ac1_auto_detect_channel(env):
    s, store, tg, sc, bot = env

    async def go():
        await bot.handle(added(OWNER))
        await asyncio.sleep(0.05)  # task quét được tạo nền
    run(go())
    assert store.state.channel_id == str(CHANNEL)
    assert any("đã kết nối" in t for t in tg.to(str(CHANNEL)))
    assert tg.pins  # dashboard được ghim


def test_stranger_cannot_add_or_command(env):
    s, store, tg, sc, bot = env
    run(bot.handle(added(STRANGER)))
    assert store.state.channel_id is None
    run(bot.handle(msg(STRANGER, "/pause")))   # AC-5
    assert store.state.paused is False
    assert "không có quyền" in tg.to(STRANGER)[-1]


def test_ac2_set_persists(env):
    s, store, tg, sc, bot = env
    run(bot.handle(msg(OWNER, "/set funding 0.03")))
    assert StateStore(s.state_file).state.overrides["funding_min_rate"] == pytest.approx(0.0003)
    run(bot.handle(msg(OWNER, "/set funding abc")))  # AC-3
    assert store.state.overrides["funding_min_rate"] == pytest.approx(0.0003)


def test_ac4_pause_blocks_alerts_not_dashboard(env):
    s, store, tg, sc, bot = env
    store.set_channel(str(CHANNEL))
    run(bot.handle(msg(OWNER, "/pause")))
    r = run(sc.run_once(force_dashboard=True))
    assert r.alerted == 0 and len(r.funding) == 1
    assert any("Bảng tin" in t for t in tg.to(str(CHANNEL)))
    assert not any("Arbitrage Alert" in t for t in tg.to(str(CHANNEL)))
    run(bot.handle(msg(OWNER, "/resume")))
    assert run(sc.run_once()).alerted == 2


def test_ac6_dashboard_repinned_when_deleted(env):
    s, store, tg, sc, bot = env
    store.set_channel(str(CHANNEL))
    run(sc.run_once(force_dashboard=True))
    first = store.state.dashboard_message_id
    tg.edit_ok = False  # tin đã bị xoá
    run(sc.run_once(force_dashboard=True))
    assert store.state.dashboard_message_id != first
    assert len(tg.pins) == 2


def test_fr3b_dashboard_off_removes_pinned(env):
    s, store, tg, sc, bot = env
    store.set_channel(str(CHANNEL))
    run(sc.run_once(force_dashboard=True))
    mid = store.state.dashboard_message_id
    run(bot.handle(msg(OWNER, "/dashboard off")))
    assert tg.unpins == [mid] and tg.deleted == [mid]
    assert store.state.dashboard_message_id is None
    n_sent = len(tg.sent)
    run(sc.run_once(force_dashboard=True))  # tắt rồi -> không đăng lại
    assert not any("Bảng tin" in t for _, t in tg.sent[n_sent:])


def test_first_start_claims_owner(tmp_path):
    s = Settings(_env_file=None, telegram_bot_token="x", state_file=str(tmp_path / "s.json"))
    store, tg = StateStore(s.state_file), FakeTG()
    bot = TelegramBot(s, tg, store, Scanner(s, FakeBingX(), tg, store))
    run(bot.handle(msg(555, "/start")))
    run(bot.handle(msg(666, "/start")))
    assert store.state.admin_ids == [555]
