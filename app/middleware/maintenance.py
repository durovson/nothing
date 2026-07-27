from collections.abc import Awaitable, Callable
from html import escape
from typing import Any

from aiogram import BaseMiddleware
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
        if user and self._admin.is_admin(user.id):
            return await handler(event, data)
        settings = await self._admin.maintenance()
        if not settings.maintenance_enabled:
            return await handler(event, data)
        bot = data.get("bot")
        if bot and user:
            await bot.send_message(user.id, escape(settings.maintenance_message))
        return None
