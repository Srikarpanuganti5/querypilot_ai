"""Independent scoring fixtures; these unit tests do not prove real service readiness."""

import asyncio
import json

import pytest
from pydantic import ValidationError

from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard
from querypilot.evaluation.dataset import Case, Dataset, load_dataset
from querypilot.evaluation.metrics import (
    citation_metrics,
    failure_category,
    latency,
    literal_present,
    retrieval_metrics,
    score_case,
    sequence_matches,
    tool_metrics,
)
from querypilot.evaluation.reports import write_reports
from querypilot.evaluation.runner import run_evaluation
from querypilot.schemas.analytics import ToolResult
from querypilot.schemas.llm import ExecutionError, ExecutionOutcome, ToolExecution

TOP = "get_top_products"
DOC = "search_business_documents"


def config():
    return Settings(
        _env_file=None,
        database_url=None,
        reader_database_url=None,
        openai_api_key=None,
        openai_model=None,
    )


def example(answer="Sample Product: USD 12.50 [E1]."):
    result = ToolResult.model_validate(
        dict(
            tool=TOP,
            status="success",
            duration_ms=2,
            data=dict(
                operation=TOP,
                rows=[
                    dict(
                        product_id=1,
                        name="Sample Product",
                        category="Office",
                        units_sold=2,
                        revenue="12.50",
                    )
                ],
                truncated=False,
            ),
        )
    )
    return ExecutionOutcome(
        trace_id="fixture",
        mode="mock",
        question="Test",
        status="completed",
        answer=answer,
        iterations=2,
        tools=[
            ToolExecution(
                evidence_id="E1", call_id="test1", tool=TOP, status="success", result=result
            )
        ],
    )


def case(**values):
    return Case(id="unit", question="Test", category="unit", expected_tools=[TOP], **values)


@pytest.mark.parametrize(
    "expected,actual,allowed,p,r,f,exact",
    [
        ([], [], [], 1, 1, 1, True),
        ([], ["a"], [], 0, 1, 0, False),
        (["a"], [], [], 1, 0, 0, False),
        (["a", "b"], ["a", "c"], [], 0.5, 0.5, 0.5, False),
        (["a", "b"], ["a"], [], 1, 0.5, 2 / 3, False),
        (["a"], ["a", "a"], [], 1, 1, 1, True),
        (["a"], ["a", "b"], ["b"], 1, 1, 1, True),
        ([], ["b"], ["b"], 1, 1, 1, True),
    ],
)
def test_tool_formulas(expected, actual, allowed, p, r, f, exact):
    value = tool_metrics(expected, actual, allowed)
    assert value["precision"] == p and value["recall"] == r
    assert value["f1"] == pytest.approx(f) and value["exact"] == exact
    assert value["repeated_attempts"] == len(actual) - len(set(actual))


@pytest.mark.parametrize(
    "expected,actual,ok",
    [
        (["a", "b"], ["a", "x", "b"], True),
        (["a", "b"], ["b", "a"], False),
        ([], ["b"], True),
        (["a", "a"], ["a"], False),
    ],
)
def test_sequence_dependencies(expected, actual, ok):
    assert sequence_matches(expected, actual) is ok


def test_retrieval_independent_ranking_and_denominators():
    value = retrieval_metrics(["b", "d"], ["a", "a", "b", "c"], 3)
    assert value["precision_at_k"] == pytest.approx(1 / 3)
    assert value["recall_at_k"] == 0.5 and value["reciprocal_rank"] == 0.5
    assert value["hit_at_k"] == 1
    assert retrieval_metrics(["a"], [], 5)["reciprocal_rank"] == 0
    assert retrieval_metrics([], ["a"], 5)["precision_at_k"] is None
    with pytest.raises(ValueError):
        retrieval_metrics(["a"], [], 0)


