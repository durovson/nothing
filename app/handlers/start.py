from aiogram import F, Router, types
from aiogram.filters import CommandObject, CommandStart

from app.config import Settings
from app.keyboards import MenuCallback, main_menu
from app.keyboards.callbacks import MenuAction
from app.locales import TextKey, translate
from app.models.entities import User
from app.services.deals import DealService
from app.services.referrals import ReferralService

router = Router(name="start")


@router.message(CommandStart(deep_link=True, magic=F.args))
async def start_with_args(
    message: types.Message,
    command: CommandObject,
    db_user: User,
    deal_service: DealService,
    referral_service: ReferralService,
    settings: Settings,
) -> None:
    argument = (command.args or "").strip()
    if argument.startswith("ref_"):
        try:
            referrer_id = int(argument.removeprefix("ref_"))
        except ValueError:
            referrer_id = 0
        await referral_service.assign_referrer(db_user.telegram_id, referrer_id)

    if len(argument) == 10 and argument.isalnum():
        deal = await deal_service.join_deal(argument, db_user.telegram_id)
        if not deal:
            await message.answer(
                translate(db_user.language, TextKey.DEAL_NOT_FOUND),
                reply_markup=main_menu(db_user.language),
            )
            return
        await message.answer(
            translate(
                db_user.language,
                TextKey.DEAL_JOINED,
                deal_id=deal.public_id,
                deal_type=deal.deal_type.value,
                description=deal.description,
                amount=deal_service.buyer_payment_amount(deal),
                currency=deal.currency.value,
                wallet_address=deal.wallet_address or "-",
            ),
            reply_markup=main_menu(db_user.language),
        )
        return

    await show_main_menu(message, db_user, settings)


@router.message(CommandStart())
async def command_start(message: types.Message, db_user: User, settings: Settings) -> None:
    await show_main_menu(message, db_user, settings)


@router.callback_query(MenuCallback.filter(F.action == MenuAction.BACK))
async def menu_back(
    callback: types.CallbackQuery,
    db_user: User,
    settings: Settings,
) -> None:
    if callback.message:
        await show_main_menu(callback.message, db_user, settings)
    await callback.answer()


async def show_main_menu(message: types.Message, user: User, settings: Settings) -> None:
    await message.answer(
        translate(
            user.language,
            TextKey.MAIN_MENU_CAPTION,
            support_username=settings.SUPPORT_USERNAME,
        ),
        reply_markup=main_menu(user.language),
    )

