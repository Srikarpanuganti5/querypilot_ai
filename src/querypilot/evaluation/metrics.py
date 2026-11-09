"""Explicit deterministic measurements, never semantic entailment scores."""

import math
import re
from decimal import Decimal
from statistics import mean, median

from querypilot.evaluation.dataset import Case
from querypilot.schemas.llm import ExecutionOutcome

CITATION = r"QP-[A-Z]{2,12}-[0-9]{3}#s[0-9]{3}-c[0-9]{3}"


def ratio(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def tool_metrics(expected: list[str], actual: list[str], allowed: list[str] = ()) -> dict:
    required, selected, permitted = set(expected), set(actual), set(allowed)
    correct = len(required & selected)
    extra = len(selected - required - permitted)
    # Repeated attempts count once for selection; all attempts count in reliability.
    precision = correct / (correct + extra) if correct + extra else 1.0
    recall = correct / len(required) if required else 1.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "exact": required <= selected and not extra,
        "correct": correct,
        "selected_scored": correct + extra,
        "expected": len(required),
        "repeated_attempts": len(actual) - len(selected),
    }


def sequence_matches(expected: list[str], actual: list[str]) -> bool:
    # Required dependency order is a subsequence; allowed extra retrieval may interleave.
    iterator = iter(actual)
    return all(any(item == required for item in iterator) for required in expected)


def retrieval_metrics(relevant: list[str], retrieved: list[str], k: int) -> dict:
    if not 1 <= k <= 10:
        raise ValueError("K must be between 1 and 10")
    # Document-level judgments: duplicate passages from a document collapse before ranking.
    ranked = list(dict.fromkeys(retrieved))[:k]
    labels = set(relevant)
    hits = len(labels & set(ranked))
    rank = next((i for i, item in enumerate(ranked, 1) if item in labels), None)
    return {
        "precision_at_k": hits / k if labels else None,
        "recall_at_k": hits / len(labels) if labels else None,
        "hit_at_k": int(bool(hits)) if labels else None,
        "reciprocal_rank": 1 / rank if rank else 0.0 if labels else None,
        "relevant": len(labels),
        "hits": hits,
        "k": k,
        "no_relevance_judgment": not labels,
    }


def numbers(text: str) -> set[Decimal]:
    text = re.sub(CITATION, "", text)
    text = re.sub(r"\bE\d+\b", "", text)
    return {
        Decimal(item.replace(",", ""))
        for item in re.findall(r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d+)?", text)
    }


