import asyncio
import logging
from html import escape

from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from app.core.constants import BROADCAST_BATCH_SIZE, BROADCAST_DELAY_SECONDS
from app.core.enums import AdminAction, AdminDisputeAction, FinancialAdminAction, UnmatchedPaymentAction, SystemMode
from app.core.exceptions import ApplicationError
from app.keyboards.admin import (
    admin_back, admin_dispute_actions, admin_disputes, admin_menu,
    admin_operation_actions, admin_operations, admin_unmatched, admin_unmatched_actions,
)
from app.keyboards.callbacks import (
    AdminCallback, AdminDisputeCallback, AdminFinancialCallback, AdminUnmatchedCallback,
)
from app.services.admin import AdminService
from app.states.forms import AdminStates
from app.utils import currency_label, format_amount, render_menu

logger = logging.getLogger(__name__)
router = Router(name="admin")


async def _show_menu(message: types.Message, actor_id: int, service: AdminService) -> None:
    service.require_admin(actor_id)
    settings = await service.maintenance(force=True)
    mode = await service.system_mode(force=True)
    status = "включён" if settings.maintenance_enabled else "выключен"
    await render_menu(
        message,
        f"🛡 Панель администратора\n\nТехнический перерыв: {status}\n"
        f"Системный режим: <b>{mode.mode.value}</b>\nПричина: {escape(mode.reason or '—')}",
        admin_menu(settings.maintenance_enabled, mode.mode),
    )


@router.message(Command("admin"))
async def open_admin(message: types.Message, admin_service: AdminService) -> None:
    if message.from_user and admin_service.is_admin(message.from_user.id):
        await _show_menu(message, message.from_user.id, admin_service)


@router.message(Command("emergency"))
async def emergency_command(
    message: types.Message, command: CommandObject, admin_service: AdminService
) -> None:
    if not message.from_user or not admin_service.is_admin(message.from_user.id):
        return
    enabled = (command.args or "").strip().lower()
    if enabled not in {"on", "off"}:
        await message.answer("Использование: /emergency on или /emergency off")
        return
    mode = SystemMode.EMERGENCY if enabled == "on" else SystemMode.NORMAL
    await admin_service.set_system_mode(
        message.from_user.id, mode, f"Manual /emergency {enabled}"
    )
    await _show_menu(message, message.from_user.id, admin_service)


@router.callback_query(AdminCallback.filter(F.action.in_({
    AdminAction.MODE_NORMAL, AdminAction.MODE_READ_ONLY, AdminAction.MODE_EMERGENCY
})))
async def set_system_mode_callback(
    callback: types.CallbackQuery,
    callback_data: AdminCallback,
    admin_service: AdminService,
) -> None:
    modes = {
        AdminAction.MODE_NORMAL: SystemMode.NORMAL,
        AdminAction.MODE_READ_ONLY: SystemMode.READ_ONLY,
        AdminAction.MODE_EMERGENCY: SystemMode.EMERGENCY,
    }
    await admin_service.set_system_mode(
        callback.from_user.id,
        modes[callback_data.action],
        f"Manual admin panel change by {callback.from_user.id}",
    )
    if callback.message:
        await _show_menu(callback.message, callback.from_user.id, admin_service)
    await callback.answer("Режим изменён", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == AdminAction.BACK))
