"""Async official SDK adapter; bounded retries and safe provider diagnostics."""

import asyncio
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from querypilot.core.config import Settings

SAFE_ERRORS = {
    "configuration_error": "Set OPENAI_API_KEY and OPENAI_MODEL for live mode.",
    "authentication_error": "OpenAI authentication failed.",
    "rate_limit": "OpenAI rate limit reached; retry later.",
    "provider_timeout": "The model request timed out.",
    "network_error": "The model provider could not be reached.",
    "provider_error": "The model provider rejected the request.",
    "provider_response_error": "The model response was malformed or exceeded its limits.",
    "tool_limit": "The tool-call limit was reached; narrow the question.",
    "unexpected_tool_call": "The answer request attempted another tool round.",
    "context_limit": "Accumulated agent context exceeded its limit.",
    "message_limit": "The model-facing message count exceeded its limit.",
    "grounding_error": "Answer failed evidence checks; inspect the tool results.",
    "evidence_limit": "Accumulated tool evidence exceeded its limit.",
    "evidence_conflict": "Retrieved records conflict; no combined factual answer is available.",
    "iteration_limit": "The agent iteration limit was reached.",
    "tool_timeout": "Agent stopped after a tool deadline.",
    "sensitive_input": "The question contains credential-like content; remove it and retry.",
    "sensitive_output": "Credential-like or private instruction content was withheld.",
}


@dataclass(frozen=True)
class ProviderTurn:
    output: list[dict[str, Any]]
    text: str = ""


class ProviderError(Exception):
    def __init__(self, code: str, message: str):
        # Treat even custom/injected provider exceptions as untrusted diagnostics.
        self.code = code if code in SAFE_ERRORS else "provider_error"
        super().__init__(SAFE_ERRORS[self.code])


class ModelProvider(Protocol):
    mode: Literal["mock", "live"]

    async def respond(
        self, instructions: str, history: list[dict], tools: list[dict], *, final: bool = False
    ) -> ProviderTurn: ...


class OpenAIProvider:
    mode: Literal["live"] = "live"

    def __init__(self, settings: Settings, *, client: AsyncOpenAI | None = None):
        key = settings.openai_api_key
        if key is None or not key.get_secret_value().strip() or not settings.openai_model:
            raise ProviderError(
                "configuration_error", "Set OPENAI_API_KEY and OPENAI_MODEL for live mode."
            )
        self.settings = settings
        self.client = (
            client
            if client is not None
            else AsyncOpenAI(
                api_key=key.get_secret_value(),
                timeout=settings.llm_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        )

    async def respond(
        self, instructions: str, history: list[dict], tools: list[dict], *, final: bool = False
    ) -> ProviderTurn:
        try:
            # This bounds the logical request including SDK retry/backoff time.
            async with asyncio.timeout(self.settings.llm_request_timeout_seconds):
                response = await self.client.responses.create(
                    model=self.settings.openai_model,
                    instructions=instructions,
                    input=history,
                    tools=tools,
                    tool_choice="none" if final else "auto",
                    parallel_tool_calls=not final,
                    max_output_tokens=self.settings.llm_max_output_tokens,
                    store=False,
                    include=["reasoning.encrypted_content"],
                )
        except AuthenticationError:
            raise ProviderError("authentication_error", "OpenAI authentication failed.") from None
        except RateLimitError:
            raise ProviderError("rate_limit", "OpenAI rate limit reached; retry later.") from None
        except (APITimeoutError, TimeoutError):
            raise ProviderError("provider_timeout", "The model request timed out.") from None
        except APIConnectionError:
            raise ProviderError(
                "network_error", "The model provider could not be reached."
            ) from None
        except APIError:
            raise ProviderError(
                "provider_error", "The model provider rejected the request."
            ) from None
        except Exception:
            raise ProviderError("provider_error", "Unexpected provider failure.") from None
        if response.status != "completed":
            raise ProviderError("provider_response_error", "The model response was not completed.")
        try:
            output = [item.model_dump(mode="json", exclude_none=True) for item in response.output]
            return ProviderTurn(output, response.output_text)
        except (AttributeError, TypeError, ValueError):
            raise ProviderError(
                "provider_response_error", "The model response was malformed."
            ) from None

    async def close(self) -> None:
        await self.client.close()
