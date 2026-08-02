import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import TypeVar

from supabase import AsyncClient, AsyncClientOptions

from app.config import Settings
from app.core.constants import (
    DB_BACKGROUND_MAX_CONCURRENCY,
    DB_INTERACTIVE_READ_RETRY_ATTEMPTS,
    DB_MAX_CONCURRENCY,
    DB_READ_RETRY_ATTEMPTS,
    DB_READ_RETRY_BASE_DELAY_SECONDS,
    SLOW_BACKGROUND_DATABASE_REQUEST_SECONDS,
    SLOW_BACKGROUND_DATABASE_WAIT_SECONDS,
    SLOW_DATABASE_REQUEST_SECONDS,
    SLOW_DATABASE_WAIT_SECONDS,
    SUPABASE_POSTGREST_TIMEOUT_SECONDS,
)
from app.core.telemetry import current_trace_id

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
        self._capacity = asyncio.Semaphore(DB_MAX_CONCURRENCY)
        self._background_capacity = asyncio.Semaphore(
            DB_BACKGROUND_MAX_CONCURRENCY
        )
        self.client = self._create_client()

    async def run(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        *,
        name: str = "unlabelled-write",
    ) -> ResultT:
        """Run one potentially mutating operation without unsafe automatic replay."""
        return await self._execute(operation, kind="write", operation_name=name)

    async def read(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        *,
        name: str = "unlabelled-read",
    ) -> ResultT:
        """Run a replay-safe read with bounded transient-network retries."""
        attempts = (
            DB_INTERACTIVE_READ_RETRY_ATTEMPTS
            if current_trace_id().startswith("telegram:")
            else DB_READ_RETRY_ATTEMPTS
        )
        for attempt in range(1, attempts + 1):
            try:
                return await self._execute(
                    operation,
                    kind="read",
                    operation_name=name,
                )
            except Exception as exc:
                if not _is_transient_transport_error(exc) or attempt >= attempts:
                    raise
                logger.warning(
                    "Transient Supabase read failed trace=%s operation=%s error=%s retry=%s/%s",
                    current_trace_id(),
                    name,
                    type(exc).__name__,
                    attempt + 1,
                    attempts,
                )
                await asyncio.sleep(
                    DB_READ_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                )
        raise RuntimeError("Unreachable Supabase read retry state")

    async def rpc(self, name: str, params: dict[str, object]):
        return await self.run(
            lambda: self.client.rpc(name, params).execute(),
            name=f"rpc:{name}",
        )

    async def ping(self) -> bool:
        response = await self.read(
            lambda: self.client.table("bot_settings").select("id").limit(1).execute(),
            name="bot_settings:health-probe",
        )
        return response.data is not None

    async def warm_up(self) -> None:
        """Open the reusable PostgREST connection before background workers fan out."""
        await self.ping()

    async def close(self) -> None:
        await self.client.postgrest.aclose()
        await self.client.auth.close()

    def _create_client(self) -> AsyncClient:
        return AsyncClient(
            self._settings.SUPABASE_URL,
            self._settings.SUPABASE_KEY,
            AsyncClientOptions(
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=SUPABASE_POSTGREST_TIMEOUT_SECONDS,
                schema="public",
            ),
        )

    async def _execute(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        *,
        kind: str,
        operation_name: str,
    ) -> ResultT:
        queued_at = perf_counter()
        trace_id = current_trace_id()
        interactive = trace_id.startswith("telegram:")
        background_acquired = False
        try:
            if not interactive:
                await self._background_capacity.acquire()
                background_acquired = True
            async with self._capacity:
                started_at = perf_counter()
                wait_seconds = started_at - queued_at
                result: ResultT | None = None
                try:
                    async with asyncio.timeout(SUPABASE_POSTGREST_TIMEOUT_SECONDS):
                        result = await operation()
                    return result
                finally:
                    request_seconds = perf_counter() - started_at
                    row_count = _response_row_count(result)
                    wait_threshold = (
                        SLOW_DATABASE_WAIT_SECONDS
                        if interactive
                        else SLOW_BACKGROUND_DATABASE_WAIT_SECONDS
                    )
                    request_threshold = (
                        SLOW_DATABASE_REQUEST_SECONDS
                        if interactive
                        else SLOW_BACKGROUND_DATABASE_REQUEST_SECONDS
                    )
                    if request_seconds >= request_threshold:
                        logger.warning(
                            "Slow Supabase request trace=%s operation=%s kind=%s rows=%s wait_ms=%.1f request_ms=%.1f",
                            trace_id,
                            operation_name,
                            kind,
                            row_count,
                            wait_seconds * 1_000,
                            request_seconds * 1_000,
                        )
                    elif wait_seconds >= wait_threshold:
                        logger.warning(
                            "Supabase operation queue congestion trace=%s operation=%s kind=%s rows=%s wait_ms=%.1f request_ms=%.1f",
                            trace_id,
                            operation_name,
                            kind,
                            row_count,
                            wait_seconds * 1_000,
                            request_seconds * 1_000,
                        )
        finally:
            if background_acquired:
                self._background_capacity.release()


def _is_transient_transport_error(error: BaseException) -> bool:
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        module = type(current).__module__.split(".", 1)[0]
        if isinstance(current, TimeoutError):
            return True
        if module in {"httpx", "httpcore"} and type(current).__name__ in _TRANSIENT_ERROR_NAMES:
            return True
        if isinstance(current, OSError) and current.errno in _TRANSIENT_ERRNOS:
            return True
        current = current.__cause__ or current.__context__
    return False


def _response_row_count(response: object | None) -> int | str:
    if response is None:
        return "unknown"
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return len(data)
    return 1 if data is not None else 0
