from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.core.enums import DealStatus, Language
from app.core.constants import DISPUTE_DESCRIPTION_MAX_LENGTH, DISPUTE_DESCRIPTION_MIN_LENGTH
from app.core.exceptions import (
    DealActionForbiddenError,
    DealConfirmationForbiddenError,
    DealNotFoundError,
)
from app.keyboards import DealCallback, MenuCallback, PageCallback, deal_actions, deals_list
from app.keyboards.callbacks import DealAction, MenuAction, PageAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.deals import DealService
from app.services.lifecycle import DealLifecycleService
from app.services.payouts import PayoutService
from app.states.forms import DisputeStates
from app.utils import currency_label, format_amount, render_menu

router = Router(name="deal-management")
MY_DEALS_TEXTS = {translate(language, TextKey.MENU_MY_DEALS) for language in Language}


@router.message(F.text.in_(MY_DEALS_TEXTS))
async def my_deals(
    message: types.Message,
    db_user: User,
    deal_service: DealService,
) -> None:
    items, has_next = await deal_service.list_user_deals(db_user.telegram_id)
    if not items:
        await message.answer(translate(db_user.language, TextKey.DEAL_LIST_EMPTY))
        return
    await message.answer(
        translate(db_user.language, TextKey.DEAL_LIST_CAPTION),
        reply_markup=deals_list(db_user.language, items, 0, has_next),
    )


@router.callback_query(MenuCallback.filter(F.action == MenuAction.DEALS))
async def my_deals_callback(
    callback: types.CallbackQuery, db_user: User, deal_service: DealService
) -> None:
    items, has_next = await deal_service.list_user_deals(db_user.telegram_id)
    if callback.message:
        caption = translate(db_user.language, TextKey.DEAL_LIST_CAPTION) if items else translate(db_user.language, TextKey.DEAL_LIST_EMPTY)
        await render_menu(callback.message, caption, deals_list(db_user.language, items, 0, has_next))
    await callback.answer()


@router.callback_query(PageCallback.filter(F.action == PageAction.CURRENT))
async def current_page(callback: types.CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(PageCallback.filter(F.action == PageAction.OPEN))
async def open_page(
    callback: types.CallbackQuery,
    callback_data: PageCallback,
    db_user: User,
    deal_service: DealService,
) -> None:
    page = max(0, callback_data.page)
    items, has_next = await deal_service.list_user_deals(db_user.telegram_id, page)
    if not items and page > 0:
        page -= 1
        items, has_next = await deal_service.list_user_deals(db_user.telegram_id, page)
    if callback.message:
        await render_menu(callback.message,
            translate(db_user.language, TextKey.DEAL_LIST_CAPTION),
            deals_list(db_user.language, items, page, has_next),
        )
    await callback.answer()


@router.callback_query(DealCallback.filter(F.action == DealAction.OPEN))
async def open_deal(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    deal_service: DealService,
) -> None:
    deal = await deal_service.get_deal(callback_data.deal_id)
    if not deal:
        if callback.message:
            await callback.message.answer(translate(db_user.language, TextKey.DEAL_NOT_FOUND))
        await callback.answer()
        return
    if db_user.telegram_id not in {deal.creator_id, deal.buyer_id}:
        if callback.message:
            await callback.message.answer(translate(db_user.language, TextKey.DEAL_FORBIDDEN))
        await callback.answer()
        return
    buyer = str(deal.buyer_id or "-")
    if deal.buyer_id == db_user.telegram_id and db_user.username:
        buyer = f"@{db_user.username}"
    if callback.message:
        await render_menu(callback.message,
            translate(
                db_user.language,
                TextKey.DEAL_CARD,
                deal_id=deal.public_id,
                status=deal.status.value,
                deal_type=deal.deal_type.value,
                description=deal.description,
                amount=format_amount(deal.amount),
                currency=currency_label(deal.currency),
                wallet_address=deal.wallet_address or "-",
                buyer=buyer,
                delivery_deadline=(
                    deal.delivery_deadline_at.isoformat() if deal.delivery_deadline_at else "-"
                ),
                inspection_deadline=(
                    deal.inspection_deadline_at.isoformat() if deal.inspection_deadline_at else "-"
                ),
            ),
            deal_actions(db_user.language, deal, db_user.telegram_id),
        )
    await callback.answer()


@router.callback_query(DealCallback.filter(F.action == DealAction.CANCEL))
async def cancel_deal(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    deal_service: DealService,
) -> None:
    deal = await deal_service.cancel_deal(callback_data.deal_id, db_user.telegram_id)
    key = TextKey.DEAL_CANCELLED if deal.status is DealStatus.CANCELLED else TextKey.DEAL_ALREADY_CANCELLED
    if callback.message:
        await callback.message.answer(translate(db_user.language, key))
    await callback.answer()


@router.callback_query(DealCallback.filter(F.action == DealAction.CONFIRM))
async def confirm_deal(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    payout_service: PayoutService,
) -> None:
    try:
        await payout_service.confirm_receipt(callback_data.deal_id, db_user.telegram_id)
    except (DealConfirmationForbiddenError, DealNotFoundError):
        key = TextKey.DEAL_FORBIDDEN
    else:
        key = TextKey.DEAL_RELEASE_ACCEPTED
    if callback.message:
        await callback.message.answer(translate(db_user.language, key))
    await callback.answer()


@router.callback_query(DealCallback.filter(F.action == DealAction.DELIVER))
async def mark_delivered(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    lifecycle_service: DealLifecycleService,
) -> None:
    try:
        await lifecycle_service.mark_delivered(callback_data.deal_id, db_user.telegram_id)
    except (DealActionForbiddenError, DealNotFoundError):
        key = TextKey.DEAL_FORBIDDEN
    else:
        key = TextKey.DEAL_DELIVERED
    if callback.message:
        await callback.message.answer(translate(db_user.language, key))
    await callback.answer()


@router.callback_query(DealCallback.filter(F.action == DealAction.DISPUTE))
async def begin_dispute(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.set_state(DisputeStates.waiting_for_description)
    await state.update_data(dispute_deal_id=callback_data.deal_id)
    if callback.message:
        await callback.message.answer(translate(db_user.language, TextKey.DEAL_DISPUTE_PROMPT))
    await callback.answer()


@router.message(DisputeStates.waiting_for_description)
async def save_dispute(
    message: types.Message,
    db_user: User,
    lifecycle_service: DealLifecycleService,
    state: FSMContext,
) -> None:
    description = (message.text or "").strip()
    if not DISPUTE_DESCRIPTION_MIN_LENGTH <= len(description) <= DISPUTE_DESCRIPTION_MAX_LENGTH:
        await message.answer(translate(db_user.language, TextKey.DEAL_DISPUTE_INVALID))
        return
    data = await state.get_data()
    deal_id = data.get("dispute_deal_id")
    if not isinstance(deal_id, int):
        await state.clear()
        await message.answer(translate(db_user.language, TextKey.DEAL_FORBIDDEN))
        return
    try:
        ticket = await lifecycle_service.open_dispute(
            deal_id,
            db_user.telegram_id,
            description,
        )
    except DealActionForbiddenError:
        key = TextKey.DEAL_FORBIDDEN
        kwargs: dict[str, object] = {}
    else:
        key = TextKey.DEAL_DISPUTE_CREATED
        kwargs = {"ticket_id": ticket.id}
    await state.clear()
    await message.answer(translate(db_user.language, key, **kwargs))
