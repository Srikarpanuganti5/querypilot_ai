"""No network: bounded orchestration with scripted model responses and real registry validation."""

import asyncio
import json
import logging
import time
from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock

import pytest

from querypilot.agent.evidence import bound_result
from querypilot.agent.mock import MockProvider
from querypilot.agent.orchestrator import SingleRoundService
from querypilot.agent.provider import ProviderError, ProviderTurn
from querypilot.agent.tool_schemas import function_schemas, normalize_arguments
from querypilot.core.config import Settings
from querypilot.core.logging import configure_logging
from querypilot.schemas.analytics import ToolResult
from querypilot.tools.registry import ToolRegistry, create_registry


@pytest.fixture(autouse=True)
def isolated_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = logging.getLogger("querypilot")
    monkeypatch.setattr(logger, "handlers", [logging.NullHandler()])
    monkeypatch.setattr(logger, "propagate", False)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key=None,
        openai_model=None,
        database_url=None,
        reader_database_url=None,
    )


def call(name="get_top_products", arguments='{"limit":5}', call_id="call_1") -> dict:
    return {"type": "function_call", "name": name, "arguments": arguments, "call_id": call_id}


class ScriptedProvider:
    mode = "mock"

    def __init__(self, turns: list):
        self.turns = iter(turns)
        self.requests = []

    async def respond(self, instructions, history, tools, *, final=False):
        self.requests.append(
            {"history": deepcopy(history), "tools": deepcopy(tools), "final": final}
        )
        assert "UNTRUSTED DATA" in instructions
        value = next(self.turns)
        if isinstance(value, Exception):
            raise value
        return value


def product_registry() -> tuple[ToolRegistry, Mock]:
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
    return ToolRegistry(repository), repository


def execute(provider, registry, settings, question="Top products?"):
    return asyncio.run(SingleRoundService(provider, registry, settings).run(question))


def test_all_schemas_strict_and_synchronized() -> None:
    definitions = ToolRegistry().definitions()
    snapshot = deepcopy(definitions)
    tools = function_schemas(definitions)
    assert len(tools) == 6
    assert definitions == snapshot
    for tool in tools:
        schema = tool["parameters"]
        assert tool["strict"] is True
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
    top = next(tool for tool in tools if tool["name"] == "get_top_products")
    limit = top["parameters"]["properties"]["limit"]["anyOf"][0]
    assert limit["minimum"] == 1 and limit["maximum"] == 20
    search = next(tool for tool in tools if tool["name"] == "search_business_documents")
    assert search["parameters"]["properties"]["query"]["maxLength"] == 500
    assert "anyOf" not in search["parameters"]["properties"]["query"]
    assert normalize_arguments(
        "get_top_products", {"limit": None, "start_date": None}, definitions
    ) == {"start_date": None}


def test_multiple_calls_protocol_reasoning_and_citations(settings: Settings) -> None:
    registry, repository = product_registry()
    reasoning = {"type": "reasoning", "id": "rs_1", "encrypted_content": "opaque", "summary": []}
    provider = ScriptedProvider(
        [
            ProviderTurn(
                [
                    reasoning,
                    call(arguments='{"limit":null,"start_date":null,"end_date":null}'),
                    call(
                        "search_business_documents", '{"query":"return window","top_k":1}', "call_2"
                    ),
                ]
            ),
            ProviderTurn(
                [], "Sample: USD 19.98 [E1]. Returns within 30 days [E2] [QP-RET-001#s002-c001]."
            ),
        ]
    )
    result = execute(provider, registry, settings)
    assert result.status == "completed"
    assert result.grounding_checks == "passed"
    assert len(result.tools) == 2
    assert repository.execute.call_args.args[1].limit == 5
    assert len(provider.requests) == 2
    second = provider.requests[1]
    assert second["final"] is True
    assert reasoning in second["history"]
    outputs = [item for item in second["history"] if item.get("type") == "function_call_output"]
    assert [item["call_id"] for item in outputs] == ["call_1", "call_2"]
    assert json.loads(outputs[0]["output"])["evidence_id"] == "E1"
    assert result.tools[1].citations == ["QP-RET-001#s002-c001"]
    assert (
        sum(len(item["output"].encode()) for item in outputs) <= settings.llm_total_evidence_bytes
    )
    assert "opaque" not in result.model_dump_json()


@pytest.mark.parametrize(
    "raw", ["not-json", "[]", '{"limit":NaN}', '{"limit":1,"limit":2}', "x" * 4097]
)
def test_invalid_json_never_executes(raw: str, settings: Settings) -> None:
    registry, repository = product_registry()
    result = execute(ScriptedProvider([ProviderTurn([call(arguments=raw)])]), registry, settings)
    assert result.status == "no_evidence"
    assert result.tools[0].error.code == "invalid_json"
    assert result.tools[0].arguments == {}
    repository.execute.assert_not_called()


