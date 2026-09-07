import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.constants import SLOW_USER_LOOKUP_SECONDS
from app.core.enums import Language
from app.core.telemetry import current_trace_id
from app.database import is_transient_database_error
from app.middleware.fast_callback import callback_from_event, is_fast_navigation_callback
from app.models.entities import User
from app.services.users import UserService

logger = logging.getLogger(__name__)
USER_NAVIGATION_FALLBACK_CACHE_SIZE = 5_000


class CurrentUserMiddleware(BaseMiddleware):
    def __init__(self, users: UserService, default_language: Language):
        self._users = users
        self._default_language = default_language
        self._last_known_users: OrderedDict[int, User] = OrderedDict()

    def _remember(self, user: User) -> None:
        self._last_known_users[user.telegram_id] = user
        self._last_known_users.move_to_end(user.telegram_id)
        if len(self._last_known_users) > USER_NAVIGATION_FALLBACK_CACHE_SIZE:
            self._last_known_users.popitem(last=False)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        event_user = data.get("event_from_user")
        if event_user and not event_user.is_bot:
            started_at = perf_counter()
            try:
                try:
                    user = await self._users.ensure_user(
                        telegram_id=event_user.id,
                        username=event_user.username,
                        default_language=self._default_language,
                    )
                except Exception as exc:
                    callback = callback_from_event(event)
                    cached_user = self._last_known_users.get(event_user.id)
                    if (
                        cached_user is None
                        or callback is None
                        or not is_fast_navigation_callback(callback.data)
                        or not is_transient_database_error(exc)
                    ):
                        raise
                    user = cached_user
                    self._last_known_users.move_to_end(event_user.id)
                    logger.warning(
                        "Using cached user for navigation after transient Supabase failure "
                        "trace=%s callback=%s error=%s",
                        current_trace_id(),
                        callback.data,
                        type(exc).__name__,
                    )
                else:
                    self._remember(user)
            finally:
                duration = perf_counter() - started_at
                if duration >= SLOW_USER_LOOKUP_SECONDS:
                    logger.warning(
                        "Slow current-user lookup trace=%s duration_ms=%.1f",
                        current_trace_id(),
                        duration * 1_000,
                    )
            data["db_user"] = user
            data["locale"] = user.language
        else:
            data["locale"] = self._default_language
        return await handler(event, data)
