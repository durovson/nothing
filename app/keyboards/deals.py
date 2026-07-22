from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import Currency, DealStatus, DealType, Language
from app.keyboards.callbacks import (
    CurrencyCallback,
    DealAction,
    DealCallback,
    DealTypeCallback,
    MenuAction,
    MenuCallback,
    PageAction,
    PageCallback,
)
from app.locales import TextKey, translate
from app.models.entities import Deal


def deal_type_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=translate(locale, TextKey.DEAL_TYPE_GIFTS), callback_data=DealTypeCallback(deal_type=DealType.GIFTS).pack()),
                InlineKeyboardButton(text=translate(locale, TextKey.DEAL_TYPE_CHANNEL), callback_data=DealTypeCallback(deal_type=DealType.CHANNEL).pack()),
            ],
            [InlineKeyboardButton(text=translate(locale, TextKey.DEAL_TYPE_ACCOUNT), callback_data=DealTypeCallback(deal_type=DealType.ACCOUNT).pack())],
        ]
    )


def currency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=Currency.TON.value, callback_data=CurrencyCallback(currency=Currency.TON).pack())]]
    )


def created_deal_actions(locale: Language, deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=translate(locale, TextKey.DEAL_CANCEL_BUTTON), callback_data=DealCallback(action=DealAction.CANCEL, deal_id=deal_id).pack())],
            [InlineKeyboardButton(text=translate(locale, TextKey.DEAL_REFRESH_BUTTON), callback_data=DealCallback(action=DealAction.OPEN, deal_id=deal_id).pack())],
        ]
    )


def deals_list(locale: Language, deals: list[Deal], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"#{deal.public_id} · {deal.status.value}", callback_data=DealCallback(action=DealAction.OPEN, deal_id=deal.id).pack())]
        for deal in deals
    ]
    pagination: list[InlineKeyboardButton] = []
    if page > 0:
        pagination.append(InlineKeyboardButton(text="⬅️", callback_data=PageCallback(action=PageAction.OPEN, page=page - 1).pack()))
    pagination.append(InlineKeyboardButton(text=str(page + 1), callback_data=PageCallback(action=PageAction.CURRENT, page=page).pack()))
    if has_next:
        pagination.append(InlineKeyboardButton(text="➡️", callback_data=PageCallback(action=PageAction.OPEN, page=page + 1).pack()))
    rows.append(pagination)
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deal_actions(locale: Language, deal: Deal, viewer_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if deal.creator_id == viewer_id and deal.status is DealStatus.PENDING:
        rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_CANCEL_BUTTON), callback_data=DealCallback(action=DealAction.CANCEL, deal_id=deal.id).pack())])
    if deal.buyer_id == viewer_id and deal.status is DealStatus.PAID:
        rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_CONFIRM_BUTTON), callback_data=DealCallback(action=DealAction.CONFIRM, deal_id=deal.id).pack())])
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_REFRESH_BUTTON), callback_data=DealCallback(action=DealAction.OPEN, deal_id=deal.id).pack())])
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

