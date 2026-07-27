from __future__ import annotations

import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner

from app.core.exceptions import ChannelConfigurationError
from app.models.dto import ChannelDescriptor
from app.models.entities import Deal, User

logger = logging.getLogger(__name__)


class TelegramChannelGateway:
    """Telegram Bot API adapter for channel validation and administrator access."""

    def __init__(self, bot: Bot):
        self._bot = bot

    async def validate_for_sale(
        self, channel_reference: int | str, seller_id: int
    ) -> ChannelDescriptor:
        try:
            chat = await self._bot.get_chat(channel_reference)
            bot_user = await self._bot.get_me()
            bot_member = await self._bot.get_chat_member(chat.id, bot_user.id)
            seller_member = await self._bot.get_chat_member(chat.id, seller_id)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            raise ChannelConfigurationError(
                "Канал не найден или бот не имеет доступа к нему"
            ) from exc
        if chat.type != "channel":
            raise ChannelConfigurationError("Нужно указать именно Telegram-канал")
        if not isinstance(seller_member, ChatMemberOwner):
            raise ChannelConfigurationError("Создатель сделки должен быть владельцем канала")
        if not isinstance(bot_member, ChatMemberAdministrator):
            raise ChannelConfigurationError("Добавьте бота администратором канала")
        required = {
            "управление каналом": bot_member.can_manage_chat,
            "публикация сообщений": bot_member.can_post_messages,
            "редактирование сообщений": bot_member.can_edit_messages,
            "удаление сообщений": bot_member.can_delete_messages,
            "приглашение пользователей": bot_member.can_invite_users,
            "назначение администраторов": bot_member.can_promote_members,
        }
        missing = [name for name, enabled in required.items() if not enabled]
        if missing:
            raise ChannelConfigurationError(
                "Боту не выданы полные права: " + ", ".join(missing)
            )
        return ChannelDescriptor(
            channel_id=chat.id,
            title=chat.title or str(chat.id),
            username=chat.username,
        )

    async def create_buyer_join_link(self, deal: Deal) -> str:
        if deal.channel_id is None:
            raise ChannelConfigurationError("У сделки отсутствует ID канала")
        invite = await self._bot.create_chat_invite_link(
            deal.channel_id,
            name=f"Deal {deal.public_id}",
            creates_join_request=True,
        )
        return invite.invite_link

    async def grant_buyer_admin(self, deal: Deal) -> bool:
        if deal.channel_id is None or deal.buyer_id is None:
            raise ChannelConfigurationError("У сделки отсутствует канал или покупатель")
        try:
            await self._bot.approve_chat_join_request(deal.channel_id, deal.buyer_id)
        except TelegramBadRequest:
            pass
        try:
            member = await self._bot.get_chat_member(deal.channel_id, deal.buyer_id)
        except TelegramBadRequest:
            return False
        if member.status in {"left", "kicked"}:
            return False
        try:
            return await self._bot.promote_chat_member(
                deal.channel_id,
                deal.buyer_id,
                is_anonymous=False,
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=True,
                can_change_info=True,
                can_invite_users=True,
                can_post_stories=True,
                can_edit_stories=True,
                can_delete_stories=True,
                can_post_messages=True,
                can_edit_messages=True,
                can_pin_messages=True,
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            raise ChannelConfigurationError(
                "Telegram не разрешил выдать покупателю права администратора"
            ) from exc

    async def access_required(self, deal: Deal, buyer: User, invite_link: str) -> None:
        await self._safe_send(
            buyer.telegram_id,
            "Оплата подтверждена и удерживается гарантом.\n\n"
            "Чтобы получить доступ к каналу, отправьте заявку по ссылке:\n"
            f"{escape(invite_link)}\n\nПосле заявки бот автоматически выдаст права администратора и запустит выплату продавцу.",
        )

    async def access_granted(
        self, deal: Deal, buyer: User | None, seller: User | None
    ) -> None:
        if buyer:
            await self._safe_send(
                buyer.telegram_id,
                f"Доступ к каналу «{escape(deal.channel_title or deal.public_id)}» выдан. "
                "Вы назначены администратором с максимальными доступными боту правами.",
            )
        if seller:
            await self._safe_send(
                seller.telegram_id,
                f"Покупателю выдан полный административный доступ к каналу «{escape(deal.channel_title or deal.public_id)}». "
                "Выплата поставлена в очередь. Передача статуса владельца выполняется вами вручную в Telegram.",
            )

    async def _safe_send(self, user_id: int, text: str) -> None:
        try:
            await self._bot.send_message(user_id, text)
        except Exception:
            logger.exception("Channel workflow notification failed user=%s", user_id)
