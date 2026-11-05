# Progress

## Day 1 — repository foundation

Status: complete and validated. Historical Day 1 results are retained below.

The earlier pass exceeded Day 1. Its API, database/LLM tools, frontend, Docker, CI,
seed/evaluation scripts, advanced tests, and operational documentation have been removed
from this working tree to match the requested scope.

At Day 1 completion: src-layout package boundaries, development configuration, environment template,
ignore rules, goals, roadmap, architecture, contributor instructions, README, synthetic
sample-data directory, and one import smoke test. There are no runtime dependencies.

## Validation

Verification used Python 3.12.15. Commands below ran from the repository root unless
otherwise stated. No PostgreSQL, OpenAI, or other application service was contacted.

| Command/check | Actual result |
| --- | --- |
| `git status --short` during initial inspection | Failed: directory is not a Git repository. No commit or push was attempted. |
| `.venv/bin/python -m pip --version` | Failed: existing uv-created environment has no pip module. Used uv instead. |
| Offline `uv sync --python 3.12 --extra dev` (full command below) | Exit 0; resolved 8 packages, rebuilt editable package, removed 58 unused later-milestone packages. |
| `.venv/bin/python --version` | Exit 0; Python 3.12.15. |
| `.venv/bin/python -c "import querypilot; print(querypilot.__name__); print(querypilot.__file__)"` | Exit 0; imported `querypilot` from this workspace's `src/querypilot/__init__.py`. |
| `.venv/bin/python -m pytest -q` | Exit 0; 1 passed in 0.00s. |
| `.venv/bin/ruff check .` | Exit 0; all checks passed. |
| `.venv/bin/ruff format --check .` | Exit 0; reported 17 files already formatted. |
| Python directory/scope assertions and tree printer | Exit 0; required directories exist, runtime dependencies are empty, exactly one test exists, source files are package initializers only, Docker/Compose/CI files are absent. |
| Offline `uv lock --check` using the same temporary executable/cache as below | Exit 0; lockfile is current, resolved 8 packages. |
| Installed package metadata inspection | Exit 0; querypilot-ai 0.1.0, Pytest 9.1.1, Ruff 0.17.2. |

The existing temporary uv installation and cached Python/dependencies allowed installation
without network access. The exact synchronization command was:

```sh
UV_PYTHON_INSTALL_DIR=/private/tmp/querypilot-python /private/tmp/querypilot-bootstrap/bin/uv sync --python 3.12 --extra dev --offline --cache-dir /private/tmp/querypilot-uv-cache
```

Normal setup commands using pip or uv are in README.md. No unresolved Day 1 blocker.
The initial Day 1 task did not initialize Git or make commits. In a follow-up request,
the user authorized committing and pushing completed daily milestones. Git is now
initialized on `main`, and that ongoing preference is recorded in AGENTS.md.

## Day 2 — FastAPI backend foundation (2026-10-26)

Status: implemented and verified. The user explicitly approved Day 2, and commit
`d0af7a7` was pushed. The results below describe the Day 2 milestone at completion.

### Accomplishments and files

- Added `src/querypilot/main.py`: application factory, metadata, lifespan, composition.
- Added `api/router.py` and `api/routes/{health,info}.py`: `/health` and `/api/v1/info`.
- Added `core/config.py`: typed environment settings and exact-origin validation.
- Added `core/logging.py` and `api/middleware.py`: JSON logs, request IDs, safe failures.
- Added `api/errors.py` and `schemas/system.py`: consistent typed JSON application errors.
- Added `tests/test_api.py` and `tests/test_config.py`; retained the Day 1 smoke test unchanged.
- Updated `pyproject.toml`/`uv.lock` with runtime FastAPI, Pydantic, Pydantic Settings,
  Uvicorn, and development-only HTTPX. Their purposes are explained in README.md.
- Updated `.env.example`, README.md, AGENTS.md, GOALS.md, PLANS.md, architecture/progress,
  and the package docstrings for the implemented layers.

### Commands and actual results

Commands used Python 3.12.15 and the existing virtual environment. No database, API key,
or external application service was needed.

| Command/check | Actual result |
| --- | --- |
| Offline uv sync using the Day 1 temporary executable/cache | Exit 0; resolved 27 packages, installed 20, rebuilt editable package. |
| Initial `ruff check . --fix` | Failed on one long line; formatting fixed it. |
| `ruff format .` then `ruff check .` | Exit 0; 6 files reformatted, lint passed. |
| Initial pytest run | 23 passed; then added wildcard-host CORS validation coverage. |
| `.venv/bin/python -m pytest -q` (final run) | 24 passed, 1 dependency deprecation warning in 0.19s. |
| `.venv/bin/ruff format --check .` | Exit 0; 28 files already formatted at that point. |
| Uvicorn reload start on 127.0.0.1:8765, sandboxed | Failed: operation not permitted. |
| Same Uvicorn command with approved sandbox escalation | Started reload and server processes; application startup complete. |
| HTTPX requests to loopback, sandboxed | Failed: operation not permitted. |
| Same HTTP checks with approved sandbox escalation | Health/info/docs/redoc/OpenAPI all returned 200; unknown route returned JSON 404. |
| Ctrl-C to verification server | Clean shutdown; application/server/reloader stopped. |
| Final `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` | Exit 0; all checks passed, 28 files already formatted. |
| Package and app import check | Exit 0; `QueryPilot AI 0.1.0`. |
| Offline `uv lock --check` with the existing temporary executable/cache | Exit 0; resolved 27 packages, lockfile current. |
| `git diff --check` | Exit 0; no whitespace errors. |
| Tracked/pending file inspection | `.env` and `.venv` excluded; only `.env.example` present; no recognized OpenAI/GitHub key or private-key patterns found. This is a targeted check, not an exhaustive secret audit. |
| `git diff -- tests/test_smoke.py` | Empty; Day 1 smoke test unchanged. |

Server command actually run:

```sh
.venv/bin/uvicorn querypilot.main:app --reload --host 127.0.0.1 --port 8765
```

Live HTTP output:

```text
GET /health: 200 application/json
{'status': 'healthy', 'service': 'querypilot-ai', 'version': '0.1.0'}
GET /api/v1/info: 200 application/json
{'name': 'QueryPilot AI', 'version': '0.1.0', 'description': 'Tool-Using LLM Agent API'}
GET /docs: 200 text/html; charset=utf-8
GET /redoc: 200 text/html; charset=utf-8
GET /openapi.json: 200 application/json
GET /unknown: 404 application/json
Live HTTP checks: PASS
```

The tests cover metadata, documentation, OpenAPI, 404/405/422/500 errors, sanitized
HTTP exception details and logs, CORS allow/deny/preflight/defaults, settings precedence,
invalid origins/log levels, and the original package import test.

### Problems and practical limits

Local socket operations required sandbox approval, after which startup and HTTP checks
passed. FastAPI/Starlette TestClient emits an upstream deprecation warning for HTTPX;
tests pass and HTTPX remains the test transport requested for this milestone. Browser
rendering and CDN asset downloads were not tested; documentation HTML and schema were.
Application error envelopes exclude raw inputs and internal details; built-in CORS
preflight responses retain their standard framework format. No unresolved functional blocker.

### Day 3 preparation

After a separate request: PostgreSQL schema constraints, a reproducible publicly shareable
synthetic e-commerce dataset, and separate setup/reader credentials. No database, seed,
chat, LLM, agent-tool, Docker, or CI implementation is included in Day 2.

