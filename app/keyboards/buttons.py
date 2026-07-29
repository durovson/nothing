from typing import Any

from aiogram.types import InlineKeyboardButton

from app.core.custom_emoji import CustomEmoji


def premium_button(
    text: str,
    *,
    icon: CustomEmoji | None = None,
    **data: Any,
) -> InlineKeyboardButton:
    """Build a button with a native Bot API custom-emoji icon."""

    return InlineKeyboardButton(
        text=text,
        icon_custom_emoji_id=icon.value if icon is not None else None,
        **data,
    )
