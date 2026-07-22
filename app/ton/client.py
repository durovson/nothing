from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from time import time

from ton_core import (
    Address,
    ContractState,
    InternalMsgInfo,
    NetworkGlobalID,
    WalletV4Config,
    WalletV4Params,
    WorkchainID,
)
from tonutils.clients import TonapiClient
from tonutils.contracts import TONTransferBuilder, WalletV4R2
from tonutils.exceptions import ProviderResponseError

from app.config import Settings
from app.core.constants import MAX_PAYOUT_MESSAGES
from app.core.enums import Currency, TonNetwork, TraceStatus
from app.core.exceptions import InvalidWalletError, TonGatewayError
from app.models.dto import PaymentObservation
from app.models.entities import Deal
from app.ton.amounts import payment_amount_atomic
from app.ton.models import PayoutMessage, PreparedPayout
from app.ton.parsing import classify_trace, decode_text_comment, transaction_hash


def _network(value: TonNetwork) -> NetworkGlobalID:
    match value:
        case TonNetwork.MAINNET:
            return NetworkGlobalID.MAINNET
        case TonNetwork.TESTNET:
            return NetworkGlobalID.TESTNET


class TonEscrowClient:
    """TON infrastructure adapter based on tonutils WalletV4R2 and TonAPI."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = TonapiClient(
            network=_network(settings.TON_NETWORK),
            api_key=settings.TON_API_KEY or None,
            base_url=settings.TON_API_ENDPOINT.rstrip("/"),
            timeout=settings.TON_REQUEST_TIMEOUT_MS / 1_000,
        )
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def start(self) -> None:
        if not self._connected:
            await self._client.connect()
            self._connected = True

    async def close(self) -> None:
        if self._connected:
            await self._client.close()
            self._connected = False

    def normalize_address(self, raw_address: str) -> str:
        try:
            return Address(raw_address).to_str(
                is_bounceable=False,
                is_test_only=self._settings.TON_NETWORK is TonNetwork.TESTNET,
            )
        except Exception as exc:
            raise InvalidWalletError("Invalid TON address") from exc

    def _wallet(self, subwallet_id: int) -> WalletV4R2:
        if not 0 <= subwallet_id <= 0xFFFFFFFF:
            raise TonGatewayError(f"subwallet_id is outside uint32: {subwallet_id}")
        wallet, _, _, _ = WalletV4R2.from_mnemonic(
            self._client,
            self._settings.TON_MNEMONIC,
            workchain=WorkchainID(self._settings.TON_WORKCHAIN),
            config=WalletV4Config(subwallet_id=subwallet_id),
        )
        return wallet

    async def get_deal_address(self, subwallet_id: int) -> str:
        return self._wallet(subwallet_id).address.to_str(
            is_bounceable=False,
            is_test_only=self._settings.TON_NETWORK is TonNetwork.TESTNET,
        )

    async def find_incoming_payment(self, deal: Deal) -> PaymentObservation | None:
        if deal.currency is not Currency.TON:
            raise TonGatewayError("USDT_TON requires a jetton-specific payment monitor")

        wallet = self._wallet(deal.subwallet_id)
        expected_atomic = payment_amount_atomic(deal.amount, self._settings.ESCROW_FEE_RATE)
        created_timestamp = int(deal.created_at.timestamp()) if deal.created_at else 0
        transactions = await wallet.get_transactions(limit=self._settings.TON_TRANSACTION_SCAN_LIMIT)

        for transaction in transactions:
            if transaction.now < created_timestamp or getattr(transaction.description, "aborted", False):
                continue
            incoming = transaction.in_msg
            info = getattr(incoming, "info", None) if incoming else None
            if not isinstance(info, InternalMsgInfo) or info.bounced:
                continue
            memo = decode_text_comment(incoming.body)
            if memo != deal.public_id or info.value_coins != expected_atomic:
                continue
            sender = info.src.to_str(is_bounceable=False) if info.src else None
            return PaymentObservation(
                tx_hash=transaction_hash(transaction),
                tx_lt=transaction.lt,
                amount_atomic=info.value_coins,
                sender=sender,
                memo=memo,
                observed_at=datetime.fromtimestamp(transaction.now, tz=UTC),
            )
        return None

    async def prepare_batch_payout(
        self,
        subwallet_id: int,
        messages: Sequence[PayoutMessage],
    ) -> PreparedPayout:
        if not 1 <= len(messages) <= MAX_PAYOUT_MESSAGES:
            raise TonGatewayError("WalletV4R2 supports 1 to 4 outgoing messages per transfer")

        builders: list[TONTransferBuilder] = []
        for item in messages:
            destination = Address(item.destination)
            recipient = await self._client.get_info(destination)
            if recipient.state == ContractState.FROZEN:
                raise TonGatewayError(f"Recipient {item.destination} is frozen")
            builders.append(
                TONTransferBuilder(
                    destination=destination,
                    amount=item.amount_atomic,
                    body=item.comment,
                    bounce=recipient.state == ContractState.ACTIVE,
                )
            )

        valid_until_unix = int(time()) + self._settings.TON_TRANSFER_TTL_SECONDS
        external_message = await self._wallet(subwallet_id).build_external_message(
            builders,
            WalletV4Params(valid_until=valid_until_unix),
        )
        return PreparedPayout(
            normalized_hash=external_message.normalized_hash,
            signed_boc=external_message.as_hex,
            valid_until=datetime.fromtimestamp(valid_until_unix, tz=UTC),
        )

    async def broadcast(self, signed_boc: str) -> None:
        await self._client.send_message(signed_boc)

    async def get_trace_status(self, normalized_hash: str) -> TraceStatus:
        try:
            trace = await self._client.provider.send_http_request("GET", f"/traces/{normalized_hash}")
        except ProviderResponseError as exc:
            if exc.code == 404:
                return TraceStatus.NOT_FOUND
            raise
        if not isinstance(trace, dict):
            raise TonGatewayError("TonAPI returned an invalid trace payload")
        return classify_trace(trace)

