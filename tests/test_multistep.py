"""Deterministic loop contracts using real registry validation, with no model network."""

import asyncio
import json
import logging
import subprocess
import sys
import time
from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from querypilot.agent.mock import MultiStepMockProvider
from querypilot.agent.multistep import MULTISTEP_INSTRUCTIONS, MultiStepService, encoded_size
from querypilot.agent.provider import ProviderError, ProviderTurn
from querypilot.core.config import Settings
from querypilot.core.logging import configure_logging
from querypilot.db.session import DatabaseError
from querypilot.tools.registry import ToolRegistry


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        reader_database_url=None,
        database_url=None,
        openai_api_key=None,
        openai_model=None,
    )


@pytest.fixture
def registry():
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
    return ToolRegistry(repository)


def call(name="get_top_products", arguments='{"limit":5}', identifier="c1"):
    return {"type": "function_call", "call_id": identifier, "name": name, "arguments": arguments}


def doc(identifier="c2"):
    return call(
        "search_business_documents", '{"query":"product return window","top_k":1}', identifier
    )


class Scripted:
    mode = "mock"

    def __init__(self, turns):
        self.turns, self.requests = iter(turns), []

    async def respond(self, instructions, history, tools, *, final=False):
        self.requests.append(deepcopy(history))
        assert not final
        assert len(tools) == 6
        assert "UNTRUSTED DATA" in instructions
        value = next(self.turns)
        if isinstance(value, Exception):
            raise value
        return value


def run(turns, registry, settings):
    provider = Scripted(turns)
    outcome = asyncio.run(MultiStepService(provider, registry, settings).run("Business question"))
    return outcome, provider


def test_one_round(settings, registry):
    result, provider = run(
        [ProviderTurn([call()]), ProviderTurn([], "Sample USD 19.98 [E1].")], registry, settings
    )
    assert result.status == "completed" and result.iterations == 2
    assert result.tools[0].iteration == 1
    assert result.elapsed_ms >= 0
    assert len(provider.requests) == 2


@pytest.mark.parametrize("reverse", [False, True])
def test_sql_and_documents_in_either_order(reverse, settings, registry):
    first, second = (doc("c1"), call(identifier="c2")) if reverse else (call(), doc())
    sql_id, doc_id = ("E2", "E1") if reverse else ("E1", "E2")
    reasoning = {"type": "reasoning", "id": "rs1", "encrypted_content": "PRIVATE", "summary": []}
    result, provider = run(
        [
            ProviderTurn([reasoning, first]),
            ProviderTurn([second]),
            ProviderTurn(
                [],
                f"Sample USD 19.98 [{sql_id}]. Returns within 30 days "
                f"[{doc_id}] [QP-RET-001#s002-c001].",
            ),
        ],
        registry,
        settings,
    )
    assert result.status == "completed" and result.iterations == 3
    assert [trace.iteration for trace in result.tools] == [1, 2]
    outputs = [item for item in provider.requests[2] if item.get("type") == "function_call_output"]
    assert [item["call_id"] for item in outputs] == ["c1", "c2"]
    assert reasoning in provider.requests[1] and reasoning in provider.requests[2]
    assert "PRIVATE" not in result.model_dump_json()


def test_multiple_calls_per_iteration(settings, registry):
    result, provider = run(
        [
            ProviderTurn([call(), doc()]),
            ProviderTurn(
                [], "Sample USD 19.98 [E1]. Returns within 30 days [E2] [QP-RET-001#s002-c001]."
            ),
        ],
        registry,
        settings,
    )
    assert result.status == "completed"
    assert [trace.iteration for trace in result.tools] == [1, 1]
    assert len(provider.requests) == 2


@pytest.mark.parametrize(
    "arguments", ["{}", '{"limit":null}', '{"end_date":null,"limit":5,"start_date":null}']
)
def test_repeated_calls_skip_repository_and_recover(arguments, settings, registry):
    result, provider = run(
        [
            ProviderTurn([call()]),
            ProviderTurn([call(arguments=arguments, identifier="c2")]),
            ProviderTurn([], "Sample USD 19.98 [E1]."),
        ],
        registry,
        settings,
    )
    assert result.status == "completed"
    assert result.tools[1].error.code == "repeated_call"
    assert registry._repository.execute.call_count == 1
    assert "repeated_call" in provider.requests[2][-1]["output"]


