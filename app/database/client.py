import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

from supabase import Client, create_client

from app.config import Settings
from app.core.constants import DB_READ_RETRY_ATTEMPTS, DB_READ_RETRY_BASE_DELAY_SECONDS

ResultT = TypeVar("ResultT")
logger = logging.getLogger(__name__)

_TRANSIENT_ERROR_NAMES = frozenset(
    {
        "ConnectError",
        "ConnectTimeout",
        "NetworkError",
        "PoolTimeout",
        "ReadError",
        "ReadTimeout",
        "RemoteProtocolError",
        "WriteError",
        "WriteTimeout",
    }
)
_TRANSIENT_ERRNOS = frozenset({11, 104, 110, 111, 113})


class SupabaseDatabase:
    """Async boundary around the synchronous Supabase client."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._lock = asyncio.Lock()
        self.client: Client = self._create_client()

    async def run(self, operation: Callable[[], ResultT]) -> ResultT:
        """Run one potentially mutating operation without unsafe automatic replay."""
        async with self._lock:
            try:
                return await asyncio.to_thread(operation)
            except Exception as exc:
                if _is_transient_transport_error(exc):
                    await self._reconnect()
                raise

    async def read(self, operation: Callable[[], ResultT]) -> ResultT:
        """Run a replay-safe read with bounded transient-network retries."""
        async with self._lock:
            for attempt in range(1, DB_READ_RETRY_ATTEMPTS + 1):
                try:
                    return await asyncio.to_thread(operation)
                except Exception as exc:
                    if not _is_transient_transport_error(exc) or attempt >= DB_READ_RETRY_ATTEMPTS:
                        if _is_transient_transport_error(exc):
                            await self._reconnect()
                        raise
                    logger.warning(
                        "Transient Supabase read failed (%s), retry %s/%s",
                        type(exc).__name__,
                        attempt + 1,
                        DB_READ_RETRY_ATTEMPTS,
                    )
                    await self._reconnect()
                    await asyncio.sleep(DB_READ_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
        raise RuntimeError("Unreachable Supabase read retry state")

    async def rpc(self, name: str, params: dict[str, object]):
        return await self.run(lambda: self.client.rpc(name, params).execute())

    def _create_client(self) -> Client:
        return create_client(self._settings.SUPABASE_URL, self._settings.SUPABASE_KEY)

    async def _reconnect(self) -> None:
        self.client = await asyncio.to_thread(self._create_client)


def _is_transient_transport_error(error: BaseException) -> bool:
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        module = type(current).__module__.split(".", 1)[0]
        if module in {"httpx", "httpcore"} and type(current).__name__ in _TRANSIENT_ERROR_NAMES:
            return True
        if isinstance(current, OSError) and current.errno in _TRANSIENT_ERRNOS:
            return True
        current = current.__cause__ or current.__context__
    return False
