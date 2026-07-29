from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, Update

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
    """Acknowledge safe navigation before database and rendering network calls."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        callback = callback_from_event(event)
        if callback is not None and is_fast_navigation_callback(callback.data):
            await callback.answer()
        return await handler(event, data)
