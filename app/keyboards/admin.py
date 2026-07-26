from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import AdminAction, AdminDisputeAction, DisputeStatus
from app.keyboards.callbacks import AdminCallback, AdminDisputeCallback
from app.models.entities import DisputeTicket


def admin_menu(maintenance_enabled: bool) -> InlineKeyboardMarkup:
    maintenance = "Выключить техперерыв" if maintenance_enabled else "Включить техперерыв"
    action = AdminAction.MAINTENANCE_OFF if maintenance_enabled else AdminAction.MAINTENANCE_ON
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Споры", callback_data=AdminCallback(action=AdminAction.DISPUTES).pack())],
        [InlineKeyboardButton(text="Рассылка", callback_data=AdminCallback(action=AdminAction.BROADCAST).pack())],
        [InlineKeyboardButton(text=maintenance, callback_data=AdminCallback(action=action).pack())],
    ])


def admin_disputes(items: list[DisputeTicket], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=f"#{item.id} · deal {item.deal_id} · {item.status.value}",
        callback_data=AdminDisputeCallback(
            action=AdminDisputeAction.OPEN, ticket_id=item.id, page=page
        ).pack(),
    )] for item in items]
    navigation: list[InlineKeyboardButton] = []
    if page > 0:
        navigation.append(InlineKeyboardButton(
            text="←", callback_data=AdminDisputeCallback(
                action=AdminDisputeAction.OPEN, ticket_id=0, page=page - 1
            ).pack()
        ))
    navigation.append(InlineKeyboardButton(text=str(page + 1), callback_data="noop"))
    if has_next:
        navigation.append(InlineKeyboardButton(
            text="→", callback_data=AdminDisputeCallback(
                action=AdminDisputeAction.OPEN, ticket_id=0, page=page + 1
            ).pack()
        ))
    rows.append(navigation)
    rows.append([InlineKeyboardButton(text="Админ-меню", callback_data=AdminCallback(action=AdminAction.BACK).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_dispute_actions(ticket: DisputeTicket, page: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if ticket.status is DisputeStatus.OPEN:
        rows.extend([
            [InlineKeyboardButton(text="Выплатить продавцу", callback_data=AdminDisputeCallback(
                action=AdminDisputeAction.RELEASE, ticket_id=ticket.id, page=page
            ).pack())],
            [InlineKeyboardButton(text="Вернуть покупателю", callback_data=AdminDisputeCallback(
                action=AdminDisputeAction.REFUND, ticket_id=ticket.id, page=page
            ).pack())],
        ])
    rows.append([InlineKeyboardButton(text="К списку", callback_data=AdminDisputeCallback(
        action=AdminDisputeAction.OPEN, ticket_id=0, page=page
    ).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)
