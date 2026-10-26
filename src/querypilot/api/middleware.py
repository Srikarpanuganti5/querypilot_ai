"""Request correlation, safe failure handling, and structured access logs."""

import logging
import time
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from querypilot.api.errors import internal_error

logger = logging.getLogger("querypilot.requests")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.monotonic()
        status = 500
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode("ascii")),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:
            logger.error(
                "request_failed", extra={"request_id": request_id, "error_type": type(exc).__name__}
            )
            if response_started:
                # Headers cannot be replaced once sent; expose only a fixed server diagnostic.
                raise RuntimeError("Response stream failed") from None
            response = await internal_error(Request(scope), exc)
            await response(scope, receive, send_with_id)
        finally:
            route = scope.get("route")
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "route": getattr(route, "path", "unmatched"),
                    "status_code": status,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                },
            )
