from __future__ import annotations

from dataclasses import dataclass

from app.services.deals import DealService
from app.services.payments import PaymentService
from app.services.payouts import PayoutService
from app.services.referrals import ReferralService
from app.services.users import UserService
from app.services.wallets import WalletService


@dataclass(frozen=True, slots=True)
class Services:
    users: UserService
    wallets: WalletService
    referrals: ReferralService
    deals: DealService
    payments: PaymentService
    payouts: PayoutService


__all__ = [
    "DealService",
    "PaymentService",
    "PayoutService",
    "ReferralService",
    "Services",
    "UserService",
    "WalletService",
]

