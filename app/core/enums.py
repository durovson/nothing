from enum import StrEnum


class Language(StrEnum):
    RU = "ru"
    EN = "en"


class Currency(StrEnum):
    TON = "TON"
    USDT_TON = "USDT_TON"


class TonNetwork(StrEnum):
    MAINNET = "mainnet"
    TESTNET = "testnet"


class WalletVersion(StrEnum):
    V4R2 = "v4r2"
    V5R1 = "v5r1"


class DealType(StrEnum):
    GIFTS = "gifts"
    CHANNEL = "channel"
    ACCOUNT = "account"


class DealStatus(StrEnum):
    CREATING = "creating"
    PENDING = "pending"
    COLLECTING = "collecting"
    COLLECTION_SUBMITTED = "collection_submitted"
    COLLECTION_FAILED = "collection_failed"
    PAID = "paid"
    RELEASE_REQUESTED = "release_requested"
    PAYOUT_PROCESSING = "payout_processing"
    PAYOUT_SUBMITTED = "payout_submitted"
    PAYOUT_FAILED = "payout_failed"
    PAYOUT_BOUNCED = "payout_bounced"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CREATION_FAILED = "creation_failed"


class PayoutStatus(StrEnum):
    CREATING = "creating"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"


class CollectionStatus(StrEnum):
    CREATING = "creating"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"


class TraceStatus(StrEnum):
    NOT_FOUND = "not_found"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    BOUNCED = "bounced"
    FAILED = "failed"
