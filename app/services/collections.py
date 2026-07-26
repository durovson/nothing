from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.core.enums import CollectionStatus, TraceStatus
from app.core.types import (
    CollectionRepositoryProtocol,
    DealRepositoryProtocol,
    NotificationGatewayProtocol,
    TonGatewayProtocol,
    UserRepositoryProtocol,
)
from app.models.entities import CollectionAttempt, Deal

logger = logging.getLogger(__name__)


class CollectionService:
    def __init__(
        self,
        settings: Settings,
        deals: DealRepositoryProtocol,
        collections: CollectionRepositoryProtocol,
        users: UserRepositoryProtocol,
        ton: TonGatewayProtocol,
        notifications: NotificationGatewayProtocol,
    ):
        self._settings = settings
        self._deals = deals
        self._collections = collections
        self._users = users
        self._ton = ton
        self._notifications = notifications

    async def start_collection(self, deal: Deal) -> None:
        comment = f"Escrow for deal {deal.public_id}"
        attempt = await self._collections.claim(
            deal,
            self._ton.guarant_address,
            comment,
        )
        if attempt is None:
            logger.info("Collection already claimed for deal %s", deal.public_id)
            return
        try:
            prepared = await self._ton.prepare_collection(deal, comment)
            attempt = await self._collections.save_prepared(
                attempt.id,
                prepared.normalized_hash,
                prepared.signed_boc,
                prepared.valid_until,
            )
        except Exception as exc:
            await self._collections.mark_failed(attempt.id, f"prepare: {exc}")
            raise
        try:
            await self._ton.broadcast(attempt.signed_boc or "")
        except Exception:
            logger.exception("Collection broadcast outcome is uncertain: %s", attempt.id)
            return
        await self._collections.mark_submitted(attempt.id)

    async def reconcile_open(self) -> None:
        for deal in await self._deals.list_collecting():
            try:
                await self.start_collection(deal)
            except Exception:
                logger.exception("Collection recovery failed for deal %s", deal.public_id)
        for attempt in await self._collections.list_open():
            try:
                await self.reconcile(attempt)
            except Exception:
                logger.exception("Collection reconciliation failed: %s", attempt.id)

    async def reconcile(self, attempt: CollectionAttempt) -> None:
        if attempt.status is CollectionStatus.CREATING:
            deal = await self._deals.get(attempt.deal_id)
            if deal is None:
                await self._collections.mark_failed(attempt.id, "Collection deal not found")
                return
            prepared = await self._ton.prepare_collection(deal, attempt.comment)
            attempt = await self._collections.save_prepared(
                attempt.id,
                prepared.normalized_hash,
                prepared.signed_boc,
                prepared.valid_until,
            )

        if attempt.status is CollectionStatus.PREPARED:
            if not attempt.signed_boc:
                await self._collections.mark_failed(attempt.id, "Prepared collection has no signed BOC")
                return
            try:
                await self._ton.broadcast(attempt.signed_boc)
            except Exception:
                logger.exception("Collection re-broadcast outcome is uncertain: %s", attempt.id)
            attempt = await self._collections.mark_submitted(attempt.id)

        status = await self._ton.get_collection_trace_status(attempt)
        match status:
            case TraceStatus.CONFIRMED:
                deal = await self._collections.mark_confirmed(attempt.id)
                if deal:
                    seller = await self._users.get(deal.creator_id)
                    buyer = await self._users.get(deal.buyer_id) if deal.buyer_id else None
                    await self._notifications.payment_received(deal, buyer, seller)
            case TraceStatus.BOUNCED:
                await self._collections.mark_bounced(attempt.id, "Collection transfer bounced")
            case TraceStatus.FAILED:
                await self._collections.mark_failed(attempt.id, "Collection trace execution failed")
            case TraceStatus.NOT_FOUND | TraceStatus.PENDING:
                await self._fail_if_expired(attempt)

    async def _fail_if_expired(self, attempt: CollectionAttempt) -> None:
        if not attempt.valid_until:
            return
        deadline = attempt.valid_until + timedelta(seconds=self._settings.TON_TRACE_GRACE_SECONDS)
        if datetime.now(UTC) > deadline:
            await self._collections.mark_failed(
                attempt.id,
                "Collection message expired and was not found in TonAPI",
            )
