from aiogram import F, Router, types

from app.config import Settings
from app.core.custom_emoji import CustomEmoji
from app.keyboards import MenuCallback, SettingsCallback
from app.keyboards.buttons import premium_button
from app.keyboards.callbacks import MenuAction, SettingsAction
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


@router.callback_query(MenuCallback.filter(F.action == MenuAction.FAQ))
async def show_faq(callback: types.CallbackQuery, db_user: User, settings: Settings) -> None:
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.FAQ_CAPTION, support_username=settings.SUPPORT_USERNAME),
            _settings_keyboard(db_user.language),
            screen="faq",
        )


@router.callback_query(MenuCallback.filter(F.action == MenuAction.DOCUMENTS))
async def show_documents(callback: types.CallbackQuery, db_user: User, settings: Settings) -> None:
    from aiogram.types import InlineKeyboardMarkup

    base_url = (settings.APP_BASE_URL or settings.RENDER_EXTERNAL_URL).rstrip("/")
    rows = []
    if base_url:
        rows.extend([
            [premium_button(translate(db_user.language, TextKey.PRIVACY_BUTTON), icon=CustomEmoji.DOCUMENTS, url=f"{base_url}/documents/privacy")],
            [premium_button(translate(db_user.language, TextKey.TERMS_BUTTON), icon=CustomEmoji.DOCUMENTS, url=f"{base_url}/documents/terms")],
            [premium_button(translate(db_user.language, TextKey.SERVICE_DESCRIPTION_BUTTON), icon=CustomEmoji.DOCUMENTS, url=f"{base_url}/documents/service")],
        ])
    rows.extend(_settings_keyboard(db_user.language).inline_keyboard)
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DOCUMENTS_CAPTION),
            InlineKeyboardMarkup(inline_keyboard=rows),
            screen="documents",
        )
