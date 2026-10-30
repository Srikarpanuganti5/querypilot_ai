# OpenAI function calling (Day 6)

Day 6 adds a direct official OpenAI Python SDK adapter and a bounded **single-round**
service. It is not the Day 7 autonomous agent loop, and adds no HTTP chat endpoint.
The six existing registry tools remain the only executable business operations.

## Configuration and modes

Install the updated project with `pip install -e '.[dev]'`, or
`uv sync --python 3.12 --extra dev --locked`. The only new direct dependency is
`openai>=2,<3`, locked to the tested SDK version in uv.lock. No agent framework is added.

Mock mode uses deterministic fake model responses and actual registry execution:

```sh
python -m querypilot.tools ask "What is the return policy?" --mock
```

It requires no API key or model setting. Document questions use the real local corpus.
SQL questions still need a seeded PostgreSQL database and READER_DATABASE_URL. Missing
SQL configuration yields tool errors and uncertainty, never fabricated database results.
The mock selector/templates are developer fixtures, not a language-model quality claim.
Mock is the default if neither mode flag is supplied; every outcome identifies its mode.

Live mode requires local environment configuration:

```dotenv
OPENAI_API_KEY=YOUR_LOCAL_SECRET
OPENAI_MODEL=YOUR_SUPPORTED_RESPONSES_TOOL_CALLING_MODEL
QUERYPILOT_LLM_REQUEST_TIMEOUT_SECONDS=25
QUERYPILOT_LLM_MAX_RETRIES=1
```

Set a model your API project can access that supports Responses function calling. The
application has no hardcoded/default model or API key. Keys are SecretStr settings and
never enter prompts, evidence packets or application logs. Keep .env out of Git.

After deliberately authorizing API usage, invoke the explicit paid-request flag:

```sh
python -m querypilot.tools ask "What are the five highest-revenue products?" --live
python -m querypilot.tools ask "What is the return policy?" --live
python -m querypilot.tools ask "How many failed payments occurred?" --live
```

Live failures never switch to mock mode. Authentication, exhausted rate limits, request
timeouts, connection failures, rejected requests and incomplete responses have distinct
safe codes. There is one bounded SDK retry by default (configurable 0–2) for the SDK's
transient-failure policy. A logical request deadline also bounds retries/backoff.

**Verification status:** no API key or model was configured during Day 6 and no paid
request was made. SDK HTTP behavior was tested with an in-memory HTTP transport. Live
model/schema acceptance, actual tool-selection quality and real-world answer accuracy
remain pending approved live verification.

## Request and function-calling lifecycle

```mermaid
sequenceDiagram
    participant U as Developer CLI
    participant S as SingleRoundService
    participant M as Model provider
    participant R as Existing registry
    U->>S: Validated question
    S->>M: Question + six strict function schemas
    M-->>S: One response with zero or more function calls
    S->>R: Bounded sequential batch of approved calls
    R-->>S: Typed results / safe errors
    S->>M: Full output replay + bounded call_id-matched evidence
    Note over S,M: Only if usable evidence exists; tools disabled
    M-->>S: Natural-language answer
    S-->>U: Checked answer + evidence traces / safe errors
```

`agent/tool_schemas.py` derives function definitions from the registry's actual Pydantic
schemas. Strict mode makes every property required, forbids extra properties, and represents
optional inputs as nullable. Explicit null for a non-null defaulted field (limit, top_k,
group_by) is normalized to omission so Pydantic applies its existing default. Required
query values, limits, enums and cross-field checks are still validated by the registry.
The adapter does not duplicate analytics queries or document retrieval.

