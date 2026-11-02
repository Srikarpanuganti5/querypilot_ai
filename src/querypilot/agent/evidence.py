"""Bound complete evidence records and check citation/numeric references, not entailment."""

import json
import re
from decimal import Decimal, InvalidOperation

from querypilot.schemas.analytics import ToolResult

DOCUMENT_CITATION = r"QP-[A-Z]{2,12}-[0-9]{3}#s[0-9]{3}-c[0-9]{3}"


def packet(evidence_id: str, payload: dict) -> str:
    return json.dumps(
        {"evidence_id": evidence_id, "untrusted_data": True, "result": payload},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def bound_result(
    result: ToolResult, evidence_id: str, max_rows: int, max_bytes: int
) -> tuple[ToolResult, str, bool]:
    value = result.model_dump(mode="json")
    data = value.get("data")
    truncated = False
    rows = None
    if data is not None:
        rows = data.get("rows", data.get("matches"))
        if len(rows) > max_rows:
            del rows[max_rows:]
            truncated = True
        while True:
            if truncated and "truncated" in data:
                data["truncated"] = True
            output = packet(evidence_id, value)
            if len(output.encode("utf-8")) <= max_bytes:
                break
            if not rows:
                raise ValueError("Evidence budget exceeded")
            rows.pop()
            truncated = True
    else:
        output = packet(evidence_id, value)
    if len(output.encode("utf-8")) > max_bytes:
        raise ValueError("Evidence budget exceeded")
    if truncated and not rows:
        raise ValueError("Evidence budget removed all records")
    return ToolResult.model_validate(value), output, truncated


def has_evidence(result: ToolResult | None) -> bool:
    if result is None or result.status != "success":
        return False
    value = result.data.model_dump()
    return bool(value.get("rows", value.get("matches", [])))


def _numbers(value: str) -> set[Decimal]:
    value = re.sub(DOCUMENT_CITATION, "", value)
    value = re.sub(r"\bE\d+\b", "", value)
    found = set()
    for token in re.findall(r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d+)?", value):
        try:
            found.add(Decimal(token.replace(",", "")))
        except InvalidOperation:
            continue
    return found


def check_answer(answer: str, traces: list) -> bool:
    reliable = {trace.evidence_id: trace for trace in traces if has_evidence(trace.result)}
    cited = set(re.findall(r"\[(E\d+)\]", answer))
    if not answer or len(answer) > 6000 or not cited or not cited <= reliable.keys():
        return False
    allowed_sources = {
        citation
        for identifier, trace in reliable.items()
        if identifier in cited
        for citation in trace.citations
    }
    if not set(re.findall(DOCUMENT_CITATION, answer)) <= allowed_sources:
        return False
    if not set(re.findall(r"\[(QP-[^\]\s]+)\]", answer)) <= allowed_sources:
        return False
    for identifier in cited:
        trace = reliable[identifier]
        if trace.tool == "search_business_documents" and not any(
            citation in answer for citation in trace.citations
        ):
            return False
    # Conservative Day 6 rule: report only numbers present in cited tool data/arguments.
    # This catches unsupported numeric literals, not semantic contradictions or number words.
    sources = []
    for identifier in cited:
        trace = reliable[identifier]
        data = trace.result.data.model_dump(mode="json")
        if trace.tool == "search_business_documents":
            sources.extend(hit["excerpt"] for hit in data["matches"])
        else:
            sources.append(json.dumps(data["rows"]))
            sources.append(
                json.dumps(
                    {
                        key: value
                        for key, value in trace.arguments.items()
                        if key in ("start_date", "end_date")
                    }
                )
            )
            sources.append(str(len(data["rows"])))
    available = " ".join(sources)
    return _numbers(answer) <= _numbers(available)