def test_unknown_function_rejected_without_echo(settings: Settings) -> None:
    registry, repository = product_registry()
    result = execute(
        ScriptedProvider([ProviderTurn([call(name="SECRET_SQL_TOOL")])]), registry, settings
    )
    assert result.tools[0].tool is None
    assert result.tools[0].error.code == "unknown_tool"
    assert "SECRET_SQL_TOOL" not in result.model_dump_json()
    repository.execute.assert_not_called()


def test_pydantic_arguments_revalidated(settings: Settings) -> None:
    registry, repository = product_registry()
    result = execute(
        ScriptedProvider([ProviderTurn([call(arguments='{"limit":99}')])]), registry, settings
    )
    assert result.tools[0].error.code == "invalid_arguments"
    repository.execute.assert_not_called()


def test_no_calls_never_forwards_unsupported_model_claim(settings: Settings) -> None:
    provider = ScriptedProvider([ProviderTurn([], "Revenue is USD 999999.")])
    result = execute(provider, ToolRegistry(), settings)
    assert result.status == "no_evidence"
    assert "999999" not in result.answer
    assert len(provider.requests) == 1


def test_empty_results_and_failures_are_distinct(settings: Settings) -> None:
    registry = ToolRegistry(Mock())
    registry._repository.execute.return_value = ([], False)
    provider = ScriptedProvider([ProviderTurn([call()])])
    empty = execute(provider, registry, settings)
    assert "no matching data" in empty.answer
    assert empty.tools[0].status == "success"
    failed = execute(
        ScriptedProvider([ProviderTurn([call()])]), create_registry(settings), settings
    )
    assert "retrieval failed" in failed.answer
    assert failed.tools[0].error.code == "reader_configuration_missing"


@pytest.mark.parametrize(
    "calls",
    [
        [call(call_id="duplicate"), call(call_id="duplicate")],
        [{"type": "function_call", "name": "get_top_products", "arguments": "{}"}],
        [{"type": "function_call", "call_id": "c", "name": "get_top_products", "arguments": {}}],
        [call(call_id=f"c{i}") for i in range(7)],
    ],
)
def test_malformed_or_excessive_batch_is_rejected(calls: list, settings: Settings) -> None:
    registry, repository = product_registry()
    result = execute(ScriptedProvider([ProviderTurn(calls)]), registry, settings)
    assert result.status == "error"
    assert result.errors[0].code in ("provider_response_error", "tool_limit")
    repository.execute.assert_not_called()


def test_followup_cannot_start_day7_loop(settings: Settings) -> None:
    registry, repository = product_registry()
    result = execute(
        ScriptedProvider([ProviderTurn([call()]), ProviderTurn([call(call_id="c2")])]),
        registry,
        settings,
    )
    assert result.errors[0].code == "unexpected_tool_call"
    assert repository.execute.call_count == 1
    assert result.answer is None


@pytest.mark.parametrize(
    "answer",
    [
        "Revenue USD 999.99 [E1]",
        "Revenue USD -19.98 [E1]",
        "Revenue USD 19.98 [E99]",
        "Revenue USD 19.98",
    ],
)
def test_unsupported_numeric_claims_and_citations_fail_closed(
    answer: str, settings: Settings
) -> None:
    registry, _ = product_registry()
    result = execute(
        ScriptedProvider([ProviderTurn([call()]), ProviderTurn([], answer)]), registry, settings
    )
    assert result.status == "error"
    assert result.errors[0].code == "grounding_error"
    assert result.answer is None


@pytest.mark.parametrize(
    "answer", ["Returns within 30 days [E1]", "Returns within 30 days [E1] [QP-FAKE-999#s001-c001]"]
)
def test_document_citations_must_be_preserved(answer: str, settings: Settings) -> None:
    provider = ScriptedProvider(
        [
            ProviderTurn(
                [call("search_business_documents", '{"query":"return window","top_k":1}')]
            ),
            ProviderTurn([], answer),
        ]
    )
    result = execute(provider, create_registry(settings), settings)
    assert result.errors[0].code == "grounding_error"


def test_evidence_is_structurally_bounded_without_mutating_original() -> None:
    registry, repository = product_registry()
    row = repository.execute.return_value[0][0]
    repository.execute.return_value = (
        [{**row, "product_id": index + 1, "name": "X" * 120} for index in range(20)],
        False,
    )
    original = registry.execute("get_top_products", {"limit": 20})
    bounded, output, truncated = bound_result(original, "E1", max_rows=10, max_bytes=1000)
    assert truncated and bounded.data.truncated
    assert len(output.encode()) <= 1000
    assert 0 < len(bounded.data.rows) < len(original.data.rows) == 20
    ToolResult.model_validate(json.loads(output)["result"])


