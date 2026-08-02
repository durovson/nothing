import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, Update

from app.core.constants import SLOW_CALLBACK_ACK_SECONDS
from app.core.telemetry import current_trace_id

logger = logging.getLogger(__name__)

_FAST_EXACT_CALLBACKS = frozenset(
    {
        "menu:back",
        "menu:wallet",
        "menu:deals",
        "menu:settings",
        "menu:referrals",
        "menu:faq",
        "menu:documents",
        "settings:back",
        "settings:referrals",
        "settings:language",
        "settings:support",
        "wallet:back",
        "wallet:edit",
    }
)
_FAST_CALLBACK_PREFIXES = (
    "page:",
    "deal:open:",
    "deal-type:",
    "currency:",
    "language:",
)


def is_fast_navigation_callback(data: str | None) -> bool:
    """Identify callbacks that never need a popup response from their handler."""
    if not data:
        return False
    return data in _FAST_EXACT_CALLBACKS or data.startswith(_FAST_CALLBACK_PREFIXES)


def callback_from_event(event: TelegramObject) -> CallbackQuery | None:
    """Extract a callback both at update-level and callback-query-level middleware."""
    if isinstance(event, CallbackQuery):
        return event
    if isinstance(event, Update):
        return event.callback_query
    return None


class FastCallbackMiddleware(BaseMiddleware):
    """Acknowledge safe navigation concurrently with rendering its next screen."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        callback = callback_from_event(event)
        if callback is None or not is_fast_navigation_callback(callback.data):
            return await handler(event, data)

        # Telegram ACK and screen rendering are independent API requests. Running
        # them concurrently removes one full network round trip from navigation.
        ack_task = asyncio.create_task(
            self._acknowledge(callback),
            name=f"callback-ack:{callback.id}",
        )
        try:
            return await handler(event, data)
        finally:
            await ack_task

    @staticmethod
    async def _acknowledge(callback: CallbackQuery) -> None:
        started_at = perf_counter()
        try:
            await callback.answer()
        except Exception:
            # A failed ACK must not suppress the actual menu handler. Aiogram's
            # polling/backoff layer will independently recover transport errors.
            logger.warning(
                "Telegram callback ACK failed trace=%s callback=%s",
                current_trace_id(),
                callback.data,
                exc_info=True,
            )
        finally:
            duration = perf_counter() - started_at
            if duration >= SLOW_CALLBACK_ACK_SECONDS:
                logger.warning(
                    "Slow Telegram callback ACK trace=%s callback=%s duration_ms=%.1f",
                    current_trace_id(),
                    callback.data,
                    duration * 1_000,
                )
