"""HTTP API (spec 001 FR-6, spec 002)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.health import compute_status
from app.services.scanner import ScanResult, Scanner

router = APIRouter()


def _scanner(request: Request) -> Scanner:
    return request.app.state.scanner


@router.get("/health/live")
async def live():
    return {"alive": True}


@router.get("/health")
async def health(request: Request):
    """Spec 003: trạng thái chi tiết; HTTP 503 khi down."""
    sc = _scanner(request)
    st, stats, r, s = sc.store.state, sc.stats, sc.last_result, sc.s
    bot = getattr(request.app.state, "bot", None)
    now = datetime.now(timezone.utc)
    status = compute_status(now, stats.started_at, stats.last_success_at, s.scan_interval_seconds, bool(r.error))

    body = {
        "status": status,
        "now": now,
        "started_at": stats.started_at,
        "uptime": _human(now - stats.started_at),
        "scan": {
            "interval_seconds": s.scan_interval_seconds,
            "last_scan": r.scanned_at,
            "last_success": stats.last_success_at,
            "next_scan_at": stats.next_scan_at,
            "next_scan_in_seconds": (
                max(0, round((stats.next_scan_at - now).total_seconds())) if stats.next_scan_at else None
            ),
            "last_duration_ms": stats.last_duration_ms,
            "scans_total": stats.scans_total,
            "scans_failed": stats.scans_failed,
            "consecutive_failures": stats.consecutive_failures,
            "last_error": r.error,
            "symbols_total": r.symbols_total,
            "symbols_eligible": r.symbols_eligible,
            "opportunities": {"funding": len(r.funding), "basis": len(r.basis)},
            "alerts_sent_total": stats.alerts_total,
            "thresholds": sc.params(),
        },
        "dashboard": {
            "enabled": sc.dashboard_enabled,
            "interval_minutes": s.dashboard_interval_minutes,
            "last_update": stats.last_dashboard_at,
            "message_id": st.dashboard_message_id,
        },
        "telegram": {
            "enabled": sc.telegram.enabled,
            "polling": bot is not None,
            "last_poll_ok": bot.last_poll_ok_at if bot else None,
            "channel_id": sc.target_chat,
            "channel_title": st.channel_title,
            "paused": st.paused,
            "admins": len(bot.admins) if bot else len(st.admin_ids),
        },
    }
    return JSONResponse(jsonable_encoder(body), status_code=503 if status == "down" else 200)


def _human(td: timedelta) -> str:
    sec = int(td.total_seconds())
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, sec = divmod(sec, 60)
    return (f"{d}d " if d else "") + f"{h:02d}:{m:02d}:{sec:02d}"


@router.get("/opportunities", response_model=ScanResult)
async def opportunities(request: Request):
    return _scanner(request).last_result


@router.post("/scan", response_model=ScanResult)
async def scan_now(request: Request):
    return await _scanner(request).run_once(force_dashboard=True)


@router.post("/test-alert")
async def test_alert(request: Request):
    sc = _scanner(request)
    if not sc.telegram.enabled:
        raise HTTPException(400, "Chưa cấu hình TELEGRAM_BOT_TOKEN")
    if not sc.target_chat:
        raise HTTPException(400, "Chưa có channel: thêm bot làm admin channel hoặc đặt TELEGRAM_CHAT_ID")
    if not await sc.telegram.send("🦈 <b>Sharkio</b>: test alert OK ✅", sc.target_chat):
        raise HTTPException(502, "Gửi Telegram thất bại, xem log")
    return {"sent": True, "chat_id": sc.target_chat}


@router.get("/config")
async def config(request: Request):
    sc = _scanner(request)
    return {
        "settings": sc.s.model_dump(exclude={"telegram_bot_token"}),
        "effective": sc.params(),
        "state": sc.store.state.model_dump(),
    }