def test_tool_deadline_skips_remaining_calls(settings: Settings) -> None:
    registry, repository = product_registry()
    rows = repository.execute.return_value

    def slow(*args):
        time.sleep(0.05)
        return rows

    repository.execute.side_effect = slow
    settings.llm_tool_timeout_seconds = 0.01
    result = execute(
        ScriptedProvider([ProviderTurn([call(), call(call_id="call_2")])]), registry, settings
    )
    assert result.tools[0].error.code == "tool_timeout"
    assert result.tools[1].error.code == "not_executed"
    assert repository.execute.call_count == 1


def test_second_provider_failure_keeps_tool_evidence(settings: Settings) -> None:
    registry, _ = product_registry()
    result = execute(
        ScriptedProvider(
            [ProviderTurn([call()]), ProviderError("network_error", "Provider unavailable.")]
        ),
        registry,
        settings,
    )
    assert result.status == "error"
    assert result.tools[0].result.status == "success"
    assert result.errors[0].code == "network_error"


def test_mock_mode_uses_real_document_tool_without_key(settings: Settings) -> None:
    result = execute(
        MockProvider(), create_registry(settings), settings, "What is the return policy?"
    )
    assert result.status == "completed"
    assert result.mode == "mock"
    assert "30 calendar days" in result.answer
    assert "QP-RET-001#s002-c001" in result.answer


def test_logs_exclude_question_provider_and_evidence_text(settings: Settings, capsys) -> None:
    configure_logging("INFO")
    registry, _ = product_registry()
    execute(
        ScriptedProvider([ProviderTurn([call()]), ProviderTurn([], "Sample USD 19.98 [E1]")]),
        registry,
        settings,
        "SECRET_QUESTION",
    )
    output = capsys.readouterr().err
    assert "SECRET_QUESTION" not in output
    assert "19.98" not in output
    records = [json.loads(line) for line in output.splitlines()]
    assert any(record["event"] == "llm_execution" for record in records)


def test_live_cli_missing_key_does_not_substitute_mock(settings: Settings, monkeypatch) -> None:
    from querypilot.agent.cli import ask

    monkeypatch.setattr("querypilot.agent.cli.Settings", lambda: settings)
    result = asyncio.run(ask("Return policy?", live=True))
    assert result.mode == "live" and result.status == "error"
    assert result.errors[0].code == "configuration_error"


@pytest.mark.parametrize("question", [" ", "x" * 4001, 123])
def test_invalid_question_never_calls_provider(question: object, settings: Settings) -> None:
    provider = ScriptedProvider([])
    result = execute(provider, ToolRegistry(), settings, question)
    assert result.errors[0].code == "invalid_question"
    assert result.question == ""
    assert provider.requests == []


def test_query_numbers_are_not_treated_as_document_evidence(settings: Settings) -> None:
    provider = ScriptedProvider(
        [
            ProviderTurn(
                [call("search_business_documents", '{"query":"return window 999","top_k":1}')]
            ),
            ProviderTurn([], "Returns within 999 days [E1] [QP-RET-001#s002-c001]."),
        ]
    )
    result = execute(provider, create_registry(settings), settings)
    assert result.errors[0].code == "grounding_error"


def test_document_sources_must_belong_to_cited_evidence(settings: Settings) -> None:
    provider = ScriptedProvider(
        [
            ProviderTurn(
                [
                    call("search_business_documents", '{"query":"return window","top_k":1}'),
                    call(
                        "search_business_documents",
                        '{"query":"failed payments","top_k":1}',
                        "call_2",
                    ),
                ]
            ),
            ProviderTurn(
                [], "Returns within 30 days [E1] [QP-RET-001#s002-c001] [QP-PAY-003#s002-c001]."
            ),
        ]
    )
    result = execute(provider, create_registry(settings), settings)
    assert result.errors[0].code == "grounding_error"


def test_tiny_total_evidence_budget_is_safe(settings: Settings) -> None:
    registry, repository = product_registry()
    row = repository.execute.return_value[0][0]
    repository.execute.return_value = ([{**row, "name": "X" * 120}], False)
    settings.llm_total_evidence_bytes = 2000
    provider = ScriptedProvider([ProviderTurn([call(call_id=f"call_{i}") for i in range(6)])])
    result = execute(provider, registry, settings)
    assert result.status == "no_evidence"
    assert all(trace.error.code == "evidence_limit" for trace in result.tools)
    assert len(provider.requests) == 1
