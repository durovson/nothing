from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher

from app.api.keepalive import RenderKeepAlive
from app.api.telegram_notifier import TelegramNotificationGateway
from app.bot import create_dispatcher
from app.config import Settings, get_settings
from app.database import SupabaseDatabase
from app.repositories import Repositories
from app.services import (
    DealService,
    PaymentService,
    PayoutService,
    ReferralService,
    Services,
    UserService,
    WalletService,
)
from app.tasks import DealMonitor
from app.ton import TonEscrowClient


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    bot: Bot
    dispatcher: Dispatcher
    database: SupabaseDatabase
    repositories: Repositories
    services: Services
    ton: TonEscrowClient
    monitor: DealMonitor
    keepalive: RenderKeepAlive


def build_container(settings: Settings | None = None) -> AppContainer:
    app_settings = settings or get_settings()
    bot = Bot(token=app_settings.TELEGRAM_BOT_TOKEN)
    database = SupabaseDatabase(app_settings)
    repositories = Repositories.build(database)
    ton = TonEscrowClient(app_settings)
    notifications = TelegramNotificationGateway(bot, app_settings.TON_NETWORK)

    users = UserService(repositories.users)
    wallets = WalletService(repositories.users, ton)
    referrals = ReferralService(app_settings, repositories.referrals)
    deals = DealService(app_settings, repositories.deals, ton)
    payouts = PayoutService(
        app_settings,
        repositories.deals,
        repositories.payouts,
        repositories.users,
        referrals,
        ton,
        notifications,
    )
    payments = PaymentService(
        app_settings,
        repositories.deals,
        repositories.users,
        ton,
        payouts,
        notifications,
    )
    services = Services(
        users=users,
        wallets=wallets,
        referrals=referrals,
        deals=deals,
        payments=payments,
        payouts=payouts,
    )
    dispatcher = create_dispatcher(app_settings, services)
    monitor = DealMonitor(app_settings, deals, payments, payouts)
    keepalive = RenderKeepAlive(app_settings)
    return AppContainer(
        settings=app_settings,
        bot=bot,
        dispatcher=dispatcher,
        database=database,
        repositories=repositories,
        services=services,
        ton=ton,
        monitor=monitor,
        keepalive=keepalive,
    )
