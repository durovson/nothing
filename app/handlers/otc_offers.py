from __future__ import annotations

from decimal import InvalidOperation
from html import escape

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.api.telegram_notifier import TelegramNotificationGateway
from app.core.constants import OTC_OFFER_MAX_DECIMAL_PLACES
from app.core.exceptions import (
    OtcOfferCooldownError,
    OtcOfferResolutionError,
    OtcOfferUnavailableError,
)
from app.keyboards.callbacks import (
    OtcOfferAction,
    OtcOfferCallback,
)
from app.keyboards.otc_offers import (
    otc_offer_buyer_profile_keyboard,
    otc_offer_input_keyboard,
)
from app.locales import TextKey, translate
from app.models.entities import DeskListing, User
from app.services.otc_offers import OtcOfferService
from app.states import OtcOfferStates
from app.utils import currency_label, format_amount, parse_decimal_amount
from app.utils.menu import remember_menu, render_menu, render_stored_menu

router = Router(name="otc_offers")


def _listing_price(listing: DeskListing) -> str:
    if listing.price is None:
        return "Offer"
    return f"{format_amount(listing.price)} {currency_label(listing.deal_currency)}"


async def begin_otc_offer(
    message: Message,
    listing_public_id: str,
    db_user: User,
    state: FSMContext,
    service: OtcOfferService,
) -> None:
    await state.clear()
    try:
        listing = await service.prepare(listing_public_id, db_user.telegram_id)
    except OtcOfferUnavailableError:
        await message.answer(
            translate(db_user.language, TextKey.OTC_OFFER_UNAVAILABLE)
        )
        return

    await state.set_state(OtcOfferStates.waiting_for_amount)
    await state.update_data(listing_public_id=listing.public_id)
    rendered = await render_menu(
        message,
        translate(
            db_user.language,
            TextKey.OTC_OFFER_PROMPT,
            item=escape(listing.description),
            price=_listing_price(listing),
        ),
        otc_offer_input_keyboard(db_user.language),
        screen="desk_create",
    )
    await remember_menu(state, rendered)


@router.message(OtcOfferStates.waiting_for_amount, F.text)
async def receive_otc_offer_amount(
    message: Message,
    db_user: User,
    state: FSMContext,
    otc_offer_service: OtcOfferService,
    notification_gateway: TelegramNotificationGateway,
) -> None:
    try:
        amount = parse_decimal_amount(message.text or "")
        decimal_places = max(0, -amount.as_tuple().exponent)
        integer_places = max(1, amount.adjusted() + 1)
        if (
            decimal_places > OTC_OFFER_MAX_DECIMAL_PLACES
            or integer_places + decimal_places > 36
        ):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(
            translate(db_user.language, TextKey.OTC_OFFER_INVALID_AMOUNT)
        )
        return

    data = await state.get_data()
    listing_public_id = str(data.get("listing_public_id", ""))
    try:
        offer = await otc_offer_service.create(
            listing_public_id, db_user, amount
        )
    except OtcOfferCooldownError as exc:
        await message.answer(
            translate(
                db_user.language,
                TextKey.OTC_OFFER_COOLDOWN,
                seconds=exc.retry_after_seconds,
            )
        )
        return
    except OtcOfferUnavailableError:
        await state.clear()
        await message.answer(
            translate(db_user.language, TextKey.OTC_OFFER_UNAVAILABLE)
        )
        return

    await notification_gateway.otc_offer_created(offer)
    await render_stored_menu(
        message,
        state,
        translate(
            db_user.language,
            TextKey.OTC_OFFER_SENT,
            amount=format_amount(offer.amount),
        ),
        otc_offer_input_keyboard(db_user.language),
        screen="desk_create",
    )
    await state.clear()


@router.callback_query(OtcOfferCallback.filter())
async def resolve_otc_offer(
    callback: types.CallbackQuery,
    callback_data: OtcOfferCallback,
    db_user: User,
    otc_offer_service: OtcOfferService,
    notification_gateway: TelegramNotificationGateway,
) -> None:
    accepted = callback_data.action is OtcOfferAction.ACCEPT
    try:
        offer = await otc_offer_service.resolve(
            callback_data.offer_id,
            db_user.telegram_id,
            accepted=accepted,
        )
    except OtcOfferResolutionError:
        await callback.answer(
            translate(
                db_user.language, TextKey.OTC_OFFER_ALREADY_RESOLVED
            ),
            show_alert=True,
        )
        return

    if callback.message:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=otc_offer_buyer_profile_keyboard(
                    db_user.language, offer.buyer_id
                )
            )
        except TelegramBadRequest:
            pass
    await notification_gateway.otc_offer_resolved(offer)
    await callback.answer()
