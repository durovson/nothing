from aiogram import F, Router, types
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext

from app.config import Settings
from app.core.exceptions import MissingLinkedWalletError
from app.keyboards import MenuCallback, main_menu, payment_keyboard
from app.keyboards.callbacks import MenuAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.deals import DealService
from app.services.referrals import ReferralService
from app.services.channels import ChannelAccessService
from app.utils import currency_label, deal_type_label, format_amount, render_menu

router = Router(name="start")


@router.message(CommandStart(deep_link=True, magic=F.args))
async def start_with_args(
    message: types.Message,
    command: CommandObject,
    db_user: User,
    deal_service: DealService,
    referral_service: ReferralService,
    settings: Settings,
    state: FSMContext,
    channel_service: ChannelAccessService,
) -> None:
    await state.clear()
    argument = (command.args or "").strip()
    if argument.startswith("ref_"):
        try:
            referrer_id = int(argument.removeprefix("ref_"))
        except ValueError:
            referrer_id = 0
        await referral_service.assign_referrer(db_user.telegram_id, referrer_id)

    if len(argument) == 10 and argument.isalnum():
        try:
            deal = await deal_service.join_deal(argument, db_user.telegram_id)
        except MissingLinkedWalletError:
            await message.answer(translate(db_user.language, TextKey.DEAL_BUYER_WALLET_REQUIRED))
            return
        if not deal:
            await message.answer(
                translate(db_user.language, TextKey.DEAL_NOT_FOUND),
                reply_markup=main_menu(db_user.language),
            )
            return
        try:
            channel_invite = await channel_service.buyer_join_link(deal)
        except Exception:
            channel_invite = None
        await message.answer(
            translate(
                db_user.language,
                TextKey.DEAL_JOINED,
                deal_id=deal.public_id,
                deal_type=deal_type_label(deal.deal_type, db_user.language),
                description=deal.description,
                amount=format_amount(deal_service.buyer_payment_amount(deal)),
                currency=currency_label(deal.currency),
                wallet_address=deal.wallet_address or "-",
            ),
            reply_markup=payment_keyboard(
                db_user.language,
                deal_service.tonkeeper_payment_link(deal),
                channel_invite,
            ),
        )
        await show_main_menu(message, db_user, settings)
        return

    await show_main_menu(message, db_user, settings)


@router.message(CommandStart())
async def command_start(
    message: types.Message, db_user: User, settings: Settings, state: FSMContext
) -> None:
    await state.clear()
    await show_main_menu(message, db_user, settings)


@router.callback_query(MenuCallback.filter(F.action == MenuAction.BACK))
async def menu_back(
    callback: types.CallbackQuery,
    db_user: User,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message:
        await show_main_menu(callback.message, db_user, settings)
    await callback.answer()


async def show_main_menu(message: types.Message, user: User, settings: Settings) -> None:
    await render_menu(
        message,
        translate(
            user.language,
            TextKey.MAIN_MENU_CAPTION,
            support_username=settings.SUPPORT_USERNAME,
        ),
        main_menu(user.language),
    )