def source_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(source_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(source_text(item) for item in value)
    return str(value)


def literal_present(value: str | int, text: str) -> bool:
    return bool(re.search(r"(?<![\w.])" + re.escape(str(value)) + r"(?![\w.])", text))


def citation_metrics(outcome: ExecutionOutcome, corpus: dict[str, str]) -> dict:
    answer = outcome.answer or ""
    claims = set(re.findall(r"\[(QP-[^\]\s]+)\]", answer))
    retrieved = {}
    for trace in outcome.tools:
        if trace.status == "success" and trace.result and trace.result.data:
            for hit in getattr(trace.result.data, "matches", []):
                retrieved[hit.source_citation] = hit.document_id
    valid = {c for c in claims if re.fullmatch(CITATION, c) and c in corpus}
    provenance = {c for c in valid if retrieved.get(c) == corpus[c]}
    evidence_refs = set(re.findall(r"\[(E\d+)\]", answer))
    usable = {
        t.evidence_id
        for t in outcome.tools
        if t.status == "success"
        and t.result
        and t.result.data
        and (getattr(t.result.data, "rows", []) or getattr(t.result.data, "matches", []))
    }
    return {
        "id_validity": ratio(len(valid), len(claims)),
        "retrieved_provenance": ratio(len(provenance), len(claims)),
        "fabricated": sorted(claims - provenance),
        "failed_or_empty_evidence_references": sorted(evidence_refs - usable),
        "claim_support": "NOT EVALUATED",
        "claim_citation_precision": "NOT EVALUATED",
    }


def score_case(case: Case, outcome: ExecutionOutcome, corpus: dict[str, str]) -> dict:
    actual = [trace.tool or "unknown" for trace in outcome.tools]
    selection = tool_metrics(case.expected_tools, actual, case.allowed_extra_tools)
    answer = outcome.answer or ""
    good = [t for t in outcome.tools if t.status == "success" and t.result and t.result.data]
    types = {
        "document" if t.tool == "search_business_documents" else "sql"
        for t in good
        if getattr(t.result.data, "rows", []) or getattr(t.result.data, "matches", [])
    }
    facts = []
    for fact in case.facts:
        matching = [
            (trace, row.model_dump(mode="json"))
            for trace in good
            if trace.tool == fact.tool
            for row in getattr(trace.result.data, "rows", [])
        ]
        matching = [
            (trace, row)
            for trace, row in matching
            if all(row.get(key) == value for key, value in fact.where.items())
        ]
        evidence_ok = any(str(row.get(fact.field)) == str(fact.value) for _, row in matching)
        answer_ok = not fact.answer_required or any(
            literal_present(fact.value, line) and f"[{trace.evidence_id}]" in line
            for trace, _ in matching
            for line in answer.splitlines()
        )
        facts.append(
            {
                "field": fact.field,
                "expected": fact.value,
                "actual": [row.get(fact.field) for _, row in matching],
                "evidence_match": evidence_ok,
                "answer_literal_and_source": answer_ok,
            }
        )
    citations = citation_metrics(outcome, corpus)
    # Conservative numeric-literal membership per cited line; no semantic interpretation.
    unsupported = set()
    traces = {t.evidence_id: t for t in good}
    for line in re.split(r"(?<=\])\s*\n", answer):
        refs = set(re.findall(r"\[(E\d+)\]", line))
        if not refs:
            unsupported.update(numbers(line))
            continue
        source = " ".join(
            source_text(traces[ref].result.data.model_dump(mode="json"))
            for ref in refs
            if ref in traces
        )
        unsupported.update(numbers(line) - numbers(source))
    abstained = outcome.status == "no_evidence" or (outcome.status == "error" and not answer)
    required = set(case.expected_citations)
    cited = set(re.findall(CITATION, answer))
    required_documents = set(case.relevant_documents)
    cited_documents = {corpus[c] for c in cited if c in corpus}
    checks = {
        "tool_set": selection["exact"],
        "tool_sequence": not case.order_matters or sequence_matches(case.expected_tools, actual),
        "status": outcome.status == case.expected_status,
        "partial": case.expected_partial is None or outcome.partial == case.expected_partial,
        "abstention": abstained == case.expected_abstention,
        "evidence_types": set(case.evidence_types) <= types,
        "facts": all(f["evidence_match"] and f["answer_literal_and_source"] for f in facts),
        "product_ranking": not case.ranked_product_ids
        or any(
            [row.product_id for row in trace.result.data.rows] == case.ranked_product_ids
            for trace in good
            if trace.tool == "get_top_products"
        ),
        "assertion_literals": all(term.casefold() in answer.casefold() for term in case.assertions),
        "required_citations": required <= cited,
        "required_document_sources": required_documents <= cited_documents,
        "citation_integrity": not citations["fabricated"]
        and not citations["failed_or_empty_evidence_references"],
        "numeric_membership": not unsupported,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "selection": selection,
        "facts": facts,
        "citations": citations,
        "required_citation_coverage": ratio(len(required & cited), len(required)),
        "required_document_coverage": ratio(
            len(required_documents & cited_documents), len(required_documents)
        ),
        "unsupported_numeric_literals": sorted(str(n) for n in unsupported),
        "semantic_faithfulness": "NOT EVALUATED",
        "abstained": abstained,
    }


def latency(values: list[float]) -> dict:
    if not values:
        return {
            "samples": 0,
            "mean_ms": None,
            "median_ms": None,
            "p95_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    ordered = sorted(values)
    return {
        "samples": len(values),
        "mean_ms": mean(values),
        "median_ms": median(values),
        "p95_ms": ordered[math.ceil(0.95 * len(values)) - 1],
        "min_ms": min(values),
        "max_ms": max(values),
    }


def failure_category(code: str) -> str:
    if code == "provider_timeout":
        return "provider_failure"
    if code in {"configuration_error", "authentication_error"}:
        return "provider_configuration"
    if code.startswith("database_") or code in {"reader_configuration_missing", "unsafe_database"}:
        return "database_availability"
    if code in {"invalid_arguments", "invalid_json", "unknown_tool", "invalid_question"}:
        return "tool_validation"
    if code.endswith(("_limit", "_timeout")) or code == "timeout":
        return "execution_limits"
    if code.startswith("provider_") or code in {"network_error", "rate_limit"}:
        return "provider_failure"
    if code in {"grounding_error", "evidence_conflict"}:
        return "citation_validation"
    if code == "document_error":
        return "evidence_retrieval"
    return (
        "tool_execution"
        if code in {"invalid_output", "sensitive_output"}
        else "unexpected_internal"
    )
