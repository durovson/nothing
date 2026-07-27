from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Language
from app.keyboards.callbacks import (
    LanguageCallback,
    MenuAction,
    MenuCallback,
    SettingsAction,
    SettingsCallback,
    ReferralAction,
    ReferralCallback,
)
from app.core.enums import Currency
from app.locales import TextKey, translate


def settings_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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


def referral_keyboard(locale: Language, ton_available: bool, usdt_available: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if ton_available:
        label = "💎 Вывести GRAM" if locale is Language.RU else "💎 Withdraw GRAM"
        rows.append([InlineKeyboardButton(text=label, callback_data=ReferralCallback(action=ReferralAction.WITHDRAW, currency=Currency.TON).pack())])
    if usdt_available:
        label = "💵 Вывести USDT" if locale is Language.RU else "💵 Withdraw USDT"
        rows.append([InlineKeyboardButton(text=label, callback_data=ReferralCallback(action=ReferralAction.WITHDRAW, currency=Currency.USDT).pack())])
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
