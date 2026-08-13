from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import urlencode

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.core.constants import DESK_PUBLICATION_FEE
from app.core.enums import Currency, DeskKind, Language
from app.core.exceptions import ServiceUnavailableError
from app.keyboards.callbacks import (
    DeskAction,
    DeskActionCallback,
    DeskCurrencyCallback,
    DeskCurrencyPurpose,
    DeskKindCallback,
    MenuAction,
    MenuCallback,
)
from app.keyboards.desk import (
    desk_amount_keyboard,
    desk_cancel_keyboard,
    desk_currency_keyboard,
    desk_invoice_keyboard,
    desk_kind_keyboard,
    description_preview_keyboard,
)
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.desk import DeskService
from app.states import DeskCreationStates
from app.ton.amounts import asset_amount_atomic
from app.utils import currency_label, format_amount, remember_menu, render_menu, render_stored_menu

router = Router(name="desk")


@router.callback_query(MenuCallback.filter(F.action == MenuAction.CREATE_DESK))
async def start_desk(
    callback: types.CallbackQuery, db_user: User, state: FSMContext
) -> None:
    await state.clear()
    if not db_user.username:
        await callback.answer(
            translate(db_user.language, TextKey.DESK_USERNAME_REQUIRED), show_alert=True
        )
        return
    if callback.message:
        await state.set_state(DeskCreationStates.waiting_for_kind)
        await remember_menu(state, callback.message)
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DESK_KIND_PROMPT),
            desk_kind_keyboard(db_user.language),
            screen="desk_create",
        )


@router.callback_query(DeskCreationStates.waiting_for_kind, DeskKindCallback.filter())
async def choose_kind(
    callback: types.CallbackQuery,
    callback_data: DeskKindCallback,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.update_data(kind=callback_data.kind.value)
    await state.set_state(DeskCreationStates.waiting_for_description)
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DESK_DESCRIPTION_PROMPT),
            desk_cancel_keyboard(db_user.language),
            screen="desk_create",
        )


@router.message(DeskCreationStates.waiting_for_description, F.text)
@router.message(DeskCreationStates.previewing_description, F.text)
async def receive_description(
    message: types.Message, db_user: User, state: FSMContext
) -> None:
    description = message.text or ""
    if not description.strip() or len(description) > 2_000:
        return
    await state.update_data(description=description)
    await state.set_state(DeskCreationStates.previewing_description)
    data = await state.get_data()
    await render_stored_menu(
        message,
        state,
        translate(
            db_user.language,
            TextKey.DESK_DESCRIPTION_PREVIEW,
            kind=data["kind"],
            description=escape(description),
        ),
        description_preview_keyboard(db_user.language),
        screen="desk_create",
    )


@router.callback_query(
    DeskCreationStates.previewing_description,
    DeskActionCallback.filter(F.action == DeskAction.CONFIRM_DESCRIPTION),
)
async def confirm_description(
    callback: types.CallbackQuery, db_user: User, state: FSMContext
) -> None:
    await state.set_state(DeskCreationStates.waiting_for_deal_currency)
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DESK_DEAL_CURRENCY_PROMPT),
            desk_currency_keyboard(db_user.language, DeskCurrencyPurpose.DEAL),
            screen="desk_create",
        )


@router.callback_query(
    DeskCreationStates.waiting_for_deal_currency,
    DeskCurrencyCallback.filter(F.purpose == DeskCurrencyPurpose.DEAL),
)
async def choose_deal_currency(
    callback: types.CallbackQuery,
    callback_data: DeskCurrencyCallback,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.update_data(deal_currency=callback_data.currency.value)
    await state.set_state(DeskCreationStates.waiting_for_amount)
    if callback.message:
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DESK_AMOUNT_PROMPT),
            desk_amount_keyboard(db_user.language),
            screen="desk_create",
        )


@router.message(DeskCreationStates.waiting_for_amount, F.text)
async def receive_amount(
    message: types.Message, db_user: User, state: FSMContext
) -> None:
    try:
        amount = Decimal((message.text or "").replace(",", "."))
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(translate(db_user.language, TextKey.DESK_INVALID_AMOUNT))
        return
    await state.update_data(price=str(amount))
    await _show_payment_currency(message, db_user, state)


@router.callback_query(
    DeskCreationStates.waiting_for_amount,
    DeskActionCallback.filter(F.action == DeskAction.OFFER_PRICE),
)
async def choose_offer_price(
    callback: types.CallbackQuery, db_user: User, state: FSMContext
) -> None:
    await state.update_data(price=None)
    if callback.message:
        await state.set_state(DeskCreationStates.waiting_for_payment_currency)
        await render_menu(
            callback.message,
            translate(db_user.language, TextKey.DESK_PAYMENT_CURRENCY_PROMPT),
            desk_currency_keyboard(db_user.language, DeskCurrencyPurpose.PAYMENT),
            screen="desk_create",
        )


async def _show_payment_currency(
    message: types.Message, db_user: User, state: FSMContext
) -> None:
    await state.set_state(DeskCreationStates.waiting_for_payment_currency)
    await render_stored_menu(
        message,
        state,
        translate(db_user.language, TextKey.DESK_PAYMENT_CURRENCY_PROMPT),
        desk_currency_keyboard(db_user.language, DeskCurrencyPurpose.PAYMENT),
        screen="desk_create",
    )


@router.callback_query(
    DeskCreationStates.waiting_for_payment_currency,
    DeskCurrencyCallback.filter(F.purpose == DeskCurrencyPurpose.PAYMENT),
)
async def choose_payment_currency(
    callback: types.CallbackQuery,
    callback_data: DeskCurrencyCallback,
    db_user: User,
    state: FSMContext,
    desk_service: DeskService,
) -> None:
    data = await state.get_data()
    price_value = data.get("price")
    try:
        listing = await desk_service.create_listing(
            db_user,
            kind=DeskKind(data["kind"]),
            description=str(data["description"]),
            deal_currency=Currency(data["deal_currency"]),
            price=Decimal(str(price_value)) if price_value is not None else None,
            payment_currency=callback_data.currency,
        )
    except ValueError:
        await callback.answer(
            translate(db_user.language, TextKey.DESK_USERNAME_REQUIRED), show_alert=True
        )
        return
    except ServiceUnavailableError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await state.clear()
    username = listing.owner_username
    url = None
    if listing.payment_currency is Currency.TON:
        query = urlencode({
            "amount": asset_amount_atomic(DESK_PUBLICATION_FEE, Currency.TON),
            "text": username,
        })
        url = f"https://app.tonkeeper.com/transfer/{listing.payment_sender or desk_service.guarant_address}?{query}"
    if callback.message:
        await render_menu(
            callback.message,
            translate(
                db_user.language,
                TextKey.DESK_PAYMENT_INVOICE,
                wallet=desk_service.guarant_address,
                fee=format_amount(DESK_PUBLICATION_FEE),
                currency=currency_label(listing.payment_currency),
                username=f"@{username}",
            ),
            desk_invoice_keyboard(db_user.language, url),
            screen="desk_create",
        )
