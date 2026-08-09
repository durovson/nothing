from html import escape

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from app.config import Settings
from app.core.enums import DealStatus, DealType, Language
from app.core.constants import DISPUTE_DESCRIPTION_MAX_LENGTH, DISPUTE_DESCRIPTION_MIN_LENGTH
from app.core.exceptions import (
    DealActionForbiddenError,
    DealConfirmationForbiddenError,
    DealNotFoundError,
    ServiceUnavailableError,
)
from app.api.telegram_notifier import TelegramNotificationGateway
from app.keyboards import DealCallback, MenuCallback, PageCallback, deal_actions, deals_list, home_keyboard
from app.keyboards.callbacks import DealAction, MenuAction, PageAction
from app.locales import TextKey, translate
from app.models.entities import Deal, User
from app.services.deals import DealService
from app.services.lifecycle import DealLifecycleService
from app.services.payouts import PayoutService
from app.states.forms import DisputeStates
from app.ton.links import tonviewer_transaction_url
from app.utils import (
    channel_member_status_label,
    currency_label,
    deal_status_html,
    deal_type_label,
    format_amount,
    render_menu,
)

router = Router(name="deal-management")
MY_DEALS_TEXTS = {translate(language, TextKey.MENU_MY_DEALS) for language in Language}


def _participant_html(user: User | None, telegram_id: int | None) -> str:
    """Render a participant with a proportional username and monospace numeric ID."""
    if telegram_id is None:
        return "—"
    identifier = f"<code>{telegram_id}</code>"
    if user and user.username:
        return f"@{escape(user.username)} ({identifier})"
    return identifier


async def render_deal_card(
    message: types.Message,
    deal: Deal,
    db_user: User,
    deal_service: DealService,
    settings: Settings,
) -> None:
    """Render the canonical deal screen for callbacks and deep links."""
    buyer_user, seller_user = await deal_service.participants(deal)
    buyer = _participant_html(buyer_user, deal.buyer_id)
    seller = _participant_html(seller_user, deal.creator_id)
    payment_amount = deal_service.buyer_payment_amount(deal)
    completed = deal.status is DealStatus.COMPLETED
    if db_user.language is Language.RU:
        seller_amount_verb = "получил" if completed else "получит"
        buyer_amount_verb = "оплатил" if completed else "оплатит"
    else:
        seller_amount_verb = "received" if completed else "will receive"
        buyer_amount_verb = "paid" if completed else "will pay"
    channel_details = ""
    if deal.deal_type is DealType.CHANNEL:
        role = channel_member_status_label(deal.channel_last_member_status, db_user.language)
        if db_user.language is Language.RU:
            channel_details = f"\nКанал: {deal.channel_title or '-'}\nРоль покупателя: {role}"
        else:
            channel_details = f"\nChannel: {deal.channel_title or '-'}\nBuyer role: {role}"
    status_marker = "__DEAL_STATUS_HTML__"
    buyer_marker = "__DEAL_BUYER_HTML__"
    seller_marker = "__DEAL_SELLER_HTML__"
    caption = translate(
        db_user.language,
        TextKey.DEAL_CARD,
        deal_id=deal.public_id,
        status=status_marker,
        deal_type=deal_type_label(deal.deal_type, db_user.language),
        description=deal.description,
        amount=format_amount(deal.amount),
        payment_amount=format_amount(payment_amount),
        seller_amount_verb=seller_amount_verb,
        buyer_amount_verb=buyer_amount_verb,
        currency=currency_label(deal.currency),
        wallet_address=deal.wallet_address or "-",
        buyer=buyer_marker,
        seller=seller_marker,
        channel_details=channel_details,
    )
    payout_url = None
    if completed and deal.payout_tx_hash:
        payout_url = tonviewer_transaction_url(deal.payout_tx_hash, settings.TON_NETWORK)
    caption = (
        caption.replace(
            status_marker,
            deal_status_html(
                deal.status,
                db_user.language,
                transaction_url=payout_url,
            ),
        )
        .replace(buyer_marker, buyer)
        .replace(seller_marker, seller)
    )
    await render_menu(
        message,
        caption,
        deal_actions(db_user.language, deal, db_user.telegram_id),
        screen="deal",
    )


@router.message(F.text.in_(MY_DEALS_TEXTS))
async def my_deals(
    message: types.Message,
    db_user: User,
    deal_service: DealService,
) -> None:
    items, total_pages = await deal_service.list_user_deals(db_user.telegram_id)
    if not items:
        total_pages = 1
    await render_menu(message, translate(db_user.language, TextKey.DEAL_LIST_CAPTION if items else TextKey.DEAL_LIST_EMPTY), deals_list(db_user.language, items, 0, total_pages), screen="deals")


@router.callback_query(MenuCallback.filter(F.action == MenuAction.DEALS))
async def my_deals_callback(
    callback: types.CallbackQuery, db_user: User, deal_service: DealService
) -> None:
    items, total_pages = await deal_service.list_user_deals(db_user.telegram_id)
    if callback.message:
        caption = translate(db_user.language, TextKey.DEAL_LIST_CAPTION) if items else translate(db_user.language, TextKey.DEAL_LIST_EMPTY)
        await render_menu(callback.message, caption, deals_list(db_user.language, items, 0, total_pages), screen="deals")


@router.callback_query(PageCallback.filter(F.action == PageAction.CURRENT))
async def current_page(callback: types.CallbackQuery) -> None:
    return None


