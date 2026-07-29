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
from app.models.dto import DepositScanBatch, PaymentObservation
from app.ton.amounts import payout_amount_atomic
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

    async def scan_deposits_since(
        self, last_lt: int | None, last_hash: str | None
    ) -> DepositScanBatch:
        """Read every transaction newer than last_lt without a fixed history window."""
        await self.start()
        assert self._guarant_jetton_wallet is not None
        expected_source = self._guarant_jetton_wallet.to_str(is_user_friendly=False)
        from_lt: int | None = None
        newest_lt: int | None = None
        newest_hash: str | None = None
        deposits: list[PaymentObservation] = []
        reached_cursor = False

        while not reached_cursor:
            transactions = await self._guarant_wallet.get_transactions(
                limit=100,
                from_lt=from_lt,
            )
            if not transactions:
                break
            if newest_lt is None:
                newest_lt = int(transactions[0].lt)
                newest_hash = transaction_hash(transactions[0])
            for transaction in transactions:
                if last_lt is not None and int(transaction.lt) == last_lt:
                    if last_hash and transaction_hash(transaction) != last_hash:
                        raise TonGatewayError(
                            "USDT deposit cursor hash does not match on-chain history"
                        )
                    reached_cursor = True
                    break
                if last_lt is not None and int(transaction.lt) < last_lt:
                    raise TonGatewayError(
                        "USDT deposit cursor is missing from sequential account history"
                    )
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
                if amount_atomic <= 0:
                    continue
                deposits.append(
                    PaymentObservation(
                        tx_hash=transaction_hash(transaction),
                        tx_lt=transaction.lt,
                        amount_atomic=amount_atomic,
                        sender=sender,
                        memo=memo,
                        jetton_wallet_address=self._guarant_jetton_wallet.to_str(
                            is_bounceable=False
                        ),
                        observed_at=datetime.fromtimestamp(transaction.now, tz=UTC),
                    )
                )
            if reached_cursor or len(transactions) < 100:
                break
            from_lt = int(transactions[-1].lt) - 1

        deposits.sort(key=lambda item: item.tx_lt)
        return DepositScanBatch(
            deposits=deposits,
            newest_lt=newest_lt,
            newest_hash=newest_hash,
        )

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

    async def operation_trace_matches(
        self,
        trace: dict,
        destination: str,
        amount_atomic: int,
        comment: str,
    ) -> bool:
        """Validate one USDT ledger leg against its transfer notification."""
        return await self._notification_matches(
            trace,
            destination,
            amount_atomic,
            comment,
        )

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
