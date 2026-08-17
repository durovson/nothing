import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.constants import SLOW_USER_LOOKUP_SECONDS
from app.core.enums import Language
from app.core.telemetry import current_trace_id
from app.services.users import UserService

logger = logging.getLogger(__name__)


class CurrentUserMiddleware(BaseMiddleware):
    def __init__(self, users: UserService, default_language: Language):
        self._users = users
        self._default_language = default_language

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
                user = await self._users.ensure_user(
                    telegram_id=event_user.id,
                    username=event_user.username,
                    default_language=self._default_language,
                )
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
