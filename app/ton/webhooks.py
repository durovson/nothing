from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlencode

from aiohttp import ClientSession, ClientTimeout
from ton_core import Address

from app.config import Settings
from app.core.enums import TonNetwork

logger = logging.getLogger(__name__)

_SUBSCRIPTION_BATCH_SIZE = 100
_MAX_RETRY_SECONDS = 300


class TonApiWebhookManager:
    """Maintain TonAPI account subscriptions without making webhooks authoritative."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._session: ClientSession | None = None
        self._webhook_id = settings.TONAPI_WEBHOOK_ID
        self._desired_accounts: set[str] = set()
        self._desired_initialized = False
        self._changed = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def enabled(self) -> bool:
        return self._settings.TONAPI_WEBHOOK_ENABLED

    async def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        if not self._settings.APP_BASE_URL:
            raise RuntimeError("APP_BASE_URL is required for TonAPI webhooks")
        if not self._settings.TON_API_KEY:
            raise RuntimeError("TON_API_KEY is required for TonAPI webhooks")
        if len(self._settings.TONAPI_WEBHOOK_SECRET) < 32:
            raise RuntimeError(
                "TONAPI_WEBHOOK_SECRET must contain at least 32 characters "
                "when TonAPI webhooks are enabled"
            )
        self._session = ClientSession(
            timeout=ClientTimeout(total=15),
            headers={"Authorization": f"Bearer {self._settings.TON_API_KEY}"},
        )
        self._task = asyncio.create_task(self._run(), name="tonapi-webhook-manager")
        self._changed.set()

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._session is not None:
            await self._session.close()
            self._session = None

    def track_account(self, address: str | None) -> None:
        if not self.enabled or not address:
            return
        account = self._raw_address(address)
        if account not in self._desired_accounts:
            self._desired_accounts.add(account)
            self._desired_initialized = True
            self._changed.set()

    def replace_accounts(self, addresses: set[str]) -> None:
        if not self.enabled:
            return
        desired = {self._raw_address(address) for address in addresses if address}
        if not self._desired_initialized or desired != self._desired_accounts:
            self._desired_accounts = desired
            self._desired_initialized = True
            self._changed.set()

    async def _run(self) -> None:
        failures = 0
        while True:
            await self._changed.wait()
            self._changed.clear()
            try:
                await self._ensure_webhook()
                if self._desired_initialized:
                    await self._sync_subscriptions()
                if failures:
                    logger.info("TonAPI webhook manager recovered after %s failure(s)", failures)
                failures = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failures += 1
                delay = min(15 * (2 ** (failures - 1)), _MAX_RETRY_SECONDS)
                logger.warning(
                    "TonAPI webhook subscription sync failed error=%s; retry in %ss",
                    type(exc).__name__,
                    delay,
                )
                try:
                    await asyncio.wait_for(self._changed.wait(), timeout=delay)
                except TimeoutError:
                    pass
                self._changed.set()

    async def _ensure_webhook(self) -> None:
        if self._webhook_id is not None:
            return
        endpoint = self._callback_url()
        payload = await self._request("GET", "/webhooks")
        for item in payload.get("webhooks", []):
            if item.get("endpoint") == endpoint:
                self._webhook_id = int(item["id"])
                return
        created = await self._request("POST", "/webhooks", {"endpoint": endpoint})
        self._webhook_id = int(created["webhook_id"])
        logger.info("TonAPI webhook registered")

    async def _sync_subscriptions(self) -> None:
        current = await self._subscriptions()
        missing = sorted(self._desired_accounts - current)
        obsolete = sorted(current - self._desired_accounts)
        for batch in _chunks(missing):
            await self._request(
                "POST",
                f"/webhooks/{self._webhook_id}/account-tx/subscribe",
                {"accounts": [{"account_id": account} for account in batch]},
            )
        for batch in _chunks(obsolete):
            await self._request(
                "POST",
                f"/webhooks/{self._webhook_id}/account-tx/unsubscribe",
                {"accounts": batch},
            )
        if missing or obsolete:
            logger.info(
                "TonAPI webhook subscriptions synchronized added=%s removed=%s total=%s",
                len(missing),
                len(obsolete),
                len(self._desired_accounts),
            )

    async def _subscriptions(self) -> set[str]:
        result: set[str] = set()
        offset = 0
        limit = 1_000
        while True:
            payload = await self._request(
                "GET",
                f"/webhooks/{self._webhook_id}/account-tx/subscriptions"
                f"?offset={offset}&limit={limit}",
            )
            rows = payload.get("account_tx_subscriptions", [])
            result.update(str(item["account_id"]) for item in rows if item.get("account_id"))
            if len(rows) < limit:
                return result
            offset += limit

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if self._session is None:
            raise RuntimeError("TonAPI webhook manager is not started")
        domain = (
            "https://rt-testnet.tonapi.io"
            if self._settings.TON_NETWORK is TonNetwork.TESTNET
            else "https://rt.tonapi.io"
        )
        async with self._session.request(method, f"{domain}{path}", json=json) as response:
            if response.status >= 400:
                raise RuntimeError(f"TonAPI webhook API returned HTTP {response.status}")
            if response.status == 204:
                return {}
            payload = await response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("TonAPI webhook API returned an invalid response")
            return payload

    def _callback_url(self) -> str:
        base = self._settings.APP_BASE_URL.rstrip("/")
        path = "/" + self._settings.TONAPI_WEBHOOK_PATH.strip("/")
        query = urlencode({"secret": self._settings.TONAPI_WEBHOOK_SECRET})
        return f"{base}{path}?{query}"

    @staticmethod
    def _raw_address(address: str) -> str:
        return Address(address).to_str(is_user_friendly=False)


def _chunks(values: list[str]):
    for index in range(0, len(values), _SUBSCRIPTION_BATCH_SIZE):
        yield values[index : index + _SUBSCRIPTION_BATCH_SIZE]
