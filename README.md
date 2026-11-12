# QueryPilot AI — Intelligent Data Agent

QueryPilot AI is a Python portfolio project for an evidence-backed business analytics
assistant. The planned application will translate natural-language questions into approved
tool calls, retrieve synthetic business information, and explain answers with evidence.

Example: **“Which five products generated the highest revenue last month?”**

**Current status: Day 13 private deployment readiness and demo verification.** FastAPI, PostgreSQL, synthetic data,
five read-only analytics tools, document retrieval, and the direct OpenAI SDK adapter are
implemented. The six-tool workflow is mock/protocol verified; actual live API verification
remains pending. The local Streamlit chat calls a typed agent HTTP endpoint, with tool
traces, evidence and limitation notices. Document demos and API health/docs work without
a database or API key. SQL questions require the actual synthetic reader database.

## Private demo and deployment readiness

The recommended interview deployment is local Docker with screen sharing, using synthetic
data and mock mode. No public cloud resource or paid API is required. Public exposure is
blocked until authentication/access control, rate limiting and HTTPS are addressed.
See [deployment options and cost research](docs/deployment.md) and the
[2–3 minute demo script, recording plan and manual browser checklist](docs/demo.md).

```sh
.venv/bin/python scripts/prepare_docker.py
make demo-up
make demo-smoke
.venv/bin/python -m querypilot.cli smoke-test --backend-url http://127.0.0.1:18000
# Automated UI against actual container HTTP; does not establish manual browser acceptance:
.venv/bin/python scripts/verify_demo_ui.py --backend-url http://127.0.0.1:18000
# When finished; database volume is retained:
make demo-down
```

`compose.demo.yaml` reuses the existing stack and adds CPU/memory/PID/log limits. The new
smoke command validates liveness/readiness, API contract and four mock acceptance workflows.
`make demo-smoke` also verifies the exact configured database and independently compares SQL
results. Host-side direct DB verification is explicitly skipped unless `--verify-database`
is requested with matching reader settings. No credentials or raw replies are printed.

