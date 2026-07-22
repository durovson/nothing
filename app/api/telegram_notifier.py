import logging

from aiogram import Bot

from app.locales import TextKey, translate
from app.models.entities import Deal, User

logger = logging.getLogger(__name__)


class TelegramNotificationGateway:
    def __init__(self, bot: Bot):
        self._bot = bot

    async def payment_received(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        if buyer:
            await self._send(buyer, TextKey.DEAL_PAID_BUYER)
        if seller:
            await self._send(seller, TextKey.DEAL_PAID_SELLER)

    async def payout_confirmed(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        for user in (buyer, seller):
            if user:
                await self._send(user, TextKey.DEAL_CONFIRMED)

    async def _send(self, user: User, key: TextKey) -> None:
        try:
            await self._bot.send_message(user.telegram_id, translate(user.language, key))
        except Exception:
            logger.exception("Telegram notification failed for user %s", user.telegram_id)

