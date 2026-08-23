from aiogram.types import InlineKeyboardMarkup

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import MenuAction, MenuCallback
from app.locales import TextKey, translate


def main_menu(locale: Language, support_username: str = "@not_jammm") -> InlineKeyboardMarkup:
    support = support_username.strip().lstrip("@") or "not_jammm"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                premium_button(
                    translate(locale, TextKey.MENU_CREATE_DEAL),
                    icon=CustomEmoji.MAIN_CREATE_DEAL,
                    callback_data=MenuCallback(action=MenuAction.CREATE_DEAL).pack(),
                ),
            ],
            [
                premium_button(
                    translate(locale, TextKey.MENU_CREATE_DESK),
                    icon=CustomEmoji.MAIN_CREATE_DESK,
                    callback_data=MenuCallback(action=MenuAction.CREATE_DESK).pack(),
                ),
            ],
            [
                premium_button(
                    translate(locale, TextKey.MENU_WALLET),
                    icon=CustomEmoji.MAIN_WALLET,
                    callback_data=MenuCallback(action=MenuAction.WALLET).pack(),
                ),
                premium_button(
                    translate(locale, TextKey.MENU_MY_DEALS),
                    icon=CustomEmoji.MAIN_MY_DEALS,
                    callback_data=MenuCallback(action=MenuAction.DEALS).pack(),
                ),
            ],
            [
                premium_button(
                    translate(locale, TextKey.SETTINGS_REFERRALS),
                    icon=CustomEmoji.MAIN_REFERRALS,
                    callback_data=MenuCallback(action=MenuAction.REFERRALS).pack(),
                ),
                premium_button(
                    translate(locale, TextKey.MENU_SETTINGS),
                    icon=CustomEmoji.MAIN_SETTINGS,
                    callback_data=MenuCallback(action=MenuAction.SETTINGS).pack(),
                ),
            ],
            [
                premium_button(
                    translate(locale, TextKey.SETTINGS_SUPPORT),
                    icon=CustomEmoji.SUPPORT,
                    url=f"https://t.me/{support}",
                ),
            ],
        ]
    )
