from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.core.enums import (
    CollectionStatus,
    Currency,
    DealStatus,
    DealType,
    Language,
    PayoutStatus,
    RefundStatus,
    DisputeStatus,
    WalletVersion,
)


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
    wallet_version: WalletVersion
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
    payment_memo_missing: bool = False
    paid_at: datetime | None = None
    custody_confirmed_at: datetime | None = None
    delivery_deadline_at: datetime | None = None
    delivered_at: datetime | None = None
    inspection_deadline_at: datetime | None = None
    resolution: str | None = None
    resolution_reason: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CollectionAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: CollectionStatus
    destination: str
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


class PayoutAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: PayoutStatus
    destination: str
    amount_atomic: int
    comment: str
    reward_destination: str | None = None
    reward_nominal_amount_atomic: int | None = None
    reward_comment: str | None = None
    currency: Currency = Currency.TON
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RefundAttempt(BaseModel):
    id: int
    deal_id: int
    idempotency_key: str
    status: RefundStatus
    destination: str
    amount_atomic: int
    comment: str
    reason: str
    currency: Currency = Currency.TON
    reward_destination: str | None = None
    reward_nominal_amount_atomic: int | None = None
    reward_comment: str | None = None
    external_message_hash: str | None = None
    signed_boc: str | None = None
    valid_until: datetime | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_checked_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DisputeTicket(BaseModel):
    id: int
    deal_id: int
    opened_by: int
    status: DisputeStatus
    description: str
    resolution: str | None = None
    resolution_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BotSettings(BaseModel):
    id: int = 1
    maintenance_enabled: bool = False
    maintenance_message: str = "Технический перерыв. Попробуйте позже."
    updated_at: datetime | None = None
