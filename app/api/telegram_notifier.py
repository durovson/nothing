import logging
from html import escape
from urllib.parse import quote

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import DealType, Language, TonNetwork
from app.keyboards.callbacks import DealAction, DealCallback, MenuAction, MenuCallback
from app.utils import currency_label, format_amount
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
        if deal.deal_type is DealType.CHANNEL:
            if buyer:
                await self._send(
                    buyer,
                    TextKey.DEAL_CHANNEL_PAID_BUYER,
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[self._open_deal(deal, self._open_label(buyer.language))]]
                    ),
                )
            if seller:
                await self._send(
                    seller,
                    TextKey.DEAL_CHANNEL_PAID_SELLER,
                    transaction_url=self._transaction_url(deal),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="Посмотреть транзакцию" if seller.language is Language.RU else "View transaction",
                            url=self._transaction_url(deal),
                        )],
                        [self._open_deal(deal, self._open_label(seller.language))],
                    ]),
                )
            return
        if buyer:
            await self._send(
                buyer,
                TextKey.DEAL_PAID_BUYER,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[self._open_deal(deal)]]),
            )
        if seller:
            await self._send(
                seller,
                TextKey.DEAL_PAID_SELLER,
                transaction_url=self._transaction_url(deal),
                deal_id=deal.public_id,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="Услуга оказана" if seller.language is Language.RU else "Service delivered",
                        callback_data=DealCallback(action=DealAction.DELIVER, deal_id=deal.id).pack(),
                    )],
                    [InlineKeyboardButton(
                        text="Посмотреть транзакцию" if seller.language is Language.RU else "View transaction",
                        url=self._transaction_url(deal),
                    )],
                    [self._open_deal(deal, "Открыть сделку" if seller.language is Language.RU else "Open deal")],
                ]),
            )

    async def payout_confirmed(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        for user in (buyer, seller):
            if user:
                await self._send(
                    user,
                    TextKey.DEAL_CONFIRMED,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [self._open_deal(deal, "Открыть сделку" if user.language is Language.RU else "Open deal")],
                        [InlineKeyboardButton(
                            text="Главное меню" if user.language is Language.RU else "Main menu",
                            callback_data=MenuCallback(action=MenuAction.BACK).pack(),
                        )],
                    ]),
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

    async def delivery_marked(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        if buyer:
            await self._send(
                buyer,
                TextKey.DEAL_DELIVERY_NOTICE,
                deal_id=deal.public_id,
                amount=format_amount(deal.amount),
                currency=currency_label(deal.currency),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[self._open_deal(deal)]]),
            )
        if seller:
            await self._send(
                seller,
                TextKey.DEAL_DELIVERED,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[self._open_deal(deal)]]),
            )

    async def dispute_opened(
        self,
        deal: Deal,
        buyer: User | None,
        seller: User | None,
    ) -> None:
        for user in (buyer, seller):
            if user:
                await self._send(user, TextKey.DEAL_DISPUTE_CREATED)

    def _transaction_url(self, deal: Deal) -> str:
        if not deal.paid_tx_hash:
            logger.error("Paid deal %s has no transaction hash", deal.public_id)
            return "—"
        host = "testnet.tonviewer.com" if self._network is TonNetwork.TESTNET else "tonviewer.com"
        return f"https://{host}/transaction/{quote(deal.paid_tx_hash, safe='')}"

    async def _send(self, user: User, key: TextKey, **kwargs: object) -> None:
        reply_markup = kwargs.pop("reply_markup", None)
        await self._send_text(
            user.telegram_id,
            translate(user.language, key, **kwargs),
            reply_markup,
        )

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
    def _open_deal(deal: Deal, text: str = "Открыть сделку") -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=text,
            callback_data=DealCallback(action=DealAction.OPEN, deal_id=deal.id).pack(),
        )

    @staticmethod
    def _open_label(language: Language) -> str:
        return "Открыть сделку" if language is Language.RU else "Open deal"

    async def buyer_joined(self, deal: Deal, buyer: User, seller: User, buyer_deals: int) -> None:
        username = f"@{escape(buyer.username)}" if buyer.username else "без username"
        if seller.language is Language.RU:
            text = (
                f"Пользователь {username} ({buyer.telegram_id}) присоединился к сделке #{deal.public_id}\n\n"
                f"• Количество сделок покупателя: {buyer_deals}\n\n"
                "‼️ Убедитесь, что это тот же пользователь, с которым вы вели диалог ранее!\n\n"
                "Дождитесь получения сообщения от бота о подтверждении оплаты, прежде чем оказать услугу!"
            )
            profile = "Профиль покупателя"
            open_text = "Открыть сделку"
        else:
            text = (
                f"User {username} ({buyer.telegram_id}) joined deal #{deal.public_id}\n\n"
                f"• Buyer deals: {buyer_deals}\n\n"
                "‼️ Make sure this is the same person you spoke with. Wait for payment confirmation before delivery."
            )
            profile = "Buyer profile"
            open_text = "Open deal"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=profile, url=f"tg://user?id={buyer.telegram_id}")],
            [self._open_deal(deal, open_text)],
        ])
        await self._send_text(seller.telegram_id, text, keyboard)
