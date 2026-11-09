"""Bounded benchmark contracts; references are curated independently of agent output."""

import hashlib
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from querypilot.schemas.analytics import ToolName
from querypilot.schemas.llm import Question

DEFAULT_DATASET = Path("data/evaluations/agent_v1.json")


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Fact(Contract):
    tool: ToolName
    where: dict[str, str | int] = Field(default_factory=dict, max_length=3)
    field: str = Field(pattern=r"^[a-z_]+$", max_length=40)
    value: str | int
    answer_required: bool = True


class Case(Question):
    id: str = Field(pattern=r"^[a-z0-9-]{1,64}$")
    category: str = Field(pattern=r"^[a-z_]{1,40}$")
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    expected_tools: list[ToolName] = Field(max_length=6)
    allowed_extra_tools: list[ToolName] = Field(default_factory=list, max_length=6)
    order_matters: bool = False
    evidence_types: list[Literal["sql", "document"]] = Field(default_factory=list, max_length=2)
    expected_citations: list[str] = Field(default_factory=list, max_length=10)
    facts: list[Fact] = Field(default_factory=list, max_length=30)
    ranked_product_ids: list[int] = Field(default_factory=list, max_length=20)
    assertions: list[str] = Field(default_factory=list, max_length=10)
    expected_status: Literal["completed", "no_evidence", "error"] = "completed"
    expected_partial: bool | None = None
    expected_abstention: bool = False
    negative: bool = False
    scenario: Literal["normal", "missing_reader", "iteration_limit"] = "normal"
    retrieval_query: str | None = Field(default=None, min_length=1, max_length=500)
    relevant_documents: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def coherent(self):
        if len(set(self.expected_tools)) != len(self.expected_tools):
            raise ValueError("Expected tools must be unique")
        if set(self.expected_tools) & set(self.allowed_extra_tools):
            raise ValueError("Allowed extra tools must be distinct from required tools")
        if self.relevant_documents and not self.retrieval_query:
            raise ValueError("Relevance judgments require an independent retrieval query")
        return self


class Dataset(Contract):
    version: str = Field(pattern=r"^[a-zA-Z0-9.-]{1,64}$")
    reference_date: date
    random_seed: int = Field(ge=0)
    ground_truth_method: str = Field(min_length=1, max_length=500)
    cases: list[Case] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Case IDs must be unique")
        return self


def load_dataset(path: Path = DEFAULT_DATASET) -> tuple[Dataset, str]:
    if path.stat().st_size > 1_000_000:
        raise ValueError("Evaluation dataset exceeds its byte limit")
    raw = path.read_bytes()
    return Dataset.model_validate_json(raw), hashlib.sha256(raw).hexdigest()