## Day 3 — PostgreSQL and synthetic e-commerce data (2026-10-27)

Implementation and native PostgreSQL verification are complete. Docker container startup
remains an unresolved environment-specific check: the Docker daemon is not running.
The PostgreSQL-only Compose definition validates, but no container was started or claimed
to pass. The user has now approved Day 3 committing and pushing in focused groups.

### Changes and review groups

1. Schema/migrations: `db/models.py`, `db/session.py`, database settings in `core/config.py`,
   `alembic.ini`, `migrations/env.py`, migration template and initial revision `0001`.
2. Data/verification/tests: `db/seed.py`, `db/verify.py`, `tests/test_database.py`,
   `tests/test_database_postgres.py`, developer analytics and reader-role SQL.
3. Development setup/docs: PostgreSQL-only `compose.yaml`, `.env.example`, dependency
   manifest/lockfile, README, database guide/ER diagram, architecture, goals, plans,
   repository instructions, sample-data policy, and this progress report.

The user's preference for multiple focused commits per day is now recorded in AGENTS.md.
These groups will be committed separately under the user's follow-up approval. No API endpoints, agent
tools, LLM dependencies, UI, full application Docker deployment, or CI were added.

### Actual dataset

Generated and loaded into an isolated native PostgreSQL **16.13 (Homebrew)** database,
using Python 3.12.15, reference date `2026-10-27`, and random seed `42`:

| Table | Actual rows |
| --- | ---: |
| customers | 500 |
| products | 100 |
| orders | 3,000 |
| order_items | 6,000 |
| payments | 3,006 |
| refunds | 120 |

Orders: 2,400 completed, 300 pending, 180 cancelled, 120 refunded. Successful payments:
2,520; failed attempts: 486 (bank transfer 166, card 163, wallet 157). Every order total
matches its Decimal line totals; refunds reference successful payments and reconcile
to full refunded-order totals. See database.md for the explicit accounting contract.

### Commands and actual verification

The initial `git status --short --branch` showed clean `main...origin/main` before edits.

| Command/check | Actual outcome |
| --- | --- |
| `docker info --format '{{.ServerVersion}}'` | Failed: Docker daemon socket unavailable. |
| Offline uv sync | Failed initially because Alembic was not cached. |
| Approved online uv sync with dev extra | Passed; resolved 34 packages; installed Alembic 1.20.1, SQLAlchemy 2.1.6, Psycopg 3.3.6 and their required dependencies. |
| Approved `pg_ctl ... -p 55432 ... start` | Passed; isolated existing temporary cluster started on loopback. |
| `createdb ... querypilot_day3_verify` | Passed; empty verification database created. |
| Alembic autogenerate initial revision, then manual review | Created static migration `0001` for all six tables/indexes. |
| `alembic upgrade head` against the empty database | Passed. |
| Final `alembic current` | `0001 (head)`. |
| Final `alembic check` | `No new upgrade operations detected.` |
| `alembic upgrade head --sql` with a nonconnecting placeholder URL | Passed; rendered DDL contains all six business tables. |
| First `python -m querypilot.db.seed --reference-date 2026-10-27` | `created: true`; actual counts above. |
| Identical seed rerun | `created: false`; no duplicate or changed rows. |
| `python -m querypilot.db.verify --reference-date 2026-10-27` | Schema, foreign keys, and accounting all `passed`; counts above. |
| `TEST_DATABASE_URL=... python -m pytest -q` (final PostgreSQL run) | **48 passed**, 1 existing dependency warning, in 4.75s. Includes 14 PostgreSQL cases. |
| `python -m pytest -q` without TEST_DATABASE_URL | **34 passed, 14 skipped**, 1 warning, in 0.41s; no database needed. |
| `pytest -q -m 'not postgres'` | **34 passed, 14 deselected**. |
| `ruff check .` and `ruff format --check .` | Passed; 37 files already formatted. |
| `docker compose config --quiet` with nonsecret validation-only environment values | Passed for the PostgreSQL 16 definition; runtime unverified. |
| Offline `uv lock --check` | Passed; 34 resolved packages and current lockfile. |
| `git diff --check` | Passed. |
| Existing Day 1/2 test/app diffs | Empty; smoke/API/settings tests and FastAPI composition unchanged. |
| Direct TestClient requests with no DATABASE_URL | `/health` and `/api/v1/info` returned expected JSON with HTTP 200. |
| Tracked/pending file and known-key-pattern scan | `.env`/`.venv` excluded; no recognized API/GitHub/private-key patterns found. Targeted review, not an exhaustive secret audit. |

Database commands used an explicit local verification URL on port 55432, not credentials
committed to the project. The native temporary cluster was used because Docker was
unavailable. Schema-isolated integration tests leave the seeded public verification
tables intact and remove their own test schemas.

### Database test and query coverage

The PostgreSQL tests apply actual migrations; compare live metadata to models; downgrade
and re-upgrade a disposable schema; test seed idempotency/conflict refusal; check commit,
rollback, connection return, and safe diagnostics; reject invalid quantities/prices/stock,
status, duplicate email, and FK writes; and deliberately corrupt cross-row amounts to
ensure the verifier detects them. Unit tests cover model types/relationships, generation,
referential/accounting rules, leap-day bounds, lazy engines, and redacted settings.

All five developer SQL examples executed successfully through the restricted reader:
13 monthly buckets, 5 top products, 5 refund categories, 500 customer count rows, and
3 failed-payment method totals. Twelve rolling months span 13 month buckets here because
the first and last are partial. Monthly revenue sums and refund allocations reconcile
to independent fixture totals in tests. Highest-revenue product: Outdoors Product 064,
USD 37,882.39. Refund category totals: Electronics 22,571.93; Home 17,678.83; Office
19,494.82; Outdoors 26,590.28; Sports 11,942.18.

The documented reader-role script was applied with a temporary random password. The
reader SELECT returned 3,000 orders. DELETE, CREATE TABLE, and CREATE TEMP TABLE were
all denied with PostgreSQL insufficient-privilege code `42501` even after disabling
read-only mode. This verifies permissions rather than relying only on a session setting.
No reader password was written into project files or printed.

### Problems, limitations, and next milestone

Initial quality checks caught long lines; formatting and lint corrections passed. Two
early sample-query tests failed: a simplistic splitter included semicolons from comments,
then an assertion incorrectly expected 12 calendar buckets. Both were corrected before
the final passing suite. Alembic's path-separator warning was eliminated by explicit
configuration. The existing FastAPI/Starlette HTTPX deprecation warning remains nonfatal.

Docker image startup and persistence across container restarts remain unverified. Native
PostgreSQL migrations, seeding, verification, role privileges, and all integration tests
were actually exercised. Partial refunds, inventory movements, cross-row database triggers,
and production provisioning are intentionally outside this fixture; cross-row write
invariants must be preserved by future business workflows. See database.md for details.

Day 4, only after a separate request: approved parameterized read-only analytics queries,
validated date/result limits, bounded execution, and tests using the restricted reader.

## Day 4 — secure read-only analytics tools (2026-10-28)

Status: implemented and verified against PostgreSQL with the restricted reader role.
Docker startup remains pending because the daemon is unavailable; this is not a blocker
for the completed PostgreSQL checks. The user has now explicitly approved committing
and pushing Day 4. Focused commit groups are recorded in PLANS.md.

### Implementation and files

