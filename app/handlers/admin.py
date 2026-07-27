import asyncio
import logging

from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.core.constants import BROADCAST_BATCH_SIZE, BROADCAST_DELAY_SECONDS
from app.core.enums import AdminAction, AdminDisputeAction
from app.core.exceptions import ApplicationError
from app.keyboards.admin import admin_back, admin_dispute_actions, admin_disputes, admin_menu
from app.keyboards.callbacks import AdminCallback, AdminDisputeCallback
from app.services.admin import AdminService
from app.states.forms import AdminStates
from app.utils import currency_label, format_amount, render_menu

logger = logging.getLogger(__name__)
router = Router(name="admin")


async def _show_menu(message: types.Message, actor_id: int, service: AdminService) -> None:
    service.require_admin(actor_id)
    settings = await service.maintenance(force=True)
    status = "включён" if settings.maintenance_enabled else "выключен"
    await render_menu(
        message,
        f"🛡 Панель администратора\n\nТехнический перерыв: {status}",
        admin_menu(settings.maintenance_enabled),
    )


@router.message(Command("admin"))
async def open_admin(message: types.Message, admin_service: AdminService) -> None:
    if message.from_user and admin_service.is_admin(message.from_user.id):
        await _show_menu(message, message.from_user.id, admin_service)


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
            f"Тикет #{ticket.id}\nСделка: #{deal.public_id} ({deal.id})\nСтатус: {ticket.status.value}\n"
            f"Открыл: {ticket.opened_by}\nПродавец: {deal.creator_id}\nПокупатель: {deal.buyer_id}\n"
            f"Сумма: {format_amount(deal.amount)} {currency_label(deal.currency)}\n\n{ticket.description}",
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
        await message.answer(f"Решение не применено: {exc}")
        return
    await state.clear()
    await message.answer(f"Решение принято. Сделка #{deal.public_id}: {deal.status.value}")


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
