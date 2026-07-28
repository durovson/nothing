from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Language
from app.locales import TextKey, translate
from app.keyboards.callbacks import MenuAction, MenuCallback


def main_menu(locale: Language, support_username: str = "@not_jammm") -> InlineKeyboardMarkup:
    support = support_username.strip().lstrip("@") or "not_jammm"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"💵 {translate(locale, TextKey.MENU_WALLET)}", callback_data=MenuCallback(action=MenuAction.WALLET).pack()),
            ],
            [InlineKeyboardButton(text=f"💼 {translate(locale, TextKey.MENU_CREATE_DEAL)}", callback_data=MenuCallback(action=MenuAction.CREATE_DEAL).pack())],
            [
                InlineKeyboardButton(text=f"📋 {translate(locale, TextKey.MENU_MY_DEALS)}", callback_data=MenuCallback(action=MenuAction.DEALS).pack()),
            ],
            [
                InlineKeyboardButton(text=f"❓ {translate(locale, TextKey.MENU_FAQ)}", callback_data=MenuCallback(action=MenuAction.FAQ).pack()),
                InlineKeyboardButton(text=f"📄 {translate(locale, TextKey.MENU_DOCUMENTS)}", callback_data=MenuCallback(action=MenuAction.DOCUMENTS).pack()),
            ],
            [
                InlineKeyboardButton(text=f"👥 {translate(locale, TextKey.SETTINGS_REFERRALS)}", callback_data=MenuCallback(action=MenuAction.REFERRALS).pack()),
                InlineKeyboardButton(text=f"⚙️ {translate(locale, TextKey.MENU_SETTINGS)}", callback_data=MenuCallback(action=MenuAction.SETTINGS).pack()),
            ],
            [InlineKeyboardButton(text=f"💬 {translate(locale, TextKey.SETTINGS_SUPPORT)}", url=f"https://t.me/{support}")],
        ]
    )
