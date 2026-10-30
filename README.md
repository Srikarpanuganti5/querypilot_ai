# QueryPilot AI — Intelligent Data Agent

QueryPilot AI is a Python portfolio project for an evidence-backed business analytics
assistant. The planned application will translate natural-language questions into approved
tool calls, retrieve synthetic business information, and explain answers with evidence.

Example: **“Which five products generated the highest revenue last month?”**

**Current status: Day 5 document search.** FastAPI, PostgreSQL migrations, synthetic data,
five read-only analytics tools, and local document retrieval are implemented. The registry
has six approved tools. Chat, LLM integration, and the UI are not implemented. Search
and API health/docs work without a database or API key.

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
| HTTPX | FastAPI TestClient HTTP transport; development only | Day 2 |
| PostgreSQL, SQLAlchemy, Psycopg | Database, models, driver | Day 3 |
| Alembic | Versioned database schema migrations | Day 3 |
| OpenAI Python SDK | LLM function/tool calling | Day 6 |
| Streamlit | Interactive analytics interface | Day 9 |
| Docker Compose, GitHub Actions | Service orchestration and CI | Later milestones |

Runtime dependencies are FastAPI, Pydantic, Pydantic Settings, Uvicorn, SQLAlchemy,
Psycopg (binary driver wheel), and Alembic. Development
dependencies are Pytest, Ruff, and HTTPX. Hatchling remains the isolated build dependency.
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
authentication. The current API allows GET and does not enable credentialed CORS.
Database settings in `.env.example` are used only by explicit database commands; OpenAI
entries remain unused. Starting the API never connects to PostgreSQL or migrates tables.

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
The `POSTGRES_*` values configure Compose; keep them consistent with the URL. The
example provides no password. See [database setup and accounting](docs/database.md).

```sh
docker compose up -d db
alembic upgrade head
alembic check
python -m querypilot.db.seed --reference-date 2026-10-27 --random-seed 42
python -m querypilot.db.verify --reference-date 2026-10-27 --random-seed 42
```

Only PostgreSQL runs in Compose. A persistent volume preserves data; no full application
deployment is included. Native PostgreSQL is also supported through `DATABASE_URL`.
No tables are created automatically: run Alembic explicitly before seeding.

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

## Development roadmap

Day 1 establishes the foundation. Day 2 adds FastAPI and health; Day 3 introduces
PostgreSQL and synthetic data; Days 4–5 add analytics and document tools; Day 6 introduces
LLM tool calling; Days 7–8 add orchestration and reliability; Day 9 adds Streamlit.
Later milestones cover broader tests, evaluations, Docker, CI, and deployment docs.
See [PLANS.md](PLANS.md) for the detailed proposed sequence.

## Project documents

- [AGENTS.md](AGENTS.md): contributor conventions and milestone boundaries.
- [GOALS.md](GOALS.md): product scope, security goals, Day 1 acceptance criteria.
- [PLANS.md](PLANS.md): roadmap and implementation plan.
- [docs/architecture.md](docs/architecture.md): planned components and dependencies.
- [docs/database.md](docs/database.md): PostgreSQL setup, ER diagram, accounting and reader access.
- [docs/tools.md](docs/tools.md): approved analytics contracts, security model, CLI and tests.
- [docs/document_search.md](docs/document_search.md): corpus, categories, safe ingestion and evaluation.
- [docs/progress.md](docs/progress.md): implementation and verification status.
- [data/sample/](data/sample/README.md): synthetic fixture policy and developer SQL.

## Security principles

The eventual agent must use approved parameterized operations, never arbitrary
LLM-generated SQL. Tools must use restricted read-only credentials, validate inputs,
and cap iterations, time, and results. Retrieved content must be treated as untrusted.
These requirements will be implemented and tested with their associated features.
Only synthetic, publicly shareable data belongs in this repository.
