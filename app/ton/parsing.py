from collections.abc import Iterable
from typing import Any

from ton_core import TextCommentBody

from app.core.enums import TraceStatus


def transaction_hash(transaction: Any) -> str:
    raw_hash = transaction.cell.hash
    return raw_hash.hex() if isinstance(raw_hash, bytes) else str(raw_hash)


def decode_text_comment(body: Any) -> str | None:
    try:
        body_slice = body.begin_parse()
        if body_slice.remaining_bits < 32 or body_slice.preload_uint(32) != 0:
            return None
        return TextCommentBody.deserialize(body_slice).text
    except Exception:
        return None


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from walk_dicts(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_dicts(nested)


def classify_trace(trace: dict[str, Any]) -> TraceStatus:
    if trace.get("is_incomplete") is True:
        return TraceStatus.PENDING

    failed = False
    for item in walk_dicts(trace):
        if item.get("bounced") is True:
            return TraceStatus.BOUNCED
        if item.get("aborted") is True or item.get("success") is False:
            failed = True

    if failed:
        return TraceStatus.FAILED
    if trace.get("is_incomplete") is False:
        return TraceStatus.CONFIRMED
    root_transaction = trace.get("transaction")
    if (
        "is_incomplete" not in trace
        and isinstance(root_transaction, dict)
        and root_transaction.get("success") is True
        and trace.get("emulated") is not True
    ):
        return TraceStatus.CONFIRMED
    return TraceStatus.PENDING


def trace_contains_payout(
    trace: dict[str, Any],
    *,
    seller_destination: str,
    seller_amount_atomic: int,
    seller_comment: str,
    reward_destination: str | None,
    reward_comment: str | None,
) -> bool:
    messages: list[dict[str, Any]] = []
    for child in trace.get("children", []):
        if not isinstance(child, dict):
            continue
        transaction = child.get("transaction")
        if not isinstance(transaction, dict) or transaction.get("success") is not True:
            continue
        incoming = transaction.get("in_msg")
        if isinstance(incoming, dict):
            messages.append(incoming)

    def matches(
        message: dict[str, Any],
        destination: str,
        comment: str,
        amount: int | None,
    ) -> bool:
        target = message.get("destination")
        decoded_body = message.get("decoded_body")
        value = message.get("value")
        return (
            isinstance(target, dict)
            and target.get("address") == destination
            and isinstance(decoded_body, dict)
            and decoded_body.get("text") == comment
            and isinstance(value, int)
            and (value == amount if amount is not None else value > 0)
            and message.get("bounced") is not True
        )

    seller_found = any(
        matches(message, seller_destination, seller_comment, seller_amount_atomic)
        for message in messages
    )
    if not seller_found:
        return False
    if reward_destination is None or reward_comment is None:
        return True
    return any(
        matches(message, reward_destination, reward_comment, None)
        for message in messages
    )
