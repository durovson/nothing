from decimal import Decimal

from app.config import Settings
from app.core.enums import Currency, DealStatus, DealType, WalletVersion
from app.models.entities import Deal


def settings() -> Settings:
    return Settings.model_construct(
        ESCROW_FEE_RATE=Decimal("0.01"),
        TON_PAYOUT_FEE_RESERVE=Decimal("0.01"),
        TON_GUARANT_PAYOUT_GAS_RESERVE=Decimal("0.003"),
        USDT_JETTON_TRANSFER_TON=Decimal("0.05"),
        TON_TRACE_GRACE_SECONDS=120,
        SERVICE_FEE_WALLET="service-wallet",
        SERVICE_FEE_COMMENT="Service fee",
    )


def deal(**changes: object) -> Deal:
    values: dict[str, object] = {
        "id": 1,
        "public_id": "abc123def0",
        "subwallet_id": 1,
        "wallet_version": WalletVersion.V5R1,
        "creator_id": 100,
        "buyer_id": 200,
        "seller_wallet_address": "seller-snapshot",
        "buyer_wallet_address": "buyer-old",
        "buyer_wallet_snapshot": "buyer-snapshot",
        "deal_type": DealType.OFFER,
        "description": "service",
        "currency": Currency.TON,
        "amount": Decimal("100"),
        "status": DealStatus.RELEASE_REQUESTED,
        "wallet_address": "escrow-wallet",
    }
    values.update(changes)
    return Deal(**values)
