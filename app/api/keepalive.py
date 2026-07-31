from __future__ import annotations

import asyncio
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.config import Settings

logger = logging.getLogger(__name__)


class RenderKeepAlive:
    """Periodically calls the public Render endpoint without blocking the event loop."""

    def __init__(self, settings: Settings):
        self._base_url = (settings.RENDER_EXTERNAL_URL or settings.APP_BASE_URL).rstrip("/")
        self._enabled = settings.RENDER_KEEPALIVE_ENABLED and bool(self._base_url)
        self._interval = settings.RENDER_KEEPALIVE_INTERVAL_SECONDS
        self._timeout = settings.RENDER_KEEPALIVE_TIMEOUT_SECONDS
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self._enabled or self.is_running:
            return
        self._validate_url()
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="render-keepalive")
        logger.info(
            "Render keep-alive started: url=%s/ interval=%ss",
            self._base_url,
            self._interval,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    def _validate_url(self) -> None:
        parsed = urlsplit(self._base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(
                "RENDER_EXTERNAL_URL or APP_BASE_URL must be a valid HTTP(S) URL "
                "when Render keep-alive is enabled"
            )

    async def _run(self) -> None:
        # A self-request during ASGI lifespan startup cannot be served yet.
        # Waiting one full interval also keeps the first wake-up inside Render's
        # inactivity window without adding startup traffic.
        if await self._wait_for_stop():
            return
        while not self._stop_event.is_set():
            try:
                status = await asyncio.to_thread(self._ping)
<<<<<<< HEAD
                logger.debug("Render keep-alive ping succeeded: status=%s", status)
=======
                logger.info("Render keep-alive ping succeeded: status=%s", status)
>>>>>>> 683710e48dd65cdb7e64e78f3317fc4f62cf47eb
            except (TimeoutError, HTTPError, URLError) as exc:
                logger.warning(
                    "Render keep-alive ping temporarily failed: error=%s",
                    type(exc).__name__,
                )
            except Exception:
                logger.exception("Render keep-alive ping failed")
            if await self._wait_for_stop():
                return

    async def _wait_for_stop(self) -> bool:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval)
        except TimeoutError:
            return False
        return True

    def _ping(self) -> int:
        request = Request(
<<<<<<< HEAD
            f"{self._base_url}/livez",
=======
            f"{self._base_url}/",
>>>>>>> 683710e48dd65cdb7e64e78f3317fc4f62cf47eb
            method="GET",
            headers={"User-Agent": "Gift-Guarant-Render-KeepAlive/1.0"},
        )
        with urlopen(request, timeout=self._timeout) as response:
            status = int(response.status)
        if not 200 <= status < 300:
            raise HTTPError(request.full_url, status, "Unexpected ping status", {}, None)
        return status
