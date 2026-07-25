import logging
from urllib.parse import quote

from aiogram import Bot

from app.core.enums import TonNetwork
from app.locales import TextKey, translate
from app.models.entities import Deal, User

logger = logging.getLogger(__name__)


class TelegramNotificationGateway:
    def __init__(self, bot: Bot, network: TonNetwork):
        self._bot = bot
        self._network = network

    async def payment_received(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        if buyer:
            await self._send(buyer, TextKey.DEAL_PAID_BUYER)
        if seller:
            await self._send(
                seller,
                TextKey.DEAL_PAID_SELLER,
                transaction_url=self._transaction_url(deal),
            )

    async def payout_confirmed(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        for user in (buyer, seller):
            if user:
                await self._send(user, TextKey.DEAL_CONFIRMED)

    def _transaction_url(self, deal: Deal) -> str:
        if not deal.paid_tx_hash:
            logger.error("Paid deal %s has no transaction hash", deal.public_id)
            return "—"
        host = "testnet.tonviewer.com" if self._network is TonNetwork.TESTNET else "tonviewer.com"
        return f"https://{host}/transaction/{quote(deal.paid_tx_hash, safe='')}"

    async def _send(self, user: User, key: TextKey, **kwargs: object) -> None:
        try:
            await self._bot.send_message(user.telegram_id, translate(user.language, key, **kwargs))
        except Exception:
            logger.exception("Telegram notification failed for user %s", user.telegram_id)