@router.callback_query(PageCallback.filter(F.action == PageAction.OPEN))
async def open_page(
    callback: types.CallbackQuery,
    callback_data: PageCallback,
    db_user: User,
    deal_service: DealService,
) -> None:
    page = max(0, callback_data.page)
    items, total_pages = await deal_service.list_user_deals(db_user.telegram_id, page)
    if not items and page > 0:
        page -= 1
        items, total_pages = await deal_service.list_user_deals(db_user.telegram_id, page)
    if callback.message:
        await render_menu(callback.message,
            translate(db_user.language, TextKey.DEAL_LIST_CAPTION),
            deals_list(db_user.language, items, page, total_pages),
            screen="deals",
        )


@router.callback_query(DealCallback.filter(F.action == DealAction.OPEN))
async def open_deal(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    deal_service: DealService,
    settings: Settings,
) -> None:
    deal = await deal_service.get_deal(callback_data.deal_id)
    if not deal:
        if callback.message:
            await callback.message.answer(translate(db_user.language, TextKey.DEAL_NOT_FOUND))
        return
    if db_user.telegram_id not in {deal.creator_id, deal.buyer_id}:
        if callback.message:
            await callback.message.answer(translate(db_user.language, TextKey.DEAL_FORBIDDEN))
        return
    if callback.message:
        await render_deal_card(callback.message, deal, db_user, deal_service, settings)


@router.callback_query(DealCallback.filter(F.action == DealAction.CANCEL))
async def cancel_deal(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    deal_service: DealService,
    notification_gateway: TelegramNotificationGateway,
    settings: Settings,
) -> None:
    deal, applied = await deal_service.cancel_deal(
        callback_data.deal_id, db_user.telegram_id
    )
    if not applied:
        await callback.answer(
            translate(db_user.language, TextKey.DEAL_ALREADY_CANCELLED),
            show_alert=True,
        )
        return
    if (
        deal.status is DealStatus.CANCELLED
        and db_user.telegram_id == deal.creator_id
        and deal.buyer_id is not None
    ):
        buyer, _ = await deal_service.participants(deal)
        if buyer:
            await notification_gateway.cancelled_by_seller(deal, buyer)
    elif deal.status is not DealStatus.CANCELLED:
        buyer, seller = await deal_service.participants(deal)
        await notification_gateway.dispute_opened(deal, buyer, seller)
        if callback.message:
            await render_deal_card(callback.message, deal, db_user, deal_service, settings)
        await callback.answer(
            "После оплаты отмена рассматривается как спор. Средства заморожены до решения администратора."
            if db_user.language is Language.RU
            else "After payment, cancellation opens a dispute. Funds remain frozen until an administrator decides.",
            show_alert=True,
        )
        return
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=home_keyboard(db_user.language))
    await callback.answer(
        translate(db_user.language, TextKey.DEAL_CANCELLED),
        show_alert=True,
    )


@router.callback_query(DealCallback.filter(F.action == DealAction.CONFIRM))
async def confirm_deal(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    payout_service: PayoutService,
    deal_service: DealService,
) -> None:
    try:
        deal = await payout_service.confirm_receipt(callback_data.deal_id, db_user.telegram_id)
    except ServiceUnavailableError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except (DealConfirmationForbiddenError, DealNotFoundError):
        await callback.answer(
            "Сделка уже завершена или выплата обрабатывается"
            if db_user.language is Language.RU
            else "The deal is already completed or its payout is processing",
            show_alert=True,
        )
        return
    if callback.message:
        await callback.message.answer(
            translate(
                db_user.language,
                TextKey.DEAL_RELEASE_ACCEPTED,
                description=deal.description,
                seller_amount=format_amount(deal.amount),
                payment_amount=format_amount(deal_service.buyer_payment_amount(deal)),
                currency=currency_label(deal.currency),
            ),
            reply_markup=home_keyboard(db_user.language),
        )
        await callback.message.edit_reply_markup(reply_markup=home_keyboard(db_user.language))
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
        await callback.answer(
            "Услуга уже отмечена как оказанная"
            if db_user.language is Language.RU
            else "Service has already been marked as delivered",
            show_alert=True,
        )
        return
    if callback.message and callback.message.reply_markup:
        rows = [
            [button for button in row if not (
                button.callback_data
                and button.callback_data
                == DealCallback(action=DealAction.DELIVER, deal_id=callback_data.deal_id).pack()
            )]
            for row in callback.message.reply_markup.inline_keyboard
        ]
        await callback.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row])
        )
    await callback.answer()


@router.callback_query(DealCallback.filter(F.action == DealAction.DISPUTE))
async def begin_dispute(
    callback: types.CallbackQuery,
    callback_data: DealCallback,
    db_user: User,
    state: FSMContext,
    deal_service: DealService,
) -> None:
    deal = await deal_service.get_deal(callback_data.deal_id)
    if (
        deal is None
        or db_user.telegram_id not in {deal.creator_id, deal.buyer_id}
        or deal.status not in {
            DealStatus.COLLECTING,
            DealStatus.COLLECTION_SUBMITTED,
            DealStatus.DELIVERY_PENDING,
            DealStatus.DELIVERED,
        }
    ):
        await callback.answer(
            translate(db_user.language, TextKey.DEAL_FORBIDDEN),
            show_alert=True,
        )
        return
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
