from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.enums import Language
from app.services.users import UserService


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
        if event_user:
            user = await self._users.ensure_user(
                telegram_id=event_user.id,
                username=event_user.username,
                default_language=self._default_language,
            )
            data["db_user"] = user
            data["locale"] = user.language
        else:
            data["locale"] = self._default_language
        return await handler(event, data)

