from __future__ import annotations

import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    ChatMemberAdministrator,
    ChatMemberMember,
    ChatMemberOwner,
    ChatMemberRestricted,
)

from app.core.enums import ChannelMemberStatus
from app.core.exceptions import ChannelConfigurationError
from app.models.dto import ChannelDescriptor
from app.models.entities import Deal, User

logger = logging.getLogger(__name__)


class TelegramChannelGateway:
    """Validate a channel and observe ownership; never changes buyer privileges."""

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
            creates_join_request=False,
        )
        return invite.invite_link

    async def buyer_status(self, deal: Deal) -> ChannelMemberStatus:
        """Return the buyer's current role reported by Telegram getChatMember."""
        if deal.channel_id is None or deal.buyer_id is None:
            raise ChannelConfigurationError("У сделки отсутствует канал или покупатель")
        try:
            member = await self._bot.get_chat_member(deal.channel_id, deal.buyer_id)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            raise ChannelConfigurationError(
                "Не удалось проверить покупателя; бот должен оставаться администратором канала"
            ) from exc
        if isinstance(member, ChatMemberOwner):
            return ChannelMemberStatus.OWNER
        if isinstance(member, ChatMemberAdministrator):
            return ChannelMemberStatus.ADMINISTRATOR
        if isinstance(member, (ChatMemberMember, ChatMemberRestricted)):
            return ChannelMemberStatus.MEMBER
        return ChannelMemberStatus.ABSENT

    async def owner_verified(
        self, deal: Deal, buyer: User | None, seller: User | None
    ) -> None:
        if buyer:
            await self._safe_send(
                buyer.telegram_id,
                f"✅ Вы стали владельцем канала «{escape(deal.channel_title or deal.public_id)}». "
                "Проверка завершена автоматически; выплата продавцу поставлена в очередь.",
            )
        if seller:
            await self._safe_send(
                seller.telegram_id,
                f"✅ Покупатель подтверждён владельцем канала «{escape(deal.channel_title or deal.public_id)}». "
                "Выплата поставлена в очередь автоматически.",
            )

    async def transfer_disputed(
        self, deal: Deal, buyer: User | None, seller: User | None
    ) -> None:
        text = (
            f"⚖️ Сделка <code>#{deal.public_id}</code> переведена в спор: к дедлайну Telegram "
            "не подтвердил покупателя владельцем канала. Средства остаются у гаранта."
        )
        for user in (buyer, seller):
            if user:
                await self._safe_send(user.telegram_id, text)

    async def _safe_send(self, user_id: int, text: str) -> None:
        try:
            await self._bot.send_message(user_id, text)
        except Exception:
            logger.exception("Channel workflow notification failed user=%s", user_id)
