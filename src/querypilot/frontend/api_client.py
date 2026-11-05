"""Typed, bounded HTTP client with no automatic retries or provider credentials."""

import json
from typing import Any

import httpx
from pydantic import ValidationError

from querypilot.frontend.config import FrontendSettings
from querypilot.frontend.messages import MESSAGES, message_for
from querypilot.schemas.agent import AgentCapabilities, AgentResponse, AskRequest

MAX_RESPONSE_BYTES = 512000


class ClientError(Exception):
    def __init__(self, code: str):
        self.code = code if code in MESSAGES else "execution_error"
        super().__init__(message_for(self.code))


class ApiClient:
    def __init__(self, settings: FrontendSettings, *, transport: httpx.BaseTransport | None = None):
        self.base_url = str(settings.api_base_url)
        self.transport = transport

    def _request(
        self, method: str, path: str, *, payload: dict | None = None, timeout: float = 3
    ) -> Any:
        try:
            with httpx.Client(
                base_url=self.base_url,
                transport=self.transport,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                with client.stream(
                    method, path, json=payload, timeout=httpx.Timeout(timeout, connect=3)
                ) as response:
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise ClientError("invalid_response")
                        chunks.append(chunk)
                    value = json.loads(b"".join(chunks))
                    if response.status_code != 200:
                        code = (
                            value.get("error", {}).get("code", "execution_error")
                            if isinstance(value, dict)
                            else "execution_error"
                        )
                        raise ClientError(code)
                    return value
        except httpx.TimeoutException:
            raise ClientError("request_timeout") from None
        except httpx.RequestError:
            raise ClientError("backend_unavailable") from None
        except (ValueError, TypeError, AttributeError, RecursionError):
            raise ClientError("invalid_response") from None

    def capabilities(self) -> AgentCapabilities:
        try:
            return AgentCapabilities.model_validate(
                self._request("GET", "/api/v1/agent/capabilities")
            )
        except ValidationError:
            raise ClientError("invalid_response") from None

    def ask(self, request: AskRequest, *, execution_timeout_seconds: float) -> AgentResponse:
        try:
            if not 0.01 <= execution_timeout_seconds <= 300:
                raise ClientError("invalid_response")
            value = self._request(
                "POST",
                "/api/v1/agent/ask",
                payload=request.model_dump(),
                timeout=execution_timeout_seconds + 15,
            )
            outcome = AgentResponse.model_validate(value)
            if outcome.mode != request.mode:
                raise ClientError("invalid_response")
            return outcome
        except ValidationError:
            raise ClientError("invalid_response") from None
