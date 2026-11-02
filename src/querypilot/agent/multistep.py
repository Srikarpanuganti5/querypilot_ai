"""Bounded, provider-independent tool loop using the existing execution boundary."""

import asyncio
import json
import logging
from datetime import UTC, datetime

from pydantic import ValidationError

from querypilot.agent.evidence import check_answer, has_evidence, packet
from querypilot.agent.orchestrator import INSTRUCTIONS, SingleRoundService, _calls, _json_object
from querypilot.agent.provider import ProviderError
from querypilot.agent.state import AgentState
from querypilot.agent.tool_schemas import function_schemas, normalize_arguments
from querypilot.schemas.llm import ExecutionError, ExecutionOutcome, Question, ToolExecution

MULTISTEP_INSTRUCTIONS = INSTRUCTIONS.replace(
    "You may select multiple tools in ONE batch; no further tool round is allowed.",
    "You may request several tools per round and additional rounds when needed. "
    "Stop when sufficient evidence is available. Do not repeat identical calls. "
    "Recover from tool errors with a corrected or different approved tool when useful.",
)
logger = logging.getLogger("querypilot.llm")


def encoded_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


class MultiStepService(SingleRoundService):
    def _context(self, instructions: str, tools: list[dict], messages: list[dict]) -> None:
        # Count complete serialized application context, including schemas/instructions.
        if encoded_size({"instructions": instructions, "tools": tools, "input": messages}) > (
            self.settings.agent_max_context_bytes
        ):
            raise ProviderError("context_limit", "Accumulated agent context exceeded its limit.")

    @staticmethod
    def _fingerprint(call: dict, definitions: dict) -> str:
        arguments = normalize_arguments(call["name"], _json_object(call["arguments"]), definitions)
        properties = definitions.get(call["name"], {}).get("input_schema", {}).get("properties", {})
        # Match omitted and explicit default/null values, without relaxing registry validation.
        canonical = {name: value.get("default") for name, value in properties.items()}
        canonical.update(arguments)
        return json.dumps([call["name"], canonical], sort_keys=True, separators=(",", ":"))

    async def _loop(self, state: AgentState) -> tuple[str, str | None, str]:
        definitions = self.registry.definitions()
        tools = function_schemas(definitions)
        instructions = MULTISTEP_INSTRUCTIONS + f"\nCurrent UTC date: {datetime.now(UTC).date()}."
        state.messages.append({"role": "user", "content": state.question})
        for iteration in range(1, self.settings.agent_max_iterations + 1):
            self._context(instructions, tools, state.messages)
            state.iteration = iteration
            turn = await self._respond(instructions, state.messages, tools)
            calls = _calls(turn, self.settings.agent_max_tools_per_iteration)
            self._context(instructions, tools, state.messages + turn.output)
            if not calls:
                if not any(has_evidence(trace.result) for trace in state.tools):
                    message = (
                        "Tool retrieval failed; no reliable evidence is available."
                        if state.errors
                        else "No matching evidence is available for this question."
                    )
                    return "no_evidence", message, "not_applicable"
                if not check_answer(turn.text.strip(), state.tools):
                    raise ProviderError(
                        "grounding_error",
                        "Answer failed evidence checks; inspect the tool results.",
                    )
                return "completed", turn.text.strip(), "passed"
            if len(state.tools) + len(calls) > self.settings.agent_max_tool_calls:
                raise ProviderError("tool_limit", "The total tool-call limit was reached.")
            if any(call["call_id"] in state.call_ids for call in calls):
                raise ProviderError("provider_response_error", "A tool-call ID was reused.")
            # Validate the entire batch before executing any of it.
            state.call_ids.update(call["call_id"] for call in calls)
            state.messages.extend(turn.output)
            for call in calls:
                identifier = f"E{len(state.tools) + 1}"
                try:
                    fingerprint = self._fingerprint(call, definitions)
                except (ValueError, TypeError, RecursionError):
                    fingerprint = None  # Existing execution boundary returns a safe JSON error.
                if fingerprint is not None and fingerprint in state.fingerprints:
                    error = ExecutionError(
                        code="repeated_call", message="Identical call skipped; use prior evidence."
                    )
                    trace = ToolExecution(
                        evidence_id=identifier,
                        call_id=call["call_id"],
                        tool=call["name"] if call["name"] in definitions else None,
                        status="error",
                        error=error,
                    )
                    output, timed_out = (
                        packet(identifier, {"status": "error", "error": error.model_dump()}),
                        False,
                    )
                else:
                    if fingerprint is not None:
                        state.fingerprints.add(fingerprint)
                    # Reserve a fair share across the maximum number of calls, including errors.
                    budget = min(
                        self.settings.llm_max_evidence_bytes,
                        self.settings.llm_total_evidence_bytes
                        // self.settings.agent_max_tool_calls,
                    )
                    trace, output, timed_out = await self._execute(
                        call, identifier, definitions, budget, False
                    )
                trace.iteration = iteration
                state.tools.append(trace)
                if trace.error:
                    state.errors.append(trace.error)
                state.evidence_bytes += len(output.encode("utf-8"))
                if state.evidence_bytes > self.settings.llm_total_evidence_bytes:
                    raise ProviderError(
                        "evidence_limit", "Accumulated tool evidence exceeded its limit."
                    )
                message = {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": output,
                }
                self._context(instructions, tools, state.messages + [message])
                state.messages.append(message)
                if timed_out:
                    # Do not overlap additional work with a synchronous worker still running.
                    raise ProviderError("tool_timeout", "Agent stopped after a tool deadline.")
        raise ProviderError("iteration_limit", "The agent iteration limit was reached.")

    async def run(self, question: str) -> ExecutionOutcome:
        state = AgentState(question="")
        answer, checks = None, "not_applicable"
        try:
            state.question = Question(question=question).question
            async with asyncio.timeout(self.settings.agent_timeout_seconds):
                state.status, answer, checks = await self._loop(state)
        except ValidationError:
            state.status = "error"
            state.errors.append(
                ExecutionError(
                    code="invalid_question", message="Provide a question of 1–4000 characters."
                )
            )
        except (ProviderError, TimeoutError) as exc:
            state.status = "error"
            code = exc.code if isinstance(exc, ProviderError) else "agent_timeout"
            message = (
                str(exc)
                if isinstance(exc, ProviderError)
                else "The agent execution deadline was reached."
            )
            state.errors.append(ExecutionError(code=code, message=message))
            if code == "grounding_error":
                checks = "failed"
        except Exception:
            state.status = "error"
            state.errors.append(
                ExecutionError(
                    code="execution_error", message="The analytics request could not be completed."
                )
            )
        logger.info(
            "llm_execution",
            extra={
                "trace_id": state.request_id,
                "mode": self.provider.mode,
                "status": state.status,
                "tool_count": len(state.tools),
                "duration_ms": state.elapsed_ms,
            },
        )
        return ExecutionOutcome(
            trace_id=state.request_id,
            mode=self.provider.mode,
            question=state.question,
            status=state.status,
            answer=answer,
            tools=state.tools,
            errors=state.errors,
            iterations=state.iteration,
            elapsed_ms=state.elapsed_ms,
            grounding_checks=checks,
        )
