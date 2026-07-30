import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.core.constants import SLOW_UPDATE_SECONDS
from app.core.telemetry import bind_trace_id, reset_trace_id

logger = logging.getLogger(__name__)


def update_kind(update: Update) -> tuple[str, str | None]:
    if update.callback_query is not None:
        return "callback_query", update.callback_query.data
    if update.message is not None:
        return "message", None
    if update.edited_message is not None:
        return "edited_message", None
    return "other", None


class PerformanceMiddleware(BaseMiddleware):
    """Correlate and report slow Telegram updates without logging message text."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)
        trace_id = f"telegram:{event.update_id}"
        token = bind_trace_id(trace_id)
        started_at = perf_counter()
        kind, callback_data = update_kind(event)
        try:
            return await handler(event, data)
        finally:
            duration = perf_counter() - started_at
            if duration >= SLOW_UPDATE_SECONDS:
                logger.warning(
                    "Slow Telegram update trace=%s kind=%s callback=%s duration_ms=%.1f",
                    trace_id,
                    kind,
                    callback_data or "-",
                    duration * 1_000,
                )
            reset_trace_id(token)
