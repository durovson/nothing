import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.utils.backoff import BackoffConfig

from app.config import Settings
from app.core.constants import (
    TELEGRAM_POLLING_BACKOFF_FACTOR,
    TELEGRAM_POLLING_BACKOFF_JITTER,
    TELEGRAM_POLLING_MAX_BACKOFF_SECONDS,
    TELEGRAM_POLLING_MIN_BACKOFF_SECONDS,
    TELEGRAM_POLLING_TIMEOUT_SECONDS,
)
from app.handlers import create_router
from app.middleware import (
    CurrentUserMiddleware,
    FastCallbackMiddleware,
    MaintenanceMiddleware,
    PerformanceMiddleware,
)
from app.services import Services

logger = logging.getLogger(__name__)

POLLING_BACKOFF_CONFIG = BackoffConfig(
    min_delay=TELEGRAM_POLLING_MIN_BACKOFF_SECONDS,
    max_delay=TELEGRAM_POLLING_MAX_BACKOFF_SECONDS,
    factor=TELEGRAM_POLLING_BACKOFF_FACTOR,
    jitter=TELEGRAM_POLLING_BACKOFF_JITTER,
)


def create_dispatcher(settings: Settings, services: Services) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.update.outer_middleware(PerformanceMiddleware())
    dispatcher.update.outer_middleware(FastCallbackMiddleware())
    dispatcher.update.outer_middleware(MaintenanceMiddleware(services.admin))
    dispatcher.update.middleware(
        CurrentUserMiddleware(services.users, settings.DEFAULT_LANGUAGE)
    )
    dispatcher["settings"] = settings
    dispatcher["user_service"] = services.users
    dispatcher["wallet_service"] = services.wallets
    dispatcher["referral_service"] = services.referrals
    dispatcher["deal_service"] = services.deals
    dispatcher["payout_service"] = services.payouts
    dispatcher["lifecycle_service"] = services.lifecycle
    dispatcher["admin_service"] = services.admin
    dispatcher["channel_service"] = services.channels
    dispatcher["desk_service"] = services.desk
    dispatcher.include_router(create_router())
    return dispatcher


async def run_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    while True:
        try:
            await dispatcher.start_polling(
                bot,
                handle_signals=False,
                close_bot_session=False,
                polling_timeout=TELEGRAM_POLLING_TIMEOUT_SECONDS,
                backoff_config=POLLING_BACKOFF_CONFIG,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram polling stopped with an error; restarting")
        else:
            logger.error("Telegram polling stopped unexpectedly; restarting")
        await asyncio.sleep(5)
