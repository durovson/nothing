from decimal import Decimal

from ton_core import to_nano

from app.core.constants import TON_DECIMAL_PLACES, USDT_DECIMALS, USDT_DECIMAL_PLACES
from app.core.enums import Currency


def payout_amount_atomic(amount: Decimal) -> int:
    atomic = to_nano(amount)
    if atomic <= 0:
        raise ValueError("Payout amount is too small")
    return atomic


def asset_quantum(currency: Currency) -> Decimal:
    return TON_DECIMAL_PLACES if currency is Currency.TON else USDT_DECIMAL_PLACES


def asset_amount_atomic(amount: Decimal, currency: Currency) -> int:
    if currency is Currency.TON:
        return payout_amount_atomic(amount)
    atomic = int((amount.quantize(USDT_DECIMAL_PLACES)) * (10**USDT_DECIMALS))
    if atomic <= 0:
        raise ValueError("Jetton amount is too small")
    return atomic


def asset_payment_amount(amount: Decimal, currency: Currency, fee_rate: Decimal, ton_reserve: Decimal) -> Decimal:
    reserve = ton_reserve if currency is Currency.TON else Decimal("0")
    return (amount * (Decimal("1") + fee_rate) + reserve).quantize(asset_quantum(currency))


def asset_payment_amount_atomic(amount: Decimal, currency: Currency, fee_rate: Decimal, ton_reserve: Decimal) -> int:
    return asset_amount_atomic(asset_payment_amount(amount, currency, fee_rate, ton_reserve), currency)


def asset_service_fee_atomic(amount: Decimal, currency: Currency, fee_rate: Decimal) -> int:
    return asset_amount_atomic((amount * fee_rate).quantize(asset_quantum(currency)), currency)
