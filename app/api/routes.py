from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from aiogram.types import Update

from app.core.types import ReadinessPayload
from app.loader import AppContainer


def create_api_router(container: AppContainer) -> APIRouter:
    router = APIRouter()
    settings = container.settings

    @router.get("/ping")
    @router.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/readyz")
    async def readiness() -> ReadinessPayload:
        checks = {
            "deal_monitor": container.monitor.is_running,
            "ton_client": container.ton.is_connected,
        }
        if container.keepalive.is_enabled:
            checks["render_keepalive"] = container.keepalive.is_running
        status = "ok" if all(checks.values()) else "starting"
        return {
            "status": status,
            "checks": checks,
        }

    @router.get("/documents/privacy", response_class=HTMLResponse)
    async def privacy_policy() -> str:
        return """<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Политика конфиденциальности</title><style>body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.6;color:#18212f}h1{line-height:1.2}</style><h1>Политика конфиденциальности</h1><p>Сервис обрабатывает Telegram ID, username, выбранный язык, привязанный TON-адрес и данные сделок исключительно для работы escrow, уведомлений, возвратов и выплат.</p><p>Секретные ключи и seed-фразы пользователей не запрашиваются. Публичные blockchain-транзакции доступны в сети TON. Данные могут храниться в Supabase в пределах срока, необходимого для исполнения сделки и разрешения споров.</p><p>Для вопросов об обработке данных обратитесь в поддержку бота.</p></html>"""

    @router.get("/documents/terms", response_class=HTMLResponse)
    async def terms_of_service() -> str:
        return """<!doctype html><html lang='ru'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Пользовательское соглашение</title><style>body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.6;color:#18212f}h1{line-height:1.2}</style><h1>Пользовательское соглашение</h1><p>Сервис предоставляет технический escrow-инструмент для сделок между продавцом и покупателем. Комиссия сервиса составляет 1% суммы сделки. Сетевые комиссии TON учитываются отдельно.</p><p>Пользователи самостоятельно отвечают за законность предмета сделки, правильность кошельков и передачу товара или услуги. Средства удерживаются гарантом до подтверждения, отмены, автоматического условия или решения спора.</p><p>При использовании биржевого, кастодиального или чужого адреса пользователь принимает риск потери зачисления. Решения по спору принимаются администратором на основании доступных материалов.</p></html>"""

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
