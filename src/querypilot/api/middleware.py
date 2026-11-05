"""Request correlation, safe failure handling, and structured access logs."""

import logging
import time
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from querypilot.api.errors import error_response, internal_error

logger = logging.getLogger("querypilot.requests")

MAX_AGENT_BODY_BYTES = 65536


class AgentBodyLimitMiddleware:
    """Bound streamed agent request bodies before FastAPI parses JSON."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"].rstrip("/") != "/api/v1/agent/ask"
        ):
            await self.app(scope, receive, send)
            return
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > MAX_AGENT_BODY_BYTES:
                response = error_response(
                    Request(scope),
                    413,
                    "payload_too_large",
                    "Agent request exceeds the body size limit.",
                )
                await response(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)


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