def test_latency_nearest_rank_and_empty():
    value = latency(list(range(1, 21)))
    assert value == dict(samples=20, mean_ms=10.5, median_ms=10.5, p95_ms=19, min_ms=1, max_ms=20)
    assert latency([])["mean_ms"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_id",
        "unknown_tool",
        "duplicate_tool",
        "unknown_field",
        "unjudged_query",
        "empty_question",
    ],
)
def test_dataset_rejects_invalid_cases(mutation):
    value = dict(
        version="test-v1",
        reference_date="2026-10-27",
        random_seed=42,
        ground_truth_method="Independent fixture",
        cases=[case().model_dump()],
    )
    item = value["cases"][0]
    if mutation == "duplicate_id":
        value["cases"].append(item.copy())
    elif mutation == "unknown_tool":
        item["expected_tools"] = ["execute_sql"]
    elif mutation == "duplicate_tool":
        item["expected_tools"] = [TOP, TOP]
    elif mutation == "unknown_field":
        item["arbitrary_sql"] = "SELECT 1"
    elif mutation == "unjudged_query":
        item["relevant_documents"] = ["QP-RET-001"]
    else:
        item["question"] = ""
    with pytest.raises(ValidationError):
        Dataset.model_validate(value)


def test_curated_dataset_rebuild_is_independent_and_stable():
    from scripts.build_evaluation_dataset import build

    dataset, checksum = load_dataset()
    assert dataset == build() and len(checksum) == 64
    assert 30 <= len(dataset.cases) <= 50
    assert len({item.category for item in dataset.cases}) >= 12
    assert {fact.tool for item in dataset.cases for fact in item.facts} == {
        TOP,
        "get_revenue_summary",
        "get_refund_analytics",
        "get_customer_order_summary",
        "get_payment_status_summary",
    }


def test_dataset_byte_bound(tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 1_000_001)
    with pytest.raises(ValueError, match="byte limit"):
        load_dataset(path)


@pytest.mark.parametrize(
    "answer,expected",
    [
        ("Sample Product: USD 12.50 [E1].", True),
        ("Sample Product: USD 99.50 [E1].", False),
        ("Sample Product: USD 12.50 [E9].", False),
        ("Sample Product: USD 12.50 [E1].\n999 sales.", False),
    ],
)
def test_independent_numeric_and_failed_reference_checks(answer, expected):
    value = score_case(case(), example(answer), {})
    assert value["passed"] is expected
    assert value["semantic_faithfulness"] == "NOT EVALUATED"


def test_facts_require_correct_row_field_and_answer_source():
    reference = case(
        facts=[dict(tool=TOP, where={"product_id": 1}, field="revenue", value="12.50")]
    )
    assert score_case(reference, example(), {})["passed"]
    assert not score_case(reference, example("USD 12.50 [E2]."), {})["passed"]
    wrong = reference.model_copy(
        update={"facts": [reference.facts[0].model_copy(update={"where": {"product_id": 999}})]}
    )
    assert not score_case(wrong, example(), {})["checks"]["facts"]
    assert not literal_present(486, "1486 failed")
    assert not literal_present("12.50", "112.50")
    assert literal_present("12.50", "USD 12.50 [E1]")


def test_ranking_is_checked_separately_from_value_membership():
    assert score_case(case(ranked_product_ids=[1]), example(), {})["checks"]["product_ranking"]
    assert not score_case(case(ranked_product_ids=[2, 1]), example(), {})["checks"][
        "product_ranking"
    ]


def test_failed_tools_cannot_be_successful_evidence():
    outcome = example("USD 12.50 [E1].")
    outcome.tools[0] = ToolExecution(
        evidence_id="E1",
        call_id="failed",
        tool=TOP,
        status="error",
        error=ExecutionError(code="database_unavailable", message="Safe error"),
    )
    result = score_case(case(evidence_types=["sql"]), outcome, {})
    assert not result["checks"]["evidence_types"] and not result["checks"]["citation_integrity"]


