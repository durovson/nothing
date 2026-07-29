from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.core.enums import Language
from app.core.exceptions import InvalidWalletError
from app.keyboards import WalletCallback, home_keyboard, wallet_actions, wallet_details
from app.keyboards.callbacks import MenuAction, WalletAction
from app.keyboards import MenuCallback
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.wallets import WalletService
from app.states import WalletStates
from app.utils import remember_menu, render_menu, render_stored_menu

router = Router(name="wallet")
WALLET_MENU_TEXTS = {translate(language, TextKey.MENU_WALLET) for language in Language}


def _short_wallet(address: str) -> str:
    return f"{address[:10]}...{address[-10:]}"


def _wallet_url(address: str) -> str:
    return f"https://tonviewer.com/{address}"


def _list_keyboard(user: User):
    return home_keyboard(user.language)


def _wallet_prompt(user: User) -> str:
    if user.wallet_address:
        return translate(
            user.language,
            TextKey.WALLET_ACTIVE_PROMPT,
            wallet=user.wallet_address,
        )
    return translate(user.language, TextKey.WALLET_PROMPT)


@router.message(F.text.in_(WALLET_MENU_TEXTS))
async def open_wallet(message: types.Message, db_user: User, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(WalletStates.waiting_for_wallet)
    menu_message = await render_menu(
        message,
        _wallet_prompt(db_user),
        _list_keyboard(db_user),
        screen="wallet",
    )
    await remember_menu(state, menu_message)


@router.callback_query(MenuCallback.filter(F.action == MenuAction.WALLET))
async def open_wallet_callback(
    callback: types.CallbackQuery, db_user: User, state: FSMContext
) -> None:
    await state.clear()
    await state.set_state(WalletStates.waiting_for_wallet)
    if callback.message:
        await remember_menu(state, callback.message)
        await render_menu(
            callback.message,
            _wallet_prompt(db_user),
            _list_keyboard(db_user),
            screen="wallet",
        )
    await callback.answer()


@router.callback_query(WalletCallback.filter(F.action == WalletAction.OPEN))
async def open_wallet_details(callback: types.CallbackQuery, db_user: User) -> None:
    address = db_user.wallet_address
    if not address:
        await callback.answer(translate(db_user.language, TextKey.WALLET_EMPTY), show_alert=True)
        return
    if callback.message:
        await render_menu(
            callback.message,
            translate(
                db_user.language,
                TextKey.WALLET_CAPTION,
                wallet=address,
                wallet_short=_short_wallet(address),
                wallet_url=_wallet_url(address),
            ),
            wallet_details(db_user.language),
            screen="wallet",
        )
    await callback.answer()


@router.callback_query(WalletCallback.filter(F.action == WalletAction.BACK))
async def wallet_back(callback: types.CallbackQuery, db_user: User) -> None:
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.WALLET_EMPTY),
            _list_keyboard(db_user),
            screen="wallet",
        )
    await callback.answer()


@router.callback_query(WalletCallback.filter(F.action == WalletAction.EDIT))
async def edit_wallet(
    callback: types.CallbackQuery,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.set_state(WalletStates.waiting_for_wallet)
    if callback.message:
        await remember_menu(state, callback.message)
        await render_menu(callback.message, translate(db_user.language, TextKey.WALLET_PROMPT), wallet_actions(db_user.language, bool(db_user.wallet_address)))
    await callback.answer()


@router.callback_query(WalletCallback.filter(F.action == WalletAction.DELETE))
async def delete_wallet(
    callback: types.CallbackQuery,
    db_user: User,
    wallet_service: WalletService,
) -> None:
    await wallet_service.delete(db_user.telegram_id)
    if callback.message:
        await render_menu(callback.message, translate(db_user.language, TextKey.WALLET_DELETED), wallet_actions(db_user.language, False))
    await callback.answer()


@router.message(WalletStates.waiting_for_wallet)
async def save_wallet(
    message: types.Message,
    db_user: User,
    wallet_service: WalletService,
    state: FSMContext,
) -> None:
    raw_address = (message.text or "").strip()
    try:
        updated_user = await wallet_service.save(db_user.telegram_id, raw_address)
    except InvalidWalletError:
        await render_stored_menu(message, state, translate(db_user.language, TextKey.WALLET_INVALID), wallet_actions(db_user.language, bool(db_user.wallet_address)))
        return
    await render_stored_menu(
        message,
        state,
        _wallet_prompt(updated_user),
        home_keyboard(updated_user.language),
        screen="wallet",
    )
