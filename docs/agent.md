# Multi-step orchestration and guardrails (Days 7–8)

MultiStepService repeatedly consumes provider output, executes approved registry calls
and returns bounded evidence until an answer or limit. Live selection is model-driven;
the service has no keyword router or hardcoded business answers. MultiStepMockProvider
is explicitly a deterministic offline fixture, and templates quote actual tool results.
It demonstrates application wiring, not model reasoning quality. SingleRoundService
remains available with its original one-batch/tools-disabled-follow-up behavior.

## CLI and configuration

```sh
# No API key or database required for document questions:
python -m querypilot.cli ask "What is the return policy?" --mock
# Set READER_DATABASE_URL for actual synthetic SQL:
python -m querypilot.cli ask "What are the top five products by revenue?" --mock --verbose
python -m querypilot.cli ask "Which products generated the most revenue, and what is our refund policy?" --mock
python -m querypilot.cli ask "What is the revenue trend, and how are failed payments handled?" --mock --max-iterations 5 --max-tool-calls 10 --max-tools-per-iteration 5 --timeout-seconds 90 --max-context-bytes 128000
# Existing commands still work:
python -m querypilot.tools ask "What is the return policy?" --mock
python -m querypilot.tools search_business_documents --arguments '{"query":"return window","top_k":1}'
```

Without --verbose, outcomes omit the question, raw arguments, call IDs and result bodies;
tool summaries, citations, status, errors, iteration and elapsed time remain visible.
Verbose traces expose bounded structured evidence, never internal prompts, model output
dumps or reasoning. Use synthetic questions only; do not submit secrets or personal data.
The application logs only fixed status/count/time fields and generated IDs, not traces.

Mock is the default. For deliberately approved **paid live usage**, set OPENAI_API_KEY and
OPENAI_MODEL in the environment or ignored .env and supply --live. No model is hardcoded,
and live failures never switch to mock. SQL tools require READER_DATABASE_URL separately;
there is no writer fallback. Neither credential is copied into model context by the app.
Live verification is still pending: both OpenAI settings were unconfigured on Day 7 and
no paid requests were made. All standard tests mock external model calls.

| Environment setting (QUERYPILOT_ prefix) | Default | Allowed range |
| --- | --- | --- |
| AGENT_MAX_ITERATIONS | 5 | 1–10 |
| AGENT_MAX_TOOL_CALLS | 10 | 1–20 |
| AGENT_MAX_TOOLS_PER_ITERATION | 5 | 1–6 |
| AGENT_TIMEOUT_SECONDS | 90 | 0.01–300 |
| AGENT_MAX_CONTEXT_BYTES | 128000 | 1000–512000 |
| AGENT_MAX_MESSAGES | 128 | 2–256 |
| LLM_MAX_EVIDENCE_BYTES | 12000 | 1000–32000 |
| LLM_TOTAL_EVIDENCE_BYTES | 48000 | 2000–128000 |
| LLM_MAX_EVIDENCE_ROWS | 10 | 1–20 |
| LLM_REQUEST_TIMEOUT_SECONDS | 25 | 0.05–120 |
| LLM_TOOL_TIMEOUT_SECONDS | 15 | 0.01–60 |
| LLM_MAX_RETRIES | 1 | 0–2 |
| LLM_MAX_OUTPUT_TOKENS | 1600 | 256–4000 |

CLI flags override the six AGENT settings, including --max-messages. Other limits use environment settings.
LLM_MAX_TOOL_CALLS is the retained Day 6 batch setting, not the Day 7 total-call limit.
Each model request consumes an iteration, including the final response; five iterations
can therefore accommodate four tool rounds plus an answer. SDK retries stay inside the
logical request/overall deadlines. Hitting a limit returns status=error, a stable code,
and prior evidence; it does not invent a partial answer. A final answer is still permitted
after exactly reaching the total-call cap, provided iterations/time/context remain.

## State, protocol and tools

Every run creates AgentState with its own request ID, question, start time, iteration,
messages, call IDs, fingerprints, tool traces, pending calls, errors and status. Tool traces contain
bounded results and citation lists. No persistent memory or conversation store exists.
Public trace_id is the request ID; iterations/elapsed_ms describe the run.

