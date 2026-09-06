from aiogram import F, Router, types

from app.config import Settings
from app.core.constants import (
    PRIVACY_POLICY_URL,
    SERVICE_DESCRIPTION_URL,
    TERMS_OF_USE_URL,
)
from app.core.custom_emoji import CustomEmoji
from app.keyboards import MenuCallback, SettingsCallback
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import FaqPageCallback, MenuAction, SettingsAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.utils import render_menu

router = Router(name="information")


def _settings_keyboard(locale):
    from aiogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(inline_keyboard=[[
        premium_button(
            text=translate(locale, TextKey.BACK_BUTTON),
            icon=CustomEmoji.BACK,
            callback_data=SettingsCallback(action=SettingsAction.BACK).pack(),
        )
    ]])


def _faq_keyboard(locale, page: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    navigation: list[InlineKeyboardButton] = []
    if page > 0:
        navigation.append(
            premium_button(
                text="\u200b",
                icon=CustomEmoji.PREVIOUS,
                callback_data=FaqPageCallback(page=page - 1).pack(),
            )
        )
    navigation.append(
        InlineKeyboardButton(text=f"{page + 1}/2", callback_data=FaqPageCallback(page=page).pack())
    )
    if page < 1:
        navigation.append(
            premium_button(
                text="\u200b",
                icon=CustomEmoji.NEXT,
                callback_data=FaqPageCallback(page=page + 1).pack(),
            )
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[navigation, *_settings_keyboard(locale).inline_keyboard]
    )


async def _render_faq(callback: types.CallbackQuery, db_user: User, settings: Settings, page: int) -> None:
    if not callback.message:
        return
    page = 1 if page == 1 else 0
    text_key = TextKey.FAQ_CAPTION_PAGE_2 if page else TextKey.FAQ_CAPTION
    await render_menu(
        callback.message,
        translate(db_user.language, text_key, support_username=settings.SUPPORT_USERNAME),
        _faq_keyboard(db_user.language, page),
        screen="faq",
    )


@router.callback_query(MenuCallback.filter(F.action == MenuAction.FAQ))
async def show_faq(callback: types.CallbackQuery, db_user: User, settings: Settings) -> None:
    await _render_faq(callback, db_user, settings, page=0)


@router.callback_query(FaqPageCallback.filter())
async def show_faq_page(
    callback: types.CallbackQuery,
    callback_data: FaqPageCallback,
    db_user: User,
    settings: Settings,
) -> None:
    await _render_faq(callback, db_user, settings, callback_data.page)


@router.callback_query(MenuCallback.filter(F.action == MenuAction.DOCUMENTS))
async def show_documents(callback: types.CallbackQuery, db_user: User, settings: Settings) -> None:
    from aiogram.types import InlineKeyboardMarkup

    rows = [
        [
            premium_button(
                translate(db_user.language, TextKey.PRIVACY_BUTTON),
                icon=CustomEmoji.DOCUMENTS,
                url=PRIVACY_POLICY_URL,
            )
        ],
        [
            premium_button(
                translate(db_user.language, TextKey.TERMS_BUTTON),
                icon=CustomEmoji.DOCUMENTS,
                url=TERMS_OF_USE_URL,
            )
        ],
        [
            premium_button(
                translate(db_user.language, TextKey.SERVICE_DESCRIPTION_BUTTON),
                icon=CustomEmoji.DOCUMENTS,
                url=SERVICE_DESCRIPTION_URL,
            )
        ],
    ]
    rows.extend(_settings_keyboard(db_user.language).inline_keyboard)
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DOCUMENTS_CAPTION),
            InlineKeyboardMarkup(inline_keyboard=rows),
            screen="documents",
        )
