from __future__ import annotations

import logging
from time import monotonic

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.core.constants import (
    TOPIC_COOLDOWN_CHAT_USERNAME,
    TOPIC_COOLDOWN_CLEANUP_INTERVAL,
    TOPIC_COOLDOWN_SECONDS,
    TOPIC_COOLDOWN_UNLIMITED_TOPIC_ID,
)

logger = logging.getLogger(__name__)
router = Router(name="topic_cooldown")

# Telegram does not provide per-topic member restrictions. Keep only the
# deadline required to remove repeated messages in the same topic. This state
# is intentionally process-local: it needs no database or background timer.
_deadlines: dict[tuple[int, int, int], float] = {}
_accepted_messages = 0


def _cleanup_expired(now: float) -> None:
    expired = [key for key, deadline in _deadlines.items() if deadline <= now]
    for key in expired:
        _deadlines.pop(key, None)


@router.message(
    F.chat.type == ChatType.SUPERGROUP,
    F.chat.username == TOPIC_COOLDOWN_CHAT_USERNAME,
    F.is_topic_message,
)
async def enforce_topic_cooldown(message: Message, bot: Bot) -> None:
    """Allow one message per user and topic during each cooldown window."""

    global _accepted_messages

    user = message.from_user
    topic_id = message.message_thread_id
    if user is None or user.is_bot or topic_id is None:
        return

    # Anonymous administrators and channel-authored posts have no ordinary
    # member identity to rate-limit and must remain untouched.
    if message.sender_chat is not None:
        return

    if topic_id == TOPIC_COOLDOWN_UNLIMITED_TOPIC_ID:
        return

    try:
        member = await bot.get_chat_member(message.chat.id, user.id)
    except TelegramAPIError as exc:
        # Fail open: a temporary Telegram error must never delete a legitimate
        # message or accidentally treat an administrator as a regular member.
        logger.warning(
            "Topic cooldown member check failed chat=%s topic=%s user=%s error=%s",
            message.chat.id,
            topic_id,
            user.id,
            type(exc).__name__,
        )
        return

    if member.status in {
        ChatMemberStatus.CREATOR,
        ChatMemberStatus.ADMINISTRATOR,
    }:
        return

    now = monotonic()
    key = (message.chat.id, topic_id, user.id)
    if now < _deadlines.get(key, 0):
        try:
            await bot.delete_message(message.chat.id, message.message_id)
        except TelegramAPIError as exc:
            logger.info(
                "Topic cooldown deletion failed chat=%s topic=%s user=%s error=%s",
                message.chat.id,
                topic_id,
                user.id,
                type(exc).__name__,
            )
        return

    _deadlines[key] = now + TOPIC_COOLDOWN_SECONDS
    _accepted_messages += 1
    if _accepted_messages % TOPIC_COOLDOWN_CLEANUP_INTERVAL == 0:
        _cleanup_expired(now)