def test_citation_existence_retrieval_and_provenance_are_different(document_response):
    outcome = document_response
    citation = "QP-RET-001#s002-c001"
    corpus = {citation: "QP-RET-001", "QP-PAY-003#s002-c001": "QP-PAY-003"}
    valid = citation_metrics(outcome, corpus)
    assert valid["id_validity"]["value"] == 1 and valid["retrieved_provenance"]["value"] == 1
    forged = outcome.model_copy(update={"answer": "Wrong [E1] [QP-PAY-003#s002-c001]"})
    score = citation_metrics(forged, corpus)
    assert score["id_validity"]["value"] == 1 and score["retrieved_provenance"]["value"] == 0
    assert score["fabricated"] == ["QP-PAY-003#s002-c001"]
    assert score["claim_support"] == "NOT EVALUATED"
    wrong_source = Case(
        id="wrong-source",
        question="Payment methods?",
        category="documents",
        expected_tools=[DOC],
        retrieval_query="payment methods",
        relevant_documents=["QP-PAY-003"],
    )
    assert not score_case(wrong_source, outcome, corpus)["checks"]["required_document_sources"]
    malformed = outcome.model_copy(update={"answer": "Wrong [E1] [QP-MADEUP]"})
    assert citation_metrics(malformed, corpus)["id_validity"]["value"] == 0
    # Multiline quoted policy paragraphs end with their citation, rather than one per line.
    assert score_case(
        Case(
            id="document",
            question="Return policy?",
            category="documents",
            expected_tools=[DOC],
            assertions=["30 calendar days"],
        ),
        outcome,
        corpus,
    )["passed"]


@pytest.mark.parametrize(
    "code,category",
    [
        ("configuration_error", "provider_configuration"),
        ("reader_configuration_missing", "database_availability"),
        ("database_unavailable", "database_availability"),
        ("invalid_arguments", "tool_validation"),
        ("document_error", "evidence_retrieval"),
        ("grounding_error", "citation_validation"),
        ("agent_timeout", "execution_limits"),
        ("iteration_limit", "execution_limits"),
        ("provider_timeout", "provider_failure"),
        ("provider_error", "provider_failure"),
        ("execution_error", "unexpected_internal"),
    ],
)
def test_failure_taxonomy(code, category):
    assert failure_category(code) == category


def doc_dataset():
    return Dataset(
        version="unit-v1",
        reference_date="2026-10-27",
        random_seed=42,
        ground_truth_method="Independent source judgment",
        cases=[
            Case(
                id="returns",
                question="What is our return policy?",
                category="documents",
                expected_tools=[DOC],
                evidence_types=["document"],
                retrieval_query="product return window",
                relevant_documents=["QP-RET-001"],
            )
        ],
    )


def test_real_document_runner_repeatable_without_database(monkeypatch):
    from pydantic import SecretStr

    from querypilot.services.agent import execute_question

    async def checked(question, **kwargs):
        assert kwargs["settings"].reader_database_url is None
        return await execute_question(question, **kwargs)

    monkeypatch.setattr("querypilot.evaluation.runner.execute_question", checked)
    settings = config().model_copy(
        update={
            "reader_database_url": SecretStr(
                "postgresql+psycopg://reader@unused.invalid/querypilot_unverified"
            )
        }
    )
    first = asyncio.run(run_evaluation(doc_dataset(), settings, dataset_hash="test"))
    second = asyncio.run(run_evaluation(doc_dataset(), settings, dataset_hash="test"))
    assert first["cases"][0]["score"] == second["cases"][0]["score"]
    assert first["summary"]["benchmark_pass_rate"]["value"] == 1
    assert first["fixture"]["status"] == "NOT EVALUATED"
    assert first["cases"][0]["provider_calls"] == 2
    assert first["cases"][0]["duration_ms"] >= 0


@pytest.mark.parametrize(
    "code", ["provider_error", "database_unavailable", "agent_timeout", "repeated_call"]
)
def test_runner_keeps_failure_denominators(monkeypatch, code):
    async def fail(*args, **kwargs):
        return ExecutionOutcome(
            trace_id="test",
            mode="mock",
            question="",
            status="error",
            errors=[ExecutionError(code=code, message="Safe failure")],
        )

    monkeypatch.setattr("querypilot.evaluation.runner.execute_question", fail)
    report = asyncio.run(run_evaluation(doc_dataset(), config(), dataset_hash="test"))
    assert report["summary"]["benchmark_pass_rate"] == dict(numerator=0, denominator=1, value=0)
    assert report["summary"]["reliability"]["error_events"] == 1
    assert report["cases"][0]["error_codes"] == [code]
    if code == "provider_error":
        assert report["summary"]["reliability"]["provider_failure"]["value"] == 1
    if code == "agent_timeout":
        assert report["summary"]["reliability"]["timeout"]["value"] == 1
    if code == "repeated_call":
        assert report["summary"]["reliability"]["duplicate_preventions"] == 1


