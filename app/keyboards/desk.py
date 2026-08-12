from aiogram.types import InlineKeyboardMarkup

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Currency, DeskKind, Language
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import (
    DeskAction,
    DeskActionCallback,
    DeskCurrencyCallback,
    DeskCurrencyPurpose,
    DeskKindCallback,
    MenuAction,
    MenuCallback,
)
from app.locales import TextKey, translate


def desk_kind_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            premium_button("WTS", icon=CustomEmoji.OFFER, callback_data=DeskKindCallback(kind=DeskKind.WTS).pack()),
            premium_button("WTB", icon=CustomEmoji.OFFER, callback_data=DeskKindCallback(kind=DeskKind.WTB).pack()),
        ],
        [_cancel(locale)],
    ])


def description_preview_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [premium_button(
            "Подтвердить" if locale is Language.RU else "Confirm",
            icon=CustomEmoji.CONFIRM,
            callback_data=DeskActionCallback(action=DeskAction.CONFIRM_DESCRIPTION).pack(),
        )],
        [premium_button(
            "Изменить описание" if locale is Language.RU else "Edit description",
            icon=CustomEmoji.BRUSH,
            callback_data=DeskActionCallback(action=DeskAction.EDIT_DESCRIPTION).pack(),
        )],
        [_cancel(locale)],
    ])


def desk_currency_keyboard(
    locale: Language, purpose: DeskCurrencyPurpose
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            premium_button("GRAM", icon=CustomEmoji.TON, callback_data=DeskCurrencyCallback(purpose=purpose, currency=Currency.TON).pack()),
            premium_button("USDT", icon=CustomEmoji.TON, callback_data=DeskCurrencyCallback(purpose=purpose, currency=Currency.USDT).pack()),
        ],
        [_cancel(locale)],
    ])


def desk_amount_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [premium_button(
            "Оффер" if locale is Language.RU else "Offer",
            icon=CustomEmoji.OFFER,
            callback_data=DeskActionCallback(action=DeskAction.OFFER_PRICE).pack(),
        )],
        [_cancel(locale)],
    ])


def desk_invoice_keyboard(locale: Language, payment_url: str | None) -> InlineKeyboardMarkup:
    rows = []
    if payment_url:
        rows.append([premium_button(
            "Оплатить в Tonkeeper" if locale is Language.RU else "Pay in Tonkeeper",
            icon=CustomEmoji.TON,
            url=payment_url,
        )])
    rows.append([_cancel(locale)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel(locale: Language):
    return premium_button(
        translate(locale, TextKey.MAIN_MENU_BUTTON),
        icon=CustomEmoji.HOME,
        callback_data=MenuCallback(action=MenuAction.BACK).pack(),
    )
