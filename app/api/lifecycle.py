from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bot import run_polling
from app.core.constants import (
    EVENT_LOOP_LAG_CONSECUTIVE_SAMPLES,
    EVENT_LOOP_LAG_WARNING_SECONDS,
    EVENT_LOOP_SEVERE_LAG_WARNING_SECONDS,
)
from app.loader import AppContainer

logger = logging.getLogger(__name__)


async def monitor_event_loop_lag(interval: float = 1.0) -> None:
    """Report blocking sync work, GIL contention, or long runtime pauses."""
    loop = asyncio.get_running_loop()
    expected = loop.time() + interval
    consecutive_lag_samples = 0
    while True:
        await asyncio.sleep(interval)
        now = loop.time()
        lag = max(0.0, now - expected)
        expected = now + interval
        if lag >= EVENT_LOOP_LAG_WARNING_SECONDS:
            consecutive_lag_samples += 1
            if (
                consecutive_lag_samples >= EVENT_LOOP_LAG_CONSECUTIVE_SAMPLES
                or lag >= EVENT_LOOP_SEVERE_LAG_WARNING_SECONDS
            ):
                logger.warning(
                    "Event loop lag detected lag_ms=%.1f consecutive_samples=%s",
                    lag * 1_000,
                    consecutive_lag_samples,
                )
        else:
            consecutive_lag_samples = 0


def create_lifespan(container: AppContainer) -> Callable[[FastAPI], AsyncIterator[None]]:
    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        settings = container.settings
        polling_task: asyncio.Task[None] | None = None
        lag_task: asyncio.Task[None] | None = None
        if not settings.TELEGRAM_USE_POLLING:
            if not settings.APP_BASE_URL:
                raise RuntimeError("APP_BASE_URL is required in webhook mode")
            if not settings.TELEGRAM_WEBHOOK_SECRET:
                raise RuntimeError("TELEGRAM_WEBHOOK_SECRET is required in webhook mode")

        try:
            await container.ton.start()
            logger.info("Startup phase completed: TON client")
            await container.database.warm_up()
            logger.info("Startup phase completed: Supabase")
            await container.monitor.start()
            logger.info("Startup phase completed: background workers")
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
            await container.keepalive.start()
            lag_task = asyncio.create_task(
                monitor_event_loop_lag(), name="event-loop-lag"
            )
            logger.info("Application runtime components started")
            yield
        finally:
            if polling_task:
                polling_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await polling_task
            await container.monitor.stop()
            await container.keepalive.stop()
            if lag_task:
                lag_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await lag_task
            await container.ton.close()
            await container.database.close()
            await container.bot.session.close()
            logger.info("Application runtime components stopped")

    return lifespan
