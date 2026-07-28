from aiogram import F, Router, types

from app.config import Settings
from app.keyboards import MenuCallback
from app.keyboards.callbacks import MenuAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.utils import render_menu

router = Router(name="information")


def _home_keyboard(locale):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from app.keyboards import MenuCallback

    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=translate(locale, TextKey.MAIN_MENU_BUTTON),
            callback_data=MenuCallback(action=MenuAction.BACK).pack(),
        )
    ]])


@router.callback_query(MenuCallback.filter(F.action == MenuAction.FAQ))
async def show_faq(callback: types.CallbackQuery, db_user: User, settings: Settings) -> None:
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.FAQ_CAPTION, support_username=settings.SUPPORT_USERNAME),
            _home_keyboard(db_user.language),
            screen="faq",
        )
    await callback.answer()


@router.callback_query(MenuCallback.filter(F.action == MenuAction.DOCUMENTS))
async def show_documents(callback: types.CallbackQuery, db_user: User, settings: Settings) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    base_url = (settings.APP_BASE_URL or settings.RENDER_EXTERNAL_URL).rstrip("/")
    rows = []
    if base_url:
        rows.extend([
            [InlineKeyboardButton(text=translate(db_user.language, TextKey.PRIVACY_BUTTON), url=f"{base_url}/documents/privacy")],
            [InlineKeyboardButton(text=translate(db_user.language, TextKey.TERMS_BUTTON), url=f"{base_url}/documents/terms")],
        ])
    rows.extend(_home_keyboard(db_user.language).inline_keyboard)
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DOCUMENTS_CAPTION),
            InlineKeyboardMarkup(inline_keyboard=rows),
            screen="documents",
        )
    await callback.answer()
