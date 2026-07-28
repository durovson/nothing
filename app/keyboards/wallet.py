from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Language
from app.keyboards.callbacks import MenuAction, MenuCallback, WalletAction, WalletCallback
from app.locales import TextKey, translate


def wallet_actions(
    locale: Language,
    has_wallet: bool,
    wallet_url: str | None = None,
    wallet_label: str | None = None,
) -> InlineKeyboardMarkup:
    label = TextKey.WALLET_CHANGE if has_wallet else TextKey.WALLET_ADD
    rows = [[InlineKeyboardButton(text=translate(locale, label), callback_data=WalletCallback(action=WalletAction.EDIT).pack())]]
    if has_wallet:
        if wallet_url:
            rows.insert(0, [InlineKeyboardButton(
                text=wallet_label or translate(locale, TextKey.WALLET_OPEN),
                callback_data=WalletCallback(action=WalletAction.OPEN).pack(),
            )])
        rows.append(
            [InlineKeyboardButton(text=translate(locale, TextKey.WALLET_DELETE), callback_data=WalletCallback(action=WalletAction.DELETE).pack())]
        )
    rows.append(
        [InlineKeyboardButton(text=translate(locale, TextKey.MAIN_MENU_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wallet_details(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=translate(locale, TextKey.WALLET_DELETE), callback_data=WalletCallback(action=WalletAction.DELETE).pack())],
        [InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=WalletCallback(action=WalletAction.BACK).pack())],
        [InlineKeyboardButton(text=translate(locale, TextKey.MAIN_MENU_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())],
    ])