@pytest.mark.parametrize(
    "bad,code",
    [
        (call("PRIVATE_UNKNOWN"), "unknown_tool"),
        (call(arguments="not json"), "invalid_json"),
        (call(arguments='{"limit":NaN}'), "invalid_json"),
        (call(arguments='{"limit":1,"limit":2}'), "invalid_json"),
        (call(arguments='{"sql":"DROP TABLE products"}'), "invalid_arguments"),
        (call(arguments='{"limit":99}'), "invalid_arguments"),
    ],
)
def test_bad_call_then_recovery(bad, code, settings, registry):
    result, provider = run(
        [
            ProviderTurn([bad]),
            ProviderTurn([doc()]),
            ProviderTurn([], "Returns within 30 days [E2] [QP-RET-001#s002-c001]."),
        ],
        registry,
        settings,
    )
    assert result.status == "completed" and result.tools[0].error.code == code
    assert result.tools[0].arguments == {}
    registry._repository.execute.assert_not_called()
    assert code in provider.requests[1][-1]["output"]
    assert "DROP TABLE" not in result.model_dump_json()
    assert "PRIVATE_UNKNOWN" not in result.model_dump_json()


def test_failure_then_document_recovery(settings, registry):
    registry._repository.execute.side_effect = DatabaseError("SECRET_DATABASE_DETAIL")
    result, _ = run(
        [
            ProviderTurn([call()]),
            ProviderTurn([doc()]),
            ProviderTurn([], "Returns within 30 days [E2] [QP-RET-001#s002-c001]."),
        ],
        registry,
        settings,
    )
    assert result.status == "completed"
    assert result.errors[0].code == "database_error"
    assert "SECRET_DATABASE_DETAIL" not in result.model_dump_json()


@pytest.mark.parametrize("failure", [False, True])
def test_empty_or_failed_results_return_distinct_uncertainty(failure, settings, registry):
    if failure:
        registry._repository.execute.side_effect = DatabaseError("private")
    else:
        registry._repository.execute.return_value = ([], False)
    result, provider = run(
        [ProviderTurn([call()]), ProviderTurn([], "Invented USD 9999")], registry, settings
    )
    assert result.status == "no_evidence"
    assert ("retrieval failed" if failure else "No matching evidence") in result.answer
    assert "9999" not in result.answer
    assert len(provider.requests) == 2


def test_no_tools_no_unsupported_claim(settings, registry):
    result, _ = run([ProviderTurn([], "Profit is USD 9999")], registry, settings)
    assert result.status == "no_evidence" and "9999" not in result.answer


@pytest.mark.parametrize(
    "answer",
    [
        "Revenue 99999 [E1]",
        "Revenue 19.98 [E99]",
        "Revenue 19.98",
        "Revenue 19.98 [E1] [QP-FAKE-999#s001-c001]",
    ],
)
def test_final_grounding_rejected(answer, settings, registry):
    result, _ = run([ProviderTurn([call()]), ProviderTurn([], answer)], registry, settings)
    assert result.status == "error" and result.answer is None
    assert result.grounding_checks == "failed"


def test_iteration_limit(settings, registry):
    settings.agent_max_iterations = 2
    result, provider = run([ProviderTurn([call()]), ProviderTurn([doc()])], registry, settings)
    assert result.errors[-1].code == "iteration_limit" and result.answer is None
    assert len(provider.requests) == 2


@pytest.mark.parametrize("per_round", [False, True])
def test_tool_limits_reject_whole_batch(per_round, settings, registry):
    if per_round:
        settings.agent_max_tools_per_iteration = 1
        turns = [ProviderTurn([call(), doc()])]
    else:
        settings.agent_max_tool_calls = 2
        turns = [ProviderTurn([call()]), ProviderTurn([doc(), call(identifier="c3")])]
    result, _ = run(turns, registry, settings)
    assert result.errors[-1].code == "tool_limit"
    assert len(result.tools) == (0 if per_round else 1)
    assert registry._repository.execute.call_count == (0 if per_round else 1)


def test_exact_total_limit_allows_answer(settings, registry):
    settings.agent_max_tool_calls = 1
    result, _ = run(
        [ProviderTurn([call()]), ProviderTurn([], "Revenue 19.98 [E1]")], registry, settings
    )
    assert result.status == "completed"


@pytest.mark.parametrize("across_rounds", [False, True])
def test_duplicate_protocol_ids_rejected(across_rounds, settings, registry):
    turns = (
        [ProviderTurn([call()]), ProviderTurn([doc("c1")])]
        if across_rounds
        else [ProviderTurn([call(), doc("c1")])]
    )
    result, _ = run(turns, registry, settings)
    assert result.errors[-1].code == "provider_response_error"
    assert len(result.tools) == (1 if across_rounds else 0)