async def back(
    callback: types.CallbackQuery,
    admin_service: AdminService,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message and callback.from_user:
        await _show_menu(callback.message, callback.from_user.id, admin_service)
    await callback.answer()


async def _show_disputes(message: types.Message, actor_id: int, page: int, service: AdminService) -> None:
    items, has_next = await service.list_disputes(actor_id, page)
    await render_menu(
        message,
        "⚖️ Споры\n\nСначала отображаются открытые тикеты.",
        admin_disputes(items, page, has_next),
    )


@router.callback_query(AdminCallback.filter(F.action == AdminAction.DISPUTES))
async def disputes(callback: types.CallbackQuery, admin_service: AdminService) -> None:
    if callback.message:
        await _show_disputes(callback.message, callback.from_user.id, 0, admin_service)
    await callback.answer()


@router.callback_query(AdminDisputeCallback.filter(F.action == AdminDisputeAction.OPEN))
async def dispute_open(callback: types.CallbackQuery, callback_data: AdminDisputeCallback, admin_service: AdminService) -> None:
    if not callback.message:
        return
    if callback_data.ticket_id == 0:
        await _show_disputes(callback.message, callback.from_user.id, callback_data.page, admin_service)
    else:
        ticket, deal = await admin_service.dispute_card(callback.from_user.id, callback_data.ticket_id)
        await render_menu(callback.message,
            f"Тикет #{ticket.id}\nСделка: <code>#{deal.public_id}</code> ({deal.id})\nСтатус: {ticket.status.value}\n"
            f"Открыл: {ticket.opened_by}\nПродавец: {deal.creator_id}\nПокупатель: {deal.buyer_id}\n"
            f"Сумма: {format_amount(deal.amount)} {currency_label(deal.currency)}\n\n{escape(ticket.description)}",
            admin_dispute_actions(ticket, callback_data.page),
        )
    await callback.answer()


@router.callback_query(AdminDisputeCallback.filter(F.action.in_({AdminDisputeAction.RELEASE, AdminDisputeAction.REFUND})))
async def begin_resolution(callback: types.CallbackQuery, callback_data: AdminDisputeCallback, state: FSMContext, admin_service: AdminService) -> None:
    admin_service.require_admin(callback.from_user.id)
    await state.set_state(AdminStates.waiting_for_resolution_reason)
    await state.update_data(ticket_id=callback_data.ticket_id, resolution_action=callback_data.action.value)
    if callback.message:
        await render_menu(callback.message, "Введите причину решения (3–1000 символов).", admin_back())
    await callback.answer()


@router.message(AdminStates.waiting_for_resolution_reason)
async def save_resolution(message: types.Message, state: FSMContext, admin_service: AdminService) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    try:
        deal = await admin_service.resolve(
            message.from_user.id,
            int(data["ticket_id"]),
            AdminDisputeAction(str(data["resolution_action"])),
            message.text or "",
        )
    except (ApplicationError, ValueError, KeyError) as exc:
        await message.answer(f"Решение не применено: {escape(str(exc))}")
        return
    await state.clear()
    await message.answer(f"Решение принято. Сделка <code>#{deal.public_id}</code>: {deal.status.value}")


async def _show_operations(message: types.Message, actor_id: int, page: int, service: AdminService) -> None:
    items, has_next = await service.list_operations(actor_id, page)
    await render_menu(message, "💸 <b>Проблемные финансовые операции</b>\n\nНеопределённые транзакции не повторяются автоматически.", admin_operations(items, page, has_next))


async def _show_operation(message: types.Message, actor_id: int, operation_id: int, page: int, service: AdminService) -> None:
    item = await service.operation(actor_id, operation_id)
    await render_menu(message,
        f"💸 <b>Операция #{item.id}</b>\nID: <code>{escape(item.operation_id)}</code>\n"
        f"Поток: {item.flow.value}\nТип: {item.type.value}\nСтатус: {item.status.value}\n"
        f"Сделка: {item.deal_id or '—'}\nСумма atomic: <code>{item.amount_atomic}</code> {item.currency.value}\n"
        f"Получатель: <code>{escape(item.destination)}</code>\nКомментарий: {escape(item.comment)}\n"
        f"Повторов: {item.retry_count}\nTx hash: <code>{escape(item.tx_hash or '—')}</code>\n"
        f"Последняя ошибка: {escape(item.last_error or '—')}", admin_operation_actions(item, page))


@router.callback_query(AdminCallback.filter(F.action == AdminAction.FINANCIAL_OPERATIONS))
async def financial_operations(callback: types.CallbackQuery, admin_service: AdminService) -> None:
    if callback.message:
        await _show_operations(callback.message, callback.from_user.id, 0, admin_service)
    await callback.answer()


@router.callback_query(AdminFinancialCallback.filter(F.action == FinancialAdminAction.OPEN))
async def financial_operation_open(callback: types.CallbackQuery, callback_data: AdminFinancialCallback, admin_service: AdminService) -> None:
    if callback.message:
        if callback_data.operation_id:
            await _show_operation(callback.message, callback.from_user.id, callback_data.operation_id, callback_data.page, admin_service)
        else:
            await _show_operations(callback.message, callback.from_user.id, callback_data.page, admin_service)
    await callback.answer()


@router.callback_query(AdminFinancialCallback.filter(F.action == FinancialAdminAction.RETRY))
async def financial_operation_retry(callback: types.CallbackQuery, callback_data: AdminFinancialCallback, admin_service: AdminService) -> None:
    operation = await admin_service.retry_operation(callback.from_user.id, callback_data.operation_id)
    if callback.message:
        await _show_operation(callback.message, callback.from_user.id, operation.id, callback_data.page, admin_service)
    await callback.answer("Операция поставлена в безопасную очередь повторов", show_alert=True)


@router.callback_query(AdminFinancialCallback.filter(F.action == FinancialAdminAction.MANUAL_REVIEW))
async def financial_operation_stop(callback: types.CallbackQuery, callback_data: AdminFinancialCallback, admin_service: AdminService) -> None:
    operation = await admin_service.stop_operation(callback.from_user.id, callback_data.operation_id)
    if callback.message:
        await _show_operation(callback.message, callback.from_user.id, operation.id, callback_data.page, admin_service)
    await callback.answer("Операция оставлена на ручной проверке", show_alert=True)


@router.callback_query(AdminFinancialCallback.filter(F.action == FinancialAdminAction.REOPEN))
async def financial_operation_reopen(callback: types.CallbackQuery, callback_data: AdminFinancialCallback, admin_service: AdminService) -> None:
    operation = await admin_service.reopen_operation(callback.from_user.id, callback_data.operation_id)
    if callback.message:
        await _show_operation(callback.message, callback.from_user.id, operation.id, callback_data.page, admin_service)
    await callback.answer("Операция переоткрыта", show_alert=True)


@router.callback_query(AdminFinancialCallback.filter(F.action == FinancialAdminAction.FORCE_COMPLETE))
async def financial_operation_force_prompt(callback: types.CallbackQuery, callback_data: AdminFinancialCallback, state: FSMContext, admin_service: AdminService) -> None:
    await admin_service.operation(callback.from_user.id, callback_data.operation_id)
    await state.set_state(AdminStates.waiting_for_force_complete_evidence)
    await state.update_data(operation_id=callback_data.operation_id)
    if callback.message:
        await render_menu(callback.message, "⚠️ <b>Force complete</b>\n\nОтправьте две строки:\n<code>64-символьный tx hash</code>\n<code>причина ручного подтверждения</code>\n\nИспользуйте только после проверки блокчейна.", admin_back())
    await callback.answer()


@router.message(AdminStates.waiting_for_force_complete_evidence)
async def financial_operation_force_save(message: types.Message, state: FSMContext, admin_service: AdminService) -> None:
    if not message.from_user:
        return
    lines = (message.text or "").splitlines()
    if len(lines) < 2:
        await message.answer("Нужны две строки: tx hash и причина.")
        return
    data = await state.get_data()
    try:
        operation = await admin_service.force_complete_operation(message.from_user.id, int(data["operation_id"]), lines[0], "\n".join(lines[1:]))
    except (ApplicationError, ValueError, KeyError) as exc:
        await message.answer(f"Операция не подтверждена: {escape(str(exc))}")
        return
    await state.clear()
    await message.answer(f"Операция #{operation.id} подтверждена вручную. Tx: <code>{operation.tx_hash}</code>")


async def _show_unmatched(message: types.Message, actor_id: int, page: int, service: AdminService) -> None:
    items, has_next = await service.list_unmatched(actor_id, page)
    await render_menu(message, "🧾 <b>Неопознанные платежи</b>\n\nПеред возвратом проверьте tx, sender и риск биржевого адреса.", admin_unmatched(items, page, has_next))


async def _show_unmatched_payment(message: types.Message, actor_id: int, payment_id: int, page: int, service: AdminService, *, confirm: bool = False) -> None:
    item = await service.unmatched(actor_id, payment_id)
    await render_menu(message,
        f"🧾 <b>Платёж #{item.id}</b>\nСтатус: {item.status.value}\nВалюта: {item.currency.value}\n"
        f"Сумма atomic: <code>{item.amount_atomic}</code>\nTx: <code>{escape(item.tx_hash)}</code>\n"
        f"LT: <code>{item.tx_lt}</code>\nSender: <code>{escape(item.sender or '—')}</code>\n"
        f"Memo: <code>{escape(item.memo or '—')}</code>\nПричина: {escape(item.reason)}\n\n"
        "⚠️ Sender биржи может не являться депозитным адресом пользователя.", admin_unmatched_actions(item, page, confirm))


@router.callback_query(AdminCallback.filter(F.action == AdminAction.UNMATCHED_PAYMENTS))
async def unmatched_payments(callback: types.CallbackQuery, admin_service: AdminService) -> None:
    if callback.message:
        await _show_unmatched(callback.message, callback.from_user.id, 0, admin_service)
    await callback.answer()


@router.callback_query(AdminUnmatchedCallback.filter(F.action == UnmatchedPaymentAction.OPEN))
async def unmatched_payment_open(callback: types.CallbackQuery, callback_data: AdminUnmatchedCallback, admin_service: AdminService) -> None:
    if callback.message:
        if callback_data.payment_id:
            await _show_unmatched_payment(callback.message, callback.from_user.id, callback_data.payment_id, callback_data.page, admin_service)
        else:
            await _show_unmatched(callback.message, callback.from_user.id, callback_data.page, admin_service)
    await callback.answer()


@router.callback_query(AdminUnmatchedCallback.filter(F.action == UnmatchedPaymentAction.REFUND))
async def unmatched_refund_confirm(callback: types.CallbackQuery, callback_data: AdminUnmatchedCallback, admin_service: AdminService) -> None:
    if callback.message:
        await _show_unmatched_payment(callback.message, callback.from_user.id, callback_data.payment_id, callback_data.page, admin_service, confirm=True)
    await callback.answer("Проверьте sender перед подтверждением", show_alert=True)


@router.callback_query(AdminUnmatchedCallback.filter(F.action == UnmatchedPaymentAction.CONFIRM_REFUND))
async def unmatched_refund_schedule(callback: types.CallbackQuery, callback_data: AdminUnmatchedCallback, admin_service: AdminService) -> None:
    operation = await admin_service.refund_unmatched(callback.from_user.id, callback_data.payment_id)
    if callback.message:
        await render_menu(callback.message, f"✅ Возврат поставлен в очередь как операция #{operation.id}.\nКомментарий: <code>Недействительный платеж</code>", admin_back())
    await callback.answer("Возврат поставлен в очередь", show_alert=True)


@router.callback_query(AdminCallback.filter(F.action == AdminAction.BROADCAST))
async def begin_broadcast(callback: types.CallbackQuery, state: FSMContext, admin_service: AdminService) -> None:
    admin_service.require_admin(callback.from_user.id)
    await state.set_state(AdminStates.waiting_for_broadcast)
    if callback.message:
        await render_menu(callback.message, "📣 Отправьте одно сообщение для рассылки.\n\nПоддерживается любой тип контента Telegram.", admin_back())
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def broadcast(message: types.Message, state: FSMContext, admin_service: AdminService) -> None:
    if not message.from_user:
        return
    admin_service.require_admin(message.from_user.id)
    await state.clear()
    await message.answer("Рассылка запущена.")
    asyncio.create_task(_broadcast_job(message, admin_service), name=f"broadcast-{message.message_id}")


async def _broadcast_job(source: types.Message, service: AdminService) -> None:
    sent = failed = offset = 0
    while True:
        ids = await service.list_user_ids(offset, BROADCAST_BATCH_SIZE)
        if not ids:
            break
        for telegram_id in ids:
            try:
                await source.bot.copy_message(telegram_id, source.chat.id, source.message_id)
                sent += 1
            except TelegramAPIError:
                failed += 1
            await asyncio.sleep(BROADCAST_DELAY_SECONDS)
        offset += len(ids)
    await source.bot.send_message(source.from_user.id, f"Рассылка завершена: {sent} доставлено, {failed} ошибок.")


@router.callback_query(AdminCallback.filter(F.action == AdminAction.MAINTENANCE_ON))
async def maintenance_prompt(callback: types.CallbackQuery, state: FSMContext, admin_service: AdminService) -> None:
    admin_service.require_admin(callback.from_user.id)
    await state.set_state(AdminStates.waiting_for_maintenance_message)
    if callback.message:
        await render_menu(callback.message, "🛠 Введите объявление о техническом перерыве.\n\nОно будет показано всем пользователям, кроме администраторов.", admin_back())
    await callback.answer()


@router.message(AdminStates.waiting_for_maintenance_message)
async def maintenance_on(message: types.Message, state: FSMContext, admin_service: AdminService) -> None:
    text = (message.text or "").strip()
    if not 3 <= len(text) <= 1000 or not message.from_user:
        await message.answer("Нужен текст длиной 3–1000 символов.")
        return
    await admin_service.set_maintenance(message.from_user.id, True, text)
    await state.clear()
    asyncio.create_task(_broadcast_job(message, admin_service), name=f"maintenance-{message.message_id}")
    await message.answer(
        "Технический перерыв включён. Бот доступен только администраторам; объявление отправляется пользователям."
    )


@router.callback_query(AdminCallback.filter(F.action == AdminAction.MAINTENANCE_OFF))
async def maintenance_off(callback: types.CallbackQuery, admin_service: AdminService) -> None:
    await admin_service.set_maintenance(callback.from_user.id, False)
    if callback.message:
        await _show_menu(callback.message, callback.from_user.id, admin_service)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery) -> None:
    await callback.answer()