def test_runner_handles_unexpected_errors_without_exposure(monkeypatch):
    async def explode(*args, **kwargs):
        raise RuntimeError("private driver diagnostics")

    monkeypatch.setattr("querypilot.evaluation.runner.execute_question", explode)
    report = asyncio.run(run_evaluation(doc_dataset(), config(), dataset_hash="test"))
    assert report["summary"]["cases"] == 1
    assert report["cases"][0]["error_codes"] == ["execution_error"]
    assert "private driver" not in json.dumps(report)


def test_negative_case_handling_partial_and_abstention(monkeypatch):
    async def empty(*args, **kwargs):
        return ExecutionOutcome(
            trace_id="test",
            mode="mock",
            question="",
            status="no_evidence",
            partial=True,
            limitations=["empty_results"],
        )

    monkeypatch.setattr("querypilot.evaluation.runner.execute_question", empty)
    data = doc_dataset()
    data.cases = [
        Case(
            id="empty",
            question="zxqvbnm",
            category="empty_results",
            expected_tools=[],
            expected_status="no_evidence",
            expected_abstention=True,
            expected_partial=True,
            negative=True,
        )
    ]
    report = asyncio.run(run_evaluation(data, config(), dataset_hash="test"))
    assert report["summary"]["reliability"]["negative_case_handling"]["value"] == 1
    assert report["summary"]["reliability"]["partial"]["value"] == 1
    assert report["summary"]["reliability"]["abstention"]["value"] == 1


def test_reports_roundtrip_redact_and_refuse_symlinks(tmp_path):
    import secrets

    report = asyncio.run(run_evaluation(doc_dataset(), config(), dataset_hash="test"))
    sentinel = "sk-proj-" + secrets.token_urlsafe(32)
    report["limitations"].append(sentinel)
    files = write_reports(report, tmp_path / "results", SecretGuard())
    assert len(files) == 2
    for path in files:
        assert sentinel not in path.read_text() and "[REDACTED]" in path.read_text()
    parsed = json.loads(files[0].read_text())
    assert parsed["summary"]["cases"] == 1
    assert "Per-case execution" in files[1].read_text()
    files[0].unlink()
    files[0].symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="symlink"):
        write_reports(report, tmp_path / "results", SecretGuard())


@pytest.mark.parametrize("format,name", [("json", "results.json"), ("markdown", "results.md")])
def test_report_format_selection(tmp_path, format, name):
    report = asyncio.run(run_evaluation(doc_dataset(), config(), dataset_hash="test"))
    assert [p.name for p in write_reports(report, tmp_path, SecretGuard(), format)] == [name]


def test_cli_mock_default_and_live_rejection(tmp_path, monkeypatch, capsys):
    from querypilot.evaluation.cli import main

    # Use explicit no-service config: document-only evaluation needs no API key or database.
    monkeypatch.setattr("querypilot.evaluation.cli.Settings", config)
    with pytest.raises(SystemExit) as result:
        main(["--category", "documents", "--limit", "1", "--output", str(tmp_path)])
    assert result.value.code == 0
    assert json.loads((tmp_path / "results.json").read_text())["summary"]["cases"] == 1
    with pytest.raises(SystemExit) as result:
        main(["--mode", "live"])
    assert result.value.code == 2
    assert "Live evaluation is not enabled" in capsys.readouterr().err


def test_cli_prerequisite_failure_does_not_fake_revenue(tmp_path, monkeypatch, capsys):
    from querypilot.evaluation.cli import main

    monkeypatch.setattr("querypilot.evaluation.cli.Settings", config)
    with pytest.raises(SystemExit, match="failed safely"):
        main(["--category", "product_revenue", "--output", str(tmp_path)])
    assert not (tmp_path / "results.json").exists()
    assert "postgresql" not in capsys.readouterr().out
