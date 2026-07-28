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
from app.utils import currency_label, deal_status_label


def deal_type_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=translate(locale, TextKey.DEAL_TYPE_OFFER), callback_data=DealTypeCallback(deal_type=DealType.OFFER).pack()),
                InlineKeyboardButton(text=translate(locale, TextKey.DEAL_TYPE_CHANNEL), callback_data=DealTypeCallback(deal_type=DealType.CHANNEL).pack()),
            ],
            [InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())],
        ]
    )


def currency_keyboard(locale: Language = Language.RU) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=currency_label(currency), callback_data=CurrencyCallback(currency=currency).pack())
            for currency in Currency
        ], [InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())]]
    )


def back_keyboard(locale: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())
    ]])


def payment_keyboard(
    locale: Language,
    payment_url: str,
    channel_invite_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=translate(locale, TextKey.DEAL_PAY_BUTTON), url=payment_url)]]
    if channel_invite_url:
        rows.insert(0, [InlineKeyboardButton(
            text=translate(locale, TextKey.DEAL_CHANNEL_JOIN_BUTTON),
            url=channel_invite_url,
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def created_deal_actions(locale: Language, deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=translate(locale, TextKey.DEAL_CANCEL_BUTTON), callback_data=DealCallback(action=DealAction.CANCEL, deal_id=deal_id).pack())],
            [InlineKeyboardButton(text=translate(locale, TextKey.MAIN_MENU_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())],
        ]
    )


def deals_list(locale: Language, deals: list[Deal], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"#{deal.public_id} | {deal_status_label(deal.status, locale)}",
            callback_data=DealCallback(action=DealAction.OPEN, deal_id=deal.id).pack(),
        )]
        for deal in deals
    ]
    pagination: list[InlineKeyboardButton] = []
    if page > 0:
        pagination.append(InlineKeyboardButton(text="⬅️", callback_data=PageCallback(action=PageAction.OPEN, page=page - 1).pack()))
    pagination.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=PageCallback(action=PageAction.CURRENT, page=page).pack()))
    if page + 1 < total_pages:
        pagination.append(InlineKeyboardButton(text="➡️", callback_data=PageCallback(action=PageAction.OPEN, page=page + 1).pack()))
    rows.append(pagination)
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.MAIN_MENU_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deal_actions(locale: Language, deal: Deal, viewer_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if deal.resolution != "refund" and viewer_id in {deal.creator_id, deal.buyer_id} and deal.status in {
        DealStatus.PENDING,
        DealStatus.COLLECTING,
        DealStatus.COLLECTION_SUBMITTED,
        DealStatus.DELIVERY_PENDING,
        DealStatus.DELIVERED,
    }:
        rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_CANCEL_BUTTON), callback_data=DealCallback(action=DealAction.CANCEL, deal_id=deal.id).pack())])
    if deal.creator_id == viewer_id and deal.status is DealStatus.DELIVERY_PENDING and deal.deal_type is not DealType.CHANNEL:
        rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_DELIVER_BUTTON), callback_data=DealCallback(action=DealAction.DELIVER, deal_id=deal.id).pack())])
    if deal.buyer_id == viewer_id and deal.status is DealStatus.DELIVERED:
        rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_CONFIRM_BUTTON), callback_data=DealCallback(action=DealAction.CONFIRM, deal_id=deal.id).pack())])
    if viewer_id in {deal.creator_id, deal.buyer_id} and deal.status in {
        DealStatus.DELIVERY_PENDING,
        DealStatus.DELIVERED,
    }:
        rows.append([InlineKeyboardButton(text=translate(locale, TextKey.DEAL_DISPUTE_BUTTON), callback_data=DealCallback(action=DealAction.DISPUTE, deal_id=deal.id).pack())])
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.BACK_BUTTON), callback_data=MenuCallback(action=MenuAction.DEALS).pack())])
    rows.append([InlineKeyboardButton(text=translate(locale, TextKey.MAIN_MENU_BUTTON), callback_data=MenuCallback(action=MenuAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
