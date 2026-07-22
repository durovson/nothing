from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.enums import Language
from app.locales import TextKey, translate


def main_menu(locale: Language) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=translate(locale, TextKey.MENU_WALLET)),
                KeyboardButton(text=translate(locale, TextKey.MENU_CREATE_DEAL)),
            ],
            [
                KeyboardButton(text=translate(locale, TextKey.MENU_MY_DEALS)),
                KeyboardButton(text=translate(locale, TextKey.MENU_SETTINGS)),
            ],
        ],
        resize_keyboard=True,
    )

