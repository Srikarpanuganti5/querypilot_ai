"""Reuse the shared request lifecycle with a counted mock provider and real tools."""

import hashlib
import json
import platform
import time
from collections import Counter
from datetime import UTC, datetime
from statistics import mean

from sqlalchemy import select, text

from querypilot.agent.mock import MultiStepMockProvider
from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard
from querypilot.db.analytics import _check_reader
from querypilot.db.models import Base
from querypilot.db.seed import generate_dataset
from querypilot.db.session import create_database
from querypilot.evaluation.dataset import Dataset
from querypilot.evaluation.metrics import (
    failure_category,
    latency,
    ratio,
    retrieval_metrics,
    score_case,
)
from querypilot.schemas.documents import DocumentSearchInput
from querypilot.services.agent import execute_question
from querypilot.services.document_search import DocumentIndex


class CountedMock(MultiStepMockProvider):
    def __init__(self):
        self.calls = 0
        self.max_context_bytes = 0

    async def respond(self, instructions, history, tools, *, final=False):
        self.calls += 1
        self.max_context_bytes = max(
            self.max_context_bytes,
            len(json.dumps([instructions, history, tools], ensure_ascii=False).encode()),
        )
        return await super().respond(instructions, history, tools, final=final)


def verify_fixture(settings: Settings, dataset: Dataset) -> dict:
    """Read every bounded synthetic row; refuse changing or merely count-matched data."""
    expected = generate_dataset(dataset.reference_date, dataset.random_seed)
    database = create_database(settings, reader=True)
    try:
        with database.transaction() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            _check_reader(session)
            server_version = session.scalar(text("SHOW server_version_num"))
            for table in Base.metadata.sorted_tables:
                key = list(table.primary_key.columns)[0]
                rows = [
                    dict(row)
                    for row in session.execute(
                        select(table).order_by(key).limit(len(expected[table.name]) + 1)
                    ).mappings()
                ]
                if rows != expected[table.name]:
                    raise ValueError(
                        "Database differs from the benchmark fixture; no cases executed"
                    )
    finally:
        database.close()
    raw = json.dumps(expected, sort_keys=True, default=str, separators=(",", ":")).encode()
    return {
        "status": "REAL DATABASE VERIFIED",
        "method": "exact six-table row comparison",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "postgres_version_num": server_version,
        "reference_date": str(dataset.reference_date),
        "random_seed": dataset.random_seed,
        "counts": {key: len(rows) for key, rows in expected.items()},
    }


