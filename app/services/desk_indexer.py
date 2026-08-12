from app.core.enums import Currency
from app.core.types import DepositRepositoryProtocol, TonGatewayProtocol
from app.models.dto import PaymentObservation
from app.services.desk import DeskService
from app.services.system_mode import SystemModeService

SCANNER_NAME = "guarant-ton-desk-v1"


class DeskTonDepositIndexer:
    def __init__(
        self,
        deposits: DepositRepositoryProtocol,
        ton: TonGatewayProtocol,
        desk: DeskService,
        system_mode: SystemModeService | None = None,
    ):
        self._deposits = deposits
        self._ton = ton
        self._desk = desk
        self._system_mode = system_mode

    async def run_once(self) -> None:
        if self._system_mode is not None and not await self._system_mode.accepts_deposits():
            return
        cursor = await self._deposits.get_cursor(SCANNER_NAME)
        batch = await self._ton.scan_guarant_ton_deposits(
            cursor.last_lt if cursor else None,
            cursor.last_hash if cursor else None,
        )
        # A newly deployed scanner starts at the current account head. Replaying
        # historical guarant-wallet transfers could misclassify old custody moves.
        if cursor is None:
            if batch.newest_lt is not None and batch.newest_hash:
                await self._deposits.save_cursor(
                    SCANNER_NAME,
                    self._ton.guarant_address,
                    batch.newest_lt,
                    batch.newest_hash,
                )
            return
        for observation in batch.deposits:
            await self._process(observation)
        if batch.newest_lt is not None and batch.newest_hash:
            await self._deposits.save_cursor(
                SCANNER_NAME, self._ton.guarant_address, batch.newest_lt, batch.newest_hash
            )

    async def _process(self, observation: PaymentObservation) -> None:
        deposit = await self._deposits.add_observed({
            "tx_hash": observation.tx_hash,
            "tx_lt": observation.tx_lt,
            "currency": Currency.TON.value,
            "amount_atomic": observation.amount_atomic,
            "sender": observation.sender,
            "memo": observation.memo,
            "account_address": self._ton.guarant_address,
            "observed_at": observation.observed_at.isoformat(),
        })
        if deposit is None or deposit.processed_at is not None:
            return
        if await self._desk.try_process_deposit(deposit):
            return
        # The guarant receives legitimate custody/service transfers too. They are
        # outside Desk. Small unattributed transfers can still be malformed Desk
        # payments, so preserve them for administrator review instead of losing evidence.
        if deposit.amount_atomic < 1_000_000_000:
            await self._deposits.add_unmatched(
                deposit, "guarant_ton_unattributed_possible_desk_payment"
            )
        await self._deposits.mark_desk_checked(deposit.id)
        await self._deposits.mark_processed(deposit.id)
