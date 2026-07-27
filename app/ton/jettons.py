from datetime import UTC, datetime

from ton_core import Address, InternalMsgInfo, SendMode
from tonutils.contracts import (
    JettonMasterStablecoin,
    JettonTransferBuilder,
    JettonWalletStablecoin,
    WalletV5R1,
)

from app.config import Settings
from app.core.enums import TonNetwork
from app.core.exceptions import TonGatewayError
from app.models.dto import PaymentObservation
from app.models.entities import Deal, PayoutAttempt, RefundAttempt
from app.ton.amounts import asset_payment_amount_atomic, payout_amount_atomic
from app.ton.models import PayoutMessage
from app.ton.parsing import (
    decode_jetton_notification,
    trace_contains_jetton_notification,
    transaction_hash,
)


class JettonEscrowGateway:
    """TEP-74 operations for the single allowlisted official USDT master."""

    def __init__(self, client: object, settings: Settings, guarant_wallet: WalletV5R1):
        self._client = client
        self._settings = settings
        self._guarant_wallet = guarant_wallet
        self._master: JettonMasterStablecoin | None = None
        self._guarant_jetton_wallet: Address | None = None

    async def start(self) -> None:
        self._ensure_mainnet()
        if self._master is not None:
            return
        self._master = await JettonMasterStablecoin.from_address(
            self._client, self._settings.USDT_MASTER_ADDRESS
        )
        self._guarant_jetton_wallet = await self._master.get_wallet_address(
            self._guarant_wallet.address
        )

    async def find_incoming_payment(self, deal: Deal) -> PaymentObservation | None:
        await self.start()
        assert self._guarant_jetton_wallet is not None
        expected_atomic = asset_payment_amount_atomic(
            deal.amount,
            deal.currency,
            self._settings.ESCROW_FEE_RATE,
            self._settings.TON_PAYOUT_FEE_RESERVE,
        )
        created_timestamp = int(deal.created_at.timestamp()) if deal.created_at else 0
        transactions = await self._guarant_wallet.get_transactions(
            limit=self._settings.TON_TRANSACTION_SCAN_LIMIT
        )
        expected_source = self._guarant_jetton_wallet.to_str(is_user_friendly=False)
        for transaction in transactions:
            if transaction.now < created_timestamp:
                continue
            incoming = transaction.in_msg
            info = getattr(incoming, "info", None) if incoming else None
            if not isinstance(info, InternalMsgInfo) or info.bounced or not info.src:
                continue
            if info.src.to_str(is_user_friendly=False) != expected_source:
                continue
            decoded = decode_jetton_notification(incoming.body)
            if decoded is None:
                continue
            amount_atomic, sender, memo = decoded
            if amount_atomic != expected_atomic or memo != deal.public_id:
                continue
            return PaymentObservation(
                tx_hash=transaction_hash(transaction),
                tx_lt=transaction.lt,
                amount_atomic=amount_atomic,
                sender=sender,
                memo=memo,
                observed_at=datetime.fromtimestamp(transaction.now, tz=UTC),
            )
        return None

    def transfer_builder(self, message: PayoutMessage) -> JettonTransferBuilder:
        self._ensure_mainnet()
        return JettonTransferBuilder(
            destination=Address(message.destination),
            jetton_amount=message.amount_atomic,
            jetton_master_address=self._settings.USDT_MASTER_ADDRESS,
            forward_payload=message.comment,
            forward_amount=1,
            amount=payout_amount_atomic(self._settings.USDT_JETTON_TRANSFER_TON),
            send_mode=int(SendMode.PAY_GAS_SEPARATELY | SendMode.IGNORE_ERRORS),
            bounce=True,
        )

    async def balance_atomic(self) -> int:
        await self.start()
        assert self._guarant_jetton_wallet is not None
        wallet = await JettonWalletStablecoin.from_address(
            self._client, self._guarant_jetton_wallet
        )
        data = await wallet.get_wallet_data()
        return int(data[0])

    async def payout_trace_matches(self, trace: dict, attempt: PayoutAttempt) -> bool:
        seller_ok = await self._notification_matches(
            trace, attempt.destination, attempt.amount_atomic, attempt.comment
        )
        if not seller_ok:
            return False
        if not attempt.reward_destination or not attempt.reward_comment:
            return True
        return await self._notification_matches(
            trace,
            attempt.reward_destination,
            int(attempt.reward_nominal_amount_atomic or 0),
            attempt.reward_comment,
        )

    async def refund_trace_matches(self, trace: dict, attempt: RefundAttempt) -> bool:
        buyer_ok = await self._notification_matches(
            trace, attempt.destination, attempt.amount_atomic, attempt.comment
        )
        if not buyer_ok or not attempt.reward_destination or not attempt.reward_comment:
            return False
        return await self._notification_matches(
            trace,
            attempt.reward_destination,
            int(attempt.reward_nominal_amount_atomic or 0),
            attempt.reward_comment,
        )

    async def transfer_trace_matches(
        self, trace: dict, destination: str, amount_atomic: int, comment: str
    ) -> bool:
        return await self._notification_matches(trace, destination, amount_atomic, comment)

    async def _notification_matches(
        self, trace: dict, owner: str, amount_atomic: int, comment: str
    ) -> bool:
        source = await self._wallet_address(owner)
        destination = Address(owner).to_str(is_user_friendly=False)
        return trace_contains_jetton_notification(
            trace,
            destination=destination,
            notification_source=source,
            amount_atomic=amount_atomic,
            comment=comment,
        )

    async def _wallet_address(self, owner: str) -> str:
        await self.start()
        assert self._master is not None
        address = await self._master.get_wallet_address(owner)
        return address.to_str(is_user_friendly=False)

    def _ensure_mainnet(self) -> None:
        if self._settings.TON_NETWORK is not TonNetwork.MAINNET:
            raise TonGatewayError("Official USDT is available only on TON mainnet")
