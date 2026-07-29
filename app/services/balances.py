from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.core.enums import Currency
from app.core.exceptions import InsufficientPayoutReserveError
from app.core.types import TonGatewayProtocol
from app.ton.amounts import payout_amount_atomic


@dataclass(frozen=True, slots=True)
class BalanceRequirement:
    asset_atomic: int
    ton_atomic: int


def operation_balance_requirement(
    settings: Settings,
    currency: Currency,
    transfer_amount_atomic: int,
) -> BalanceRequirement:
    """Return the complete balance requirement for one independently sent leg."""
    gas = payout_amount_atomic(settings.TON_GUARANT_PAYOUT_GAS_RESERVE)
    if currency is Currency.TON:
        return BalanceRequirement(asset_atomic=0, ton_atomic=transfer_amount_atomic + gas)
    attached_ton = payout_amount_atomic(settings.USDT_JETTON_TRANSFER_TON)
    return BalanceRequirement(
        asset_atomic=transfer_amount_atomic,
        ton_atomic=gas + attached_ton,
    )


class FinancialBalanceGuard:
    def __init__(self, settings: Settings, ton: TonGatewayProtocol):
        self._settings = settings
        self._ton = ton

    async def ensure_available(self, currency: Currency, amount_atomic: int) -> None:
        requirement = operation_balance_requirement(self._settings, currency, amount_atomic)
        if requirement.asset_atomic:
            asset_balance = await self._ton.get_guarant_asset_balance_atomic(currency)
            if asset_balance < requirement.asset_atomic:
                raise InsufficientPayoutReserveError(
                    f"Guarant {currency.value} balance is below the complete transfer requirement"
                )
        ton_balance = await self._ton.get_guarant_balance_atomic()
        if ton_balance < requirement.ton_atomic:
            raise InsufficientPayoutReserveError(
                "Guarant TON balance is below transfer plus gas requirement"
            )
