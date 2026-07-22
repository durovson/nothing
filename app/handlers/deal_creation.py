from decimal import Decimal, InvalidOperation

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from pydantic import ValidationError

from app.config import Settings
from app.core.enums import Currency, DealType, Language
from app.keyboards import (
    CurrencyCallback,
    DealTypeCallback,
    created_deal_actions,
    currency_keyboard,
    deal_type_keyboard,
)
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.deals import DealService
from app.states import DealCreationStates

router = Router(name="deal-creation")
CREATE_DEAL_TEXTS = {translate(language, TextKey.MENU_CREATE_DEAL) for language in Language}


@router.message(F.text.in_(CREATE_DEAL_TEXTS))
async def start_deal_creation(
    message: types.Message,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(DealCreationStates.waiting_for_type)
    await message.answer(
        translate(db_user.language, TextKey.DEAL_CREATE_INTRO),
        reply_markup=deal_type_keyboard(db_user.language),
    )


@router.callback_query(DealCreationStates.waiting_for_type, DealTypeCallback.filter())
async def choose_deal_type(
    callback: types.CallbackQuery,
    callback_data: DealTypeCallback,
    db_user: User,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.update_data(deal_type=callback_data.deal_type.value)
    await state.set_state(DealCreationStates.waiting_for_description)
    if callback.message:
        if callback_data.deal_type is DealType.CHANNEL:
            await callback.message.answer(
                translate(
                    db_user.language,
                    TextKey.DEAL_CHANNEL_WARNING,
                    warning=settings.CHANNEL_PASSWORD_WARNING,
                )
            )
        else:
            await callback.message.answer(translate(db_user.language, TextKey.DEAL_DESCRIPTION_PROMPT))
    await callback.answer()


@router.message(DealCreationStates.waiting_for_description)
async def handle_description(
    message: types.Message,
    db_user: User,
    state: FSMContext,
) -> None:
    description = (message.text or "").strip()
    if not 1 <= len(description) <= 2_000:
        await message.answer(translate(db_user.language, TextKey.DEAL_DESCRIPTION_PROMPT))
        return
    await state.update_data(description=description)
    await state.set_state(DealCreationStates.waiting_for_currency)
    await message.answer(
        translate(db_user.language, TextKey.DEAL_CURRENCY_PROMPT),
        reply_markup=currency_keyboard(),
    )


@router.callback_query(DealCreationStates.waiting_for_currency, CurrencyCallback.filter())
async def choose_currency(
    callback: types.CallbackQuery,
    callback_data: CurrencyCallback,
    db_user: User,
    state: FSMContext,
) -> None:
    await state.update_data(currency=callback_data.currency.value)
    await state.set_state(DealCreationStates.waiting_for_amount)
    if callback.message:
        await callback.message.answer(translate(db_user.language, TextKey.DEAL_AMOUNT_PROMPT))
    await callback.answer()


@router.message(DealCreationStates.waiting_for_amount)
async def handle_amount(
    message: types.Message,
    db_user: User,
    deal_service: DealService,
    settings: Settings,
    state: FSMContext,
) -> None:
    try:
        amount = Decimal((message.text or "").strip())
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(translate(db_user.language, TextKey.DEAL_AMOUNT_INVALID))
        return

    data = await state.get_data()
    try:
        deal = await deal_service.create_deal(
            creator_id=db_user.telegram_id,
            deal_type=DealType(data["deal_type"]),
            description=str(data["description"]),
            currency=Currency(data["currency"]),
            amount=amount,
        )
    except (ValidationError, KeyError, ValueError):
        await message.answer(translate(db_user.language, TextKey.DEAL_AMOUNT_INVALID))
        return
    await state.clear()

    bot_username = settings.TELEGRAM_BOT_USERNAME or (await message.bot.get_me()).username or "YourBot"
    deep_link = f"https://t.me/{bot_username}?start={deal.public_id}"
    await message.answer(
        translate(
            db_user.language,
            TextKey.DEAL_CREATED,
            deal_id=deal.public_id,
            deal_type=deal.deal_type.value,
            description=deal.description,
            amount=deal.amount,
            payment_amount=deal_service.buyer_payment_amount(deal),
            currency=deal.currency.value,
            wallet_address=deal.wallet_address or "-",
            deep_link=deep_link,
        ),
        reply_markup=created_deal_actions(db_user.language, deal.id),
    )

