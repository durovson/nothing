from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bot import run_polling
from app.loader import AppContainer

logger = logging.getLogger(__name__)


def create_lifespan(container: AppContainer) -> Callable[[FastAPI], AsyncIterator[None]]:
    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        settings = container.settings
        polling_task: asyncio.Task[None] | None = None
        if not settings.TELEGRAM_USE_POLLING:
            if not settings.APP_BASE_URL:
                raise RuntimeError("APP_BASE_URL is required in webhook mode")
            if not settings.TELEGRAM_WEBHOOK_SECRET:
                raise RuntimeError("TELEGRAM_WEBHOOK_SECRET is required in webhook mode")

        try:
            await container.ton.start()
            await container.monitor.start()
            if settings.TELEGRAM_USE_POLLING:
                await container.bot.delete_webhook(drop_pending_updates=False)
                polling_task = asyncio.create_task(
                    run_polling(container.bot, container.dispatcher),
                    name="telegram-polling",
                )
                logger.info("Telegram polling started")
            else:
                webhook_url = f"{settings.APP_BASE_URL.rstrip('/')}{settings.TELEGRAM_WEBHOOK_PATH}"
                await container.bot.set_webhook(
                    webhook_url,
                    secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                )
                logger.info("Telegram webhook configured: %s", webhook_url)
            yield
        finally:
            if polling_task:
                polling_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await polling_task
            if not settings.TELEGRAM_USE_POLLING:
                await container.bot.delete_webhook(drop_pending_updates=False)
            await container.monitor.stop()
            await container.ton.close()
            await container.bot.session.close()

    return lifespan

