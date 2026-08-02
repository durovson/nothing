from aiogram.types import InlineKeyboardMarkup

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import (
    MenuAction,
    MenuCallback,
    WalletAction,
    WalletCallback,
)
from app.locales import TextKey, translate


def wallet_actions(
    locale: Language,
    has_wallet: bool,
    wallet_url: str | None = None,
    wallet_label: str | None = None,
) -> InlineKeyboardMarkup:
    label = TextKey.WALLET_CHANGE if has_wallet else TextKey.WALLET_ADD
    rows = [[premium_button(translate(locale, label), icon=CustomEmoji.WALLET, callback_data=WalletCallback(action=WalletAction.EDIT).pack())]]
    if has_wallet:
        if wallet_url:
            rows.insert(0, [premium_button(
                text=wallet_label or translate(locale, TextKey.WALLET_OPEN),
                icon=CustomEmoji.WALLET,
                url=wallet_url,
            )])
        rows.append(
            [premium_button(translate(locale, TextKey.WALLET_DELETE), icon=CustomEmoji.CANCEL, callback_data=WalletCallback(action=WalletAction.DELETE).pack())]
        )
    rows.append(
        [premium_button(translate(locale, TextKey.MAIN_MENU_BUTTON), icon=CustomEmoji.HOME, callback_data=MenuCallback(action=MenuAction.BACK).pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wallet_details(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [premium_button(translate(locale, TextKey.WALLET_DELETE), icon=CustomEmoji.CANCEL, callback_data=WalletCallback(action=WalletAction.DELETE).pack())],
        [premium_button(translate(locale, TextKey.BACK_BUTTON), icon=CustomEmoji.BACK, callback_data=WalletCallback(action=WalletAction.BACK).pack())],
        [premium_button(translate(locale, TextKey.MAIN_MENU_BUTTON), icon=CustomEmoji.HOME, callback_data=MenuCallback(action=MenuAction.BACK).pack())],
    ])
