from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PayoutMessage:
    destination: str
    amount_atomic: int
    comment: str


@dataclass(frozen=True, slots=True)
class PreparedPayout:
    normalized_hash: str
    signed_boc: str
    valid_until: datetime

