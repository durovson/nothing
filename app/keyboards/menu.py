from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Language
from app.locales import TextKey, translate
from app.keyboards.callbacks import MenuAction, MenuCallback


def main_menu(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"💰 {translate(locale, TextKey.MENU_WALLET)}", callback_data=MenuCallback(action=MenuAction.WALLET).pack()),
            ],
            [InlineKeyboardButton(text=f"💼 {translate(locale, TextKey.MENU_CREATE_DEAL)}", callback_data=MenuCallback(action=MenuAction.CREATE_DEAL).pack())],
            [
                InlineKeyboardButton(text=f"📋 {translate(locale, TextKey.MENU_MY_DEALS)}", callback_data=MenuCallback(action=MenuAction.DEALS).pack()),
            ],
            [
                InlineKeyboardButton(text=f"👥 {translate(locale, TextKey.SETTINGS_REFERRALS)}", callback_data=MenuCallback(action=MenuAction.REFERRALS).pack()),
                InlineKeyboardButton(text=f"⚙️ {translate(locale, TextKey.MENU_SETTINGS)}", callback_data=MenuCallback(action=MenuAction.SETTINGS).pack()),
            ],
        ]
    )
