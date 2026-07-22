from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from aiogram.types import Update

from app.core.types import ReadinessPayload
from app.loader import AppContainer


def create_api_router(container: AppContainer) -> APIRouter:
    router = APIRouter()
    settings = container.settings

    @router.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/readyz")
    async def readiness() -> ReadinessPayload:
        checks = {
            "deal_monitor": container.monitor.is_running,
            "ton_client": container.ton.is_connected,
        }
        status = "ok" if all(checks.values()) else "starting"
        return {
            "status": status,
            "checks": checks,
        }

    @router.post(settings.TELEGRAM_WEBHOOK_PATH)
    async def telegram_webhook(request: Request) -> JSONResponse:
        if settings.TELEGRAM_USE_POLLING:
            raise HTTPException(status_code=409, detail="Webhook mode is disabled")
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not settings.TELEGRAM_WEBHOOK_SECRET or secret != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")
        try:
            update = Update.model_validate(await request.json())
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid Telegram update") from exc
        await container.dispatcher.feed_update(container.bot, update)
        return JSONResponse({"ok": True})

    return router
