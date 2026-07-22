from aiogram import Bot, Dispatcher

from app.config import Settings
from app.handlers import create_router
from app.middleware import CurrentUserMiddleware
from app.services import Services


def create_dispatcher(settings: Settings, services: Services) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.update.middleware(
        CurrentUserMiddleware(services.users, settings.DEFAULT_LANGUAGE)
    )
    dispatcher["settings"] = settings
    dispatcher["user_service"] = services.users
    dispatcher["wallet_service"] = services.wallets
    dispatcher["referral_service"] = services.referrals
    dispatcher["deal_service"] = services.deals
    dispatcher["payment_service"] = services.payments
    dispatcher["payout_service"] = services.payouts
    dispatcher.include_router(create_router())
    return dispatcher


async def run_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    await dispatcher.start_polling(bot)

