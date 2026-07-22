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
    return TraceStatus.PENDING