The provider uses the Responses API with store=false. Function outputs retain their
original call_id. Every first-response output item, including encrypted reasoning items,
is replayed for stateless continuation. The one answer request uses tool_choice=none;
any unexpected function call in its response is rejected without execution. This protocol
follows the official [function-calling guide](https://developers.openai.com/api/docs/guides/function-calling).

There are at most two logical model requests: selection and answer. Zero-call replies
are not forwarded as unsupported business answers. Empty results, failed tools and budget
failures remain distinct in traces. With no usable evidence, the service returns a fixed
uncertainty response and skips synthesis. Multiple first-response calls are supported,
but malformed IDs, duplicate IDs or an excessive batch fail before execution.

## Bounds and evidence

| Setting | Default / bound |
| --- | --- |
| Question | 1–4,000 characters |
| Function argument JSON | 4,096 UTF-8 bytes per call; object only; duplicates/nonfinite numbers rejected |
| Model response replay | At most 64 output items and 128,000 encoded bytes |
| Model request timeout | 25 seconds, configurable 0.05–120 |
| SDK retries | 1, configurable 0–2 |
| Model output tokens | 1,600, configurable 256–4,000 |
| Tool calls in one batch | 6 maximum, configurable downwards |
| Tool await deadline | 15 seconds, configurable 0.01–60 |
| Evidence records per tool | 10, configurable 1–20 |
| Evidence packet | 12,000 UTF-8 bytes per tool, configurable 1,000–32,000 |
| Total evidence packets | 48,000 bytes, configurable 2,000–128,000 |

Evidence limits are divided across the actual batch. Whole records are removed as needed;
JSON is never cut mid-string. Trace output_truncated flags reductions, and analytics
truncated metadata is retained. Document citation lists include only forwarded passages.
If all records are removed or an error packet cannot fit, evidence_limit is returned.
The full original oversized result is not exposed as an unbounded trace.

SQL execution retains all previous role audits, read-only transactions, statement/lock
timeouts, input/output validation and result bounds. Synchronous registry execution runs
off the event loop. An await deadline does not forcibly kill its worker thread; database
server deadlines still bound SQL work. After a tool deadline, remaining calls are skipped,
preventing additional background work. asyncio.run may wait for a cancelled worker during
executor shutdown, so this is not a guaranteed hard CLI wall-clock deadline.

## Outcome and grounding checks

`schemas/llm.py` defines trace_id, mode, normalized question, status, answer, tools,
safe errors and grounding_checks. Each tool trace includes its original call_id, evidence
ID, approved name, validated successful-call arguments, status, bounded result, citations
and truncation/error information. Invalid raw JSON and unknown names are not echoed.
Private prompts, provider response dumps and reasoning items are not returned.

Answers require valid [E1]-style references to nonempty successful results. Referenced
document evidence also requires an exact source citation, such as
`[QP-RET-001#s002-c001]`. Unknown/orphan citations fail closed. Numeric literals must occur
in the cited rows/passages or actual SQL date bounds; user query text, retrieval scores
and timing metadata do not count as numeric evidence. New arithmetic is deliberately
unsupported in Day 6. Empty/failed evidence cannot support a citation.

These checks catch malformed references and some unsupported numbers, **not semantic
entailment**. Wrong relationships, number words, misleading interpretations or a false
claim with otherwise valid references may still pass. A prompt and valid citations do
not guarantee correctness. Review important answers against the returned evidence.

Questions, product/database text and document passages are untrusted data. They cannot
add tools, change SQL privileges or authorize command execution. The final answer request
has tools disabled. Application logs include trace ID, mode, status, tool count and time,
plus the registry's existing approved-name/status records; no question, prompt, key, raw
exception, argument or evidence body is logged. Avoid enabling raw SDK/HTTP debug logs
when handling secrets; the application's safe logger does not govern external loggers.

## Tests and examples actually exercised

```sh
pytest -q -m 'not postgres'
pytest -q tests/test_llm.py tests/test_openai_provider.py
# Existing writer/reader PostgreSQL variables enable the full suite:
pytest -q
```

The standard suite mocks every external model call. Tests use the official SDK with
httpx.MockTransport for wire-format/error/retry/deadline checks, scripted provider turns
for call batching and replay, mock SQL rows for orchestration, and the actual local
document index. No live API test is included in default CI.

The three demo questions were exercised in **mock mode with actual registry results**:
top five product revenues beginning with Outdoors Product 064 at USD 37,882.39;
the 30-calendar-day return window with its original citation; and 486 failed payment
attempts. They verify application wiring, not live model selection or reasoning.
See progress.md for actual test counts, environment repairs and remaining checks.
