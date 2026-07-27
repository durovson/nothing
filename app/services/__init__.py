from __future__ import annotations

from dataclasses import dataclass

from app.services.deals import DealService
from app.services.collections import CollectionService
from app.services.lifecycle import DealLifecycleService
from app.services.payments import PaymentService
from app.services.payouts import PayoutService
from app.services.referrals import ReferralService
from app.services.refunds import RefundService
from app.services.users import UserService
from app.services.wallets import WalletService
from app.services.admin import AdminService
from app.services.channels import ChannelDealService


@dataclass(frozen=True, slots=True)
class Services:
    users: UserService
    wallets: WalletService
    referrals: ReferralService
    deals: DealService
    payments: PaymentService
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
    "PaymentService",
    "PayoutService",
    "ReferralService",
    "RefundService",
    "Services",
    "UserService",
    "WalletService",
    "AdminService",
    "ChannelDealService",
]
