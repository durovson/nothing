from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.models.entities import User
from app.services.community_desk import CommunityDeskService, looks_like_community_listing

logger = logging.getLogger(__name__)
router = Router(name="community_desk")


def _chat_member_status(member: types.ChatMember) -> str:
    """Normalize aiogram versions that expose status as either str or enum."""
    status = member.status
    return getattr(status, "value", status)


def _message_source_bot(message: types.Message) -> types.User | None:
    """Return the verifiable bot that authored a direct or forwarded message."""
    sender = message.from_user
    if sender is not None and sender.is_bot:
        return sender

    # A human forwarding a bot message becomes Message.from, while Telegram
    # preserves the original bot in Message.forward_origin.sender_user.
    origin = getattr(message, "forward_origin", None)
    origin_user = getattr(origin, "sender_user", None)
    if origin_user is not None and origin_user.is_bot:
        return origin_user
    return None


def _listing_payload(
    message: types.Message,
) -> tuple[str | None, list[types.MessageEntity] | None]:
    """Read listings from both plain-text messages and media captions."""
    if message.text is not None:
        return message.text, message.entities
    return message.caption, message.caption_entities


@router.message(Command("connect"))
async def connect_community_desk(
    message: types.Message,
    bot: Bot,
    db_user: User,
    community_desk_service: CommunityDeskService,
) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Команда /connect доступна только в ветке сообщества.")
        return
    topic_id = message.message_thread_id
    if not message.is_topic_message or topic_id is None:
        await message.answer("Отправьте /connect внутри нужной ветки форума.")
        return
    try:
        member = await bot.get_chat_member(message.chat.id, db_user.telegram_id)
    except Exception:
        logger.warning(
            "Could not verify Community Desk administrator chat=%s user=%s",
            message.chat.id,
            db_user.telegram_id,
            exc_info=True,
        )
        await message.answer("Не удалось проверить права администратора.")
        return
    if _chat_member_status(member) not in {"creator", "administrator"}:
        await message.answer("Подключить ветку может только администратор сообщества.")
        return
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
    except Exception:
        await message.answer("Не удалось проверить права бота в сообществе.")
        return
    if _chat_member_status(bot_member) not in {"creator", "administrator"}:
        await message.answer(
            "Сначала назначьте бота администратором сообщества, затем повторите /connect."
        )
        return

    source_bot = (
        _message_source_bot(message.reply_to_message)
        if message.reply_to_message is not None
        else None
    )
    community = await community_desk_service.connect(
        chat_id=message.chat.id,
        topic_id=topic_id,
        name=message.chat.title or "Community",
        username=message.chat.username,
        owner_user_id=db_user.telegram_id,
        source_bot_id=source_bot.id if source_bot is not None else None,
        source_bot_username=source_bot.username if source_bot is not None else None,
    )
    moderation = "включена" if community.desk_enabled else "выключена"
    if community.desk_source_bot_id is not None:
        source_label = (
            f"@{escape(community.desk_source_bot_username)}"
            if community.desk_source_bot_username
            else f"<code>{community.desk_source_bot_id}</code>"
        )
    else:
        source_label = (
            "будет привязан по первой подходящей публикации. Поддерживаются "
            "как прямые bot-to-bot сообщения, так и пересланные сообщения бота."
        )

    private_text = (
        f"<tg-emoji emoji-id='{CustomEmoji.CONFIRM.value}'>✅</tg-emoji> "
        "<b>Ветка Community Desk подключена.</b>\n\n"
        f"<b>Chat ID:</b> <code>{message.chat.id}</code>\n"
        f"<b>Topic ID:</b> <code>{topic_id}</code>\n"
        f"<b>Сообщество:</b> {escape(community.name)}\n"
        f"<b>Бот-источник:</b> {source_label}\n"
        f"<b>Публикация:</b> {moderation}"
    )
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    try:
        await bot.send_message(db_user.telegram_id, private_text)
    except TelegramForbiddenError:
        logger.warning(
            "Could not send private Community Desk confirmation user=%s",
            db_user.telegram_id,
        )


@router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.is_topic_message,
    (
        F.text.func(looks_like_community_listing)
        | F.caption.func(looks_like_community_listing)
    ),
)
async def mirror_visible_community_listing(
    message: types.Message,
    community_desk_service: CommunityDeskService,
) -> None:
    topic_id = message.message_thread_id
    source_bot = _message_source_bot(message)
    text, entities = _listing_payload(message)
    if (
        message.chat.type not in {"group", "supergroup"}
        or not message.is_topic_message
        or topic_id is None
        or source_bot is None
        or not looks_like_community_listing(text)
    ):
        return
    try:
        await community_desk_service.ingest(
            chat_id=message.chat.id,
            topic_id=topic_id,
            message_id=message.message_id,
            source_bot_id=source_bot.id,
            source_bot_username=source_bot.username,
            text=text or "",
            entities=entities,
            owner_language=Language.RU,
        )
    except Exception:
        logger.exception(
            "Community Desk ingestion failed chat=%s topic=%s message=%s",
            message.chat.id,
            topic_id,
            message.message_id,
        )