- Added `schemas/analytics.py`: strict, extra-forbidden inputs, bounded typed outputs,
  Decimal money and a validated success/error envelope.
- Added `db/analytics.py`: five code-owned SELECT builders, UTC filters, deterministic
  sorting, row/fetch caps, read-only transactions, statement timeouts and a per-call role audit.
- Added `tools/registry.py`: fixed allowlist, schema descriptions, validation, dispatch,
  output validation, safe errors and execution logs independent of any LLM provider.
- Added `tools/__main__.py`: developer-only CLI with JSON results and meaningful exit codes.
- Added `tests/test_tools.py` and `tests/test_tools_postgres.py`: contract, injection-shaped
  rejection, privacy, accounting, bounds, permission and actual timeout tests.
- Extended `db/session.py` to classify PostgreSQL cancellation without exposing driver
  details, and `core/logging.py` to allowlist tool name/status fields.
- Updated `.env.example`, tools package documentation, README, GOALS.md, AGENTS.md,
  PLANS.md, architecture/database guides, and added `docs/tools.md`.
- No new dependencies, migrations, data writes through tools, HTTP routes, LLM integration,
  document search, chatbot, or frontend. Existing Day 1–3 tests and API/schema/migrations
  remain unchanged.

The tools are get_top_products, get_revenue_summary, get_refund_analytics,
get_customer_order_summary, and get_payment_status_summary. Complete schemas, accounting,
date semantics, caps and invocation examples are documented in tools.md.

### Actual commands and results

Git inspection before editing showed clean `main...origin/main`.

| Command/check | Actual result |
| --- | --- |
| Docker info | Failed: Docker daemon socket unavailable; container startup still unverified. |
| Sandboxed PostgreSQL status/readiness | Could not observe the outside-sandbox server. |
| Approved `pg_ctl ... start` | Did not start another server: existing postmaster lock detected. No lock files removed. |
| Approved `pg_isready -h 127.0.0.1 -p 55432` | Existing server accepting connections. |
| Existing independent tests before tool tests | 34 passed. |
| New plus existing independent suite | 74 passed; no PostgreSQL required. |
| Complete suite with TEST_DATABASE_URL and TEST_READER_DATABASE_URL | **106 passed**, 1 existing dependency warning, in 5.22s. Includes all prior 48 tests. |
| Final targeted restricted-reader suite after strengthening read-only observation | **18 passed** in 1.08s. |
| Full pytest without database variables | **74 passed, 32 skipped**, 1 warning, in 0.41s. Integration skips are explicit. |
| `ruff check .` | All checks passed. |
| `ruff format --check .` | 44 files already formatted. |
| Offline `uv lock --check` | Passed; 34 packages, no dependency changes. |
| `git diff --check` | Passed. |
| Top-products CLI against actual seeded PostgreSQL | Exit 0; five validated product rows, truncated=true, JSON tool status/duration log. |
| Other four operations through the real reader registry | All returned success and validated actual rows; examples below. |
| CLI with an empty reader URL and a writer URL present | Exit 1, configuration_error; no writer fallback. |
| Existing health/info/docs/redoc/OpenAPI requests using TestClient with no database | All returned 200. |
| Existing tests, FastAPI composition, models and migration diffs | Empty; preserved unchanged. |
| Tracked/pending file check | No `.env` or `.venv` files; no recognized OpenAI/GitHub/private-key patterns. Targeted scan, not an exhaustive secret audit. |

Full database regression command used the isolated local writer/reader URLs from Day 3:

```sh
# Set both URLs securely in the environment before running:
TEST_DATABASE_URL=... TEST_READER_DATABASE_URL=... .venv/bin/python -m pytest -q
```

Developer CLI executed, with the existing restricted URL supplied via the environment:

```sh
python -m querypilot.tools get_top_products --arguments '{"limit":5}'
```

### Real tool results

The existing Day 3 fixture (reference 2026-10-27, seed 42) was queried without changing
its business rows. Actual outputs included:

- Top products: IDs 64, 35, 21, 76, 63 with USD revenues 37,882.39; 36,509.32;
  35,946.86; 35,386.60; 34,591.86. First product: Outdoors Product 064, 144 units.
- Monthly completed-order revenue: 13 buckets; January 2026 had 209 completed orders
  and USD 160,833.26. The rolling-year fixture spans partial months at its endpoints.
- Refund analytics: five categories; Outdoors USD 26,590.28, Electronics 22,571.93,
  Office 19,494.82, Home 17,678.83, Sports 11,942.18. Counts are category-local,
  not additive across categories.
- Customer summary with limit 2: IDs 156 and 339 each had 13 orders; completed revenues
  USD 4,815.22 and USD 8,107.08. No names, emails, cities or states were selected/returned.
- Payments: 486 failed attempts totaling USD 358,283.06 and 2,520 successful payments
  totaling USD 1,888,399.87. Failed amounts are attempted charges, not revenue.

### Security and accounting verification

Tests use fresh isolated schemas migrated with Alembic and explicitly grant SELECT/USAGE
to the existing restricted reader. Admin/writer credentials supplied to the analytics
repository are rejected. Unknown names, SQL-shaped parameters, extras, invalid IDs,
invalid date windows and oversized limits fail before database access. Outputs reject
unexpected customer personal fields and serialize money without float conversion.

Hand-calculated fixtures cover inclusive/exclusive UTC dates, tie sorting, completed-only
revenue, payment retries without revenue multiplication, category count semantics, refund
date attribution, missing/zero-order customers, failed amounts and empty tables. A long
history test confirms the 400-row revenue cap and explicit truncation.

With read-only mode disabled, direct INSERT, UPDATE, DELETE, DROP, ALTER, CREATE TABLE
and CREATE TEMP TABLE attempts all failed with PostgreSQL insufficient-privilege code
`42501`. A test-only slow SELECT triggered actual server cancellation; the public result
was timeout, the transaction rolled back, the connection returned to the pool, and a
subsequent approved call succeeded. That test also observes transaction_read_only=on
inside the running tool after explicitly turning the connection default off.

### Problems, limits and Day 5 preparation

The first integration run had 9 failures and 96 passes: PostgreSQL needed an explicit
text cast for the bound table name in the privilege audit's format() call. The cast was
added without interpolating caller strings. Initial test logging also reused a closed
pytest capture stream; new tests now isolate/configure their logging streams. Long lines
and import ordering were fixed before final lint/format checks. The existing upstream
FastAPI/Starlette HTTPX deprecation warning remains nonfatal.

Timeouts are per SQL statement, not a whole-agent deadline. Role checks cover the active
schema's six tables and relevant role/database capabilities, not every object in the
cluster. Category counts are not globally additive. Partial-refund item attribution is
still the documented Day 3 simplification. Docker runtime remains unverified. No unresolved
restricted-role or analytics verification blocker remains.

Day 5, after a separate request: bounded document search over synthetic business documents,
source identifiers, retrieval tests, and untrusted-content handling. No Day 5 code has begun.

## Day 5 — document search and citations (2026-10-29)

Status: implemented and verified, including existing PostgreSQL analytics regressions.
No model API, embeddings, agent loop, extra database, new HTTP endpoint or frontend was
added. The user has now explicitly approved committing and pushing Day 5 in focused groups.
Focused review groups are recorded in PLANS.md. Days 1–4 were already pushed at start.

### Files and implementation

- Added ten Markdown policies in `data/documents/`, each with unique ID/title/category,
  actual content and section headings. The fictional company is QueryPilot Demo Store.
