# Local Streamlit application (Day 9)

QueryPilot's Streamlit chat calls FastAPI through a thin typed HTTP client. All provider,
tool and database execution stays in the backend. Mock mode uses deterministic model
fixtures with actual approved tools; it does not invent database rows when PostgreSQL
is unavailable. Live OpenAI behavior remains unverified until approved real requests succeed.

## Install and start

From the repository root with Python 3.12:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
# Or, with uv:
uv sync --python 3.12 --extra dev --locked
```

Streamlit is the only new direct dependency (`>=1.49,<2`, resolved/tested at 1.67.0).
It supplies chat widgets, session state, evidence tables and AppTest. HTTPX already
existed for tests and is now an explicit runtime dependency for API transport. No
additional frontend/agent framework was added. Streamlit's transitive rendering/table
dependencies are recorded in uv.lock; the lock resolved 62 packages during this milestone.

Run these in separate terminals, with the virtual environment activated in each:

```sh
# Backend: reads the optional ignored .env for its own secrets/settings
uvicorn querypilot.main:app --host 127.0.0.1 --port 8000
```

```sh
# Frontend: reads this API origin from its process environment, not backend .env
QUERYPILOT_API_BASE_URL=http://127.0.0.1:8000 streamlit run src/querypilot/frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501. .streamlit/config.toml sets a restrained light theme,
loopback binding and disabled anonymous usage statistics. The API origin defaults to
http://127.0.0.1:8000 and accepts only HTTP(S) origins without credentials, paths,
query strings or fragments. No API key or database credentials are required in the UI
process. Imports of frontend modules do not create providers or database connections.

For SQL questions, follow [database setup](database.md) to migrate/seed synthetic data
and provision READER_DATABASE_URL in the backend. Document-policy questions require
only the local corpus. API startup and capability checks do not contact PostgreSQL.
Connected means the API is reachable, not that its database/provider is ready.

Both servers are a **local development demo**. Do not bind/expose them publicly without
authentication, authorization, rate limiting and appropriate deployment/security controls.
CORS is a browser policy, not access control. No public hosting or deployment is included.

## Use the workspace

The sidebar selects Mock demo or Live OpenAI, shows current server limits and lists the
six tool capabilities. Example buttons fill the composer; they never send a question.
Send explicitly to run. During execution, submission, mode, example and clear controls
are disabled. A progress status reports execution without inventing intermediate calls.
Reruns render stored results instead of resubmitting them. History holds up to 20 recent
exchanges in the browser's Streamlit session and disappears on clear/session loss.

Each question runs independently: the request contains only question and mode. Previous
chat messages are never passed to the agent. This is display history, not persistent
multi-turn agent memory. Use synthetic questions only, such as:

- What are our top five products by revenue?
- What is our return policy?
- Which products generated the most revenue, and what is our refund policy?
- How are failed payments handled?

Mock answers are labeled as demonstrations. A completed loop is not a correctness
guarantee. Partial/limited records, failed grounding, conflicting evidence and missing
evidence have distinct visible notices. Reference checks are described precisely rather
than presented as a fully verified answer.

Execution details show the actual request/trace IDs, order, iteration, approved name,
status, total calls and elapsed duration. Per-tool duration is displayed only when the
backend recorded it. Supporting evidence shows actual SQL rows or document passages
and exact source IDs. It does not manufacture citations, SQL, totals or timing data.
Text/passages render as plain text; external images/HTML in retrieved content are not
activated. SQL evidence is a read-only table. No raw model messages, internal prompts,
tool arguments, provider call IDs, stack traces or settings dumps are displayed.

## Live mode

In the backend environment or ignored backend .env, set:

```dotenv
QUERYPILOT_AGENT_LIVE_ENABLED=true
OPENAI_API_KEY=YOUR_LOCAL_SECRET
OPENAI_MODEL=YOUR_SUPPORTED_RESPONSES_TOOL_CALLING_MODEL
```

Restart FastAPI, select Live OpenAI, then explicitly submit a question. If live execution
is disabled or key/model is absent, the UI explains the missing availability and disables
submission. Direct API calls are also gated. The CLI's existing --live opt-in is preserved.
The API gate is not authentication or authorization.

There is no live execution on startup, capability reads, mode selection, example clicks,
history rendering or ordinary reruns. Failed live execution stays live; it never silently
switches to mock. Requests may cost money, so the client performs no automatic retries.
No actual OpenAI request was made during Day 9; live schema/model behavior remains pending.

