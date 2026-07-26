from decimal import Decimal

from ton_core import to_nano

from app.core.constants import TON_DECIMAL_PLACES


def payment_amount(
    amount: Decimal,
    fee_rate: Decimal,
    network_fee_reserve: Decimal,
) -> Decimal:
    if not Decimal("0") <= fee_rate < Decimal("1"):
        raise ValueError("ESCROW_FEE_RATE must be in [0, 1)")
    if network_fee_reserve <= 0:
        raise ValueError("TON_PAYOUT_FEE_RESERVE must be positive")
    return (
        amount * (Decimal("1") + fee_rate) + network_fee_reserve
    ).quantize(TON_DECIMAL_PLACES)


def payment_amount_atomic(
    amount: Decimal,
    fee_rate: Decimal,
    network_fee_reserve: Decimal,
) -> int:
    return to_nano(payment_amount(amount, fee_rate, network_fee_reserve))


def payout_amount_atomic(amount: Decimal) -> int:
    atomic = to_nano(amount)
    if atomic <= 0:
        raise ValueError("Payout amount is too small")
    return atomic


def service_fee_amount_atomic(amount: Decimal, fee_rate: Decimal) -> int:
    fee_atomic = to_nano((amount * fee_rate).quantize(TON_DECIMAL_PLACES))
    if fee_atomic <= 0:
        raise ValueError("Service fee is too small")
    return fee_atomic
