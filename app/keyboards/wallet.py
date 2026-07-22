from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Language
from app.keyboards.callbacks import MenuAction, MenuCallback, WalletAction, WalletCallback
from app.locales import TextKey, translate


def wallet_actions(locale: Language, has_wallet: bool) -> InlineKeyboardMarkup:
    label = TextKey.WALLET_CHANGE if has_wallet else TextKey.WALLET_ADD
    rows = [[InlineKeyboardButton(text=translate(locale, label), callback_data=WalletCallback(action=WalletAction.EDIT).pack())]]
    if has_wallet:
        rows.append(
            [InlineKeyboardButton(text=translate(locale, TextKey.WALLET_DELETE), callback_data=WalletCallback(action=WalletAction.DELETE).pack())]
        )
    rows.append(
        [InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)