Manual browser acceptance and live OpenAI remain **NOT VERIFIED**. Day 12 remote CI passed
on `f43b45e`; Day 13 was pushed through `9ab3c07`. See the
[Day 13 CI run](https://github.com/Srikarpanuganti5/querypilot_ai/actions/runs/43164942219)
for its actual remote status. The local benchmark still
passes **24/38**, with **14 known failures**, and does not measure production-level accuracy.

## Docker quick start and CI

```sh
.venv/bin/python scripts/prepare_docker.py
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up --build --wait --wait-timeout 180
docker compose --env-file .env.docker exec -T backend python -m querypilot.services.container_smoke
docker compose --env-file .env.docker down --timeout 40
```

Backend: http://127.0.0.1:18000; Streamlit: http://127.0.0.1:18501. PostgreSQL is internal.
The distinct `querypilot_day12` project/volume preserves native databases. A one-shot job
applies existing migrations/seed and verifies restricted reader access before the backend
starts. `/health` is liveness; `/ready` verifies database/document readiness and returns
503 when unavailable. Backend receives no administrative database credentials.

**DOCKER VERIFIED (2026-11-11):** both builds, four real container workflows, the protected
benchmark gate, outage/restart recovery, persistent storage and clean shutdown passed.
A one-line Compose tmpfs quoting fix remains uncommitted.
Track the current remote result in [GitHub Actions](https://github.com/Srikarpanuganti5/querypilot_ai/actions/workflows/ci.yml). See
[container setup, recovery and exact commands](docs/containers.md).

For native CI parity after preparing the dedicated test environment:

```sh
set -a
source .local/integration.env
set +a
.venv/bin/python scripts/run_checks.py
```

This runs lint, formatting, the full suite with coverage, mandatory original PostgreSQL
case checks, doctor and the reviewed case-level benchmark gate. No skipped test is accepted
by CI. The gate preserves 24 previously passing cases while reporting all 14 known failures.

## Planned features

- FastAPI backend with `/health` and `/api/v1/chat`.
- Synthetic e-commerce data in PostgreSQL.
- Predefined, parameterized read-only SQL analytics tools.
- Document search, multi-step LLM tool calling, and evidence-backed answers.
- Tool traces, input validation, errors, timeouts, and logging.
- Streamlit interface, automated tests, evaluations, Docker Compose, and CI.

## Planned architecture

```text
Streamlit → FastAPI routes → Services / Agent → Approved tools
                                               ├── Analytics → PostgreSQL
                                               └── Document search → Synthetic documents
```

The src-layout package separates routes, orchestration, tools, database access, schemas,
services, and configuration. See [architecture](docs/architecture.md) for boundaries.

## Technology stack

| Technology | Purpose | Milestone |
| --- | --- | --- |
| Python 3.12 | Language and development baseline | Day 1 |
| Hatchling | Build/install the src-layout package | Day 1 build dependency |
| Pytest | Automated tests, starting with package import | Day 1 development dependency |
| Ruff | Linting, import sorting, formatting | Day 1 development dependency |
| FastAPI, Pydantic, Uvicorn | HTTP API, validation, server | Day 2 |
| Pydantic Settings | Typed environment and optional `.env` configuration | Day 2 |
| HTTPX | TestClient transport and frontend-to-backend HTTP client | Day 2; runtime in Day 9 |
| PostgreSQL, SQLAlchemy, Psycopg | Database, models, driver | Day 3 |
| Alembic | Versioned database schema migrations | Day 3 |
| OpenAI Python SDK | Direct async Responses function calling, with bounded retries | Day 6 |
| Streamlit | Interactive analytics interface | Day 9 |
| Docker Compose, GitHub Actions | Isolated services and locked-dependency CI | Day 12; Docker/remote execution unverified |

Runtime dependencies are FastAPI, Pydantic, Pydantic Settings, Uvicorn, SQLAlchemy,
Psycopg (binary driver wheel), Alembic, the official OpenAI SDK, HTTPX and Streamlit.
Development dependencies are Pytest, Ruff and pinned coverage for CI measurement. Hatchling remains the isolated build dependency.
Other libraries will be added when used. Uvicorn's base install supports `--reload`
through polling, so no optional watcher or event-loop packages are required.

## Setup and validation

Install Python 3.12, then run from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c "import querypilot; print(querypilot.__name__)"
python -m pytest -q
ruff check .
ruff format --check .
```

On Windows, activate with `.venv\Scripts\activate` instead. `-e` installs in editable
mode; `[dev]` adds Pytest and Ruff. Hatchling builds package metadata for the installer.
The smoke test imports the installed package without modifying Python's import path.

Alternatively, with uv already installed:

```sh
uv sync --python 3.12 --extra dev --locked
uv run --extra dev python -m pytest -q
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
```

`uv.lock` records resolved versions for uv users. The pip workflow uses compatible
ranges in `pyproject.toml`. Installation alone does not start the server.

## Start the backend

For a repeatable native PostgreSQL setup, install PostgreSQL server tools, then run:

```sh
.venv/bin/python scripts/prepare_local.py
.venv/bin/python -m querypilot.cli doctor --reference-date 2026-10-27
```

The helper creates an owned loopback cluster under ignored `.local/postgres` on port
55440, separate synthetic development/test databases and restricted reader credentials.
It writes a private ignored `.env` only if none exists, preserves existing data/configuration,
and never resets a database. Restart FastAPI after changing its configuration. Mock SQL
requires a configured **reader database**, not an OpenAI key; a healthy `/health` alone
does not verify SQL readiness. [Testing and diagnostics](docs/testing.md) explains exact
prerequisites, safety checks and alternative existing database setup.

With the virtual environment activated:

```sh
uvicorn querypilot.main:app --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI, or http://127.0.0.1:8000/redoc for ReDoc.
The HTML documentation pages reference CDN-hosted browser assets; the JSON API and
OpenAPI specification work without loading those assets. `--reload` is for development.

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Process liveness, independent of databases and providers |
| `GET /api/v1/info` | API name, package version, description |
| `GET /api/v1/agent/capabilities` | Safe mode availability and execution limits; no credentials |
| `POST /api/v1/agent/ask` | Independent question in mock/live mode; safe outcomes and evidence |
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc |
| `GET /openapi.json` | OpenAPI specification |

```sh
curl http://127.0.0.1:8000/health
# {"status":"healthy","service":"querypilot-ai","version":"0.1.0"}
curl http://127.0.0.1:8000/api/v1/info
# {"name":"QueryPilot AI","version":"0.1.0","description":"Tool-Using LLM Agent API"}
```

`/api/v1/chat` is deliberately absent and returns 404. Health is not database readiness.

## Start the interactive frontend

Run both processes from the repository root in separate terminals, with `.venv` activated:

```sh
# Terminal 1 — backend; reads your local backend .env
uvicorn querypilot.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — UI; only needs its API origin, not backend secrets
QUERYPILOT_API_BASE_URL=http://127.0.0.1:8000 streamlit run src/querypilot/frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501. Mock demo is the default and uses deterministic model fixtures
with actual approved tools. The sidebar examples fill the composer; sending executes a
question. Displayed history survives reruns but is never sent as agent memory. Each answer
has execution and supporting-evidence panels, with exact citations and partial-result notices.

Live mode makes paid requests only when a question is explicitly submitted. Set
`QUERYPILOT_AGENT_LIVE_ENABLED=true`, `OPENAI_API_KEY` and `OPENAI_MODEL` in the **backend**
environment, then restart FastAPI. Mode selection/page load never invokes the agent.
Live failures do not fall back to mock. Live model verification is still pending.

This is a **local development demonstration**, without authentication, authorization or
rate limiting. Keep both servers on loopback. Public deployment requires those controls
and appropriate deployment hardening. CORS is not authentication. See
[frontend setup, API behavior and troubleshooting](docs/frontend.md).

## Configuration, errors, and logs

All settings have working defaults. Optionally copy `.env.example` to `.env` and edit:

```dotenv
QUERYPILOT_LOG_LEVEL=INFO
QUERYPILOT_CORS_ORIGINS=["http://localhost:8501"]
```

Environment variables override `.env`. Settings are validated once per process; restart
the server after changing them. `QUERYPILOT_CORS_ORIGINS` defaults to `[]`, allowing no
cross-origin browser access. Supply exact HTTP(S) origins as a JSON array, without paths,
credentials, query strings, fragments, or wildcards. CORS is a browser policy, not
authentication. The current API allows GET/POST and does not enable credentialed CORS.
Database settings are used by explicit database/tool commands. OpenAI settings are used
only by explicit live CLI/HTTP questions. API startup never calls OpenAI, connects to PostgreSQL
or migrates tables.

Application HTTP errors use an `error` object with `code`, `message`, `request_id`, and
`details`. Invalid requests receive 422; unknown routes 404; unexpected failures 500.
Error responses exclude internal exception text, stack traces, and submitted values.
The framework's CORS preflight responses retain their standard protocol format.

Application logs are JSON on stderr. Request records contain generated IDs, method,
route template, status, and duration; failure logs include the exception class only.
Query strings, headers, bodies, settings, and exception messages are not logged.
The standard Uvicorn access logger is disabled at application startup to avoid raw URL
logging; Uvicorn's lifecycle logs remain separate. `X-Request-ID` correlates application
responses with logs. Never commit `.env`, API keys, passwords, or private data.

## PostgreSQL and synthetic data

Copy `.env.example` to `.env`, choose local database credentials, and set `DATABASE_URL`
using `postgresql+psycopg://USER:ENCODED_PASSWORD@localhost:5432/querypilot`.
These are manual/native settings. The full Docker workflow uses separate `.env.docker`
configuration and an internal service hostname. No password is supplied in examples.
See [database setup and accounting](docs/database.md).

```sh
alembic upgrade head
alembic check
python -m querypilot.db.seed --reference-date 2026-10-27 --random-seed 42
python -m querypilot.db.verify --reference-date 2026-10-27 --random-seed 42
```

The commands above target an explicitly configured native database. Day 12 Compose instead
runs PostgreSQL, setup, backend and frontend, with setup invoking the same migration/seed
mechanisms. API startup never automatically creates tables.

The reference fixture contains **500 customers, 100 products, 3,000 orders, 6,000 items,
3,006 payments, and 120 refunds**. It covers the preceding twelve calendar months relative
to the explicit reference date. Rerunning the same fixture is a no-op; different or edited
existing data is refused without overwriting it. Identities are synthetic and emails use
`example.invalid`. No Faker dependency or external data download is needed.

Money uses Decimal/NUMERIC in USD; timestamps use UTC. Order totals equal item totals.
Completed-order revenue excludes pending, cancelled, and fully refunded orders. Failed
payments are attempts, never collected revenue. Refunds are full-order in this fixture
and never exceed their successful payment. See the [accounting contract](docs/database.md)
for cash-versus-status semantics, simplifications, and cross-row verification limits.

The [developer SQL examples](data/sample/analytics.sql) include monthly revenue, top five
products, refunds by category, customer order counts, and failed payments. Run them with
`psql -v ON_ERROR_STOP=1 -f data/sample/analytics.sql` using local PG authentication settings.
They are not exposed as agent tools. Configure the separate SELECT-only reader role using
[reader-role instructions](docs/database.md#read-only-role-provisioning) for SQL tools.

```sh
# Independent tests, including existing API checks:
pytest -q -m 'not postgres'
# With TEST_DATABASE_URL set to an expendable PostgreSQL database:
pytest -q -m postgres
```

Database tests use actual Alembic migrations in isolated temporary schemas; they require
CREATE SCHEMA privileges. They skip explicitly when `TEST_DATABASE_URL` is absent.
Do not point tests at production. See [actual results](docs/progress.md): native PostgreSQL
was tested; Docker daemon/container startup was unavailable in this environment.

## Read-only analytics tools

Day 4 adds five predefined operations, with validated inputs/outputs, bounded results,
UTC date filters, structured errors/logs, and PostgreSQL query timeouts. No new dependencies
were needed. There is no arbitrary SQL interface or analytics HTTP endpoint.

| Tool | Parameters |
| --- | --- |
| `get_top_products` | optional dates, `limit=5` (max 20) |
| `get_revenue_summary` | optional dates, `group_by=day/month/category` (default month) |
| `get_refund_analytics` | optional dates, `limit=10` (max 20) |
| `get_customer_order_summary` | optional positive customer ID, `limit=10` (max 20); no customer PII |
| `get_payment_status_summary` | optional dates; successful/failed attempts kept separate |

Provision the dedicated reader as described in [database setup](docs/database.md#read-only-role-provisioning),
then set `READER_DATABASE_URL` in your local `.env`. This URL is mandatory for tools;
writer credentials are never used as a fallback. A privilege audit rejects elevated roles,
table owners, memberships, and write/schema/TEMP privileges. Every execution explicitly
uses a read-only transaction. Runtime queries use SQLAlchemy/Psycopg, not shell commands.

```sh
python -m querypilot.tools get_top_products --arguments '{"limit":5}'
python -m querypilot.tools get_revenue_summary --arguments '{"group_by":"month"}'
pytest -q -m 'not postgres'
# After setting TEST_DATABASE_URL (writer) and TEST_READER_DATABASE_URL (reader):
pytest -q -m postgres
```

Dates use inclusive start/exclusive end in UTC. Supplied two-sided ranges are capped at
366 days; omitted bounds cover available history. Results serialize Decimal money as
strings, mark truncation explicitly, and expose no customer names/emails. Revenue counts
current completed orders, excluding fully refunded orders; payment settlement and refund
dates follow separate rules. Read the [tool contracts and security guide](docs/tools.md)
before interpreting these aggregates. FastAPI still requires no database at startup.

## Local document search

`search_business_documents` retrieves actual passages from **10 synthetic documents / 40
chunks** using deterministic BM25. Results contain document ID/title/category, section,
excerpt, score and citation. It does not generate answers or execute retrieved instructions.
No embeddings, search service, model API or new dependency is involved.

```sh
python -m querypilot.tools search_business_documents --arguments '{"query":"What is the return window for products?","top_k":1}'
python -m querypilot.tools search_business_documents --arguments '{"query":"How are failed payments handled?","top_k":1}'
python -m querypilot.tools search_business_documents --arguments '{"query":"When can customers cancel an order?","top_k":1}'
python -m querypilot.services.evaluate_search
```

Categories: `refunds`, `shipping`, `payments`, `cancellations`, `products`, `support`,
`discounts`, `fraud`, `inventory`, `faq`. Query strings are capped at 500 characters;
`top_k` defaults to 5 and is capped at 10. A category filter is optional.

Example: “Customers may request a return within 30 calendar days of delivery.”
Citation: `QP-RET-001#s002-c001`. Failed-payment and cancellation passages cite
`QP-PAY-003#s002-c001` and `QP-CAN-004#s002-c001` respectively.

Run from the repository root. `QUERYPILOT_DOCUMENTS_PATH` selects the trusted corpus
(default `data/documents`); tool arguments cannot select paths. Safe ingestion rejects
symlinks/unsupported files and bounds file/chunk sizes. Every result marks passages as
untrusted. See [the search guide](docs/document_search.md) for platform/trust boundaries.

The index is built lazily and cached per registry. Recreate the registry after edits.
Search needs no database settings; SQL tools still require READER_DATABASE_URL with no
writer fallback. All five existing analytics operations remain available.

Run `pytest -q -m 'not postgres'` for search and independent tests; configure writer/reader
test URLs for the full PostgreSQL suite. The authored 20-question set measured **Hit
Rate@5 = 1.0 and MRR@5 = 1.0**. This is a curated regression set, not a held-out benchmark
or a guarantee for arbitrary questions.

## Multi-step agent demonstration

Day 7 extends the workflow into repeated model/tool rounds with a grounded final answer.
Strict schemas still derive from all six registry tools. The Day 6 SingleRoundService
remains available for compatibility; both ask CLI entry points now use MultiStepService.

```sh
# Fake model selection/synthesis, actual local document retrieval; no API key needed:
python -m querypilot.cli ask "What is the return policy?" --mock
# Mock SQL demonstrations still require the real restricted reader database:
python -m querypilot.tools ask "What are the five highest-revenue products?" --mock
python -m querypilot.tools ask "How many failed payments occurred?" --mock
python -m querypilot.cli ask "Which products generated the most revenue, and what is our refund policy?" --mock --verbose
python -m querypilot.cli ask "What is the revenue trend, and how are failed payments handled?" --mock --max-iterations 5 --max-tool-calls 10 --timeout-seconds 90
```

The mock policy answer quotes the 30-calendar-day window with `[E1]` and
`[QP-RET-001#s002-c001]`. Actual seeded SQL demos reported five product revenues beginning
with USD 37,882.39 and 486 failed payment attempts. These are **mock-mode wiring results**,
not real model-selection measurements. SQL failures never substitute fake metrics.

For deliberately authorized paid usage, set `OPENAI_API_KEY` and `OPENAI_MODEL` in your
local environment or ignored `.env`. Choose a supported Responses tool-calling model
available to your project; no model identifier or API key is hardcoded.

```sh
python -m querypilot.tools ask "What is the return policy?" --live
```

Live failures remain live errors, never silent mock fallback. No live request was made
during Days 6–7: key/model were not configured. Real API/schema acceptance and answer quality
remain unverified. See [LLM setup](docs/llm.md) and [agent limits](docs/agent.md) before enabling live usage.

Verbose outcomes contain trace ID, explicit mode, question, answer, tool status/evidence/citations
and safe errors. Requests/retries, batch size, tool wait time and evidence bytes/rows are
bounded. Citation membership and supported numeric literals are checked, but these checks
do **not** prove semantic grounding or guarantee correctness. Retrieved text stays untrusted;
SQL privileges and registry validation still enforce the actual execution boundary.

```sh
pytest -q tests/test_llm.py tests/test_openai_provider.py
pytest -q -m 'not postgres'
```

All external model calls in standard tests are mocked, including official SDK HTTP tests
using an in-memory transport. Live verification is opt-in via the CLI, outside default CI.

The default limits are **5 model iterations, 10 total calls, 5 calls per iteration and
90 seconds**. A final answer request counts as an iteration. Pydantic enforces upper
bounds of 10 iterations, 20 total calls, 6 calls per iteration and 300 seconds. Context
is capped at 128,000 UTF-8 serialized bytes (instructions, schemas and history); individual
tool packets at 12,000 bytes and accumulated evidence at 48,000 bytes. All are configurable
through the settings in `.env.example`; CLI flags override the corresponding agent limits.
Calls execute sequentially, and repeated canonical calls return errors without reexecution.
Limit failures preserve earlier evidence but do not return a fabricated partial answer.

Without `--verbose`, the CLI omits the question, arguments, call IDs and result bodies;
verbose mode includes bounded evidence, never private reasoning or internal prompts.
Only use synthetic input. State is local to each run, with no persistent conversation memory.
Tool await cancellation cannot kill a running worker thread; CLI shutdown can outlast its
deadline. See [agent behavior and limitations](docs/agent.md).

## Development roadmap

Day 11 adds a versioned 38-case benchmark, independent fixture-derived facts, tool/retrieval/
citation metrics, reliability/performance measurements and JSON/Markdown reports. It reuses
the existing agent request lifecycle and real tools with a deterministic mock provider.

```sh
.venv/bin/python -m querypilot.cli eval --mode mock --output reports/evaluation/day11
.venv/bin/python -m querypilot.cli eval --category documents --limit 1 --output reports/evaluation/doc-smoke
```

SQL evaluation requires the exact prepared synthetic fixture and restricted reader.
The full benchmark currently passes **24/38 cases**, with **14 known failures**, and exits 1 while preserving its
reports; the one-case document smoke exits 0. Failed cases expose mock routing/filtering
limitations. Mock scores and timings do not measure live LLM accuracy or latency.
This benchmark does not establish production-level agent accuracy.
Semantic faithfulness and claim-level citation precision are **NOT EVALUATED**; live
OpenAI evaluation remains unverified and `eval --mode live` is rejected. Generated reports
are ignored. See [evaluation definitions and limitations](docs/evaluation.md).

Day 10 diagnosed the observed top-products failure: the normal backend had no reader
configuration, while Day 9's temporary verification server received one explicitly.
The durable local setup and specific database diagnostics close that setup gap. The
combined failed-payment count/policy question now selects both real payment analytics
and document retrieval in mock mode.

To run all real integration tests after preparation:

```sh
set -a
source .local/integration.env
set +a
.venv/bin/python -m pytest -q
# Only actual loopback HTTP and UI-to-database smoke checks:
.venv/bin/python -m pytest -q -m local_http
```

The explicit acknowledgement and dedicated test database are required before fixtures
may create disposable schemas. Development database URLs are rejected. Without the
integration environment, PostgreSQL cases skip explicitly. No OpenAI requests are needed.
See [the verification matrix](docs/testing.md) for what each test category proves.

Day 8 strengthens the existing agent with credential screening, safe provider errors,
message-count limits, explicit partial-result metadata, citation provenance and conflicting
record checks, correlated telemetry, and owned worker cleanup on timeout/cancellation.
The default message limit is 128 (hard maximum 256), configured with
`QUERYPILOT_AGENT_MAX_MESSAGES` or `--max-messages`. Existing iteration/call/time defaults
remain 5/10/5/90 seconds. No runtime or development dependencies were added.

Credential-like input is rejected before model requests. Credential-bearing tool results
are withheld rather than forwarded as evidence. Configured API keys, database URLs and
passwords are screened; common authorization/key patterns and sensitive configuration
fields are also redacted from application-controlled output. Provider diagnostics use a
fixed code/message catalog. No raw authorization headers or environment dumps are logged.

Outcomes expose `partial`, `limitations` and `pending_tool_calls`. A completed loop may
still have limited evidence; it is not a claim that the whole question was answered.
Errors preserve earlier bounded traces and suppress a misleading final answer. Contradictory
values for the same scoped record/passage stop synthesis. Cancellation propagates after
the current synchronous worker is drained, before resources close. Cleanup can therefore
outlast the execution deadline; a thread cannot be forcibly terminated safely.

See [the security threat model and limitations](docs/security.md). Structural boundaries,
least privilege, screening and adversarial tests reduce risk; they do not guarantee prompt
injection immunity, detect every secret encoding, or establish factual entailment.
Live OpenAI verification remains pending; no paid requests were made on Day 8.

Day 1 establishes the foundation. Day 2 adds FastAPI and health; Day 3 introduces
PostgreSQL and synthetic data; Days 4–5 add analytics and document tools; Day 6 introduces
LLM tool calling; Days 7–8 add orchestration and reliability; Day 9 adds Streamlit.
Day 12 adds Docker/CI configuration; required Docker verification is blocked by the local
daemon. Day 13 deployment and end-to-end demonstration require a separate request.
See [PLANS.md](PLANS.md) for the detailed proposed sequence.

## Project documents

- [AGENTS.md](AGENTS.md): contributor conventions and milestone boundaries.
- [GOALS.md](GOALS.md): product scope, security goals, Day 1 acceptance criteria.
- [PLANS.md](PLANS.md): roadmap and implementation plan.
- [docs/architecture.md](docs/architecture.md): planned components and dependencies.
- [docs/database.md](docs/database.md): PostgreSQL setup, ER diagram, accounting and reader access.
- [docs/tools.md](docs/tools.md): approved analytics contracts, security model, CLI and tests.
- [docs/document_search.md](docs/document_search.md): corpus, categories, safe ingestion and evaluation.
- [docs/llm.md](docs/llm.md): Responses adapter, setup and retained Day 6 service.
- [docs/agent.md](docs/agent.md): Day 7 loop, state, limits, recovery and CLI.
- [docs/security.md](docs/security.md): Day 8 trust boundaries, error behavior and verification limits.
- [docs/frontend.md](docs/frontend.md): local Streamlit setup, typed HTTP contracts, session state and UX.
- [docs/testing.md](docs/testing.md): isolated test setup, doctor, verification labels and real workflows.
- [docs/progress.md](docs/progress.md): implementation and verification status.
- [data/sample/](data/sample/README.md): synthetic fixture policy and developer SQL.

## Security principles

The agent uses approved parameterized operations, never arbitrary LLM-generated SQL.
Tools require restricted read-only credentials, validate inputs, and cap iterations,
time and results. Retrieved content stays untrusted. Preserve these tested boundaries
as new features are added.
Only synthetic, publicly shareable data belongs in this repository.
