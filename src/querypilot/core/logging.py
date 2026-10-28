"""Allowlisted JSON logs: never serialize request data or exception messages."""

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
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
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    logger = logging.getLogger("querypilot")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
    # Uvicorn's default access messages include raw URLs/query strings.
    # RequestLoggingMiddleware supplies safe structured access records instead.
    logging.getLogger("uvicorn.access").disabled = True
