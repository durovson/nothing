from decimal import Decimal

from ton_core import to_nano

from app.core.constants import TON_DECIMAL_PLACES


def payment_amount(amount: Decimal, fee_rate: Decimal) -> Decimal:
    if not Decimal("0") <= fee_rate < Decimal("1"):
        raise ValueError("ESCROW_FEE_RATE must be in [0, 1)")
    return (amount * (Decimal("1") + fee_rate)).quantize(TON_DECIMAL_PLACES)


def payment_amount_atomic(amount: Decimal, fee_rate: Decimal) -> int:
    return to_nano(payment_amount(amount, fee_rate))


def payout_amount_atomic(amount: Decimal) -> int:
    atomic = to_nano(amount)
    if atomic <= 0:
        raise ValueError("Payout amount is too small")
    return atomic