def aggregate(records: list[dict]) -> dict:
    n = len(records)
    selected = [r["score"]["selection"] for r in records]
    retrieval = [
        r["retrieval"]
        for r in records
        if r["retrieval"] is not None and not r["retrieval"]["no_relevance_judgment"]
    ]
    unique_retrieval_queries = {
        (r["retrieval_query"], tuple(r["relevant_documents"]))
        for r in records
        if r["retrieval"] is not None and not r["retrieval"]["no_relevance_judgment"]
    }
    ordered = [r for r in records if r["order_matters"]]
    negative = [r for r in records if r["negative"]]
    attempted = sum(len(r["tools"]) for r in records)
    errors = [code for r in records for code in r["error_codes"]]
    citations = [r["score"]["citations"] for r in records]

    def pooled(field):
        return ratio(
            sum(c[field]["numerator"] for c in citations),
            sum(c[field]["denominator"] for c in citations),
        )

    return {
        "cases": n,
        "benchmark_pass_rate": ratio(sum(r["score"]["passed"] for r in records), n),
        "tool_selection": {
            **{
                field: {
                    "value": mean(s[field] for s in selected) if n else None,
                    "denominator_cases": n,
                }
                for field in ("precision", "recall", "f1")
            },
            "exact_match": ratio(sum(s["exact"] for s in selected), n),
            "sequence_accuracy": ratio(
                sum(r["score"]["checks"]["tool_sequence"] for r in ordered), len(ordered)
            ),
            "correct_unique_tools": sum(s["correct"] for s in selected),
            "expected_unique_tools": sum(s["expected"] for s in selected),
            "selected_scored_unique_tools": sum(s["selected_scored"] for s in selected),
        },
        "retrieval": {
            "averaging": "case-weighted, including repeated labeled queries",
            "unique_labeled_queries": len(unique_retrieval_queries),
            "unjudged_queries": sum(
                r["retrieval"] is not None and r["retrieval"]["no_relevance_judgment"]
                for r in records
            ),
            "metrics": {
                field: {
                    "value": mean(r[field] for r in retrieval) if retrieval else None,
                    "denominator_queries": len(retrieval),
                }
                for field in ("precision_at_k", "recall_at_k", "hit_at_k", "reciprocal_rank")
            },
        },
        "citations": {
            "id_validity": pooled("id_validity"),
            "retrieved_provenance": pooled("retrieved_provenance"),
            "fabricated_count": sum(len(c["fabricated"]) for c in citations),
            "required_reference_coverage": ratio(
                sum(r["score"]["required_citation_coverage"]["numerator"] for r in records),
                sum(r["score"]["required_citation_coverage"]["denominator"] for r in records),
            ),
            "claim_support": "NOT EVALUATED",
            "required_document_coverage": ratio(
                sum(r["score"]["required_document_coverage"]["numerator"] for r in records),
                sum(r["score"]["required_document_coverage"]["denominator"] for r in records),
            ),
            "claim_precision": "NOT EVALUATED",
        },
        "factual_checks": {
            "evidence_match": ratio(
                sum(f["evidence_match"] for r in records for f in r["score"]["facts"]),
                sum(len(r["score"]["facts"]) for r in records),
            ),
            "answer_literal_and_source": ratio(
                sum(f["answer_literal_and_source"] for r in records for f in r["score"]["facts"]),
                sum(len(r["score"]["facts"]) for r in records),
            ),
            "unsupported_numeric_case_rate": ratio(
                sum(bool(r["score"]["unsupported_numeric_literals"]) for r in records), n
            ),
            "semantic_faithfulness": "NOT EVALUATED",
        },
        "reliability": {
            "completed": ratio(sum(r["status"] == "completed" for r in records), n),
            "partial": ratio(sum(r["partial"] for r in records), n),
            "abstention": ratio(sum(r["score"]["abstained"] for r in records), n),
            "tool_failure": ratio(
                sum(t["status"] == "error" for r in records for t in r["tools"]), attempted
            ),
            "provider_failure": ratio(
                sum(
                    any(
                        failure_category(c) in {"provider_failure", "provider_configuration"}
                        for c in r["error_codes"]
                    )
                    for r in records
                ),
                n,
            ),
            "timeout": ratio(
                sum(any("timeout" in c for c in r["error_codes"]) for r in records), n
            ),
            "execution_limit": ratio(
                sum(any(c.endswith("_limit") for c in r["error_codes"]) for r in records), n
            ),
            "negative_case_handling": ratio(
                sum(r["score"]["passed"] for r in negative), len(negative)
            ),
            "duplicate_preventions": sum(c == "repeated_call" for c in errors),
            "duplicate_prevention_opportunities": "NOT EVALUATED: fingerprints not exposed",
            "failure_categories": dict(Counter(failure_category(code) for code in errors)),
            "error_events": len(errors),
        },
        "performance": {
            **latency([r["duration_ms"] for r in records]),
            "mean_tool_attempts": mean(len(r["tools"]) for r in records) if n else None,
            "mean_iterations": mean(r["iterations"] for r in records) if n else None,
            "mean_provider_calls": mean(r["provider_calls"] for r in records) if n else None,
            "mean_response_bytes": mean(r["response_bytes"] for r in records) if n else None,
            "mean_evidence_bytes": mean(r["evidence_bytes"] for r in records) if n else None,
            "max_observed_provider_input_bytes": max(
                (r["provider_context_bytes"] for r in records), default=0
            ),
            "per_tool_latency": {
                name: latency(
                    [
                        t["duration_ms"]
                        for r in records
                        for t in r["tools"]
                        if t["tool"] == name and t["duration_ms"] is not None
                    ]
                )
                for name in sorted({t["tool"] or "unknown" for r in records for t in r["tools"]})
            },
            "label": "local mock-provider performance; excludes preflight and retrieval-only probe",
        },
    }


