from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
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
    PayoutService,
    ReferralService,
    RefundService,
    Services,
    UserService,
    WalletService,
    AdminService,
    ChannelDealService,
    UsdtDepositIndexer,
    TonDepositIndexer,
)
from app.tasks import DealMonitor
from app.ton import TonEscrowClient
from app.core.enums import FinancialOperationFlow
from app.core.constants import TELEGRAM_REQUEST_TIMEOUT_SECONDS
from app.services.financial_processor import FinancialOperationProcessor
from app.services.health import HealthService
from app.services.system_mode import SystemModeService


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
    notifications: TelegramNotificationGateway
    health: HealthService


def build_container(settings: Settings | None = None) -> AppContainer:
    app_settings = settings or get_settings()
    bot = Bot(
        token=app_settings.TELEGRAM_BOT_TOKEN,
        session=AiohttpSession(timeout=TELEGRAM_REQUEST_TIMEOUT_SECONDS),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
    database = SupabaseDatabase(app_settings)
    repositories = Repositories.build(database)
    ton = TonEscrowClient(app_settings)
    notifications = TelegramNotificationGateway(bot, app_settings)
    channel_gateway = TelegramChannelGateway(bot)

    system_mode = SystemModeService(
        app_settings, repositories.system, database, ton
    )
    users = UserService(repositories.users)
    wallets = WalletService(repositories.users, ton)
    referrals = ReferralService(
        app_settings,
        repositories.referrals,
        repositories.financial_operations,
        ton,
        system_mode,
    )
    channels = ChannelDealService(repositories.deals, repositories.users, channel_gateway)
    deals = DealService(
        app_settings, repositories.deals, repositories.users, ton, system_mode
    )
    payouts = PayoutService(
        app_settings,
        repositories.deals,
        repositories.financial_operations,
        repositories.users,
        referrals,
        ton,
        notifications,
        system_mode,
    )
    collections = CollectionService(
        app_settings,
        repositories.deals,
        repositories.financial_operations,
        repositories.users,
        notifications,
        channels,
        ton.guarant_address,
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
        repositories.financial_operations,
        repositories.users,
        ton,
        notifications,
    )
    usdt_indexer = UsdtDepositIndexer(
        app_settings,
        repositories.deposits,
        repositories.deals,
        ton,
        collections,
        system_mode,
    )
    ton_indexer = TonDepositIndexer(
        app_settings,
        repositories.deposits,
        repositories.deals,
        ton,
        collections,
        system_mode,
    )
    collection_processor = FinancialOperationProcessor(
        app_settings,
        FinancialOperationFlow.COLLECTION,
        repositories.financial_operations,
        ton,
        on_confirmed=collections.on_operation_confirmed,
        deals=repositories.deals,
        system_mode=system_mode,
    )
    payout_processor = FinancialOperationProcessor(
        app_settings,
        FinancialOperationFlow.PAYOUT,
        repositories.financial_operations,
        ton,
        payouts.on_operation_confirmed,
        system_mode=system_mode,
    )
    refund_processor = FinancialOperationProcessor(
        app_settings,
        FinancialOperationFlow.REFUND,
        repositories.financial_operations,
        ton,
        refunds.on_operation_confirmed,
        system_mode=system_mode,
    )
    referral_processor = FinancialOperationProcessor(
        app_settings,
        FinancialOperationFlow.REFERRAL,
        repositories.financial_operations,
        ton,
        system_mode=system_mode,
    )
    unmatched_refund_processor = FinancialOperationProcessor(
        app_settings,
        FinancialOperationFlow.UNMATCHED_REFUND,
        repositories.financial_operations,
        ton,
        system_mode=system_mode,
    )
    admin = AdminService(
        app_settings,
        repositories.admin,
        repositories.deals,
        repositories.users,
        repositories.financial_operations,
        repositories.deposits,
        system_mode,
    )
    services = Services(
        users=users,
        wallets=wallets,
        referrals=referrals,
        deals=deals,
        payouts=payouts,
        collections=collections,
        lifecycle=lifecycle,
        refunds=refunds,
        admin=admin,
        channels=channels,
    )
    dispatcher = create_dispatcher(app_settings, services)
    dispatcher["notification_gateway"] = notifications
    monitor = DealMonitor(
        app_settings,
        deals,
        lifecycle,
        refunds,
        payouts,
        channels,
        ton_indexer,
        usdt_indexer,
        collection_processor,
        refund_processor,
        payout_processor,
        referral_processor,
        unmatched_refund_processor,
        system_mode,
    )
    keepalive = RenderKeepAlive(app_settings)
    health = HealthService(database, ton, bot, monitor)
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
        notifications=notifications,
        health=health,
    )
