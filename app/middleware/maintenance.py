from collections.abc import Awaitable, Callable
from html import escape
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import TelegramObject

from app.services.admin import AdminService


class MaintenanceMiddleware(BaseMiddleware):
    def __init__(self, admin: AdminService):
        self._admin = admin

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        # Bot-to-bot group updates are service input, not an interactive user
        # session. Never try to open a private chat with the source bot and let
        # the dedicated Community Desk handler process the message normally.
        if user and user.is_bot:
            return await handler(event, data)
        if user and self._admin.is_admin(user.id):
            return await handler(event, data)
        settings = await self._admin.maintenance()
        if not settings.maintenance_enabled:
            return await handler(event, data)
        bot = data.get("bot")
        if bot and user:
            try:
                await bot.send_message(user.id, escape(settings.maintenance_message))
            except (TelegramBadRequest, TelegramForbiddenError):
                # A group member may not have started the bot in private yet.
                # Maintenance mode must still suppress the update without
                # turning this expected Telegram restriction into an error.
                pass
        return None