The service supplies all six strict schemas on every iteration. It replays every provider
output item and returns function_call_output under the original opaque call_id. IDs must
be unique across the entire run. Complete reasoning items are kept internally, including
encrypted content for stateless store=false continuation. This follows the official
[function-calling](https://developers.openai.com/api/docs/guides/function-calling) and
[reasoning](https://developers.openai.com/api/docs/guides/reasoning) guidance.
There is no extra forced answer request after the iteration limit.

Batches are validated for count, protocol structure, unique IDs and context size before
execution. Calls execute sequentially through the existing registry, preserving all
Pydantic validation, allowlist checks, fixed parameterized SQL, role audit and read-only
transactions. Arguments are JSON objects capped at 4096 UTF-8 bytes; duplicate keys,
nonfinite numbers and oversized input are rejected. No arbitrary SQL interface exists.

Canonical fingerprints normalize JSON key order, null optional defaults and omitted
defaults. Repeated calls receive repeated_call without additional tool I/O; attempts
still count toward the total budget. This also suppresses retrying an identical failed
call in the same request; the model may try corrected arguments or another tool.
Fingerprints are internal and are not logged or persisted.

## Error recovery, evidence and context

Unknown tools, invalid JSON/arguments, ordinary tool failures and repeated calls return
structured errors with the original ID. Empty results remain successful empty results,
so the model can distinguish them from failures and retrieve other evidence. A no-call
response ends the loop. With no successful nonempty evidence, the service returns fixed
uncertainty instead of forwarding unsupported model prose. With evidence, the final
answer must pass the existing reference/source/numeric checks.

Tool/provider/overall deadlines, invalid protocol, exhausted budgets and unexpected
internal failures terminate safely. Earlier bounded evidence remains available. Day 8
retains each synchronous worker task and drains it on timeout/cancellation before
returning or closing the registry. No later batch member is launched after a deadline.
Cancellation is re-raised after cleanup, including repeated cancellation during the
worker drain. Python cannot forcibly terminate a worker thread: cleanup may outlast
the execution deadline, so this is **not a hard process wall-clock guarantee**.
The existing bounded loader and database statement/connection/pool deadlines matter;
an arbitrary hung extension could delay cleanup indefinitely. Such extensions are not
supported. The CLI returns a safe request_cancelled code/exit 130 on KeyboardInterrupt.

Each tool is allocated min(per-tool limit, total evidence limit / configured total-call
cap) bytes. Default allocation is 4800 bytes. Complete records are removed to fit both
row and byte caps, preserving valid JSON. Trace results are the same bounded evidence
forwarded to the model. Errors count toward accumulated evidence too. Tiny allocations
can produce evidence_limit instead of a usable record. The accumulated cap is checked
before replay, including safe fallback errors. References use E1 through E20, assigned
to attempts, and document source citations include only forwarded passages.

Context size counts compact UTF-8 JSON containing instructions, schemas and message
history. It is checked before requests, before accumulating output and before adding
tool messages. Oversized context stops execution without dropping unmatched calls or
reasoning items. This is not a token counter, provider context-window guarantee or whole
process memory cap. Provider output also retains its existing 64-item/128000-byte limit.

Day 8 also checks message counts before requests and reserves space for every batch
member's result before starting tool I/O. Raw questions are bounded before whitespace
normalization. Provider output may contain only assistant messages, reasoning and
function calls; system/developer/user output roles are rejected rather than replayed.
An instruction-shaped JSON string inside a passage stays inside function output data.

## Trust, secrets and partial results

The [security guide](security.md) defines the threat model and exact screening limits.
Configured credentials and recognizable credential patterns are rejected in questions,
provider output and decoded function arguments. The registry and shared executor withhold
credential-bearing tool data before evidence/traces. Application log formatting redacts
known credentials and sensitive configuration fields as a backup. Provider errors use
canonical messages, including unknown provider diagnostics. There is no environment,
configuration, filesystem, shell, arbitrary SQL or HTTP-exfiltration tool.

Outcomes now include partial, limitations and pending_tool_calls. Status=completed means
the loop produced a mechanically checked answer, not that coverage or factual accuracy
is guaranteed. Failed tools, successful empty results and selected/truncated records are
distinct in limitations. Limited evidence always adds an application-generated notice;
the application never cuts an answer mid-citation to fit that notice. A notice that
cannot fit the answer cap causes safe rejection instead.

Error exits retain bounded earlier traces, omit a final answer and mark execution_stopped
when tools were attempted. Pending calls are accepted batch calls without a recorded
outcome, including an interrupted call whose worker was drained and its remaining peers;
they must not be interpreted as successful execution. An external cancellation propagates
to the caller rather than returning an outcome, with a cancelled terminal log record.

Passage citation IDs must match their document and be unique within a search result.
Across rounds, different excerpts for one citation, or different row values for the same
operation/filter scope and row identity, cause evidence_conflict and stop synthesis.
Different dates or grouping scopes are allowed. This detects structural conflicts, not
all semantic contradictions between distinct policies. All original reference/numeric
checks remain in effect, with the same incomplete semantic guarantees.

Retrieved text stays untrusted data. Mechanical checks reject unknown evidence IDs,
unknown/orphan document citations (including invented short document references), and
some unsupported numeric literals. They do **not** prove semantic entailment, detect all
misleading relationships, prevent every injection, or validate new arithmetic. Existing
SQL permissions and the fixed tool allowlist enforce execution safety independently.

## Verification

```sh
pytest -q tests/test_multistep.py tests/test_llm.py tests/test_openai_provider.py
pytest -q
ruff check .
ruff format --check .
python -m querypilot.services.evaluate_search
```

The full suite needs TEST_DATABASE_URL and TEST_READER_DATABASE_URL to execute all
PostgreSQL tests; absent variables produce explicit skips. New loop tests cover both
SQL/document orders, batching, recovery, repeated calls, deadlines, limits, state
isolation, CLI options and safe logs. The real SDK uses in-memory HTTP transport to
verify three-round replay and exact IDs without a network request. Day 6 tests still
exercise the retained service. Actual A–D demonstration details and counts are in
[progress.md](progress.md). No frontend, persistent memory, new HTTP route, dependency
or deployment infrastructure was added.
