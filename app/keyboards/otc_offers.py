from aiogram.types import InlineKeyboardMarkup

from app.core.custom_emoji import CustomEmoji
from app.core.enums import Language
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import MenuAction, MenuCallback
from app.locales import TextKey, translate


def otc_offer_input_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        premium_button(
            translate(locale, TextKey.MAIN_MENU_BUTTON),
            icon=CustomEmoji.HOME,
            callback_data=MenuCallback(action=MenuAction.BACK).pack(),
        )
    ]])


def otc_offer_buyer_profile_keyboard(
    locale: Language, buyer_id: int
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        premium_button(
            translate(locale, TextKey.OTC_OFFER_PROFILE_BUTTON),
            icon=CustomEmoji.PERSON,
            url=f"tg://user?id={buyer_id}",
        )
    ]])
