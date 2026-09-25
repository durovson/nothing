from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router, types
from aiogram.filters import Command

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.models.entities import User
from app.services.community_desk import CommunityDeskService, looks_like_community_listing

logger = logging.getLogger(__name__)
router = Router(name="community_desk")


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
    if member.status.value not in {"creator", "administrator"}:
        await message.answer("Подключить ветку может только администратор сообщества.")
        return
    try:
        bot_member = await bot.get_chat_member(message.chat.id, bot.id)
    except Exception:
        await message.answer("Не удалось проверить права бота в сообществе.")
        return
    if bot_member.status.value not in {"creator", "administrator"}:
        await message.answer(
            "Сначала назначьте бота администратором сообщества, затем повторите /connect."
        )
        return

    replied_user = (
        message.reply_to_message.from_user
        if message.reply_to_message is not None
        else None
    )
    source_bot = (
        replied_user if replied_user is not None and replied_user.is_bot else None
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
    moderation = "включена" if community.desk_enabled else "ожидает ручного включения"
    if community.desk_source_bot_id is not None:
        source_label = (
            f"@{escape(community.desk_source_bot_username)}"
            if community.desk_source_bot_username
            else f"<code>{community.desk_source_bot_id}</code>"
        )
    else:
        source_label = (
            "будет зафиксирован по первой подходящей публикации; можно сразу "
            "привязать его, отправив /connect ответом на сообщение исходного бота"
        )
    await message.answer(
        f"<tg-emoji emoji-id='{CustomEmoji.CONFIRM.value}'>✅</tg-emoji> "
        "<b>Ветка Community Desk сохранена.</b>\n\n"
        f"<b>Chat ID:</b> <code>{message.chat.id}</code>\n"
        f"<b>Topic ID:</b> <code>{topic_id}</code>\n"
        f"<b>Сообщество:</b> {escape(community.name)}\n"
        f"<b>Бот-источник:</b> {source_label}\n"
        f"<b>Публикация:</b> {moderation}",
    )


@router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.is_topic_message,
    F.text.func(looks_like_community_listing),
)
async def mirror_visible_community_listing(
    message: types.Message,
    community_desk_service: CommunityDeskService,
) -> None:
    topic_id = message.message_thread_id
    sender = message.from_user
    if (
        message.chat.type not in {"group", "supergroup"}
        or not message.is_topic_message
        or topic_id is None
        or sender is None
        or not sender.is_bot
        or not looks_like_community_listing(message.text)
    ):
        return
    try:
        await community_desk_service.ingest(
            chat_id=message.chat.id,
            topic_id=topic_id,
            message_id=message.message_id,
            source_bot_id=sender.id,
            source_bot_username=sender.username,
            text=message.text or "",
            entities=message.entities,
            owner_language=Language.RU,
        )
    except Exception:
        logger.exception(
            "Community Desk ingestion failed chat=%s topic=%s message=%s",
            message.chat.id,
            topic_id,
            message.message_id,
        )
