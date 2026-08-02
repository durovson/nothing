from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.core.enums import Language
from app.core.exceptions import InvalidWalletError
from app.keyboards import MenuCallback, wallet_actions
from app.keyboards.callbacks import MenuAction
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


def _wallet_keyboard(user: User):
    return wallet_actions(user.language)


def _wallet_prompt(user: User) -> str:
    if user.wallet_address:
        return translate(
            user.language,
            TextKey.WALLET_ACTIVE_PROMPT,
            wallet_short=_short_wallet(user.wallet_address),
            wallet_url=_wallet_url(user.wallet_address),
        )
    return translate(user.language, TextKey.WALLET_PROMPT)


@router.message(F.text.in_(WALLET_MENU_TEXTS))
async def open_wallet(message: types.Message, db_user: User, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(WalletStates.waiting_for_wallet)
    menu_message = await render_menu(
        message,
        _wallet_prompt(db_user),
        _wallet_keyboard(db_user),
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
            _wallet_keyboard(db_user),
            screen="wallet",
        )


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
        await render_stored_menu(
            message,
            state,
            translate(db_user.language, TextKey.WALLET_INVALID),
            _wallet_keyboard(db_user),
        )
        return
    await render_stored_menu(
        message,
        state,
        _wallet_prompt(updated_user),
        _wallet_keyboard(updated_user),
        screen="wallet",
    )