@pytest.mark.parametrize("overall", [False, True])
def test_model_and_overall_deadlines(overall, settings, registry):
    class Slow:
        mode = "mock"

        async def respond(self, *args, **kwargs):
            await asyncio.sleep(0.2)

    if overall:
        settings.agent_timeout_seconds = 0.01
    else:
        settings.llm_request_timeout_seconds = 0.05
    result = asyncio.run(MultiStepService(Slow(), registry, settings).run("Question"))
    assert result.errors[-1].code == ("agent_timeout" if overall else "provider_timeout")
    registry._repository.execute.assert_not_called()


def test_tool_deadline_stops_remaining_work(settings, registry):
    value = registry._repository.execute.return_value

    def slow(*args):
        time.sleep(0.05)
        return value

    registry._repository.execute.side_effect = slow
    settings.llm_tool_timeout_seconds = 0.01
    result, provider = run([ProviderTurn([call(), doc()])], registry, settings)
    assert result.errors[-1].code == "tool_timeout"
    assert len(result.tools) == 1 and len(provider.requests) == 1


def test_context_limit_before_first_request(settings, registry):
    settings.agent_max_context_bytes = 1000
    result, provider = run([], registry, settings)
    assert result.errors[-1].code == "context_limit"
    assert provider.requests == []


def test_context_growth_stops_before_tool_execution(settings, registry):
    # The initial schemas fit; oversized returned reasoning cannot be accumulated.
    reasoning = {"type": "reasoning", "encrypted_content": "X" * 60000}
    settings.agent_max_context_bytes = 50000
    result, provider = run([ProviderTurn([reasoning, call()])], registry, settings)
    assert result.errors[-1].code == "context_limit"
    registry._repository.execute.assert_not_called()
    assert len(provider.requests) == 1


def test_utf8_context_size():
    assert encoded_size({"x": "é"}) > len(
        json.dumps({"x": "é"}, ensure_ascii=False, separators=(",", ":"))
    )


def test_accumulated_error_packets_cannot_exceed_replay_budget(settings, registry):
    settings.agent_max_tool_calls = 20
    settings.llm_total_evidence_bytes = 2000
    turns = [
        ProviderTurn([call(identifier=f"c{batch}_{i}") for i in range(5)]) for batch in range(4)
    ]
    result, provider = run(turns, registry, settings)
    assert result.errors[-1].code == "evidence_limit"
    assert result.answer is None
    for history in provider.requests:
        outputs = [item["output"] for item in history if item.get("type") == "function_call_output"]
        assert sum(len(output.encode()) for output in outputs) <= 2000
    assert registry._repository.execute.call_count == 1


def test_evidence_payload_bounded(settings, registry):
    row = registry._repository.execute.return_value[0][0]
    registry._repository.execute.return_value = (
        [{**row, "name": "X" * 120} for _ in range(20)],
        False,
    )
    settings.llm_max_evidence_bytes = 1000
    result, provider = run(
        [ProviderTurn([call(arguments='{"limit":20}')]), ProviderTurn([], "Revenue 19.98 [E1]")],
        registry,
        settings,
    )
    assert result.status == "completed" and result.tools[0].output_truncated
    assert len(provider.requests[1][-1]["output"].encode()) <= 1000


def test_state_isolated_for_concurrent_requests(settings):
    async def scenario():
        service = MultiStepService(
            MultiStepMockProvider(), ToolRegistry(settings=settings), settings
        )
        return await asyncio.gather(
            service.run("What is the return policy?"),
            service.run("How are failed payments handled?"),
        )

    first, second = asyncio.run(scenario())
    assert first.status == second.status == "completed"
    assert first.trace_id != second.trace_id
    assert first.tools[0].evidence_id == second.tools[0].evidence_id == "E1"
    assert "QP-RET-001" in first.answer and "QP-PAY-003" in second.answer
    assert "QP-RET-001" not in second.answer


@pytest.mark.parametrize(
    "name,value",
    [
        ("agent_max_iterations", 0),
        ("agent_max_iterations", 11),
        ("agent_max_tool_calls", 0),
        ("agent_max_tool_calls", 21),
        ("agent_max_tools_per_iteration", 0),
        ("agent_max_tools_per_iteration", 7),
        ("agent_timeout_seconds", 0),
        ("agent_timeout_seconds", 301),
        ("agent_timeout_seconds", float("inf")),
        ("agent_timeout_seconds", float("nan")),
        ("agent_max_context_bytes", 999),
        ("agent_max_context_bytes", 512001),
    ],
)
def test_configuration_hard_bounds(name, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{name: value})


