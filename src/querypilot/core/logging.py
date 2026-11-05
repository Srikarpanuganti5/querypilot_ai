"""Allowlisted JSON logs: never serialize request data or exception messages."""

import json
import logging
import sys
from datetime import UTC, datetime

from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard


class JsonFormatter(logging.Formatter):
    def __init__(self, guard: SecretGuard | None = None):
        super().__init__()
        self.guard = guard or SecretGuard()

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "route",
            "status_code",
            "duration_ms",
            "error_type",
            "tool",
            "status",
            "trace_id",
            "mode",
            "tool_count",
            "iteration_count",
            "error_category",
            "limit_reason",
            "pending_tool_calls",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(self.guard.sanitize(payload))


def configure_logging(level: str, *, settings: Settings | None = None) -> None:
    logger = logging.getLogger("querypilot")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        JsonFormatter(SecretGuard(settings if settings is not None else Settings()))
    )
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
    # Uvicorn's default access messages include raw URLs/query strings.
    # RequestLoggingMiddleware supplies safe structured access records instead.
    logging.getLogger("uvicorn.access").disabled = True
