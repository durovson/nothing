from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from aiogram.types import Update

from app.loader import AppContainer


DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "documents"


def _legal_document(filename: str) -> str:
    """Read a versioned legal document without accepting a user-controlled path."""
    return (DOCUMENTS_DIR / filename).read_text(encoding="utf-8")


def create_api_router(container: AppContainer) -> APIRouter:
    router = APIRouter()
    settings = container.settings

    @router.get("/ping")
    @router.get("/healthz")
    async def healthcheck() -> JSONResponse:
        result = await container.health.check()
        return JSONResponse(result, status_code=200 if result["status"] == "ok" else 503)

    @router.get("/readyz")
    async def readiness() -> JSONResponse:
        result = await container.health.check()
        return JSONResponse(result, status_code=200 if result["status"] == "ok" else 503)

    @router.get("/documents/privacy", response_class=HTMLResponse)
    async def privacy_policy() -> str:
        return _legal_document("privacy.html")

    @router.get("/documents/terms", response_class=HTMLResponse)
    async def terms_of_service() -> str:
        return _legal_document("terms.html")

    @router.get("/documents/service", response_class=HTMLResponse)
    async def service_description() -> str:
        return _legal_document("service.html")

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
