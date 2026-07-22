from aiogram import F, Router, types

from app.config import Settings
from app.core.enums import Language
from app.keyboards import LanguageCallback, SettingsCallback, language_keyboard, settings_keyboard
from app.keyboards.callbacks import SettingsAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.referrals import ReferralService
from app.services.users import UserService

router = Router(name="settings")
SETTINGS_MENU_TEXTS = {translate(language, TextKey.MENU_SETTINGS) for language in Language}


@router.message(F.text.in_(SETTINGS_MENU_TEXTS))
async def settings_menu(message: types.Message, db_user: User) -> None:
    await message.answer(
        translate(db_user.language, TextKey.SETTINGS_CAPTION),
        reply_markup=settings_keyboard(db_user.language),
    )


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.BACK))
async def settings_back(callback: types.CallbackQuery, db_user: User) -> None:
    if callback.message:
        await callback.message.answer(
            translate(db_user.language, TextKey.SETTINGS_CAPTION),
            reply_markup=settings_keyboard(db_user.language),
        )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.LANGUAGE))
async def choose_language(callback: types.CallbackQuery, db_user: User) -> None:
    if callback.message:
        await callback.message.answer(
            translate(db_user.language, TextKey.SETTINGS_CAPTION),
            reply_markup=language_keyboard(db_user.language),
        )
    await callback.answer()


@router.callback_query(LanguageCallback.filter())
async def save_language(
    callback: types.CallbackQuery,
    callback_data: LanguageCallback,
    db_user: User,
    user_service: UserService,
) -> None:
    user = await user_service.change_language(db_user.telegram_id, callback_data.language)
    if callback.message:
        await callback.message.answer(
            translate(user.language, TextKey.LANGUAGE_SAVED, language=user.language.value),
            reply_markup=settings_keyboard(user.language),
        )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.SUPPORT))
async def support_info(
    callback: types.CallbackQuery,
    db_user: User,
    settings: Settings,
) -> None:
    if callback.message:
        await callback.message.answer(
            translate(
                db_user.language,
                TextKey.SUPPORT_TEXT,
                support_username=settings.SUPPORT_USERNAME,
            )
        )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.REFERRALS))
async def referral_info(
    callback: types.CallbackQuery,
    db_user: User,
    referral_service: ReferralService,
    settings: Settings,
) -> None:
    stats = await referral_service.get_stats(db_user.telegram_id)
    bot_username = settings.TELEGRAM_BOT_USERNAME or (await callback.bot.get_me()).username or "YourBot"
    link = f"https://t.me/{bot_username}?start=ref_{db_user.telegram_id}"
    if callback.message:
        await callback.message.answer(
            translate(
                db_user.language,
                TextKey.REFERRAL_CAPTION,
                link=link,
                count=stats.count,
                earned_ton=stats.earned_ton,
            )
        )
    await callback.answer()

