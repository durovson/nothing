from typing import Any

from ton_core import Address, TextCommentBody

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


def _trace_transactions(trace: dict[str, Any]):
    transaction = trace.get("transaction")
    if isinstance(transaction, dict):
        yield transaction
    for child in trace.get("children", []):
        if isinstance(child, dict):
            yield from _trace_transactions(child)


def _same_address(left: object, right: str) -> bool:
    if not isinstance(left, str):
        return False
    try:
        return Address(left) == Address(right)
    except Exception:
        return False


def classify_trace(trace: dict[str, Any]) -> TraceStatus:
    if trace.get("is_incomplete") is True:
        return TraceStatus.PENDING

    failed = False
    for transaction in _trace_transactions(trace):
        incoming = transaction.get("in_msg")
        if isinstance(incoming, dict) and incoming.get("bounced") is True:
            return TraceStatus.BOUNCED
        if transaction.get("aborted") is True or transaction.get("success") is False:
            failed = True
        compute_phase = transaction.get("compute_phase")
        if isinstance(compute_phase, dict) and (
            compute_phase.get("success") is False
            or compute_phase.get("exit_code") not in (None, 0)
        ):
            failed = True
        action_phase = transaction.get("action_phase")
        if isinstance(action_phase, dict) and (
            action_phase.get("success") is False
            or action_phase.get("result_code") not in (None, 0)
            or int(action_phase.get("skipped_actions") or 0) > 0
        ):
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
    reward_amount_atomic: int | None,
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
            and _same_address(target.get("address"), destination)
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
        matches(message, reward_destination, reward_comment, reward_amount_atomic)
        for message in messages
    )


def trace_contains_transfer(
    trace: dict[str, Any],
    *,
    destination: str,
    comment: str,
) -> bool:
    for child in trace.get("children", []):
        if not isinstance(child, dict):
            continue
        transaction = child.get("transaction")
        if not isinstance(transaction, dict) or transaction.get("success") is not True:
            continue
        incoming = transaction.get("in_msg")
        if not isinstance(incoming, dict):
            continue
        target = incoming.get("destination")
        decoded_body = incoming.get("decoded_body")
        value = incoming.get("value")
        credit_phase = transaction.get("credit_phase")
        compute_phase = transaction.get("compute_phase")
        uninitialized_credit = (
            transaction.get("aborted") is True
            and transaction.get("orig_status") == "uninit"
            and transaction.get("end_status") == "uninit"
            and isinstance(compute_phase, dict)
            and compute_phase.get("skipped") is True
            and compute_phase.get("skip_reason") == "cskip_no_state"
        )
        if (
            isinstance(target, dict)
            and _same_address(target.get("address"), destination)
            and isinstance(decoded_body, dict)
            and decoded_body.get("text") == comment
            and isinstance(value, int)
            and value > 0
            and isinstance(credit_phase, dict)
            and credit_phase.get("credit") == value
            and transaction.get("bounce_phase") is None
            and (transaction.get("aborted") is False or uninitialized_credit)
            and incoming.get("bounced") is not True
        ):
            return True
    return False
