from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from time import time

from ton_core import (
    Address,
    ContractState,
    InternalMsgInfo,
    NetworkGlobalID,
    SendMode,
    WalletV4Config,
    WalletV4Params,
    WalletV5Config,
    WalletV5Params,
    WalletV5SubwalletID,
    WorkchainID,
)
from tonutils.clients import TonapiClient
from tonutils.contracts import TONTransferBuilder, WalletV4R2, WalletV5R1
from tonutils.exceptions import ProviderResponseError

from app.config import Settings
from app.core.constants import (
    WALLET_V4_MAX_PAYOUT_MESSAGES,
    WALLET_V5_MAX_PAYOUT_MESSAGES,
    WALLET_V5_MAX_SUBWALLET_NUMBER,
)
from app.core.enums import Currency, TonNetwork, TraceStatus, WalletVersion
from app.core.exceptions import InvalidWalletError, TonGatewayError
from app.models.dto import PaymentObservation
from app.models.entities import CollectionAttempt, Deal, PayoutAttempt
from app.ton.amounts import payment_amount_atomic
from app.ton.models import PayoutMessage, PreparedPayout
from app.ton.parsing import (
    classify_trace,
    decode_text_comment,
    trace_contains_payout,
    trace_contains_transfer,
    transaction_hash,
)

logger = logging.getLogger(__name__)


def _network(value: TonNetwork) -> NetworkGlobalID:
    match value:
        case TonNetwork.MAINNET:
            return NetworkGlobalID.MAINNET
        case TonNetwork.TESTNET:
            return NetworkGlobalID.TESTNET


def _credited_amount_atomic(description: object) -> int | None:
    """Return the TON amount retained by the account during the credit phase."""
    credit_phase = getattr(description, "credit_ph", None)
    credit = getattr(credit_phase, "credit", None)
    grams = getattr(credit, "grams", None)
    return grams if isinstance(grams, int) else None


