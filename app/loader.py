from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.api.keepalive import RenderKeepAlive
from app.api.telegram_notifier import TelegramNotificationGateway
from app.api.channel_gateway import TelegramChannelGateway
from app.bot import create_dispatcher
from app.config import Settings, get_settings
from app.database import SupabaseDatabase
from app.repositories import Repositories
from app.services import (
    CollectionService,
    DealService,
    DealLifecycleService,
    PaymentService,
    PayoutService,
    ReferralService,
    RefundService,
    Services,
    UserService,
    WalletService,
    AdminService,
    ChannelDealService,
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
    bot = Bot(
        token=app_settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
    database = SupabaseDatabase(app_settings)
    repositories = Repositories.build(database)
    ton = TonEscrowClient(app_settings)
    notifications = TelegramNotificationGateway(bot, app_settings.TON_NETWORK)
    channel_gateway = TelegramChannelGateway(bot)

    users = UserService(repositories.users)
    wallets = WalletService(repositories.users, ton)
    referrals = ReferralService(app_settings, repositories.referrals, ton)
    channels = ChannelDealService(repositories.deals, repositories.users, channel_gateway)
    deals = DealService(app_settings, repositories.deals, repositories.users, ton)
    payouts = PayoutService(
        app_settings,
        repositories.deals,
        repositories.payouts,
        repositories.refunds,
        repositories.users,
        referrals,
        ton,
        notifications,
    )
    collections = CollectionService(
        app_settings,
        repositories.deals,
        repositories.collections,
        repositories.users,
        ton,
        notifications,
        channels,
    )
    lifecycle = DealLifecycleService(
        repositories.deals,
        repositories.disputes,
        repositories.users,
        notifications,
    )
    refunds = RefundService(
        app_settings,
        repositories.deals,
        repositories.refunds,
        repositories.payouts,
        repositories.users,
        ton,
        notifications,
    )
    payments = PaymentService(
        app_settings,
        repositories.deals,
        ton,
        collections,
    )
    admin = AdminService(app_settings, repositories.admin, repositories.deals, repositories.users)
    services = Services(
        users=users,
        wallets=wallets,
        referrals=referrals,
        deals=deals,
        payments=payments,
        payouts=payouts,
        collections=collections,
        lifecycle=lifecycle,
        refunds=refunds,
        admin=admin,
        channels=channels,
    )
    dispatcher = create_dispatcher(app_settings, services)
    monitor = DealMonitor(
        app_settings,
        deals,
        payments,
        collections,
        lifecycle,
        refunds,
        payouts,
        referrals,
        channels,
    )
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
