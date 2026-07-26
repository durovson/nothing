from dataclasses import dataclass
from datetime import datetime

from app.core.enums import Currency


@dataclass(frozen=True, slots=True)
class PayoutMessage:
    destination: str
    amount_atomic: int
    comment: str
    sweep_balance: bool = False
    currency: Currency = Currency.TON


@dataclass(frozen=True, slots=True)
class PreparedPayout:
    normalized_hash: str
    signed_boc: str
    valid_until: datetime
