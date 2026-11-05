"""HTTP contracts: omit raw tool arguments, provider call IDs and internal messages."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from querypilot.schemas.analytics import ToolName, ToolResult
from querypilot.schemas.llm import ExecutionError, ExecutionOutcome, Question


class AskRequest(Question):
    mode: Literal["mock", "live"] = "mock"


class PublicToolExecution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(pattern=r"^E([1-9]|1[0-9]|20)$")
    iteration: int = Field(ge=1, le=10)
    tool: ToolName | None
    status: Literal["success", "error"]
    duration_ms: int | None = Field(default=None, ge=0)
    result: ToolResult | None = None
    citations: list[str] = Field(default_factory=list, max_length=10)
    output_truncated: bool = False
    error: ExecutionError | None = None

    @model_validator(mode="after")
    def coherent_evidence(self) -> "PublicToolExecution":
        if self.result and self.result.tool != self.tool:
            raise ValueError("Mismatched tool result")
        if self.status == "success" and (
            not self.result or self.result.status != "success" or self.error
        ):
            raise ValueError("Successful trace needs successful evidence")
        if self.status == "error" and (
            not self.error or (self.result and self.result.status != "error")
        ):
            raise ValueError("Failed trace cannot present successful evidence")
        expected = []
        if self.status == "success" and self.tool == "search_business_documents":
            expected = [hit.source_citation for hit in self.result.data.matches]
        if self.citations != expected:
            raise ValueError("Citations must match the forwarded passages")
        return self


class AgentResponse(ExecutionOutcome):
    request_id: str = Field(min_length=1, max_length=64)
    tools: list[PublicToolExecution] = Field(default_factory=list, max_length=20)

    @field_validator("request_id", "trace_id")
    @classmethod
    def valid_identifier(cls, value: str) -> str:
        return str(UUID(value))

    @model_validator(mode="after")
    def unique_evidence(self) -> "AgentResponse":
        identifiers = [trace.evidence_id for trace in self.tools]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Duplicate evidence references")
        return self


class AgentCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    live_enabled: bool
    live_configured: bool
    execution_timeout_seconds: float = Field(ge=0.01, le=300)
    max_iterations: int = Field(ge=1, le=10)
    max_tool_calls: int = Field(ge=1, le=20)
    max_tools_per_iteration: int = Field(ge=1, le=6)
    max_question_chars: Literal[4000] = 4000
