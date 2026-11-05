import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.clients.bingx import BingXClient
from app.clients.telegram import TelegramNotifier
from app.config import get_settings
from app.services.scanner import Scanner
from app.services.telegram_bot import TelegramBot
from app.state import StateStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # không log URL chứa bot token


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    store = StateStore(s.state_file)
    bingx = BingXClient(s.bingx_base_url)
    telegram = TelegramNotifier(s.telegram_bot_token, s.telegram_chat_id)
    scanner = Scanner(s, bingx, telegram, store)
    app.state.scanner = scanner
    app.state.store = store

    app.state.bot = None
    tasks = [asyncio.create_task(scanner.run_forever())]
    if telegram.enabled and s.telegram_polling:
        app.state.bot = TelegramBot(s, telegram, store, scanner)
        tasks.append(asyncio.create_task(app.state.bot.run_forever()))
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await t
        await bingx.close()
        await telegram.close()


app = FastAPI(title="Sharkio — BingX Arbitrage Alert", version="1.1.0", lifespan=lifespan)
app.include_router(router)
