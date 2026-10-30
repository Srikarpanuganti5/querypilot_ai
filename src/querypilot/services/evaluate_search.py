"""Measure document-ID Hit Rate@5 and passage-rank MRR@5 on a fixed local set."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from querypilot.core.config import Settings
from querypilot.schemas.documents import DocumentSearchInput
from querypilot.services.document_search import DocumentError, DocumentIndex
from querypilot.tools.registry import ToolRegistry

CASES_PATH = Path("data/evaluations/document_search.json")


class SearchCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    query: str = Field(min_length=1, max_length=500)
    relevant_document_ids: list[str] = Field(min_length=1)


def load_cases(path: Path = CASES_PATH) -> list[SearchCase]:
    cases = TypeAdapter(list[SearchCase]).validate_json(path.read_text(encoding="utf-8"))
    if not cases or len({case.id for case in cases}) != len(cases):
        raise ValueError("Evaluation cases must have unique IDs and cannot be empty")
    return cases


def metrics(ranks: list[int | None]) -> dict[str, float]:
    if not ranks:
        raise ValueError("Evaluation cannot be empty")
    return {
        "hit_rate_at_5": sum(rank is not None for rank in ranks) / len(ranks),
        "mrr_at_5": sum(1 / rank for rank in ranks if rank is not None) / len(ranks),
    }


def evaluate(index: DocumentIndex, cases: list[SearchCase]) -> dict:
    registry = ToolRegistry(document_index=index)
    known_ids = {chunk.metadata.document_id for chunk in index.chunks}
    records = []
    for case in cases:
        if not set(case.relevant_document_ids) <= known_ids:
            raise ValueError("Evaluation relevance IDs must exist in the index")
        arguments = DocumentSearchInput(query=case.query, top_k=5)
        result = registry.execute("search_business_documents", arguments.model_dump())
        if result.status != "success":
            raise ValueError("Search evaluation tool execution failed")
        ids = [match.document_id for match in result.data.matches]
        rank = next(
            (
                number
                for number, identifier in enumerate(ids, 1)
                if identifier in case.relevant_document_ids
            ),
            None,
        )
        records.append({"id": case.id, "first_relevant_rank": rank, "retrieved_document_ids": ids})
    return {
        "questions": len(cases),
        "indexed_documents": index.document_count,
        "indexed_chunks": len(index.chunks),
        **metrics([record["first_relevant_rank"] for record in records]),
        "cases": records,
    }


def main() -> None:
    try:
        index = DocumentIndex.from_directory(Settings().documents_path)
        print(json.dumps(evaluate(index, load_cases()), indent=2))
    except (DocumentError, OSError, ValueError, ValidationError):
        raise SystemExit(
            "Search evaluation failed; check the local corpus and evaluation set."
        ) from None


if __name__ == "__main__":
    main()
