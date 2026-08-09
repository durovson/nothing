from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Currency, Language
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import (
    LanguageCallback,
    MenuAction,
    MenuCallback,
    ReferralAction,
    ReferralCallback,
    SettingsAction,
    SettingsCallback,
)
from app.locales import TextKey, translate


def settings_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [premium_button(translate(locale, TextKey.SETTINGS_LANGUAGE), icon=CustomEmoji.LANGUAGE, callback_data=SettingsCallback(action=SettingsAction.LANGUAGE).pack())],
            [
                premium_button(translate(locale, TextKey.MENU_DOCUMENTS), icon=CustomEmoji.DOCUMENTS, callback_data=MenuCallback(action=MenuAction.DOCUMENTS).pack()),
                premium_button(translate(locale, TextKey.MENU_FAQ), icon=CustomEmoji.FAQ, callback_data=MenuCallback(action=MenuAction.FAQ).pack()),
            ],
            [premium_button(translate(locale, TextKey.MAIN_MENU_BUTTON), icon=CustomEmoji.HOME, callback_data=MenuCallback(action=MenuAction.BACK).pack())],
        ]
    )


def language_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                premium_button(translate(locale, TextKey.LANG_RU), icon=CustomEmoji.RUSSIAN, callback_data=LanguageCallback(language=Language.RU).pack()),
                premium_button(translate(locale, TextKey.LANG_EN), icon=CustomEmoji.ENGLISH, callback_data=LanguageCallback(language=Language.EN).pack()),
            ],
            [premium_button(translate(locale, TextKey.BACK_BUTTON), icon=CustomEmoji.BACK, callback_data=SettingsCallback(action=SettingsAction.BACK).pack())],
        ]
    )


def home_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        premium_button(
            text=translate(locale, TextKey.MAIN_MENU_BUTTON),
            icon=CustomEmoji.HOME,
            callback_data=MenuCallback(action=MenuAction.BACK).pack(),
        )
    ]])


def referral_keyboard(locale: Language, ton_available: bool, usdt_available: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if ton_available:
        label = "💎 Вывести GRAM" if locale is Language.RU else "💎 Withdraw GRAM"
        rows.append([premium_button(text=label.removeprefix("💎 "), icon=CustomEmoji.TON, callback_data=ReferralCallback(action=ReferralAction.WITHDRAW, currency=Currency.TON).pack())])
    if usdt_available:
        label = "💵 Вывести USDT" if locale is Language.RU else "💵 Withdraw USDT"
        rows.append([premium_button(text=label.removeprefix("💵 "), icon=CustomEmoji.TON, callback_data=ReferralCallback(action=ReferralAction.WITHDRAW, currency=Currency.USDT).pack())])
    rows.append([premium_button(translate(locale, TextKey.MAIN_MENU_BUTTON), icon=CustomEmoji.HOME, callback_data=MenuCallback(action=MenuAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
