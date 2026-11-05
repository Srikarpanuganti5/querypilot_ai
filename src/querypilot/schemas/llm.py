"""Bounded execution outcomes; provider prompts/reasoning are never exposed."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from querypilot.schemas.analytics import ToolName, ToolResult


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=4000, strict=True)

    @field_validator("question", mode="before")
    @classmethod
    def bound_raw_question(cls, value: object) -> object:
        if isinstance(value, str) and len(value) > 4000:
            raise ValueError("Question exceeds the character limit")
        return value


class ExecutionError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)


class ToolExecution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(pattern=r"^E([1-9]|1[0-9]|20)$")
    iteration: int = Field(default=1, ge=1, le=10)
    call_id: str = Field(min_length=1, max_length=200)
    tool: ToolName | None
    status: Literal["success", "error"]
    arguments: dict[str, Any] = Field(default_factory=dict, max_length=4)
    result: ToolResult | None = None
    citations: list[str] = Field(default_factory=list, max_length=10)
    output_truncated: bool = False
    error: ExecutionError | None = None


class ExecutionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trace_id: str
    mode: Literal["mock", "live"]
    question: str = Field(max_length=4000)
    status: Literal["completed", "no_evidence", "error"]
    answer: str | None = Field(default=None, max_length=6000)
    tools: list[ToolExecution] = Field(default_factory=list, max_length=20)
    errors: list[ExecutionError] = Field(default_factory=list, max_length=21)
    iterations: int = Field(default=0, ge=0, le=10)
    elapsed_ms: int = Field(default=0, ge=0)
    grounding_checks: Literal["not_applicable", "passed", "failed"] = "not_applicable"
    partial: bool = False
    pending_tool_calls: int = Field(default=0, ge=0, le=20)
    limitations: list[str] = Field(default_factory=list, max_length=5)
