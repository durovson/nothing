from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


_AMOUNT_PATTERN = re.compile(
    r"(?<![\d.,])[-+]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?![\d.,])"
)


def parse_decimal_amount(value: str) -> Decimal:
    """Extract one positive decimal amount from user input.

    Asset labels around the amount are intentionally ignored. More than one
    number is rejected because choosing one silently could create a deal for a
    different amount than the user intended.
    """

    matches = _AMOUNT_PATTERN.findall(value.strip())
    if len(matches) != 1:
        raise InvalidOperation("exactly one amount is required")
    amount = Decimal(matches[0].replace(",", "."))
    if not amount.is_finite() or amount <= 0:
        raise InvalidOperation("amount must be finite and positive")
    return amount
