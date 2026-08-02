from aiogram.types import InlineKeyboardMarkup

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import MenuAction, MenuCallback
from app.locales import TextKey, translate


def wallet_actions(locale: Language) -> InlineKeyboardMarkup:
    """Wallet input screen only needs navigation back to the main menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [premium_button(translate(locale, TextKey.MAIN_MENU_BUTTON), icon=CustomEmoji.HOME, callback_data=MenuCallback(action=MenuAction.BACK).pack())],
    ])