def test_provider_failure_preserves_previous_evidence(settings, registry):
    result, _ = run(
        [ProviderTurn([call()]), ProviderError("network_error", "Provider unavailable.")],
        registry,
        settings,
    )
    assert result.errors[-1].code == "network_error"
    assert result.tools[0].result.status == "success"


def test_all_six_tools_remain_accessible(settings, registry):
    registry._repository.execute.return_value = ([], False)
    names = list(registry.definitions())
    turns = [
        ProviderTurn(
            [
                call(
                    name,
                    '{"query":"return window"}' if name == "search_business_documents" else "{}",
                    f"c{i}",
                )
                for i, name in enumerate(names[:5])
            ]
        ),
        ProviderTurn([call(names[5], "{}", "last")]),
        ProviderTurn([], "Returns within 30 days [E1] [QP-RET-001#s002-c001]."),
    ]
    result, _ = run(turns, registry, settings)
    assert result.status == "completed"
    assert {trace.tool for trace in result.tools} == set(names)
    assert all(trace.status == "success" for trace in result.tools)


def test_multistep_instructions_remove_single_round_rule():
    assert "ONE batch" not in MULTISTEP_INSTRUCTIONS
    assert "additional rounds" in MULTISTEP_INSTRUCTIONS


def test_invented_short_document_id_rejected(settings, registry):
    result, _ = run(
        [ProviderTurn([call()]), ProviderTurn([], "Revenue 19.98 [E1] [QP-FAKE-999]")],
        registry,
        settings,
    )
    assert result.errors[-1].code == "grounding_error"


def test_ten_call_identifiers_and_repeats_count_toward_budget(settings, registry):
    turns = [
        ProviderTurn([call(identifier=f"c{i}") for i in range(5)]),
        ProviderTurn([call(identifier=f"c{i}") for i in range(5, 10)]),
        ProviderTurn([], "Sample 19.98 [E1]"),
    ]
    result, _ = run(turns, registry, settings)
    assert result.status == "completed"
    assert result.tools[-1].evidence_id == "E10"
    assert registry._repository.execute.call_count == 1
    assert len(result.errors) == 9


@pytest.mark.parametrize(
    "answer", ["Returns within 30 days [E1]", "Returns within 30 days [E1] [QP-FAKE-999#s001-c001]"]
)
def test_document_citation_validation_after_rounds(answer, settings, registry):
    result, _ = run([ProviderTurn([doc("c1")]), ProviderTurn([], answer)], registry, settings)
    assert result.errors[-1].code == "grounding_error" and result.answer is None


def test_logs_exclude_internal_state(settings, registry, capsys, monkeypatch):
    logger = logging.getLogger("querypilot")
    original_handlers = logger.handlers[:]
    monkeypatch.setattr(logger, "handlers", original_handlers)
    monkeypatch.setattr(logger, "propagate", False)
    configure_logging("INFO")
    provider = Scripted([ProviderTurn([call()]), ProviderTurn([], "Sample 19.98 [E1]")])
    result = asyncio.run(MultiStepService(provider, registry, settings).run("PRIVATE_QUESTION"))
    output = capsys.readouterr().err
    assert "PRIVATE_QUESTION" not in output and "19.98" not in output
    assert "UNTRUSTED DATA" not in output
    assert any(json.loads(line).get("trace_id") == result.trace_id for line in output.splitlines())


@pytest.mark.parametrize("verbose", [False, True])
def test_cli_limits_and_optional_traces(verbose, settings, monkeypatch, capsys):
    from querypilot.agent.cli import main

    monkeypatch.setattr(
        "querypilot.agent.cli.Settings", lambda **limits: Settings(_env_file=None, **limits)
    )
    arguments = ["What is the return policy?", "--mock", "--max-iterations", "3"]
    if verbose:
        arguments.append("--verbose")
    main(arguments)
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "completed" and value["iterations"] == 2
    assert ("result" in value["tools"][0]) == verbose
    assert ("question" in value) == verbose


def test_cli_invalid_limit_returns_safe_error(monkeypatch, capsys):
    from querypilot.agent.cli import main

    monkeypatch.setattr(
        "querypilot.agent.cli.Settings", lambda **limits: Settings(_env_file=None, **limits)
    )
    with pytest.raises(SystemExit) as error:
        main(["Return policy?", "--mock", "--max-iterations", "999"])
    assert error.value.code == 1
    value = json.loads(capsys.readouterr().out)
    assert value["errors"][0]["code"] == "configuration_error"
    assert "999" not in json.dumps(value)


def test_public_cli_help_forwards_ask_options():
    result = subprocess.run(
        [sys.executable, "-m", "querypilot.cli", "ask", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--max-iterations" in result.stdout and "--verbose" in result.stdout
