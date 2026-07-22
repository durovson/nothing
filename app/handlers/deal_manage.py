from aiogram import F, Router, types

from app.core.enums import DealStatus, Language
from app.core.exceptions import DealConfirmationForbiddenError, MissingPayoutWalletError
from app.keyboards import DealCallback, PageCallback, deal_actions, deals_list
from app.keyboards.callbacks import DealAction, PageAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.deals import DealService
from app.services.payouts import PayoutService

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
        await callback.message.answer(
            translate(db_user.language, TextKey.DEAL_LIST_CAPTION),
            reply_markup=deals_list(db_user.language, items, page, has_next),
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
        await callback.message.answer(
            translate(
                db_user.language,
                TextKey.DEAL_CARD,
                deal_id=deal.public_id,
                status=deal.status.value,
                deal_type=deal.deal_type.value,
                description=deal.description,
                amount=deal.amount,
                currency=deal.currency.value,
                wallet_address=deal.wallet_address or "-",
                buyer=buyer,
            ),
            reply_markup=deal_actions(db_user.language, deal, db_user.telegram_id),
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
    except MissingPayoutWalletError:
        key = TextKey.DEAL_WAIT_WALLET
    except DealConfirmationForbiddenError:
        key = TextKey.DEAL_FORBIDDEN
    else:
        key = TextKey.DEAL_CONFIRMED
    if callback.message:
        await callback.message.answer(translate(db_user.language, key))
    await callback.answer()