async def run_evaluation(
    dataset: Dataset,
    settings: Settings,
    *,
    dataset_hash: str,
    category: str | None = None,
    limit: int | None = None,
    k: int = 5,
) -> dict:
    if not 1 <= k <= 10 or (limit is not None and not 1 <= limit <= 100):
        raise ValueError("Invalid evaluation bounds")
    cases = [c for c in dataset.cases if category is None or c.category == category]
    if limit:
        cases = cases[:limit]
    if not cases:
        raise ValueError("No matching evaluation cases")
    index = DocumentIndex.from_directory(settings.documents_path)
    corpus = {c.citation: c.metadata.document_id for c in index.chunks}
    for case in cases:
        if (
            not set(case.relevant_documents) <= set(corpus.values())
            or not set(case.expected_citations) <= corpus.keys()
        ):
            raise ValueError("Dataset references are absent from the corpus")
    needs_database = any(
        any(t != "search_business_documents" for t in c.expected_tools) for c in cases
    )
    fixture = verify_fixture(settings, dataset) if needs_database else {"status": "NOT EVALUATED"}
    corpus_hash = hashlib.sha256(
        json.dumps(
            [(c.metadata.model_dump(), c.section, c.citation, c.excerpt) for c in index.chunks],
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    records = []
    guard = SecretGuard(settings)
    for case in cases:
        config = settings.model_copy(update={"agent_live_enabled": False})
        if not needs_database:
            # Document-only subsets must not read an unverified database on a routing mistake.
            config = config.model_copy(update={"reader_database_url": None})
        if case.scenario == "missing_reader":
            config = config.model_copy(update={"reader_database_url": None})
        if case.scenario == "iteration_limit":
            config = config.model_copy(update={"agent_max_iterations": 1})
        provider = CountedMock()
        started = time.perf_counter()
        try:
            outcome = await execute_question(
                case.question,
                live=False,
                settings=config,
                provider_factory=lambda _, current=provider: current,
            )
        except Exception:
            # Keep every case in the denominator; never expose an exception or driver text.
            from querypilot.schemas.llm import ExecutionError, ExecutionOutcome

            outcome = ExecutionOutcome(
                trace_id="evaluation-internal",
                mode="mock",
                question="",
                status="error",
                errors=[
                    ExecutionError(code="execution_error", message="Evaluation execution failed.")
                ],
            )
        duration = (time.perf_counter() - started) * 1000
        retrieval = None
        retrieved = []
        if case.retrieval_query:
            hits = index.search(DocumentSearchInput(query=case.retrieval_query, top_k=10)).matches
            retrieved = [h.document_id for h in hits]
            retrieval = retrieval_metrics(case.relevant_documents, retrieved, k)
        projection = outcome.model_dump(mode="json", exclude={"question", "trace_id"})
        for trace in projection["tools"]:
            trace.pop("arguments", None)
            trace.pop("call_id", None)
        records.append(
            guard.sanitize(
                {
                    "id": case.id,
                    "category": case.category,
                    "scenario": case.scenario,
                    "negative": case.negative,
                    "order_matters": case.order_matters,
                    "expected_tools": case.expected_tools,
                    "expected_status": case.expected_status,
                    "status": outcome.status,
                    "partial": outcome.partial,
                    "selected_tools": [t.tool or "unknown" for t in outcome.tools],
                    "tools": [
                        {
                            "tool": t.tool,
                            "status": t.status,
                            "duration_ms": t.result.duration_ms if t.result else None,
                        }
                        for t in outcome.tools
                    ],
                    "error_codes": [e.code for e in outcome.errors],
                    "score": score_case(case, outcome, corpus),
                    "retrieval": retrieval,
                    "retrieval_query": case.retrieval_query,
                    "relevant_documents": case.relevant_documents,
                    "retrieved_document_ids": list(dict.fromkeys(retrieved))[:k],
                    "duration_ms": duration,
                    "iterations": outcome.iterations,
                    "provider_calls": provider.calls,
                    "provider_context_bytes": provider.max_context_bytes,
                    "response_bytes": len(json.dumps(projection, ensure_ascii=False).encode()),
                    "evidence_bytes": sum(
                        len(t.result.model_dump_json().encode()) for t in outcome.tools if t.result
                    ),
                }
            )
        )
    return guard.sanitize(
        {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "mode": "MOCK PROVIDER + REAL DATABASE"
            if needs_database
            else "MOCK PROVIDER + REAL DOCUMENTS",
            "live_openai": "LIVE OPENAI NOT VERIFIED",
            "dataset_version": dataset.version,
            "dataset_sha256": dataset_hash,
            "fixture": fixture,
            "corpus_sha256": corpus_hash,
            "python": platform.python_version(),
            "configuration": {
                "k": k,
                "category": category,
                "limit": limit,
                "agent_max_iterations": settings.agent_max_iterations,
                "agent_max_tool_calls": settings.agent_max_tool_calls,
                "agent_timeout_seconds": settings.agent_timeout_seconds,
                "context_budget_bytes": settings.agent_max_context_bytes,
                "evidence_rows_per_tool": settings.llm_max_evidence_rows,
                "evidence_bytes_per_tool": settings.llm_max_evidence_bytes,
                "total_evidence_bytes": settings.llm_total_evidence_bytes,
                "tool_timeout_seconds": settings.llm_tool_timeout_seconds,
                "provider": "MultiStepMockProvider (no SDK/network retries)",
                "retrieval_candidate_passages": 10,
                "bm25_k1": 1.5,
                "bm25_b": 0.75,
            },
            "summary": aggregate(records),
            "categories": {
                name: aggregate([r for r in records if r["category"] == name])
                for name in sorted({r["category"] for r in records})
            },
            "cases": records,
            "limitations": [
                "Deterministic mock selection is not live LLM accuracy.",
                "Literal assertions and numeric membership are not semantic faithfulness.",
                "Claim-to-source entailment and citation precision are NOT EVALUATED.",
                "No UI verification is established by the evaluation runner.",
                "Fixture must remain unchanged during a sequential benchmark run.",
                "Unjudged queries are excluded from retrieval averages and disclosed per case.",
                "No database or provider error cases are removed from agent metric denominators.",
            ],
        }
    )