## HTTP contracts

```text
POST /api/v1/agent/ask
{"question":"What is our return policy?","mode":"mock"}
```

The question uses the existing strict 1–4000-character schema, with raw length checked
before trimming. Extra fields (including tools, SQL, history and limit overrides) are
rejected. A streamed 65536-byte body cap applies before JSON parsing, including bodies
without a trustworthy Content-Length. The server uses its existing execution limits.

The response reuses ExecutionOutcome with request_id and projected public tool traces.
It includes status, mode, safe question/answer, evidence, citations, iterations, elapsed_ms,
partial, limitations, pending_tool_calls and safe errors. trace_id identifies the agent
run; request_id matches X-Request-ID for the HTTP request. Tool arguments/provider call
IDs are omitted. Tool result/citation coherence and UUID identifiers validate at the
public boundary. Existing credential screening and tool/SQL security remain in force.

HTTP-level failures use the existing safe error envelope: 422 validation/JSON failures,
413 oversized body, 403 live mode disabled, and 500 unexpected failures. Agent/provider/
tool failures return HTTP 200 with status=error or no_evidence and bounded prior evidence.
The client and UI inspect the outcome status, not HTTP status alone.

GET /api/v1/agent/capabilities returns only live availability flags and bounded numeric
limits. It exposes no key, model name, database URL or environment mapping and performs
no model/tool execution. Existing health/info/docs endpoints remain available; the
unimplemented /api/v1/chat path remains 404. CORS now advertises GET and POST for explicitly
configured origins; Streamlit's server-to-server client does not require CORS configuration.

## Timeouts and troubleshooting

The HTTP client has a 3-second connection timeout and a read timeout equal to the backend's
advertised agent budget plus 15 seconds (105 seconds at defaults). Responses are capped
at 512000 decoded bytes before JSON parsing. Redirects, inherited proxy credentials and
automatic retries are disabled. Schemas/mode are validated before display; arbitrary
backend error text is never shown. These are transport timeouts, not cancellation of an
already-running backend request or a strict global wall-clock guarantee.

| Symptom | What to check |
| --- | --- |
| Backend unavailable | Start FastAPI; check the frontend API origin/port, then Reconnect |
| Incompatible response | Ensure both processes run this repository/version; check the API origin |
| Live disabled | Opt in on the backend, restart it, then explicitly submit in live mode |
| Missing configuration | Supply backend key/model for live, or restricted reader settings for SQL |
| Database unavailable/unsafe role | Check database readiness, seeded tables and SELECT-only reader provisioning |
| Document collection unavailable | Run from repository root or configure the trusted backend documents path |
| Partial/conflicting evidence | Inspect notices and evidence; narrow the question; do not treat results as complete |
| HTTP timeout | Backend cleanup may still be running; inspect backend status before manually resubmitting |

Day 8 drains workers before resource closure. Cleanup can outlast the client margin,
and closing the browser/HTTP connection does not guarantee cancellation of that request.
A manual retry may therefore create another paid live execution. Day 9 does not add
cross-request idempotency, background jobs, streaming/cancellation controls or a durable
conversation store. UI session gating prevents routine duplicate submissions within a
running session, not globally across separate clients/reloads.

## Verification

```sh
python -m pytest -q
python -m pytest -q tests/test_agent_api.py tests/test_frontend_client.py tests/test_frontend_app.py
ruff check .
ruff format --check .
```

Set TEST_DATABASE_URL and TEST_READER_DATABASE_URL to the isolated synthetic verification
database to execute PostgreSQL tests; otherwise they skip explicitly. API tests use actual
mock orchestration/document retrieval. Client tests use in-memory HTTP transports. AppTest
exercises the actual frontend widgets, state, safe text, SQL tables and citation panels.

Day 9 also ran AppTest without a fake client against a real loopback FastAPI server and
the actual seeded PostgreSQL reader for all four examples. Native HTTP startup checks
covered Streamlit root/health and existing FastAPI routes. This verifies UI element
rendering and the complete mock HTTP/database path, not a manual browser/pixel review or
live OpenAI behavior. See [progress.md](progress.md) for actual results and test counts.
The implementation follows the official [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
and [chat input](https://docs.streamlit.io/develop/api-reference/chat/st.chat_input) APIs.
