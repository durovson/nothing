from typing import Any

from ton_core import Address, TextCommentBody

from app.core.constants import JETTON_TRANSFER_NOTIFICATION_OPCODE

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


def decode_jetton_notification(body: Any) -> tuple[int, str | None, str | None] | None:
    """Decode the TEP-74 transfer_notification body without trusting metadata."""
    try:
        source = body.begin_parse()
        if source.load_uint(32) != JETTON_TRANSFER_NOTIFICATION_OPCODE:
            return None
        source.load_uint(64)
        amount = source.load_coins()
        sender = source.load_address()
        payload = source.load_ref().begin_parse() if source.load_bit() else source
        memo = None
        if payload.remaining_bits >= 32 and payload.load_uint(32) == 0:
            memo = payload.load_snake_string()
        sender_text = sender.to_str(is_bounceable=False) if isinstance(sender, Address) else None
        return int(amount or 0), sender_text, memo
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


def _credited_without_bounce(
    transaction: dict[str, Any],
    incoming: dict[str, Any],
    value: int,
) -> bool:
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
    return (
        isinstance(credit_phase, dict)
        and credit_phase.get("credit") == value
        and transaction.get("bounce_phase") is None
        and (transaction.get("aborted") is False or uninitialized_credit)
        and incoming.get("bounced") is not True
    )
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
    received: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for child in trace.get("children", []):
        if not isinstance(child, dict):
            continue
        transaction = child.get("transaction")
        if not isinstance(transaction, dict) or transaction.get("success") is not True:
            continue
        incoming = transaction.get("in_msg")
        if isinstance(incoming, dict):
            received.append((transaction, incoming))

    def matches(
        transaction: dict[str, Any],
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
            and _credited_without_bounce(transaction, message, value)
        )

    seller_found = any(
        matches(transaction, message, seller_destination, seller_comment, seller_amount_atomic)
        for transaction, message in received
    )
    if not seller_found:
        return False
    if reward_destination is None or reward_comment is None:
        return True
    return any(
        matches(transaction, message, reward_destination, reward_comment, reward_amount_atomic)
        for transaction, message in received
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
        if (
            isinstance(target, dict)
            and _same_address(target.get("address"), destination)
            and isinstance(decoded_body, dict)
            and decoded_body.get("text") == comment
            and isinstance(value, int)
            and value > 0
            and _credited_without_bounce(transaction, incoming, value)
        ):
            return True
    return False


def trace_contains_jetton_notification(
    trace: dict[str, Any],
    *,
    destination: str,
    notification_source: str,
    amount_atomic: int,
    comment: str,
) -> bool:
    """Validate the final TEP-74 notification received by the owner wallet."""
    for transaction in _trace_transactions(trace):
        incoming = transaction.get("in_msg")
        if not isinstance(incoming, dict):
            continue
        incoming_value = incoming.get("value")
        transaction_ok = transaction.get("success") is True or (
            isinstance(incoming_value, int)
            and _credited_without_bounce(transaction, incoming, incoming_value)
        )
        if not transaction_ok:
            continue
        target = incoming.get("destination")
        source = incoming.get("source")
        decoded = incoming.get("decoded_body")
        if not (
            isinstance(target, dict)
            and _same_address(target.get("address"), destination)
            and isinstance(source, dict)
            and _same_address(source.get("address"), notification_source)
            and isinstance(decoded, dict)
        ):
            continue
        raw_amount = decoded.get("amount")
        try:
            parsed_amount = int(raw_amount)
        except (TypeError, ValueError):
            continue
        payload = decoded.get("forward_payload")
        payload_text = None
        if isinstance(payload, dict):
            payload_text = payload.get("value") or payload.get("text")
        if payload_text is None:
            payload_text = decoded.get("forward_payload_text") or decoded.get("text")
        opcode = incoming.get("op_code") or incoming.get("opcode")
        op_name = str(incoming.get("decoded_op_name") or "").lower()
        opcode_ok = opcode in (JETTON_TRANSFER_NOTIFICATION_OPCODE, hex(JETTON_TRANSFER_NOTIFICATION_OPCODE))
        if parsed_amount == amount_atomic and payload_text == comment and (
            opcode_ok or "jetton" in op_name and "notif" in op_name
        ):
            return True
    return False
