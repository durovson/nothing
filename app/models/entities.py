from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.core.enums import Currency, DealStatus, DealType, Language, PayoutStatus


class User(BaseModel):
    telegram_id: int
    username: str | None = None
    wallet_address: str | None = None
    language: Language = Language.RU
    referrer_id: int | None = None
    created_at: datetime | None = None


class Deal(BaseModel):
    id: int
    public_id: str
    subwallet_id: int
    creator_id: int
    buyer_id: int | None = None
    deal_type: DealType
    description: str
    currency: Currency
    amount: Decimal
    status: DealStatus
    wallet_address: str | None = None
    paid_tx_hash: str | None = None
    paid_tx_lt: int | None = None
    paid_amount_atomic: int | None = None
    payment_sender: str | None = None
    paid_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PayoutAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: PayoutStatus
    destination: str
    amount_atomic: int
    comment: str
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

