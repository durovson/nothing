from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.enums import (
    AdminAction,
    AdminDisputeAction,
    DisputeStatus,
    FinancialAdminAction,
    FinancialOperationStatus,
    UnmatchedPaymentAction,
    SystemMode,
)
from app.keyboards.callbacks import (
    AdminCallback,
    AdminDisputeCallback,
    AdminFinancialCallback,
    AdminUnmatchedCallback,
)
from app.models.entities import DisputeTicket, FinancialOperation, UnmatchedPayment


def admin_menu(maintenance_enabled: bool, system_mode: SystemMode) -> InlineKeyboardMarkup:
    maintenance = "Выключить техперерыв" if maintenance_enabled else "Включить техперерыв"
    action = AdminAction.MAINTENANCE_OFF if maintenance_enabled else AdminAction.MAINTENANCE_ON
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ Споры", callback_data=AdminCallback(action=AdminAction.DISPUTES).pack())],
        [InlineKeyboardButton(text="💸 Финансовые операции", callback_data=AdminCallback(action=AdminAction.FINANCIAL_OPERATIONS).pack())],
        [InlineKeyboardButton(text="🧾 Неопознанные платежи", callback_data=AdminCallback(action=AdminAction.UNMATCHED_PAYMENTS).pack())],
        [InlineKeyboardButton(text="📣 Рассылка", callback_data=AdminCallback(action=AdminAction.BROADCAST).pack())],
        [InlineKeyboardButton(text=f"Режим: {system_mode.value}", callback_data="noop")],
        [
            InlineKeyboardButton(text="✅ Normal", callback_data=AdminCallback(action=AdminAction.MODE_NORMAL).pack()),
            InlineKeyboardButton(text="👁 Read only", callback_data=AdminCallback(action=AdminAction.MODE_READ_ONLY).pack()),
        ],
        [InlineKeyboardButton(text="⚠️ Emergency", callback_data=AdminCallback(action=AdminAction.MODE_EMERGENCY).pack())],
        [InlineKeyboardButton(text=f"🛠 {maintenance}", callback_data=AdminCallback(action=action).pack())],
    ])


def admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminCallback(action=AdminAction.BACK).pack())
    ]])


def admin_disputes(items: list[DisputeTicket], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=f"#{item.id} · deal {item.deal_id} · {item.status.value}",
        callback_data=AdminDisputeCallback(action=AdminDisputeAction.OPEN, ticket_id=item.id, page=page).pack(),
    )] for item in items]
    rows.extend(_dispute_navigation(page, has_next))
    rows.append(admin_back().inline_keyboard[0])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_dispute_actions(ticket: DisputeTicket, page: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if ticket.status is DisputeStatus.OPEN:
        rows.extend([
            [InlineKeyboardButton(text="Выплатить продавцу", callback_data=AdminDisputeCallback(action=AdminDisputeAction.RELEASE, ticket_id=ticket.id, page=page).pack())],
            [InlineKeyboardButton(text="Вернуть покупателю", callback_data=AdminDisputeCallback(action=AdminDisputeAction.REFUND, ticket_id=ticket.id, page=page).pack())],
        ])
    rows.append([InlineKeyboardButton(text="К списку", callback_data=AdminDisputeCallback(action=AdminDisputeAction.OPEN, ticket_id=0, page=page).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_operations(items: list[FinancialOperation], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=f"#{item.id} · {item.flow.value}/{item.type.value} · {item.status.value}",
        callback_data=AdminFinancialCallback(action=FinancialAdminAction.OPEN, operation_id=item.id, page=page).pack(),
    )] for item in items]
    navigation: list[InlineKeyboardButton] = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text="←", callback_data=AdminFinancialCallback(action=FinancialAdminAction.OPEN, operation_id=0, page=page - 1).pack()))
    navigation.append(InlineKeyboardButton(text=str(page + 1), callback_data="noop"))
    if has_next:
        navigation.append(InlineKeyboardButton(text="→", callback_data=AdminFinancialCallback(action=FinancialAdminAction.OPEN, operation_id=0, page=page + 1).pack()))
    rows.extend([navigation, admin_back().inline_keyboard[0]])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_operation_actions(operation: FinancialOperation, page: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if operation.status in {FinancialOperationStatus.FAILED, FinancialOperationStatus.BOUNCED}:
        rows.append([InlineKeyboardButton(text="🔁 Повторить безопасно", callback_data=AdminFinancialCallback(action=FinancialAdminAction.RETRY, operation_id=operation.id, page=page).pack())])
        rows.append([InlineKeyboardButton(text="⏸ Mark failed / ручная проверка", callback_data=AdminFinancialCallback(action=FinancialAdminAction.MANUAL_REVIEW, operation_id=operation.id, page=page).pack())])
    elif operation.status is FinancialOperationStatus.MANUAL_REVIEW:
        rows.append([InlineKeyboardButton(text="🔓 Переоткрыть manual review", callback_data=AdminFinancialCallback(action=FinancialAdminAction.REOPEN, operation_id=operation.id, page=page).pack())])
    rows.append([InlineKeyboardButton(text="✅ Force complete по tx hash", callback_data=AdminFinancialCallback(action=FinancialAdminAction.FORCE_COMPLETE, operation_id=operation.id, page=page).pack())])
    rows.append([InlineKeyboardButton(text="К списку", callback_data=AdminFinancialCallback(action=FinancialAdminAction.OPEN, operation_id=0, page=page).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_unmatched(items: list[UnmatchedPayment], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=f"#{item.id} · {item.currency.value} · {item.reason[:24]}",
        callback_data=AdminUnmatchedCallback(action=UnmatchedPaymentAction.OPEN, payment_id=item.id, page=page).pack(),
    )] for item in items]
    navigation: list[InlineKeyboardButton] = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text="←", callback_data=AdminUnmatchedCallback(action=UnmatchedPaymentAction.OPEN, payment_id=0, page=page - 1).pack()))
    navigation.append(InlineKeyboardButton(text=str(page + 1), callback_data="noop"))
    if has_next:
        navigation.append(InlineKeyboardButton(text="→", callback_data=AdminUnmatchedCallback(action=UnmatchedPaymentAction.OPEN, payment_id=0, page=page + 1).pack()))
    rows.extend([navigation, admin_back().inline_keyboard[0]])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_unmatched_actions(payment: UnmatchedPayment, page: int, confirm: bool = False) -> InlineKeyboardMarkup:
    action = UnmatchedPaymentAction.CONFIRM_REFUND if confirm else UnmatchedPaymentAction.REFUND
    label = "⚠️ Подтвердить возврат отправителю" if confirm else "↩️ Вернуть отправителю"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=AdminUnmatchedCallback(action=action, payment_id=payment.id, page=page).pack())],
        [InlineKeyboardButton(text="К списку", callback_data=AdminUnmatchedCallback(action=UnmatchedPaymentAction.OPEN, payment_id=0, page=page).pack())],
    ])


def _dispute_navigation(page: int, has_next: bool) -> list[list[InlineKeyboardButton]]:
    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(InlineKeyboardButton(text="←", callback_data=AdminDisputeCallback(action=AdminDisputeAction.OPEN, ticket_id=0, page=page - 1).pack()))
    row.append(InlineKeyboardButton(text=str(page + 1), callback_data="noop"))
    if has_next:
        row.append(InlineKeyboardButton(text="→", callback_data=AdminDisputeCallback(action=AdminDisputeAction.OPEN, ticket_id=0, page=page + 1).pack()))
    return [row]
