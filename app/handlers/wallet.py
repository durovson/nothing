from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.core.enums import Language
from app.core.exceptions import InvalidWalletError
from app.keyboards import WalletCallback, main_menu, wallet_actions
from app.keyboards.callbacks import WalletAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.wallets import WalletService
from app.states import WalletStates

router = Router(name="wallet")
WALLET_MENU_TEXTS = {translate(language, TextKey.MENU_WALLET) for language in Language}


@router.message(F.text.in_(WALLET_MENU_TEXTS))
async def open_wallet(message: types.Message, db_user: User) -> None:
    wallet = db_user.wallet_address or translate(db_user.language, TextKey.WALLET_EMPTY)
    await message.answer(
        translate(db_user.language, TextKey.WALLET_CAPTION, wallet=wallet),
        reply_markup=wallet_actions(db_user.language, bool(db_user.wallet_address)),
    )


@router.callback_query(WalletCallback.filter(F.action == WalletAction.EDIT))
async def edit_wallet(
    callback: types.CallbackQuery,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.set_state(WalletStates.waiting_for_wallet)
    if callback.message:
        await callback.message.answer(translate(db_user.language, TextKey.WALLET_PROMPT))
    await callback.answer()


@router.callback_query(WalletCallback.filter(F.action == WalletAction.DELETE))
async def delete_wallet(
    callback: types.CallbackQuery,
    db_user: User,
    wallet_service: WalletService,
) -> None:
    await wallet_service.delete(db_user.telegram_id)
    if callback.message:
        await callback.message.answer(translate(db_user.language, TextKey.WALLET_DELETED))
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
        await message.answer(translate(db_user.language, TextKey.WALLET_INVALID))
        return
    await state.clear()
    await message.answer(
        translate(
            updated_user.language,
            TextKey.WALLET_SAVED,
            wallet=updated_user.wallet_address,
        ),
        reply_markup=main_menu(updated_user.language),
    )

