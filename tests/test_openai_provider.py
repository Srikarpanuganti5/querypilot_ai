"""Use the actual SDK with an in-memory HTTP transport; no paid/live requests."""

import asyncio
import json
import logging
from decimal import Decimal
from unittest.mock import Mock

import httpx
import pytest
from openai import AsyncOpenAI

from querypilot.agent.orchestrator import SingleRoundService
from querypilot.agent.provider import OpenAIProvider, ProviderError
from querypilot.core.config import Settings
from querypilot.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def isolated_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging.getLogger("querypilot"), "handlers", [logging.NullHandler()])
    monkeypatch.setattr(logging.getLogger("querypilot"), "propagate", False)


def response(status="completed", output=None):
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "status": status,
        "model": "model-from-configuration",
        "output": output or [],
        "error": None,
        "incomplete_details": None,
        "tools": [],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "metadata": {},
    }


def run(handler, *, final=False, retries=0, timeout=2):
    async def scenario():
        settings = Settings(
            _env_file=None,
            openai_api_key="TEST_SECRET_KEY",
            openai_model="model-from-configuration",
            llm_request_timeout_seconds=timeout,
            llm_max_retries=retries,
        )
        client = AsyncOpenAI(
            api_key="TEST_SECRET_KEY",
            max_retries=retries,
            timeout=timeout,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        provider = OpenAIProvider(settings, client=client)
        try:
            return await provider.respond(
                "private instructions", [{"role": "user", "content": "Question"}], [], final=final
            )
        finally:
            await provider.close()

    return asyncio.run(scenario())


def test_official_sdk_request_shape_and_followup_choice() -> None:
    received = []

    def handler(request):
        received.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response(
                output=[
                    {
                        "type": "function_call",
                        "id": "fc_test",
                        "call_id": "call_test",
                        "name": "get_top_products",
                        "arguments": "{}",
                        "status": "completed",
                    }
                ]
            ),
        )

    turn = run(handler)
    assert turn.output[0]["call_id"] == "call_test"
    run(handler, final=True)
    assert received[0]["model"] == "model-from-configuration"
    assert received[0]["store"] is False
    assert received[0]["include"] == ["reasoning.encrypted_content"]
    assert received[0]["tool_choice"] == "auto"
    assert received[0]["parallel_tool_calls"] is True
    assert received[1]["tool_choice"] == "none"
    assert received[1]["parallel_tool_calls"] is False


@pytest.mark.parametrize(
    "status,code", [(401, "authentication_error"), (429, "rate_limit"), (500, "provider_error")]
)
def test_safe_http_errors(status: int, code: str) -> None:
    def handler(request):
        return httpx.Response(
            status, json={"error": {"message": "SECRET_PROVIDER_DETAIL", "type": "api_error"}}
        )

    with pytest.raises(ProviderError) as error:
        run(handler)
    assert error.value.code == code
    assert "SECRET" not in str(error.value)


@pytest.mark.parametrize("timeout", [False, True])
def test_safe_network_and_timeout_errors(timeout: bool) -> None:
    def handler(request):
        if timeout:
            raise httpx.ReadTimeout("SECRET_TIMEOUT", request=request)
        raise httpx.ConnectError("SECRET_NETWORK", request=request)

    with pytest.raises(ProviderError) as error:
        run(handler)
    assert error.value.code == ("provider_timeout" if timeout else "network_error")
    assert "SECRET" not in str(error.value)


def test_transient_retry_is_limited_and_successful() -> None:
    attempts = []

    def handler(request):
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(
                429, headers={"retry-after-ms": "1"}, json={"error": {"message": "temporary"}}
            )
        return httpx.Response(200, json=response())

    run(handler, retries=1)
    assert len(attempts) == 2


def test_exhausted_retries_do_not_loop() -> None:
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(
            429, headers={"retry-after-ms": "1"}, json={"error": {"message": "temporary"}}
        )

    with pytest.raises(ProviderError, match="rate limit"):
        run(handler, retries=1)
    assert len(attempts) == 2


def test_logical_request_deadline_bounds_transport() -> None:
    async def handler(request):
        await asyncio.sleep(0.2)
        return httpx.Response(200, json=response())

    with pytest.raises(ProviderError) as error:
        run(handler, timeout=0.05)
    assert error.value.code == "provider_timeout"


def test_incomplete_response_is_rejected() -> None:
    with pytest.raises(ProviderError) as error:
        run(lambda request: httpx.Response(200, json=response(status="incomplete")))
    assert error.value.code == "provider_response_error"


def test_live_provider_requires_key_and_model() -> None:
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        OpenAIProvider(Settings(_env_file=None, openai_api_key=None, openai_model=None))


def test_sdk_to_registry_end_to_end_without_network() -> None:
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert len(body["tools"]) == 6
        if len(requests) == 1:
            return httpx.Response(
                200,
                json=response(
                    output=[
                        {
                            "type": "function_call",
                            "id": "fc_test",
                            "call_id": "call_exact",
                            "name": "get_top_products",
                            "status": "completed",
                            "arguments": '{"limit":null,"start_date":null,"end_date":null}',
                        }
                    ]
                ),
            )
        assert body["tool_choice"] == "none"
        outputs = [item for item in body["input"] if item.get("type") == "function_call_output"]
        assert outputs[0]["call_id"] == "call_exact"
        assert json.loads(outputs[0]["output"])["result"]["data"]["rows"][0]["revenue"] == "19.98"
        return httpx.Response(
            200,
            json=response(
                output=[
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Sample: USD 19.98 [E1].",
                                "annotations": [],
                            }
                        ],
                    }
                ]
            ),
        )

    async def scenario():
        settings = Settings(
            _env_file=None, openai_api_key="TEST_KEY", openai_model="configured-model"
        )
        client = AsyncOpenAI(
            api_key="TEST_KEY",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        provider = OpenAIProvider(settings, client=client)
        repository = Mock()
        repository.execute.return_value = (
            [
                {
                    "product_id": 1,
                    "name": "Sample",
                    "category": "Home",
                    "units_sold": 2,
                    "revenue": Decimal("19.98"),
                }
            ],
            False,
        )
        try:
            return await SingleRoundService(provider, ToolRegistry(repository), settings).run(
                "Top products?"
            )
        finally:
            await provider.close()

    result = asyncio.run(scenario())
    assert result.status == "completed"
    assert result.tools[0].call_id == "call_exact"
    assert len(requests) == 2
