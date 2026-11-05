"""Ephemeral execution state: never shared across requests or persisted."""

import time
from dataclasses import dataclass, field
from uuid import uuid4

from querypilot.schemas.llm import ExecutionError, ToolExecution


@dataclass
class AgentState:
    question: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    started: float = field(default_factory=time.monotonic)
    iteration: int = 0
    messages: list[dict] = field(default_factory=list, repr=False)
    tools: list[ToolExecution] = field(default_factory=list)
    call_ids: set[str] = field(default_factory=set, repr=False)
    fingerprints: set[str] = field(default_factory=set, repr=False)
    evidence_bytes: int = 0
    pending_tool_calls: int = 0
    status: str = "running"
    errors: list[ExecutionError] = field(default_factory=list)

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started) * 1000)

    @property
    def citations(self) -> set[str]:
        return {citation for trace in self.tools for citation in trace.citations}