- Added `schemas/documents.py` and `services/document_search.py`: typed inputs/results,
  literal metadata parsing, bounded safe ingestion, section chunks and deterministic BM25.
- Added `data/evaluations/document_search.json` and `services/evaluate_search.py`:
  20 relevance questions, actual registry execution, Hit Rate@5 and MRR@5 calculation.
- Added `tests/test_document_search.py`: 35 new cases covering retrieval, provenance,
  bounds, missing/empty/malformed collections, determinism, filesystem safety, independent
  resources, untrusted instructions, safe logs and metric correctness.
- Extended the shared result union and allowlist, registry, CLI, Settings and `.env.example`
  for the sixth tool and trusted `QUERYPILOT_DOCUMENTS_PATH` configuration.
- Updated two Day 4 test modules: the allowlist is now six; SQL configuration is checked
  at execution instead of factory construction; empty-SQL checks still cover all five
  SQL tools separately from the new passage output. SQL query/security code is unchanged.
- Updated package docstrings, README, goals/plans/instructions, architecture/analytics
  guides and added `docs/document_search.md`. No dependency or lockfile changes.

`search_business_documents` accepts a required nonblank query capped at 500 raw characters,
strict top_k=1..10 (default 5), and an optional approved category. No tool argument can
select a filename or directory. Search returns original section text with citations,
score and explicit untrusted-content classification; it does not synthesize an answer.

### Actual collection and evaluation

The actual index contains **10 documents and 40 chunks**. The ten categories cover refunds,
shipping, payments, cancellations, products, support, discounts, fraud, inventory and FAQ.
The policies preserve Day 3 accounting: completed-only revenue, full refunds against
successful payments, historical discounted unit prices, and stock as a snapshot. Shipping,
support and fraud workflows are explicitly fictional examples without invented DB events.

The evaluation uses 20 fixed questions with expected relevant document IDs. Actual output:

```json
{
  "questions": 20,
  "indexed_documents": 10,
  "indexed_chunks": 40,
  "hit_rate_at_5": 1.0,
  "mrr_at_5": 1.0
}
```

All 20 expected document IDs appeared at passage rank 1. This is a small authored
regression set, not a held-out benchmark, general semantic accuracy claim or future-model
injection-resistance measure. The evaluator prints actual per-question ranks/IDs and
checks expected IDs exist. Repeated chunks from one document occupy real rank positions.

### Commands and real results

Git was clean (`main...origin/main`) before edits. No installation was needed because
the existing editable environment and standard library supply all dependencies.

| Command/check | Actual outcome |
| --- | --- |
| Existing independent tests after initial registry integration | 74 passed. |
| First search/evaluation test run | 105 independent cases passed; 20-question metrics both 1.0. |
| Additional raw-query/collection bounds and SQL-isolation tests | Independent suite increased to 109 passing cases. |
| Full suite with TEST_DATABASE_URL and TEST_READER_DATABASE_URL (final) | **141 passed**, 1 existing dependency warning, in 5.26s. Includes 32 real PostgreSQL cases. |
| Full pytest without database variables | **109 passed, 32 skipped**, 1 warning, in 0.52s. |
| `pytest -q -m 'not postgres'` | **109 passed, 32 deselected** in 0.44s. |
| `python -m querypilot.services.evaluate_search` | 10 documents, 40 chunks, 20 questions; Hit Rate@5=1.0, MRR@5=1.0. |
| CLI demonstrations for return window, failed payments and cancellations | All exit 0, actual passages/citations below; no database needed. |
| `ruff check .` | Passed. |
| `ruff format --check .` | Passed; 59 files already formatted. |
| `git diff --check` | Passed. |
| Offline `uv lock --check` | Passed; 34 resolved packages, unchanged dependencies. |
| PostgreSQL readiness (approved outside-sandbox check) | Existing local server accepting connections on port 55432. |
| Docker info | Failed: daemon socket unavailable; container runtime remains unverified. |
| API TestClient checks without DATABASE_URL | Health, info, docs, redoc and OpenAPI all returned 200. |
| API composition/routes, SQL builders/audit, models/migrations and dependency diffs | Empty; retained unchanged. |
| Tracked/pending files and recognized-secret-pattern review | No `.env`/`.venv` files or recognized API/GitHub/private-key patterns found. Targeted review, not an exhaustive secret audit. |

Final PostgreSQL regression command used the existing isolated local database and reader:

```sh
# Configure both URLs securely in the environment first:
TEST_DATABASE_URL=... TEST_READER_DATABASE_URL=... .venv/bin/python -m pytest -q
```

No existing business rows were changed by search. PostgreSQL tests continued to use their
isolated temporary schemas and verify all five SQL operations and privilege/timeout rules.

### Actual demonstrations

Commands were run through the existing developer CLI:

```sh
python -m querypilot.tools search_business_documents --arguments '{"query":"What is the return window for products?","top_k":3}'
python -m querypilot.tools search_business_documents --arguments '{"query":"How are failed payments handled?","top_k":1}'
python -m querypilot.tools search_business_documents --arguments '{"query":"When can customers cancel an order?","top_k":1}'
```

The top returned passages/citations were:

- `QP-RET-001#s002-c001`, Product return window: customers may request a return within
  30 calendar days of delivery; unused products must be complete and in original packaging.
- `QP-PAY-003#s002-c001`, Failed payments and retries: failed attempts collect no money,
  remain excluded from revenue, and retries do not duplicate orders or line revenue.
- `QP-CAN-004#s002-c001`, When customers can cancel: pending orders without successful
  payment may be considered for cancellation; search itself cannot cancel orders.

These are quotations/paraphrases of indexed policy sections, not generated AI answers.

### Security, limitations and problems encountered

Descriptor-relative no-follow loading rejects leaf symlinks and a symlink root; regular-file,
hard-link, size, UTF-8 and collection checks bound ingestion. Tests cover unsupported files,
path-shaped arguments, duplicate IDs, missing/empty collections, long sections, deterministic
ties, valid citations, category filters, irrelevant queries, result/query caps, and malformed
inputs rejected before I/O. A mocked forbidden database initializer proves search never
creates a database; a missing document collection does not disable SQL dispatch.

Command-like injected text was retrieved only as untrusted content; no sentinel file was
created. Execution logs excluded both query text and document content. No claim is made
that a future LLM cannot follow malicious text; Day 6 must preserve the data boundary.

Initial Ruff checks caught a long stopword line and a long test fixture string; both were
corrected before the final passing checks. No pytest failures occurred during Day 5.
The existing FastAPI/Starlette HTTPX deprecation warning remains nonfatal.

The safe loader requires POSIX descriptor-relative/no-follow support. Root configuration
and ancestor directories are trusted operator infrastructure. Corpus files are not bundled
into the wheel; deployments must supply them. Indexes are per-registry snapshots, with
citations tied to their section ordinals; recreate a registry after edits. Retrieval is
lexical English BM25, without stemming/synonyms or semantic guarantees. Duplicate passages
from a document may share the top results. Docker runtime is still unavailable, but the
actual PostgreSQL regression suite passed. No unresolved Day 5 verification blocker remains.

Day 6, after a separate request: OpenAI function calling using the existing provider-neutral
schemas/registry, mocked protocol tests, and strict treatment of passages as untrusted
evidence. No OpenAI SDK/API calls or agent loops were implemented on Day 5.

## Day 6 — OpenAI function calling, single round (2026-10-30)

