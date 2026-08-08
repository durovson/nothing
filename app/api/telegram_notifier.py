import logging
from html import escape
from urllib.parse import quote

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import Settings
from app.core.constants import (
    COMPLETED_DEALS_CHANNEL,
    COMPLETED_DEALS_TOPIC_ID,
)
from app.core.custom_emoji import CustomEmoji
from app.core.enums import DealType, Language, TonNetwork
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import DealAction, DealCallback, MenuAction, MenuCallback
from app.locales import TextKey, translate
from app.models.entities import Deal, User
from app.ton.amounts import asset_payment_amount
from app.utils import currency_label, format_amount

logger = logging.getLogger(__name__)


class TelegramNotificationGateway:
    """Send one role-specific Telegram notification for each domain event."""

    def __init__(self, bot: Bot, settings: Settings):
        self._bot = bot
        self._settings = settings

    async def buyer_joined(self, deal: Deal, buyer: User, seller: User, buyer_deals: int) -> None:
        username = f"@{escape(buyer.username)}" if buyer.username else "без username"
        if seller.language is Language.RU:
            text = (
                f"Пользователь {username} ({buyer.telegram_id}) присоединился к сделке "
                f"#{deal.public_id}\n\n"
                f"• Сделок завершено: {buyer_deals}\n\n"
                "⚠️ <b>ВАЖНО</b>\n\n"
                "Проверьте, что Telegram ID и username совпадают с пользователем, с которым вы "
                "договорились о сделке вне бота.\n\n"
                "Никогда не оказывайте услугу до получения уведомления «Оплата подтверждена».\n\n"
                "Дождитесь сообщения от бота о подтверждении оплаты, прежде чем оказать услугу!"
            )
            profile = "Профиль покупателя"
            open_text = "Открыть сделку"
        else:
            text = (
                f"User {username} ({buyer.telegram_id}) joined deal #{deal.public_id}\n\n"
                f"• Buyer completed deals: {buyer_deals}\n\n"
                "⚠️ Make sure this is the same person you spoke with.\n\n"
                "Do not deliver the service until the bot confirms payment."
            )
            profile = "Buyer profile"
            open_text = "Open deal"
        await self._send_text(
            seller.telegram_id,
            text,
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=profile, url=f"tg://user?id={buyer.telegram_id}")],
                [self._open_deal(deal, open_text)],
            ]),
        )

    async def payment_received(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        transaction_url = self._transaction_url(deal)
        if deal.deal_type is DealType.CHANNEL:
            if buyer:
                await self._send(
                    buyer,
                    TextKey.DEAL_CHANNEL_PAID_BUYER,
                    deal_id=deal.public_id,
                    transaction_url=transaction_url,
                    reply_markup=self._open_keyboard(deal, buyer.language),
                )
            if seller:
                await self._send(
                    seller,
                    TextKey.DEAL_CHANNEL_PAID_SELLER,
                    deal_id=deal.public_id,
                    transaction_url=transaction_url,
                    reply_markup=self._transaction_keyboard(deal, seller.language, transaction_url),
                )
            return

        if buyer:
            await self._send(
                buyer,
                TextKey.DEAL_PAID_BUYER,
                deal_id=deal.public_id,
                description=deal.description,
                seller=self._user_label(seller),
                transaction_url=transaction_url,
                reply_markup=self._transaction_keyboard(deal, buyer.language, transaction_url),
            )
        if seller:
            await self._send(
                seller,
                TextKey.DEAL_PAID_SELLER,
                deal_id=deal.public_id,
                description=deal.description,
                buyer=self._user_label(buyer),
                transaction_url=transaction_url,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [premium_button(
                        text="Услуга оказана" if seller.language is Language.RU else "Service delivered",
                        icon=CustomEmoji.COMPLETE,
                        callback_data=DealCallback(action=DealAction.DELIVER, deal_id=deal.id).pack(),
                    )],
                    [self._transaction_button(seller.language, transaction_url)],
                    [self._open_deal(deal, self._open_label(seller.language))],
                ]),
            )

    async def delivery_marked(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        del seller
        if not buyer:
            return
        payment_amount = asset_payment_amount(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )
        await self._send(
            buyer,
            TextKey.DEAL_DELIVERY_NOTICE,
            deal_id=deal.public_id,
            description=deal.description,
            payment_amount=format_amount(payment_amount),
            currency=currency_label(deal.currency),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [premium_button(
                    text="Завершить сделку" if buyer.language is Language.RU else "Complete deal",
                    icon=CustomEmoji.CONFIRM,
                    callback_data=DealCallback(action=DealAction.CONFIRM, deal_id=deal.id).pack(),
                )],
                [self._open_deal(deal, self._open_label(buyer.language))],
                [premium_button(
                    text="Открыть спор" if buyer.language is Language.RU else "Open dispute",
                    icon=CustomEmoji.DISPUTE,
                    callback_data=DealCallback(action=DealAction.DISPUTE, deal_id=deal.id).pack(),
                )],
            ]),
        )

    async def payout_confirmed(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        del buyer
        if not seller:
            return
        payout_url = self._transaction_url(deal, payout=True)
        await self._send(
            seller,
            TextKey.DEAL_PAYOUT_RECEIVED,
            deal_id=deal.public_id,
            description=deal.description,
            amount=format_amount(deal.amount),
            currency=currency_label(deal.currency),
            wallet=escape(deal.seller_wallet_address or seller.wallet_address or "—"),
            transaction_url=payout_url,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [self._transaction_button(seller.language, payout_url)],
                [self._home_button(seller.language)],
            ]),
        )

    async def completed_deal_feed(self, deal: Deal) -> bool:
        """Publish one safely escaped summary after the payout is finalized."""
        payment_amount = asset_payment_amount(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )
        text = translate(
            Language.RU,
            TextKey.COMPLETED_DEAL_FEED,
            deal_id=deal.public_id,
            description=deal.description,
            amount=format_amount(deal.amount),
            payment_amount=format_amount(payment_amount),
            currency=currency_label(deal.currency),
        )
        try:
            await self._bot.send_message(
                COMPLETED_DEALS_CHANNEL,
                text,
                message_thread_id=COMPLETED_DEALS_TOPIC_ID,
            )
        except Exception:
            logger.exception(
                "Completed deal feed publication failed deal=%s channel=%s",
                deal.public_id,
                COMPLETED_DEALS_CHANNEL,
            )
            return False
        return True

    async def cancelled_by_seller(self, deal: Deal, buyer: User) -> None:
        await self._send(
            buyer,
            TextKey.DEAL_CANCELLED_BY_SELLER,
            deal_id=deal.public_id,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[self._home_button(buyer.language)]]),
        )

    async def refund_confirmed(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        for user in (buyer, seller):
            if user:
                await self._send(user, TextKey.DEAL_REFUNDED)

    async def dispute_opened(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        for user in (buyer, seller):
            if user:
                await self._send(user, TextKey.DEAL_DISPUTE_CREATED)

    def _transaction_url(self, deal: Deal, *, payout: bool = False) -> str:
        transaction_hash = deal.payout_tx_hash if payout else deal.paid_tx_hash
        if not transaction_hash:
            logger.error("Deal %s has no %s transaction hash", deal.public_id, "payout" if payout else "payment")
            return "https://tonviewer.com/"
        host = "testnet.tonviewer.com" if self._settings.TON_NETWORK is TonNetwork.TESTNET else "tonviewer.com"
        return f"https://{host}/transaction/{quote(transaction_hash, safe='')}"

    async def _send(self, user: User, key: TextKey, **kwargs: object) -> None:
        reply_markup = kwargs.pop("reply_markup", None)
        await self._send_text(user.telegram_id, translate(user.language, key, **kwargs), reply_markup)

    async def _send_text(
        self,
        user_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        try:
            await self._bot.send_message(user_id, text, reply_markup=reply_markup)
        except Exception:
            logger.exception("Telegram notification failed for user %s", user_id)

    @staticmethod
    def _user_label(user: User | None) -> str:
        if not user:
            return "—"
        return f"@{escape(user.username)} ({user.telegram_id})" if user.username else str(user.telegram_id)

    @staticmethod
    def _open_deal(deal: Deal, text: str = "Открыть сделку") -> InlineKeyboardButton:
        return premium_button(
            text=text,
            icon=CustomEmoji.CREATE_DEAL,
            callback_data=DealCallback(action=DealAction.OPEN, deal_id=deal.id).pack(),
        )

    @staticmethod
    def _open_label(language: Language) -> str:
        return "Открыть сделку" if language is Language.RU else "Open deal"

    @staticmethod
    def _transaction_button(language: Language, url: str) -> InlineKeyboardButton:
        return premium_button(
            text="Посмотреть транзакцию" if language is Language.RU else "View transaction",
            icon=CustomEmoji.TON,
            url=url,
        )

    @staticmethod
    def _home_button(language: Language) -> InlineKeyboardButton:
        return premium_button(
            text="Главное меню" if language is Language.RU else "Main menu",
            icon=CustomEmoji.HOME,
            callback_data=MenuCallback(action=MenuAction.BACK).pack(),
        )

    def _open_keyboard(self, deal: Deal, language: Language) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[[self._open_deal(deal, self._open_label(language))]])

    def _transaction_keyboard(
        self,
        deal: Deal,
        language: Language,
        transaction_url: str,
    ) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [self._transaction_button(language, transaction_url)],
            [self._open_deal(deal, self._open_label(language))],
        ])
