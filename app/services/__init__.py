from __future__ import annotations

from dataclasses import dataclass

from app.services.deals import DealService
from app.services.collections import CollectionService
from app.services.lifecycle import DealLifecycleService
from app.services.payouts import PayoutService
from app.services.referrals import ReferralService
from app.services.refunds import RefundService
from app.services.users import UserService
from app.services.wallets import WalletService
from app.services.admin import AdminService
from app.services.channels import ChannelDealService
from app.services.financial_processor import FinancialOperationProcessor
from app.services.usdt_indexer import UsdtDepositIndexer
from app.services.ton_indexer import TonDepositIndexer


@dataclass(frozen=True, slots=True)
class Services:
    users: UserService
    wallets: WalletService
    referrals: ReferralService
    deals: DealService
    payouts: PayoutService
    collections: CollectionService
    lifecycle: DealLifecycleService
    refunds: RefundService
    admin: AdminService
    channels: ChannelDealService


__all__ = [
    "DealService",
    "CollectionService",
    "DealLifecycleService",
    "PayoutService",
    "ReferralService",
    "RefundService",
    "Services",
    "UserService",
    "WalletService",
    "AdminService",
    "ChannelDealService",
    "FinancialOperationProcessor",
    "UsdtDepositIndexer",
    "TonDepositIndexer",
]