Implementation and mock/protocol verification are complete. **Actual live OpenAI
verification is pending**: OPENAI_API_KEY and OPENAI_MODEL were both unconfigured, and
no paid live usage was authorized or performed. No live-operational claim is made.
The user has now approved committing and pushing Day 6 in five meaningful groups:
provider/configuration, contracts/evidence, orchestration/CLI, tests, and documentation.

### Files and scope

- Added `agent/provider.py`: official AsyncOpenAI Responses adapter, required environment
  key/model, bounded SDK retries/deadline and safe auth/rate/network/response errors.
- Added `agent/tool_schemas.py`: strict schemas derived from all six registry definitions;
  nullable optional properties and normalization back to existing Pydantic defaults.
- Added `agent/orchestrator.py`: one selection, one bounded sequential batch, at most one
  answer request with tools disabled; preserved call IDs and full stateless output replay.
- Added `agent/evidence.py`: complete-record row/UTF-8 budgets, reference/source checks,
  conservative supported-number checks and no-evidence handling.
- Added `agent/mock.py`, `agent/cli.py` and extended the tools CLI with `ask --mock/--live`.
  Mock selection/templates execute actual tools and do not fake database metrics.
- Added `schemas/llm.py`: bounded public outcomes, trace IDs, tool status/results, citations
  and safe errors; no private prompts/provider dumps/reasoning are returned.
- Added `tests/test_llm.py` and `tests/test_openai_provider.py` (46 new cases).
- Updated settings/environment template, safe logging fields, agent package docstring,
  pyproject/lockfile, README, architecture, goals/plans/instructions and added docs/llm.md.
- The only new direct dependency is official `openai>=2,<3`, resolved to **2.54.0**.
  No frameworks, new database technology, HTTP routes, frontend or deployment were added.
  Existing registry, SQL operations/privilege audit, document search, models/migrations
  and prior test files remain unchanged.

### Actual commands and results

Initial Git state was clean `main...origin/main`. Python 3.12.15 was used after restoring
the damaged temporary runtime described below.

| Command/check | Actual result |
| --- | --- |
| Initial offline uv sync | Failed: temporary Python standard library missing (`encodings`). |
| Offline Python reinstall | Failed: required runtime archive no longer cached. |
| Approved online Python reinstall | Restored Python 3.12.15. |
| First SDK installation using the old cache | Failed: an incomplete packaging wheel cache entry had no WHEEL file. |
| Approved uv sync using a fresh temporary cache | Passed; 39 packages resolved; official SDK 2.54.0 plus required transitive dependencies installed. |
| First full PostgreSQL run against the old temporary cluster | 154 tests passed, 32 setup errors: missing `global/pg_filenode.map`. Not an application assertion failure. |
| Fresh isolated PostgreSQL bootstrap using existing migration/seed scripts | Passed on loopback port 55436; six business tables and standard fixture counts restored in a separate verification database. |
| Existing reader-role script with a temporary random password | Passed; password not printed or stored in project files. |
| Final full pytest with both PostgreSQL test URLs | **187 passed**, 1 existing dependency warning, in 5.84s. Includes all 32 prior PostgreSQL cases. |
| Final pytest without database variables | **155 passed, 32 skipped**, 1 warning, in 1.04s. |
| `pytest -q -m 'not postgres'` | **155 passed, 32 deselected** in 1.08s. |
| `pytest -q tests/test_llm.py tests/test_openai_provider.py` | **46 passed** in 0.76s. All external model traffic mocked. |
| `ruff check .` / `ruff format --check .` | Passed; 69 files already formatted. |
| `git diff --check` | Passed. |
| Offline `uv lock --check` with fresh cache | Passed; 39 packages, current lockfile. |
| Function-schema inspection | Exactly six strict schemas, generated from the existing registry. |
| Safe configuration-presence check | api_key_configured=false, model_configured=false; values never printed. |
| Mock ask CLI, document question without any key/model | Completed with actual policy excerpt, E1 and original source citation. |
| Three mock-provider question demos with actual registry tools | All completed with mechanically checked evidence; actual outputs below. |
| Existing document evaluation | 20 questions, 10 documents/40 chunks, Hit Rate@5=1.0 and MRR@5=1.0 unchanged. |
| API TestClient checks with no external services | Health, info, Swagger, ReDoc and OpenAPI returned 200. |
| Existing API/SQL/audit/registry/retrieval/migration code diffs | Empty; those implementations retained unchanged. |
| Tracked/pending file review | No .env/.venv files or recognized OpenAI/GitHub/private-key patterns. Targeted review, not an exhaustive secret audit. |

Final full regression command used the fresh verification instance, not a live model:

```sh
TEST_DATABASE_URL=postgresql+psycopg://querypilot_admin@127.0.0.1:55436/querypilot_day6_verify TEST_READER_DATABASE_URL=postgresql+psycopg://querypilot_reader@127.0.0.1:55436/querypilot_day6_verify .venv/bin/python -m pytest -q --tb=short
```

### Mocked SDK/protocol and grounding coverage

The actual SDK was exercised with httpx.MockTransport: request shape, model setting,
store=false, encrypted-reasoning inclusion, tool_choice=none on follow-up, safe 401/429/500
handling, network/timeout mapping, one-retry success/exhaustion, logical deadlines and
incomplete responses. An end-to-end SDK-to-service-to-registry test verified six schemas,
the exact call ID, actual Pydantic execution and tool-output replay without network access.

Orchestration tests cover multiple calls and reasoning replay, JSON errors/nonfinite
numbers/duplicate keys, unknown tools, Pydantic limits, malformed/duplicate IDs, excessive
batches rejected before execution, no-tool replies, empty versus failed tools, forbidden
second tool rounds, source preservation, unsupported numeric literals, invalid/orphan
citations, capped evidence and post-timeout skipping. They also verify actual local document
retrieval, safe logs and explicit live-configuration failure without mock substitution.

These are deterministic contract/mechanical-grounding tests, not semantic answer guarantees.
Citation membership and numeric checks cannot establish full factual entailment. The
service deliberately refuses new arithmetic in Day 6. See docs/llm.md for exact limits.

### Actual mock-mode demonstrations

These used the fake provider with **real** seeded SQL/document registry operations, not
OpenAI. Every outcome identified mode=mock and grounding_checks=passed:

1. “What are the five highest-revenue products?” selected get_top_products and returned
   Outdoors Product 064 USD 37,882.39; Office Product 035 USD 36,509.32; Electronics
   Product 021 USD 35,946.86; Electronics Product 076 USD 35,386.60; Sports Product 063
   USD 34,591.86, each referencing [E1].
