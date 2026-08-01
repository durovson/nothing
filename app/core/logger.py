import logging
from copy import deepcopy
from typing import Any

from uvicorn.config import LOGGING_CONFIG


class HealthCheckAccessFilter(logging.Filter):
    """Hide successful probe traffic without suppressing useful access logs."""

    _QUIET_PATHS = frozenset(
        {"/healthz", "/readyz", "/ping", "/livez", "/favicon.ico"}
    )

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3:
            path = str(args[2]).partition("?")[0]
            return path not in self._QUIET_PATHS
        return True


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # Supabase polling generates a large number of successful HTTP requests.
    # Keep application events at INFO without flooding production logs with one
    # transport line per request; warnings and errors remain visible.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def uvicorn_log_config() -> dict[str, Any]:
    """Return Uvicorn defaults with only routine health probes filtered out."""
    config = deepcopy(LOGGING_CONFIG)
    config.setdefault("filters", {})["skip_health_checks"] = {
        "()": "app.core.logger.HealthCheckAccessFilter"
    }
    config["handlers"]["access"]["filters"] = ["skip_health_checks"]
    return config