class TonEscrowClient:
    """TON adapter supporting legacy Wallet V4R2 and new Wallet V5R1 deals."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = TonapiClient(
            network=_network(settings.TON_NETWORK),
            api_key=settings.TON_API_KEY or None,
            base_url=settings.TON_API_ENDPOINT.rstrip("/"),
            timeout=settings.TON_REQUEST_TIMEOUT_MS / 1_000,
        )
        self._guarant_wallet = self._v5_wallet(0)
        self._validate_guarant_address()
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

    @property
    def guarant_address(self) -> str:
        return self._guarant_wallet.address.to_str(
            is_bounceable=False,
            is_test_only=self._settings.TON_NETWORK is TonNetwork.TESTNET,
        )

    def _validate_guarant_address(self) -> None:
        try:
            expected = Address(self._settings.TON_GUARANT_ADDRESS).to_str(
                is_user_friendly=False
            )
        except Exception as exc:
            raise TonGatewayError("TON_GUARANT_ADDRESS is not a valid TON address") from exc
        actual = self._guarant_wallet.address.to_str(is_user_friendly=False)
        if expected != actual:
            raise TonGatewayError(
                "TON_GUARANT_ADDRESS does not match TON_MNEMONIC, TON_NETWORK, "
                "TON_WORKCHAIN and Wallet V5R1 subwallet number 0"
            )

    def _v5_wallet(self, subwallet_number: int) -> WalletV5R1:
        workchain = WorkchainID(self._settings.TON_WORKCHAIN)
        wallet, _, _, _ = WalletV5R1.from_mnemonic(
            self._client,
            self._settings.TON_MNEMONIC,
            workchain=workchain,
            config=WalletV5Config(
                subwallet_id=WalletV5SubwalletID(
                    subwallet_number=subwallet_number,
                    workchain=workchain,
                    version=0,
                    network=_network(self._settings.TON_NETWORK),
                )
            ),
        )
        return wallet

    def _wallet(self, deal: Deal) -> WalletV4R2 | WalletV5R1:
        workchain = WorkchainID(self._settings.TON_WORKCHAIN)
        match deal.wallet_version:
            case WalletVersion.V4R2:
                if not 0 <= deal.subwallet_id <= 0xFFFFFFFF:
                    raise TonGatewayError(
                        f"Wallet V4R2 subwallet_id is outside uint32: {deal.subwallet_id}"
                    )
                wallet, _, _, _ = WalletV4R2.from_mnemonic(
                    self._client,
                    self._settings.TON_MNEMONIC,
                    workchain=workchain,
                    config=WalletV4Config(subwallet_id=deal.subwallet_id),
                )
                return wallet
            case WalletVersion.V5R1:
                if not 0 <= deal.subwallet_id <= WALLET_V5_MAX_SUBWALLET_NUMBER:
                    raise TonGatewayError(
                        "Wallet V5R1 subwallet number is outside uint15: "
                        f"{deal.subwallet_id}"
                    )
                return self._v5_wallet(deal.subwallet_id)

    async def get_deal_address(self, deal: Deal) -> str:
        return self._wallet(deal).address.to_str(
            is_bounceable=False,
            is_test_only=self._settings.TON_NETWORK is TonNetwork.TESTNET,
        )

    async def find_incoming_payment(self, deal: Deal) -> PaymentObservation | None:
        if deal.currency is not Currency.TON:
            raise TonGatewayError("USDT_TON requires a jetton-specific payment monitor")

        wallet = self._wallet(deal)
        expected_atomic = payment_amount_atomic(
            deal.amount,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )
        created_timestamp = int(deal.created_at.timestamp()) if deal.created_at else 0
        transactions = await wallet.get_transactions(limit=self._settings.TON_TRANSACTION_SCAN_LIMIT)

        for transaction in transactions:
            if transaction.now < created_timestamp:
                continue
            incoming = transaction.in_msg
            info = getattr(incoming, "info", None) if incoming else None
            if not isinstance(info, InternalMsgInfo) or info.bounced:
                continue

            description = transaction.description
            credited_atomic = _credited_amount_atomic(description)
            if (
                credited_atomic != expected_atomic
                or getattr(description, "bounce", None) is not None
                or getattr(description, "destroyed", False)
            ):
                continue

            memo = decode_text_comment(incoming.body)
            if memo != deal.public_id or info.value_coins != expected_atomic:
                continue

            tx_hash = transaction_hash(transaction)
            logger.info(
                "Matched TON payment deal=%s tx=%s amount_atomic=%s account_aborted=%s",
                deal.public_id,
                tx_hash,
                credited_atomic,
                getattr(description, "aborted", False),
            )
            sender = info.src.to_str(is_bounceable=False) if info.src else None
            return PaymentObservation(
                tx_hash=tx_hash,
                tx_lt=transaction.lt,
                amount_atomic=info.value_coins,
                sender=sender,
                memo=memo,
                observed_at=datetime.fromtimestamp(transaction.now, tz=UTC),
            )
        return None

    async def prepare_batch_payout(
        self,
        deal: Deal,
        messages: Sequence[PayoutMessage],
    ) -> PreparedPayout:
        max_messages = (
            WALLET_V5_MAX_PAYOUT_MESSAGES
            if deal.wallet_version is WalletVersion.V5R1
            else WALLET_V4_MAX_PAYOUT_MESSAGES
        )
        if not 1 <= len(messages) <= max_messages:
            raise TonGatewayError(
                f"{deal.wallet_version.value} supports 1 to {max_messages} outgoing messages"
            )
        sweep_positions = [
            index for index, message in enumerate(messages) if message.sweep_balance
        ]
        if sweep_positions and sweep_positions != [len(messages) - 1]:
            raise TonGatewayError("Balance sweep must be the final and only sweep message")

        builders: list[TONTransferBuilder] = []
        for item in messages:
            destination = Address(item.destination)
            recipient = await self._client.get_info(destination)
            if recipient.state == ContractState.FROZEN:
                raise TonGatewayError(f"Recipient {item.destination} is frozen")
            if item.sweep_balance:
                send_mode = int(SendMode.CARRY_ALL_REMAINING_BALANCE)
                amount_atomic = 0
            else:
                send_mode = int(SendMode.PAY_GAS_SEPARATELY)
                amount_atomic = item.amount_atomic
            if deal.wallet_version is WalletVersion.V5R1:
                send_mode |= int(SendMode.IGNORE_ERRORS)
            builders.append(
                TONTransferBuilder(
                    destination=destination,
                    amount=amount_atomic,
                    body=item.comment,
                    send_mode=send_mode,
                    bounce=recipient.state == ContractState.ACTIVE,
                )
            )

        valid_until_unix = int(time()) + self._settings.TON_TRANSFER_TTL_SECONDS
        wallet = self._wallet(deal)
        params = (
            WalletV5Params(valid_until=valid_until_unix)
            if deal.wallet_version is WalletVersion.V5R1
            else WalletV4Params(valid_until=valid_until_unix)
        )
        external_message = await wallet.build_external_message(builders, params)
        return PreparedPayout(
            normalized_hash=external_message.normalized_hash,
            signed_boc=external_message.as_hex,
            valid_until=datetime.fromtimestamp(valid_until_unix, tz=UTC),
        )

    async def prepare_collection(self, deal: Deal, comment: str) -> PreparedPayout:
        return await self.prepare_batch_payout(
            deal,
            [
                PayoutMessage(
                    destination=self.guarant_address,
                    amount_atomic=0,
                    comment=comment,
                    sweep_balance=True,
                )
            ],
        )

    async def prepare_guarant_payout(
        self,
        messages: Sequence[PayoutMessage],
    ) -> PreparedPayout:
        if not messages or any(message.sweep_balance for message in messages):
            raise TonGatewayError("Guarant payout requires explicit non-sweep amounts")
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
                    send_mode=int(SendMode.PAY_GAS_SEPARATELY | SendMode.IGNORE_ERRORS),
                    bounce=recipient.state == ContractState.ACTIVE,
                )
            )
        valid_until_unix = int(time()) + self._settings.TON_TRANSFER_TTL_SECONDS
        external_message = await self._guarant_wallet.build_external_message(
            builders,
            WalletV5Params(valid_until=valid_until_unix),
        )
        return PreparedPayout(
            normalized_hash=external_message.normalized_hash,
            signed_boc=external_message.as_hex,
            valid_until=datetime.fromtimestamp(valid_until_unix, tz=UTC),
        )

    async def get_guarant_balance_atomic(self) -> int:
        info = await self._client.get_info(self._guarant_wallet.address)
        return int(info.balance)

    async def broadcast(self, signed_boc: str) -> None:
        await self._client.send_message(signed_boc)

    async def get_payout_trace_status(self, attempt: PayoutAttempt) -> TraceStatus:
        if not attempt.external_message_hash:
            raise TonGatewayError("Payout attempt has no external message hash")
        try:
            trace = await self._client.provider.send_http_request(
                "GET",
                f"/traces/{attempt.external_message_hash}",
            )
        except ProviderResponseError as exc:
            if exc.code == 404:
                return TraceStatus.NOT_FOUND
            raise
        if not isinstance(trace, dict):
            raise TonGatewayError("TonAPI returned an invalid trace payload")
        status = classify_trace(trace)
        if status is not TraceStatus.CONFIRMED:
            return status

        seller_destination = Address(attempt.destination).to_str(is_user_friendly=False)
        reward_destination = (
            Address(attempt.reward_destination).to_str(is_user_friendly=False)
            if attempt.reward_destination
            else None
        )
        if not trace_contains_payout(
            trace,
            seller_destination=seller_destination,
            seller_amount_atomic=attempt.amount_atomic,
            seller_comment=attempt.comment,
            reward_destination=reward_destination,
            reward_amount_atomic=attempt.reward_nominal_amount_atomic,
            reward_comment=attempt.reward_comment,
        ):
            logger.error(
                "Confirmed trace does not contain the complete payout batch attempt=%s",
                attempt.id,
            )
            return TraceStatus.FAILED
        return TraceStatus.CONFIRMED

    async def get_collection_trace_status(
        self,
        attempt: CollectionAttempt,
    ) -> TraceStatus:
        if not attempt.external_message_hash:
            raise TonGatewayError("Collection attempt has no external message hash")
        try:
            trace = await self._client.provider.send_http_request(
                "GET",
                f"/traces/{attempt.external_message_hash}",
            )
        except ProviderResponseError as exc:
            if exc.code == 404:
                return TraceStatus.NOT_FOUND
            raise
        if not isinstance(trace, dict):
            raise TonGatewayError("TonAPI returned an invalid collection trace")
        if trace.get("is_incomplete") is True:
            return TraceStatus.PENDING
        destination = Address(attempt.destination).to_str(is_user_friendly=False)
        if trace_contains_transfer(
            trace,
            destination=destination,
            comment=attempt.comment,
        ):
            return TraceStatus.CONFIRMED
        status = classify_trace(trace)
        return TraceStatus.FAILED if status is TraceStatus.CONFIRMED else status