2. “What is the return policy?” selected search_business_documents, quoted the 30-calendar-day
   return window and restrictions, and preserved [E1] plus [QP-RET-001#s002-c001].
3. “How many failed payments occurred?” selected get_payment_status_summary and answered
   “486 failed payment attempts [E1].”

The existing tools CLI was extended, not replaced:

```sh
python -m querypilot.tools ask "What is the return policy?" --mock
```

No live API answer, live tool selection result, paid request, or real-world accuracy
metric was produced. Live checks for all three questions remain explicitly pending.

### Environment repairs and remaining limitations

Temporary Python/cache files and the old PostgreSQL cluster had lost files during
environment cleanup. The Python runtime was restored and a new cache was used. The old
PostgreSQL cluster/directory was not deleted or modified; a separate temporary cluster
was initialized, migrated and seeded using existing code. The new fixture again contains
500 customers, 100 products, 3,000 orders, 6,000 items, 3,006 payments and 120 refunds.
No database repair or deployment infrastructure was added to the application.

Ruff caught two long strings and import ordering; corrections passed final checks. No
Day 6 application assertion failures occurred. The existing FastAPI/Starlette HTTPX
deprecation warning remains nonfatal. Normal README setup uses a regular Python 3.12
installation, not the test environment's temporary runtime/cache locations.

Live OpenAI verification is the unresolved integration check. Answer checks are conservative
and incomplete; wrong relationships or number words can still mislead despite valid IDs.
Tool await cancellation does not kill worker threads, and server-side SQL deadlines remain
important. There is no autonomous retry/planning loop beyond the bounded SDK transport
retry policy and no additional tool round after synthesis.

Day 7, after a separate request: bounded multi-step orchestration with explicit iteration,
tool and overall budgets while preserving protocol, privileges, citations and safe logging.
At the close of Day 6, no Day 7 implementation had begun. Explicit approval for the focused Day 6 commits/push
was received in the follow-up request; live API usage remains separately unapproved.

## Day 7 — Bounded multi-step orchestration (2026-11-02)

Implementation and mock/protocol verification are complete. The initial working tree was
clean on main, synchronized with origin/main. Days 1–6 were already committed/pushed.
The Day 7 attachment initially required approval before committing/pushing. The user
has now explicitly approved five focused commits and a push to the existing repository. No paid OpenAI requests, new HTTP routes, UI, persistent
memory, deployment infrastructure, dependencies or schema migrations were added.

### Files and architecture

Created:

- `src/querypilot/agent/multistep.py`: generic bounded loop reusing the Day 6 registry
  execution and provider boundary, full stateless replay, recovery and budget checks.
- `src/querypilot/agent/state.py`: request-local UUID/question/messages, iteration,
  call IDs/fingerprints, evidence/citations, safe errors, status and monotonic elapsed time.
- `src/querypilot/cli.py`: public `python -m querypilot.cli ask` entry point.
- `tests/test_multistep.py`: 60 deterministic cases covering loop behavior, limits,
  state isolation, protocol, recovery, CLI, logging and evidence/citation security.
- `docs/agent.md`: current CLI, limits, state, error handling and known limitations.

Modified:

- `core/config.py`, `.env.example`: five validated agent settings and documented defaults.
- `schemas/llm.py`: up to 20 traces/E IDs, per-tool iteration, run iterations/elapsed_ms.
- `agent/cli.py`: MultiStepService, optional verbose evidence and five limit overrides.
- `agent/mock.py`: explicit deterministic multi-round fixture using actual registry
  results; revenue templates now show forwarded buckets and acknowledge truncation.
- `agent/evidence.py`: additionally reject invented short bracketed document references.
- `agent/__init__.py`: current capability description.
- `tests/test_openai_provider.py`: actual SDK, in-memory HTTP transport, three-request
  replay test with original IDs, complete prior output and encrypted reasoning.
- README, AGENTS, GOALS, PLANS, architecture, LLM guide and this progress log: current
  scope, approval boundary, Mermaid sequence, setup, actual results and remaining checks.

The Day 6 SingleRoundService remains unchanged and regression-tested. Current ask CLIs
use MultiStepService, while direct tool CLI commands retain their behavior. SQL builders,
restricted-role audit, registry dispatch, models, migrations, document retrieval and API
implementations remain unchanged. Existing dependencies were sufficient; the installed
editable environment and Python 3.12.15 worked without reinstalling anything.

Each model response is one iteration, including the final answer. Calls within a batch
execute sequentially; later batches can depend on earlier results. Every iteration uses
all six schemas and full call_id-matched output/reasoning replay. State is created inside
run() rather than retained on the service. Errors can be fed back for correction or a
different tool; canonical duplicate calls return repeated_call without new I/O and still
count against the call cap. Live dispatch has no keyword-based planning; only the explicit
offline mock fixture has deterministic selection/templates.

### Actual verification

All external model traffic in these tests used scripted providers or httpx.MockTransport.
The existing native PostgreSQL fixture on loopback port 55436 was used, with the existing
restricted reader. Database tests use isolated schemas as before; no cluster was recreated
or seeded during Day 7. Initial sandbox pg_isready returned no response; the approved
outside-sandbox check confirmed the server was accepting connections.

| Command/check | Actual result |
| --- | --- |
| `.venv/bin/python --version` | Python 3.12.15. |
| Initial existing pytest suite before new tests | 155 passed, 32 skipped; compatibility retained. |
| First 50 new loop tests | 50 passed. |
| Intermediate full suite with PostgreSQL | 237 passed; later additions increased coverage. |
| Final full suite with both PostgreSQL test URLs | **248 passed**, 1 existing dependency warning, in 6.53s. Includes all 32 PostgreSQL cases. |
| Final full suite without database test settings | **216 passed, 32 skipped**, 1 warning, in 1.90s. |
| `pytest -q tests/test_multistep.py tests/test_llm.py tests/test_openai_provider.py --tb=short` | **107 passed** in 1.61s. |
| `ruff check .` | Passed. |
| `ruff format --check .` | Passed; 74 files already formatted. |
| `git diff --check` | Passed before final progress update; checked again after documentation. |
| Four mock-provider scenarios with actual reader SQL/document registry | All completed with original source citations and grounding_checks=passed (mechanical checks only). |
| Public CLI document command with --mock --verbose | Exit 0, actual excerpt, bounded typed evidence and original citation. |
| Existing tools ask command in --mock mode | Exit 0, document answer and concise traces. |
| Search evaluation | 20 questions, 10 documents/40 chunks; Hit Rate@5=1.0, MRR@5=1.0 unchanged. Authored regression set, not general accuracy. |
| Safe OpenAI settings-presence check | api_key_configured=false, model_configured=false; no values printed. |
| Live OpenAI requests | Not run: credentials/model unconfigured and paid live usage not approved. |
| Dependency installation / lock regeneration | Not needed; dependencies and lockfile unchanged. |
| Docker startup | Not attempted; outside Day 7 scope, no new container verification claim. |

The final database regression command was:

```sh
TEST_DATABASE_URL=postgresql+psycopg://querypilot_admin@127.0.0.1:55436/querypilot_day6_verify TEST_READER_DATABASE_URL=postgresql+psycopg://querypilot_reader@127.0.0.1:55436/querypilot_day6_verify .venv/bin/python -m pytest -q --tb=short
```

The full suite includes existing FastAPI endpoint/error/CORS tests, all five SQL operations,
actual reader write denial and statement cancellation/recovery, document search/filesystem
regressions and retained Day 6 protocol tests. New tests cover both SQL→document and
document→SQL order, multiple calls in a round, repeated calls/default normalization,
invalid arguments/JSON/unknown names, failures and recovery, empty results, provider
failure preservation, duplicate call IDs across rounds, E10 handling, concurrent request
isolation, context growth/UTF-8 size, payload and accumulated error-packet budgets,
iteration/total/per-round call limits, tool/model/overall timeouts, config upper bounds,
safe logs, CLI options and invented document references.

Initial Ruff checks caught long lines/import ordering; formatting and string wrapping
resolved them before final checks. No pytest assertion failures occurred. The existing
FastAPI/Starlette HTTPX deprecation warning remains nonfatal; no dependency migration was
introduced to suppress it.

### Actual mock A–D scenarios

All four questions were run through the current ask service in mock mode with the real
registry, existing synthetic PostgreSQL data and local documents. Optional date arguments
were null (all available fixture history); the configured reader performed the SQL.

| Scenario | Executed operations and arguments, in order | Iterations / actual answer evidence |
| --- | --- | --- |
| A: top five products by revenue | `get_top_products(limit=5)` | 2; E1, five actual product revenues. |
| B: return policy | `search_business_documents(query="product return window", top_k=1)` | 2; E1, `QP-RET-001#s002-c001`. |
| C: top products and refund policy | `get_top_products(limit=5)` → the same return-window search | 3; E1 product rows, E2 and original return source. |
| D: revenue trend and failed-payment handling | `get_revenue_summary(group_by="month")` → `search_business_documents(query="failed payments and retries", top_k=1)` | 3; E1 monthly rows, E2 and `QP-PAY-003#s002-c001`. |

A/C returned Outdoors Product 064 USD 37,882.39; Office Product 035 USD 36,509.32;
Electronics Product 021 USD 35,946.86; Electronics Product 076 USD 35,386.60; Sports Product
063 USD 34,591.86. The repository marks that more products exist; these are the selected
top five, not whole-catalog totals.

B/C quoted the actual 30-calendar-day return passage, unused/original-packaging conditions
and the limitation that delivery events are absent from the database. The fixture selects
one relevant policy passage; this is not a full summary of every refund-policy section.
D displayed ten monthly buckets, beginning 2025-10 USD 25,302.17 and ending 2026-07
USD 142,766.77. The row cap omitted later buckets; both the trace and answer explicitly
marked the displayed series incomplete. The payment passage states that failed attempts
collect no money, stay out of revenue, and retries do not duplicate orders or line revenue.
All figures and excerpts came from forwarded actual tool results, not an OpenAI response.

### Safety limits and remaining work

Defaults: 5 model requests, 10 total call attempts, 5 calls per round, 90-second execution
await budget, 128000-byte serialized context, 12000-byte per-tool evidence cap and
48000-byte accumulated evidence cap. Hard upper bounds and smaller limits are validated
and tested. Evidence reserves are divided across the configured total-call cap, removing
whole records to fit. Invalid/oversized batches fail before executing any member. Tool
deadlines stop further work; limit errors preserve prior bounded evidence without an
invented partial answer. Prompts/history/private reasoning are absent from public traces.

No unresolved Day 7 implementation blocker remains. Live API acceptance/behavior is still
unverified. Grounding validation checks membership and numeric literals, not semantic
entailment; false relationships or number words may still pass. Retrieved content remains
untrusted, without a claim of complete prompt-injection resistance. Thread cancellation
cannot forcibly stop synchronous tools, so process shutdown may exceed the await deadline.
Context limits count serialized bytes, not provider tokens or entire process memory.
Duplicate suppression also prevents identical transient-failure retries within one run.

Approved focused commit groups: limits/state/contracts; loop/evidence checks;
CLI/mock; tests; documentation. Day 8 preview is Advanced Guardrails and Reliability,
including broader adversarial and failure-path evaluation. At the close of Day 7,
Day 8 had not been started.

## Day 8 — Advanced security guardrails and reliability (2026-11-04)

Implementation and deterministic verification are complete. Git was clean on main,
synchronized with origin/main at a985adb, before changes. Day 8 explicitly requires
approval before committing/pushing. The user has now explicitly approved focused
commits and a push to the existing repository. No frontend,
deployment infrastructure, persistent memory, new business tool or HTTP route was added.
Actual OpenAI verification remains pending: key/model were unconfigured and no paid
API usage was authorized or performed. No formal security audit or penetration test
was performed.

### Gap analysis and implementation

Existing protections were preserved: six fixed operations, strict Pydantic schemas,
predefined SQLAlchemy queries, separately configured restricted reader credentials,
per-call privilege audits, read-only transactions, native DB deadlines, bounded local
ingestion, request-local agent state, call/iteration/time/byte caps and citation checks.

The review found gaps in application-controlled paths:

- Credentials could appear in otherwise-valid product/passage text, a provider diagnostic
  or a verbose trace. SecretStr settings alone did not protect those data paths.
- Thread await cancellation could abandon a still-running tool and let CLI cleanup race it.
- Context had byte caps without an independent message-count cap; raw question length
  was not checked before whitespace normalization.
- Citation syntax did not enforce document-ID correspondence/uniqueness, and repeated
  row/passage identities could carry conflicting values across rounds.
- Limited evidence could produce a completed answer without an application-generated
  notice; tool telemetry lacked request correlation and terminal error/limit categories.

Day 8 closes these specific gaps without rewriting queries/retrieval or adding a framework.
SecretGuard screens configured API keys, writer/reader URLs and password encodings,
common credential patterns and sensitive keys. Credential-bearing questions/provider
arguments are rejected before dispatch; tool results are withheld before evidence/replay.
ProviderError uses canonical known/unknown diagnostics, and JSON logs have redaction as
a backup. Non-assistant provider output roles are rejected; malicious document text
remains function-output data and cannot add tool capabilities.

Owned workers are shielded and drained before cancellation propagation or resource cleanup.
Subsequent calls stop after a deadline. The raw question cap and message-count budget
are enforced early; expected result slots are reserved before tool I/O. Provenance and
scoped conflict checks stop inconsistent synthesis. Outcomes expose partial, limitations
and pending_tool_calls, with deterministic limitation notices. Agent tool and terminal
events share generated trace IDs and safe operational fields.

### Files created and modified

Created:

- `core/security.py`: credential/pattern screening and recursive sensitive-field redaction.
- `agent/execution.py`: retained/shielded worker tasks and cancellation drain semantics.
- `tests/test_guardrails.py`: **53** new deterministic adversarial/reliability cases.
- `docs/security.md`: threat model, boundaries, failure categories and verification limits.

Modified:

- `agent/provider.py`: canonical diagnostics and unexpected SDK failure handling.
- `agent/orchestrator.py`: shared credential/role/text checks, decoded argument screening,
  and owned execution helper; preserves the retained Day 6 single-round lifecycle.
- `agent/multistep.py`, `agent/state.py`: message reservation, partial/pending metadata,
  conflict handling, generated notices, cancellation terminal logging and tool correlation.
- `agent/evidence.py`: scoped record/passage conflict detection and limitation categories.
- `agent/cli.py`: message-limit override, screened output, safe interruption and independent
  provider/registry cleanup without raw exception output.
- `core/config.py`, `.env.example`: AGENT_MAX_MESSAGES=128, validated range 2–256.
- `core/logging.py`: credential-aware formatter, iteration/error/limit/pending fields.
- `schemas/analytics.py`, `schemas/documents.py`, `schemas/llm.py`: sensitive_output tool
  errors, citation/document consistency and uniqueness, raw question cap and outcome fields.
- `tools/registry.py`: screen validated output for direct and agent users.
- `main.py`, `tools/__main__.py`: inject the active Settings into logging redaction.
- README, AGENTS, GOALS, PLANS, agent/architecture/LLM guides and this progress log.

No project dependency or lockfile changes were needed. Database builders, reader audit,
models/migrations, BM25 retrieval and existing test modules remain unchanged. Existing
API routes retain their behavior. The only new standalone utility was pip-audit in a
temporary tool environment for the requested advisory check, not a project dependency.

### Actual commands and results

| Check | Actual result |
| --- | --- |
| Initial `.venv/bin/python --version` | Reported 3.12.15; subsequent startup revealed missing standard-library encodings. |
| Initial `python -m pytest` | Could not start: temporary Python standard library missing encodings. |
| First runtime restoration command | Failed: previous temporary uv bootstrap binary was also missing. |
| Approved temporary uv bootstrap install and Python reinstall | Passed; restored Python 3.12.15 without changing project dependencies. |
| Existing independent suite after repair | 216 passed, 32 PostgreSQL cases explicitly skipped. |
| Old PostgreSQL readiness/cluster inspection | No server; temporary cluster lacked PG_VERSION/config/global metadata. |
| Separate Day 8 cluster, migration, seed and reader setup | Passed on loopback port 55438; original synthetic fixture counts restored using existing scripts. Old directory left untouched. |
| Intermediate full suite | 297 passed before final coverage additions. |
| Final full pytest with writer/reader test URLs | **301 passed**, 1 existing dependency warning, in 6.67s; all 32 PostgreSQL cases executed. |
| Final pytest without database test settings | **269 passed, 32 skipped**, 1 warning, in 2.22s. |
| Agent/provider/adversarial subset | **160 passed** in 1.91s. |
| New adversarial module | **53 passed** in 0.50s. |
| `ruff check .` | Passed. |
| `ruff format --check .` | Passed; 78 files already formatted. |
| Four real mock CLI A–D demonstrations | All exit 0, mode=mock, status=completed, grounding_checks=passed; explicit limited-record notices where applicable. |
| Document-search evaluation | 20 questions, 10 documents/40 chunks; Hit Rate@5=1.0, MRR@5=1.0 unchanged. |
| pip-audit against installed project environment | Exit 0; **36 third-party packages checked, zero known advisories**. Editable querypilot-ai explicitly skipped. |
| Safe key/model presence check | api_key_configured=false, model_configured=false; values never printed. |
| Live OpenAI requests | Not run; unconfigured and separately unapproved. |
| Docker/deployment/frontend checks | Not run; no new work in those milestones. |
| Dependency, DB builder/migration and BM25 implementation diffs | Empty. |

The existing FastAPI/Starlette HTTPX deprecation warning remains nonfatal. Initial Ruff
checks caught long lines, an import and Python 3.12 generic syntax. The first new partial
batch test accidentally used identical calls, which correctly hit duplicate suppression;
distinct arguments fixed that fixture. A later document-conflict test needed a missing
ToolResult import. These two test-development failures were corrected before final runs;
no failed assertion remains. Failed patch applications were atomic and left no partial edits.

Final full regression command:

```sh
TEST_DATABASE_URL=postgresql+psycopg://querypilot_admin@127.0.0.1:55438/querypilot_day8_verify TEST_READER_DATABASE_URL=postgresql+psycopg://querypilot_reader@127.0.0.1:55438/querypilot_day8_verify .venv/bin/python -m pytest -q --tb=short
```

Focused regression command:

```sh
.venv/bin/python -m pytest -q tests/test_guardrails.py tests/test_multistep.py tests/test_llm.py tests/test_openai_provider.py --tb=short
```

The dependency check ran pip-audit through temporary uv tooling with
`--path .venv/lib/python3.12/site-packages --skip-editable --format json`, writing a
temporary report outside the repository. It checked installed versions, not a formal
application/OS/database audit, package provenance or every possible unknown vulnerability.
No dependency remediation was needed based on that result.

### Adversarial and reliability evidence

Tests demonstrate that malicious retrieved text and fake system/developer instructions
remain data, unauthorized names cannot reach the SQL repository, and arbitrary SQL-shaped,
oversized, nonfinite, duplicate-key or out-of-bound arguments fail safely. Legitimate
quoted suspicious text remains answerable with the actual citation. Known credentials,
password encodings, authorization patterns, provider diagnostics and sensitive config
keys are withheld/redacted in model replay, direct results, logs and verbose CLI output.
Exact copies of long trusted prompt lines are withheld as a supplemental measure.

Event-driven tests cancel a running tool, cancel it again during drain, and verify that
the worker finishes before cancellation propagates. The end-to-end ask cancellation test
proves provider/registry cleanup waits for that worker and later batch calls do not run.
Provider cancellation propagates and emits safe terminal telemetry. Tests also cover
cleanup exceptions, pending partial batches, message caps before I/O, raw padded-question
limits, SQL/passage conflicts, citation provenance and truncation notices.

Existing tests continue to cover actual DB write denial, read-only enforcement, timeout
cancellation/recovery, all SQL tools, BM25 filesystem/relevance regressions, FastAPI routes,
SDK authentication/rate/retry/timeout handling, exact call-ID/reasoning replay, call/iteration/
byte limits, duplicate suppression and concurrent request state isolation. All external
model traffic remains mocked; no paid request is in the default suite.

### Actual mock CLI behavior

All four commands used `python -m querypilot.cli ask QUESTION --mock --verbose
--max-messages 128`, the real synthetic reader on port 55438 and the local documents:

- A selected get_top_products(limit=5), took two iterations, and returned the same five
  revenues beginning Outdoors Product 064 USD 37,882.39. partial=true and
  truncated_evidence identify that more catalog rows exist; the selected top five remain valid.
- B selected search_business_documents(query="product return window", top_k=1), took two
  iterations and retained QP-RET-001#s002-c001 with the actual 30-day passage. partial=false
  means no mechanically detected limitation, not proof of complete policy coverage.
- C executed those SQL/document operations in two separate rounds, then combined actual
  product rows and E2 policy evidence in iteration three, with the limited-record notice.
- D executed get_revenue_summary(group_by="month") then a failed-payment document search,
  followed by synthesis. It retained QP-PAY-003#s002-c001 and showed ten actual monthly
  buckets with both partial/truncated metadata and an explicit incomplete-series notice.

These demonstrate real tool wiring and deterministic safeguards, not live model selection
or a factual accuracy benchmark. The search evaluation remains an authored regression set.

### Remaining limitations and next milestone

No Day 8 implementation blocker remains. Live OpenAI acceptance and behavior are pending.
Credential screening can miss unknown/transformed formats and can reject benign text,
especially when short configured passwords overlap data. It is not comprehensive data-loss
prevention or personal-data anonymization. Application-controlled logs are protected;
external raw SDK/HTTP/SQL debug logging is outside this formatter.

Prompt-injection risk is reduced, not eliminated: malicious content may influence approved
tool choices or produce misleading prose. Exact prompt-copy detection is incomplete.
Citation/numeric membership and structural conflicts do not establish semantic entailment,
resolve different-policy contradictions or provide a consistent DB snapshot across rounds.
Selected/truncated data cannot establish all-data totals. A completed loop with partial
metadata must not be presented as a fully answered request.

Worker draining avoids abandonment and cleanup races, but cannot terminate a hung thread;
cleanup can exceed the execution deadline. Existing bounded tools/native DB deadlines are
required. Arbitrary hung extensions and forceful process termination are not gracefully
isolated. There is no user/tenant authorization boundary yet and no chat HTTP endpoint.

Prepare focused commits for credential/trust safety, worker reliability, budgets/evidence/
telemetry, tests and documentation. Commit/push approval has now been received;
use six groups: credential safety, contracts, execution, CLI, tests and documentation. Day 9, after a new request, adds the
Streamlit interface using these safe outcomes and limitation indicators. Day 9 has not begun.
