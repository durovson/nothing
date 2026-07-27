from aiogram import F, Router, types

from app.config import Settings
from app.core.enums import Language
from app.keyboards import LanguageCallback, MenuCallback, ReferralCallback, SettingsCallback, language_keyboard, referral_keyboard, settings_keyboard
from app.keyboards.callbacks import MenuAction, ReferralAction, SettingsAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.referrals import ReferralService
from app.services.users import UserService
from app.utils import format_amount
from app.utils import render_menu
from app.core.exceptions import MissingLinkedWalletError, ReferralWithdrawalError
from app.core.constants import (
    REFERRAL_COMMISSION_SHARE,
    REFERRAL_MIN_WITHDRAW_TON,
    REFERRAL_MIN_WITHDRAW_USDT,
)

router = Router(name="settings")
SETTINGS_MENU_TEXTS = {translate(language, TextKey.MENU_SETTINGS) for language in Language}


@router.message(F.text.in_(SETTINGS_MENU_TEXTS))
async def settings_menu(message: types.Message, db_user: User) -> None:
    await message.answer(
        translate(db_user.language, TextKey.SETTINGS_CAPTION),
        reply_markup=settings_keyboard(db_user.language),
    )


@router.callback_query(MenuCallback.filter(F.action == MenuAction.SETTINGS))
async def settings_menu_callback(callback: types.CallbackQuery, db_user: User) -> None:
    if callback.message:
        await render_menu(callback.message, translate(db_user.language, TextKey.SETTINGS_CAPTION), settings_keyboard(db_user.language))
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.BACK))
async def settings_back(callback: types.CallbackQuery, db_user: User) -> None:
    if callback.message:
        await render_menu(callback.message,
            translate(db_user.language, TextKey.SETTINGS_CAPTION),
            settings_keyboard(db_user.language),
        )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.LANGUAGE))
async def choose_language(callback: types.CallbackQuery, db_user: User) -> None:
    if callback.message:
        await render_menu(callback.message,
            translate(db_user.language, TextKey.SETTINGS_CAPTION),
            language_keyboard(db_user.language),
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
        await render_menu(callback.message,
            translate(user.language, TextKey.LANGUAGE_SAVED, language=user.language.value),
            settings_keyboard(user.language),
        )
    await callback.answer()


@router.callback_query(SettingsCallback.filter(F.action == SettingsAction.SUPPORT))
async def support_info(
    callback: types.CallbackQuery,
    db_user: User,
    settings: Settings,
) -> None:
    if callback.message:
        await render_menu(callback.message,
            translate(
                db_user.language,
                TextKey.SUPPORT_TEXT,
                support_username=settings.SUPPORT_USERNAME,
            ), settings_keyboard(db_user.language)
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
        await render_menu(callback.message,
            translate(
                db_user.language,
                TextKey.REFERRAL_CAPTION,
                link=link,
                count=stats.count,
                earned_ton=format_amount(stats.earned_ton),
                earned_usdt=format_amount(stats.earned_usdt),
                rate=format_amount(REFERRAL_COMMISSION_SHARE * 100),
            ),
            referral_keyboard(
                db_user.language,
                stats.balance_ton >= REFERRAL_MIN_WITHDRAW_TON,
                stats.balance_usdt >= REFERRAL_MIN_WITHDRAW_USDT,
            ),
        )
    await callback.answer()


@router.callback_query(ReferralCallback.filter(F.action == ReferralAction.WITHDRAW))
async def withdraw_referral_reward(
    callback: types.CallbackQuery,
    callback_data: ReferralCallback,
    db_user: User,
    referral_service: ReferralService,
) -> None:
    try:
        withdrawal = await referral_service.request_withdrawal(db_user, callback_data.currency)
    except MissingLinkedWalletError:
        text = (
            "Сначала привяжите личный TON-кошелёк в разделе «Мой кошелёк»."
            if db_user.language is Language.RU else
            "Link your personal TON wallet in My wallet first."
        )
    except ReferralWithdrawalError as exc:
        text = f"Вывод сейчас недоступен: {exc}" if db_user.language is Language.RU else f"Withdrawal is unavailable: {exc}"
    except Exception:
        text = (
            "Не удалось подготовить вывод. Баланс не потерян; попробуйте позже."
            if db_user.language is Language.RU else
            "Could not prepare the withdrawal. Your balance is safe; try again later."
        )
    else:
        if db_user.language is Language.RU:
            text = (f"Вывод {format_amount(withdrawal.amount)} {withdrawal.currency.value} отправлен в сеть TON.\n\n"
                    "Адрес взят из профиля. При использовании биржевого или чужого адреса сервис не отвечает за зачисление средств.")
        else:
            text = (f"Withdrawal of {format_amount(withdrawal.amount)} {withdrawal.currency.value} was submitted to TON.\n\n"
                    "The linked profile address was used. The service is not responsible for exchange or third-party address crediting.")
    stats = await referral_service.get_stats(db_user.telegram_id)
    if callback.message:
        await render_menu(callback.message, text, referral_keyboard(
            db_user.language,
            stats.balance_ton >= REFERRAL_MIN_WITHDRAW_TON,
            stats.balance_usdt >= REFERRAL_MIN_WITHDRAW_USDT,
        ))
    await callback.answer()
