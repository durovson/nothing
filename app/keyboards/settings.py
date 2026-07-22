from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Language
from app.keyboards.callbacks import (
    LanguageCallback,
    MenuAction,
    MenuCallback,
    SettingsAction,
    SettingsCallback,
)
from app.locales import TextKey, translate


def settings_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=translate(locale, TextKey.SETTINGS_REFERRALS), callback_data=SettingsCallback(action=SettingsAction.REFERRALS).pack())],
            [InlineKeyboardButton(text=translate(locale, TextKey.SETTINGS_LANGUAGE), callback_data=SettingsCallback(action=SettingsAction.LANGUAGE).pack())],
            [InlineKeyboardButton(text=translate(locale, TextKey.SETTINGS_SUPPORT), callback_data=SettingsCallback(action=SettingsAction.SUPPORT).pack())],
            [InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())],
        ]
    )


def language_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=translate(locale, TextKey.LANG_RU), callback_data=LanguageCallback(language=Language.RU).pack()),
                InlineKeyboardButton(text=translate(locale, TextKey.LANG_EN), callback_data=LanguageCallback(language=Language.EN).pack()),
            ],
            [InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=SettingsCallback(action=SettingsAction.BACK).pack())],
        ]
    )

