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
Streamlit interface using these safe outcomes and limitation indicators. At the close of
Day 8, Day 9 had not begun.

## Day 9 — Interactive Streamlit frontend (2026-11-05)

Implementation and mock verification are complete. Git was clean on main at 3646fde,
synchronized with origin/main. The Day 9 attachment initially required approval before
committing/pushing. The user has now confirmed the UI works locally and explicitly
approved focused commits and a push to the existing repository. No paid OpenAI requests, persistent agent memory,
public hosting, authentication platform or Day 10–14 infrastructure was introduced.
Live OpenAI integration remains unverified.

### Architecture and scope

The UI uses a thin typed HTTP client to call FastAPI. POST /api/v1/agent/ask accepts only
an independent question and mock/live mode. GET /api/v1/agent/capabilities returns safe
availability flags and limits without executing a provider or tool. The lifecycle
previously in the CLI was moved into services/agent.py; HTTP and CLI now share resource
creation, MultiStepService execution and cleanup. Existing CLI factory seams were retained
so prior cancellation/security tests still exercise the same behavior.

Public responses reuse ExecutionOutcome while projecting safe tool summaries/evidence.
Raw arguments, provider call IDs, internal messages/prompts and reasoning are excluded.
Request IDs match HTTP headers; the independent agent trace ID remains available.
Body bytes are bounded before JSON parsing, and request schemas forbid client tools,
SQL, memory and execution-limit overrides. All original server-side limits, credential
checks, fixed queries and read-only privileges remain in effect. Live HTTP execution
requires a separate backend opt-in; startup/mode/capability reads never invoke it.

Streamlit keeps only display history (maximum 20 exchanges) in each UI session. A pending
request disables submission controls, and reruns render stored results without resending.
Examples fill the composer instead of executing. The interface renders actual tool order,
iteration/status/timing, SQL rows, original passages/citations and limitation/error notices.
Untrusted narrative renders as plain text, not executable HTML or Markdown images. The
backend capability timeout plus a 15-second margin configures the HTTP client; redirects,
inherited proxy credentials and automatic retries are disabled.

### Files created and modified

Created:

- `api/routes/agent.py`: safe local ask/capabilities endpoints and live-mode gate.
- `schemas/agent.py`: request, capability and public response/trace contracts, including
  coherent citations/results and UUID identifiers.
- `services/agent.py`: shared CLI/API request lifecycle and cleanup.
- `frontend/__init__.py`, `frontend/app.py`: dedicated presentation package and chat UI.
- `frontend/api_client.py`, `frontend/config.py`, `frontend/messages.py`: bounded typed
  HTTP transport, frontend-only environment configuration and fixed safe diagnostics.
- `frontend/components.py`: answer/execution/evidence rendering with explicit limitations.
- `.streamlit/config.toml`: built-in light theme, loopback defaults and disabled usage stats.
- `tests/conftest.py`: public response fixture using real mock document execution.
- `tests/test_agent_api.py`, `tests/test_frontend_client.py`, `tests/test_frontend_app.py`:
  20 backend, 16 client and 15 Streamlit cases respectively (**51 new cases**).
- `docs/frontend.md`: exact startup, contracts, modes, session behavior and troubleshooting.

Modified:

- `agent/cli.py`: delegates lifecycle to the shared service; keeps existing commands/modes.
- `api/router.py`, `api/middleware.py`, `main.py`: mount routes, cap streamed agent bodies
  at 65536 bytes before parsing and advertise GET/POST for explicit CORS origins.
- `core/config.py`, `.env.example`: disabled-by-default agent_live_enabled and UI API origin.
- `pyproject.toml`, `uv.lock`: Streamlit runtime dependency; HTTPX promoted from dev-only
  to runtime for the UI client. No second HTTP library or new agent framework.
- `tests/test_api.py`: OpenAPI path inventory now includes the two intentional new routes.
- README, AGENTS, GOALS, PLANS, architecture/agent/security guides and this progress log.

The sole new direct library is `streamlit>=1.49,<2`, resolved to **1.67.0**. HTTPX remains
0.28.1. uv resolved **62 packages**, installing 23 third-party additions transitively with
Streamlit and rebuilding the editable project. Dependency purposes and startup commands
are documented. SQL builders, models/migrations, registry/guardrail/retrieval code and
the existing agent/provider implementation remain unchanged; CLI lifecycle logic moved
without duplicating orchestration in the frontend.

### Actual verification results

The existing Python 3.12.15 environment and PostgreSQL fixture on port 55438 were usable;
no runtime or database repair was needed. Dependencies were synchronized using temporary
uv tooling and a fresh temporary cache. No real key was read into frontend settings.

| Command/check | Actual result |
| --- | --- |
| `uv sync --python 3.12 --extra dev` with the temporary cache | Passed; 62 packages resolved; Streamlit 1.67.0 installed. |
| First full independent regression run | One expected failure: the old OpenAPI test asserted only the two Day 2 paths. Its inventory was updated for the new routes. Other existing cases passed/skipped as expected. |
| `pytest -q tests/test_agent_api.py` | **20 passed** in 0.61s. |
| Client and initial UI tests | 27 passed before four final UI evidence/error cases were added. |
| Final new API/client/UI subset | **51 passed**, 1 existing dependency warning, in 2.19s. |
| Final full suite with both PostgreSQL test URLs | **352 passed**, 1 warning, in 8.88s; all 32 PostgreSQL cases executed. |
| Final full suite without database test settings | **320 passed, 32 skipped**, 1 warning, in 4.04s. |
| `ruff check .` | Passed. |
| `ruff format --check .` | Passed; 91 files already formatted. |
| Offline `uv lock --check` | Passed; 62 packages, current lockfile. |
| Document-search evaluation | 20 cases, 10 documents/40 chunks; Hit Rate@5=1.0, MRR@5=1.0 unchanged. |
| Existing FastAPI health/info/docs/redoc/OpenAPI over real HTTP | All HTTP 200. |
| Streamlit root and /_stcore/health | HTTP 200, including after restarting with the matching backend URL. |
| Four real mock end-to-end AppTest scenarios | All completed; 8 chat messages, 2 SQL tables, 3 source citations and zero rendering exceptions. |
| Live OpenAI calls | Not performed; test backend explicitly disabled live and had no key/model. |
| Public deployment/auth/rate-limit/browser pixel review | Not performed; outside Day 9's local demo verification. |

Existing FastAPI/Starlette HTTPX deprecation warnings remain nonfatal. AppTest emitted
its known missing-ScriptRunContext warning when launched by the temporary external
verification script; rendering checks passed. Initial Ruff checks caught import order
and long UI strings, corrected before final checks. The first temporary E2E script used
a relative AppTest path resolved under /private/tmp and failed before rendering; changing
it to the absolute repository app path fixed the harness. No application assertion failed
in the final new API/client/UI tests. This is automated element rendering, not a manual
browser layout/pixel review.

Full PostgreSQL regression command:

```sh
TEST_DATABASE_URL=postgresql+psycopg://querypilot_admin@127.0.0.1:55438/querypilot_day8_verify TEST_READER_DATABASE_URL=postgresql+psycopg://querypilot_reader@127.0.0.1:55438/querypilot_day8_verify .venv/bin/python -m pytest -q --tb=short
```

Focused command:

```sh
.venv/bin/python -m pytest -q tests/test_agent_api.py tests/test_frontend_client.py tests/test_frontend_app.py --tb=short
```

### Actual startup and full-path demonstration

Verification started real loopback servers using the repository entry points:

```sh
READER_DATABASE_URL=postgresql+psycopg://querypilot_reader@127.0.0.1:55438/querypilot_day8_verify QUERYPILOT_AGENT_LIVE_ENABLED=false OPENAI_API_KEY= OPENAI_MODEL= .venv/bin/uvicorn querypilot.main:app --host 127.0.0.1 --port 58009 --no-access-log
QUERYPILOT_API_BASE_URL=http://127.0.0.1:58009 .venv/bin/streamlit run src/querypilot/frontend/app.py --server.address 127.0.0.1 --server.port 58509 --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false
```

The temporary Streamlit server was initially started without the test API origin, then
restarted with the matching URL above. Root/health were checked successfully afterward.
Both temporary web servers were stopped cleanly after verification; the pre-existing
synthetic PostgreSQL instance was left running. Standard user-facing commands use ports
8000/8501 and are documented in README and docs/frontend.md.

AppTest then used the **real frontend ApiClient without mocking network calls**, the real
FastAPI server, existing MultiStepService and actual synthetic SQL/document tools:

| Submitted question | Actual tool sequence | Evidence/UI result |
| --- | --- | --- |
| What are our top five products by revenue? | get_top_products(limit=5) | Two iterations; real top-five table and E1, partial/selected-record notice. |
| What is our return policy? | search_business_documents(query="product return window", top_k=1) | Two iterations; 30-day passage and QP-RET-001#s002-c001. |
| Which products generated the most revenue, and what is our refund policy? | get_top_products → search_business_documents | Three iterations; actual SQL rows and E2 policy citation, limitation notice. |
| How are failed payments handled? | search_business_documents(query="failed payments and retries", top_k=1) | Two iterations; actual policy and QP-PAY-003#s002-c001. |

The top SQL row was Outdoors Product 064, USD **37,882.39**, followed by the same four
fixture products from prior milestones. Rendering asserted that value directly in the
table. All four responses identified mock mode and passed mechanical reference checks.
No fake SQL rows or in-memory transport replaced the database path in this demonstration.
Component tests separately use synthetic fixture rows/in-memory transports as documented.

### Security and limitations

Tests cover streamed body limits before parsing, strict questions/modes/extra fields,
live opt-in and missing configuration without fallback, safe secret/error serialization,
limit failures with retained evidence, client construction/parsing/timeouts/no retries,
malformed/oversized/redirected responses and invented citations. AppTest covers startup,
examples, clear/history/reruns, mode selection without execution, disabled busy controls,
missing backend/live configuration, safe retryable errors, SQL tables, exact citations,
partial/conflicting/empty results and inert untrusted HTML/image-looking text. Existing
Day 6–8 security/cancellation/provider and real SQL permission/timeout regressions passed.

This is local-only functionality without authentication, authorization or rate limiting;
do not present it as a public production endpoint. A UI timeout/disconnect does not prove
backend cancellation, and cleanup may exceed the HTTP margin. There is no automatic retry
or cross-client idempotency; manually resubmitting a live request may incur another charge.
Display history is not persistent memory and is lost on session reset. Secret screening,
reference checks and deterministic mock selection retain their documented limitations.
Actual live OpenAI selection/schema/answer behavior remains pending approved verification.

No Day 9 implementation blocker remains. Prepare focused service/contracts, API, frontend/
client, tests and documentation commits. Commit/push approval has now been received. Day 10 preview is Expanded
Automated Testing and Integration Coverage; it has not been started.

## Day 10 — Real integration verification and reliability (2026-11-06)

Day 10 is complete locally; the user has now approved focused commits and a GitHub push.
The Day 9 closing paragraph above records the earlier milestone state. Day 11 has not
started. Full commands, boundary labels and fixture expectations are in [testing.md](testing.md).

### Root cause and regression fixes

Reproduced the exact top-products question through the running backend: the mock selected
`get_top_products`, but returned `configuration_error` with no evidence. Safe configuration
inspection confirmed `.env` absent and no reader URL configured. PostgreSQL was running
on existing ports; the failure occurred before any database connection. Earlier temporary
verification supplied an explicit reader URL and did not verify normal startup.

Fixed misleading diagnostics with a dedicated missing-reader code and frontend guidance
to configure reader settings and restart FastAPI. Other fixed categories distinguish
invalid configuration, unavailable server, authentication, nonexistent database, missing
tables, permissions and timeout. Raw connection details remain private. After explicit
approval, restarted only the project's backend on port 8000; its cached old settings had
otherwise retained the failure. The repaired backend remains running; the user's existing
Streamlit instance on 8501 was preserved and remained healthy.

The exact failed-payment count/handling question exposed a second defect: the mock
selector suppressed analytics whenever “handled” appeared. Quantitative wording now
selects payment analytics plus policy search. Two regression tests failed before these
fixes and passed afterward. The actual OpenAI adapter was not changed or called.

### Implementation and safety

Added `services/doctor.py` and the `doctor` CLI command; checks are read-only and distinguish
PASS, FAIL and dependent/optional SKIP. Added `scripts/prepare_local.py` using existing
PostgreSQL, Alembic and seed code, with private owned native storage on loopback port 55440.
Separate deterministic dev/test databases and restricted reader access were verified.
The helper succeeded twice, preserving existing data/configuration on its repeat run.
No existing database was reset; unrelated PostgreSQL instances remained untouched.
Docker was unavailable locally, so native PostgreSQL supplied the real engine.

Added acknowledged test-target guards in `tests/postgres_support.py`, real service fixtures
in `conftest.py`, 16 actual workflow tests and 14 diagnostic unit cases, plus one frontend
missing-reader regression. Existing PostgreSQL tests now enforce dedicated-target safety.
New actual connection failures and a fixture-owned empty schema test exercise safe error
serialization and released connections. Existing security controls were retained.

Updated database classification, registry errors, analytics error contracts, frontend
messages, CLI dispatch and mock selection. Updated README, architecture/security/testing
guides, repository instructions, goals and plans. No project dependency additions were
needed; pytest markers distinguish PostgreSQL and actual local HTTP checks. `.env` and
`.local/` credentials, database files and reports are ignored and excluded from changes.

### Actual verification results

- REAL DATABASE VERIFIED / MOCK PROVIDER VERIFIED: full configured suite **383 passed,
  0 failed, 0 skipped** in 10.70 seconds. The same suite under branch coverage passed all
  383 again in 14.64 seconds. All five SQL operations use actual PostgreSQL expectations;
  **48 tests** require the real database, including prior schema/security cases.
- Without database variables: **335 passed, 48 explicitly skipped**, 0 failed in 4.06 seconds.
  The focused real workflow module passed **16 tests** in 1.85 seconds.
- Both full suites emit one existing Starlette TestClient/httpx deprecation warning.
  No dependency was changed merely to silence that warning.
- Coverage measured using temporary external coverage 7.17.2: **2037/2241 statements
  (90.9%)**, **518/626 branches (82.7%)**, **89.1% combined**, scoped to `src/querypilot`.
  Tests, scripts and third-party packages are not included. Report is ignored locally.
- Final quality commands: `.venv/bin/ruff check .` passed;
  `.venv/bin/ruff format --check .` reported **99 files already formatted**;
  `git diff --check` passed. A credential-pattern scan of 29 changed/untracked nonignored
  files flagged only the existing README example placeholder, not a real credential.
  `git check-ignore` confirmed private environment, credential and coverage files excluded.
- REAL DATABASE VERIFIED / MOCK PROVIDER VERIFIED: doctor with reference date 2026-10-27
  and backend 8000 yielded **10 PASS, 0 FAIL, 0 SKIP**. Backend capabilities are only a
  reachability check; actual workflow tests supply SQL execution proof.
- MOCK HTTP VERIFIED / UI VERIFIED: isolated frontend tests retain fake transport for
  controlled error states and safe rendering. These are separate from the real HTTP tests.
- UI VERIFIED / REAL DATABASE VERIFIED / MOCK PROVIDER VERIFIED: actual typed-client TCP
  requests and AppTest exercised Streamlit through FastAPI to real tools. Four questions
  rendered eight chat messages, three SQL tables, three document citations, zero exceptions;
  test reruns did not resubmit and clearing removed session history.

All four acceptance questions passed against both an isolated actual HTTP test backend
and the repaired normal backend on 8000. Return policy cites `QP-RET-001#s002-c001` and
30 calendar days. Top products rank IDs 64, 35, 21, 76, 63 with respective revenue
37882.39, 36509.32, 35946.86, 35386.60, 34591.86. The combined revenue/refund question
retains both evidence types. Failed-payment question returns **486** from SQL and handling
policy from `QP-PAY-003#s002-c001`. No revenue rows were substituted. The valid top-five
subset may retain a limited-selection notice because additional products exist.

### Remaining limitations and Git preparation

NOT VERIFIED: live OpenAI behavior, manual browser acceptance, public deployment or formal
security audit. Existing grounding, screening and cancellation limitations remain. No
Day 10 implementation blocker remains; native setup requires installed PostgreSQL binaries.
Security regression tests cover allowlisting, read-only privileges, parameterization,
redaction, malicious retrieved content, references, budgets, cancellation and isolation;
passing deterministic tests does not establish prompt-injection immunity.

Recommended focused commit groups: safe database errors; mock selector regression;
doctor CLI; repeatable native setup/test guards; real workflow and UI tests; documentation.
Suggested milestone message: `test: expand real integration coverage and fix SQL retrieval`.
GitHub publication is now authorized; its result will be reported after execution.
Day 11 preview: Agent Evaluation &
Performance Metrics, requiring a new request and separate approval for live usage.

## Day 11 — Agent evaluation and benchmarking (2026-11-09)

Day 10 was already committed/pushed in six focused commits through `cc3cd21`; the working
tree was clean at inspection. Day 11 is implemented and verified locally. The user has now
approved focused Day 11 commits and a push to the existing repository. No Day 12 work
or paid OpenAI/judge request was performed.

### Gap analysis and design

Existing tests established execution wiring and safety, and the Day 5 relevance set
measured basic search hits/ranks. They did not provide one versioned agent benchmark,
independent numeric references, multi-category verdicts, citation/retrieval separation,
failure denominators or repeatable performance reports. The new pipeline loads a bounded
dataset, verifies the exact fixture/corpus, calls the existing shared request lifecycle,
scores outcomes/probes and writes safe per-case/category/aggregate reports. It introduces
neither a second agent nor a new dependency. Existing mock selection was left unchanged.

### Files and references

- Added `src/querypilot/evaluation/` with dataset contracts, deterministic metrics,
  real-tool runner/instrumentation, JSON/Markdown reports and CLI dispatch.
- Added `data/evaluations/agent_v1.json`: **38 cases**, 14 categories. Categories/counts:
  product revenue 3; revenue summaries 3; refund analytics 2; customers 2; payments 3;
  documents 10; combined 4; ambiguous 2; unsupported 2; empty 2; adversarial 2; missing
  evidence 1; partial results 1; execution limits 1.
- Added `scripts/build_evaluation_dataset.py`, using independent Python Decimal
  aggregation over synthetic seed rows and curated policy labels. References cover all
  five SQL operations; no generated agent answer is a gold reference.
- Added `tests/test_evaluation.py` (53 tests) and `tests/test_evaluation_postgres.py`
  (two real database tests). Tests use independent formula/outcome fixtures and separately
  verify the real benchmark, repeatable verdicts, report round trips and fixture rejection.
- Updated CLI, ignore rules, README, architecture/testing/evaluation guides, goals, plans
  and repository instructions. Generated benchmark/coverage reports remain ignored.

The configured reader matched every row of the pinned six-table fixture, not just counts:
500 customers, 100 products, 3,000 orders, 6,000 items, 3,006 payment attempts and 120 refunds.
Reference date 2026-10-27, seed 42, PostgreSQL version number 160013. Fixture SHA256:
`afbca1f4dbdbbb4b40913ebe417948641b26c2852447189b7cb5dacf0750d0e7`.
A different seed was safely rejected, and the normal fixture verified again afterward.
All verification uses the restricted reader and read-only transactions; no data was changed.

### Actual benchmark snapshot

Command: `.venv/bin/python -m querypilot.cli eval --mode mock --output reports/evaluation/day11`.
Generated `reports/evaluation/day11/results.json` and `results.md` at
2026-11-09T09:14:19Z. Exit **1** correctly indicates **24/38 benchmark passes (63.16%)**,
not an evaluator crash. All cases remain in their applicable denominators.

Mode/environment for every following benchmark metric: **MOCK PROVIDER VERIFIED + REAL
DATABASE VERIFIED**, actual local PostgreSQL 16.13 synthetic fixture and BM25 documents,
Python 3.12.16, sequential shared-service execution. Retrieval rows are additionally
**RETRIEVAL VERIFIED** independent probes. These are not live LLM measurements.

| Metric | Actual result and denominator |
| --- | --- |
| Tool precision / recall / F1 | Macro means **68.42% / 84.21% / 68.42%**, each over 38 cases |
| Exact tool match | **26/38 (68.42%)** |
| Required sequence accuracy | **4/4**, ordered cases only |
| Unique-tool counts | 31 correct, 37 expected, 43 selected/scored across cases |
| Precision@5 | **20%**, macro mean over 14 labeled probes |
| Recall@5 / Hit Rate@5 / MRR@5 | **100% / 100% / 1.0**, each over 14 labeled probes |
| Retrieval judgments | 11 unique query/label pairs; repeated queries remain case-weighted; one unjudged empty probe excluded/disclosed |
| Citation corpus validity / retrieved provenance | **22/22 / 22/22** case-unique citation events; zero fabricated/unretrieved citations |
| Required exact reference coverage | **4/4** required citation references |
| Required document-source coverage | **13/14** required labeled sources |
| Factual evidence match / answer literal-and-source checks | **48/60 / 48/60** independent field assertions |
| Unsupported numeric literal detections | **0/38** cases; conservative membership check only |
| Completed / partial / abstention | **33/38 / 19/38 / 5/38** cases |
| Tool failure | **2/43** attempted calls; both controlled missing-reader scenarios |
| Provider failure / timeout | **0/38 / 0/38** cases |
| Execution-limit termination | **1/38** cases; deliberately constrained iteration case |
| Correct negative-case handling | **4/11** negative cases |
| Prevented duplicate events | **0**, across 43 attempts; opportunity/success rate NOT EVALUATED |
| Error events | Three: two database-configuration events, one execution-limit event |
| Latency mean / median / P95 | **9.331 / 3.754 / 29.485 ms**, 38 local mock-provider samples |
| Latency min / max | **2.605 / 30.948 ms**, same 38 samples |
| Mean tool attempts / iterations / provider calls | **1.132 / 2.105 / 2.105**, each over 38 cases (43 attempts, 80 provider calls) |
| Mean safe-response / evidence bytes | **1558.76 / 769.71**, each over 38 cases |
| Maximum observed provider-input JSON | **7755 bytes** across 80 calls; configured context budget 128000 bytes; not tokens |

The reference checks do not establish semantic correctness. Semantic faithfulness,
claim-level entailment/citation precision, universal claim coverage and LLM-as-judge
scores are **NOT EVALUATED**. A source can be valid and retrieved while still irrelevant
to a claim. Literal matches, numeric membership and completed status are not substitutes.
No performance improvement or live latency claim is made; this is one local sample per
case with no load test. Separate retrieval/preflight time is excluded, resource cleanup
included; integer-ms registry timings can round fast search to zero.

### Four acceptance questions

All four completed and passed with **MOCK PROVIDER VERIFIED + REAL DATABASE VERIFIED**:

| Case | Selected tools | Evidence and citation check | Duration |
| --- | --- | --- | ---: |
| Top five products | `get_top_products` | IDs 64, 35, 21, 76, 63 in verified revenue order; all ten name/value assertions match | 20.295 ms |
| Return policy | `search_business_documents` | 30-calendar-day assertion; `QP-RET-001#s002-c001` exists and was retrieved | 3.488 ms |
| Revenue plus refund policy | top products → document search | Both evidence types and expected policy citation preserved | 16.311 ms |
| Failed-payment count plus handling | payment summary → document search | **486 independently reverified failed attempts**; `QP-PAY-003#s002-c001`; distinct source references | 14.543 ms |

Top-product revenues remain 37882.39, 36509.32, 35946.86, 35386.60 and 34591.86.
The evaluator uses the same service as FastAPI; existing separate tests additionally
exercise actual HTTP and Streamlit. **UI VERIFIED** here applies to those rerun real
AppTest→HTTP→PostgreSQL smoke tests, not to the benchmark runner. Manual browser review
and **LIVE OPENAI** remain **NOT VERIFIED**.

### Failed benchmark cases and root causes

Fourteen failed expectations are intentionally retained:

- `empty-products`: mock ignores the explicit 1999 filter and returns all-time products.
- `category-revenue`: “product” + “revenue” selects top products instead of category summary.
- `refund-category`, `refund-totals`: mock has no refund analytics selector, so searches docs.
- `customer-one`: mock ignores customer ID and returns its default busiest-customer list.
- `payment-statuses`, `successful-payments`: selector recognizes failed-payment wording only.
- `cancellation`: “customer” + “order” incorrectly selects SQL for a policy question.
- `ambiguous-best`, `ambiguous-performance`: benchmark requires no tools/abstention;
  the mock still dispatches document search, even when it ultimately abstains.
- `unsupported-weather`, `unsupported-stocks`, `adversarial-write`, `adversarial-secrets`:
  broad keyword matches trigger document retrieval and answers rather than required
  no-tool abstention. This is selection/answer behavior, not successful execution of
  forbidden SQL or credential access; the real registry/security boundaries remain intact.

Per-category passes/cases: product 3/3; revenue 2/3; refunds 0/2; customers 1/2; payments
1/3; documents 9/10; combined 4/4; ambiguous 0/2; unsupported 0/2; empty 1/2; adversarial
0/2; missing 1/1; partial 1/1; limits 1/1. Detailed metrics, actual/expected facts and
failed check names are preserved in both report formats where applicable. The benchmark
does not execute refund analytics because the mock fails to select it; retained Day 10
real SQL tests independently verify that tool. No mock behavior was tuned today.

### Verification and environment results

- Full configured pytest suite: **438 passed, zero failed/skipped**, 12.11 seconds.
- Final branch-coverage full suite after scoring refinements: **438 passed**, zero
  failed/skipped, 16.95 seconds. **50 PostgreSQL-marked tests**, including two new ones.
- Without integration variables: **388 passed, 50 explicitly skipped**, 4.65 seconds.
- Evaluation subset: **55 passed**; 53 scoring/runner/report unit/document tests and
  two real PostgreSQL benchmark tests. Existing document, protocol, guardrail, API/client
  and Streamlit suites are included in the full run; no skipped security check is implied.
- One existing Starlette TestClient/httpx deprecation warning remains; dependencies
  were not changed simply to silence it.
- Measured coverage (`src/querypilot`, external coverage 7.17.2): **2377/2582 statements
  (92.06%)**, **613/720 branches (85.14%)**, **90.55% combined**. Scripts/tests/third-party
  code excluded. Coverage JSON remains ignored at `.local/day11-coverage.json`.
- Doctor after runtime repair: nine PASS, no FAIL, backend URL deliberately omitted
  and reported SKIP. Reader role, fixture, migrations, corpus and mock readiness passed.
- Initial validation was blocked by missing standard-library files in the old temporary
  Python installation. Downloaded Python 3.12.16 and repointed only the ignored virtual
  environment interpreter. No committed dependency/runtime path changed.
- During evaluator development a multiline policy excerpt initially triggered a false
  numeric-membership failure. Fixed scoring to use citation-terminated spans and actual
  source text rather than escaped JSON; regression checks now cover this case. Early Ruff
  wrapping/import findings were fixed. No unresolved pytest failures remain.
- Final `.venv/bin/ruff check .` passed, `.venv/bin/ruff format --check .` reported
  **109 files already formatted**, and `git diff --check` passed. JSON/Markdown artifacts
  were parsed/checked after generation. The exact document-only CLI command passed
  **1/1**, exit 0. A pattern scan of 20 changed/untracked nonignored files flagged only
  the existing README URL placeholder; no real credential was found. `git check-ignore`
  confirmed `.env`, private setup credentials, benchmark artifacts and coverage excluded.
- Document-only subsets explicitly clear reader settings, preventing an unexpected SQL
  selection from reading an unverified database. A configured-but-unused reader URL is
  covered by the regression test. Report layout was refreshed while preserving the saved
  benchmark's actual measurements; final coverage includes these refinements.

### Limits and next step

No Day 11 implementation blocker remains. Remaining limits are explicit benchmark
weaknesses, small/nonexhaustive policy labels, mock-only behavior, heuristic factual checks,
no semantic judge, no duplicate-prevention opportunity rate and one local timing sample
per case. No source code uses administrative access for evaluation. Generated reports are
secret-screened and ignored. Security tests remain engineering regressions, not a formal
audit or proof of prompt-injection immunity.

Suggested focused commits: dataset/reference builder; metrics; runner/fixture/instrumentation;
reports/CLI; evaluation unit/real tests; docs/results. Suggested milestone message:
`feat: add reproducible agent evaluation and benchmarking`.
Commit/push approval has now been received; publication results will be reported after execution.
Day 12 preview: Docker Compose & GitHub Actions CI;
neither has been started.

## Day 12 — Containers, CI and reproducible setup (2026-11-10)

Day 11 was already committed/pushed through `efa5d5a`; the working tree was clean at
inspection. Day 12 implementation and native verification are present, but **Day 12 is
not fully complete**: mandatory Docker build/runtime verification is blocked by the absent
Docker Desktop daemon socket. Starting Docker Desktop was declined, and that decision was
respected. No images, containers or Docker volumes were created/deleted locally. There
was no cloud deployment, image publication, paid API call, commit or push.

### Inspection and implementation plan

Read repository specifications and guides, inspected the lock, actual startup/configuration,
Alembic, seed/reader setup, doctor/evaluation paths and original database-only Compose file.
Correct entry points are `uvicorn querypilot.main:app`, Streamlit's existing app file,
`querypilot.cli doctor` and the existing shared agent service. Planned and implemented:
non-root images, isolated Compose setup, separate readiness, exact original PostgreSQL
test enforcement, reviewed case-level benchmark baseline and local/remote CI parity.

### Files and boundaries

- Added `docker/Dockerfile.backend` (runtime/test targets), `docker/Dockerfile.frontend`
  and allowlisted `.dockerignore`. Runtime stages exclude dev tools/uv and use UID 10001.
  Both images reuse one locked runtime graph; no separate frontend lock or size claim.
- Replaced old `compose.yaml` with the isolated `querypilot_day12` stack: PostgreSQL 16.13,
  one-shot setup, reader-only backend and frontend. Added `compose.test.yaml` for a separate
  project/test database. App roots are read-only, capabilities dropped, no socket/host-source
  mounts, and no PostgreSQL host port. Backend/frontend host ports default 18000/18501.
- Added `db/bootstrap.py` reusing existing Alembic, seed, verifier, exact fixture comparison
  and reader audit. Only empty schemas migrate automatically; existing different schema/data
  is refused. Setup receives writer access, application runtime does not.
- Added root `/ready` through existing read-only doctor checks; `/health` stays liveness.
  Missing reader, unreachable/authentication failures, missing tables and empty seed return
  503. No HTTP request provisions data. Updated the explicit OpenAPI route contract test.
- Added `scripts/prepare_docker.py`, updated `.env.example`; private generated `.env.docker`
  is mode 0600, URL-safe, ignored, preserved on rerun and separate from native `.env`.
- Added reviewed `baseline_day11.json`, unchanged gold dataset, and `evaluation/gate.py`.
  It checks dataset/corpus/fixture identity, all case IDs, protected passes and known failures.
  Added `postgres_required.json` containing all original 50 node IDs, and a JUnit checker
  that rejects skipped/failed/missing cases even when aggregate counts could look adequate.
- Added `.github/workflows/ci.yml`, `scripts/ci_database.py`, `scripts/run_checks.py`,
  `scripts/check_ci_results.py`, `scripts/check_compose_logs.py`, Makefile targets and
  `services/container_smoke.py`. The workflow is PR/main, contents-read, immutable action
  hashes, no image publishing or paid API. Random ephemeral CI database credentials are
  masked before output. Docker smoke verifies real HTTP, frontend, outages, restart,
  volume identity, exact data and bounded log screening when it can actually execute.
- Added 14 unit and four real PostgreSQL tests in the deployment modules. Updated one
  existing missing-reader test to specify `reader_database_url=None`, preventing an
  inherited CI reader URL from invalidating that unit test's intended missing-config state.
- Updated README, architecture/database/testing/evaluation/security guides, goals, plans,
  instructions and new [containers.md](containers.md) with commands and honest boundaries.

The only new dependency is **development-only coverage 7.17.2**, previously used externally
on Day 11. Lock resolution now has 63 packages; every pre-existing package version is
unchanged. No secrets/private reports enter source control or the image build context.

### Actual command results

| Command/check | Result and boundary |
| --- | --- |
| Initial Git status | Clean, main at efa5d5a; Day 10/11 work preserved |
| Docker version/info | Client/Compose installed, daemon socket absent; DOCKER NOT VERIFIED |
| Start Docker Desktop | Permission declined; not retried or bypassed |
| Backend `docker build` | Failed exit 1: cannot connect to daemon; no build verification |
| Frontend `docker build` | Failed exit 1: cannot connect to daemon; no build verification |
| Compose `up --build --wait --wait-timeout 180` | Failed exit 1: daemon unavailable |
| Development/test `docker compose ... config --quiet` | Both passed, using private settings without printing resolved secrets |
| `uv lock` and `uv sync --locked --extra dev` | Passed; only coverage added; original versions checked unchanged |
| Focused deployment unit tests | 14 passed |
| Focused real setup/readiness/gate tests | Four passed, REAL DATABASE VERIFIED |
| `python scripts/run_checks.py` with acknowledged native test environment | Exit 0, LOCAL CI VERIFIED |
| Complete suite under coverage | **456 passed, zero failed/skipped**, 22.41 seconds; includes actual native HTTP/Streamlit tests |
| Required PostgreSQL verification | **54 executed**, including every original 50 node ID; JUnit checker passed |
| Suite without integration variables | **402 passed, 54 explicitly skipped**, 4.67 seconds; this is not CI parity |
| Doctor from parity command | Nine PASS, zero FAIL; backend URL intentionally omitted (one optional SKIP) |
| Benchmark gate | 38 cases, 24 pass/14 known fail, **24 protected, zero regressions**, exit 0 |
| Benchmark exact tool match | 26/38, unchanged; MOCK PROVIDER VERIFIED + REAL DATABASE VERIFIED |
| `actionlint` 1.7.7 | Workflow passes local validation; temporary tool outside project dependencies |
| Action SHA verification | checkout v4.2.2/setup-python v5.6.0 tags resolved independently to the pinned immutable hashes |
| Final Ruff lint / format / whitespace | All pass; **121 files already formatted**; `git diff --check` clean |
| Configured-secret scan | 37 changed/untracked nonignored files; zero matching configured secret values |
| Resolved Compose policy checks | Reader-only backend, frontend API-origin-only environment, no PG host ports, app read-only roots/capability drops/no host mounts, distinct volume namespace all pass; configuration only |

One existing Starlette TestClient/httpx deprecation warning remains. An initial parity run
found the expected new `/ready` path missing from the old OpenAPI test and exposed the unit
test's inherited-reader assumption; both were corrected without removing security assertions.
Early Ruff line-wrapping findings were fixed. No unresolved pytest failure remains.

Coverage measured across `src/querypilot`: **2482/2762 statements (89.86%)**, **633/752
branches (84.18%)**, **88.65% combined**. Scripts/tests/third-party packages are excluded.
The new container smoke module remains at 0% locally because Docker is unavailable; CLI
checks run after pytest are also outside that coverage invocation. The lower aggregate
than Day 11 is reported honestly; no unverified infrastructure code was excluded to inflate it.
Reports remain ignored at `.local/ci-results.xml`, `.local/ci-coverage.json` and
`reports/evaluation/gate/`.

### Real database and failure/recovery evidence

The new setup regression creates a randomly named owned database/role on the acknowledged
test cluster, applies the existing initial migration, seeds the standard 500/100/3000/6000/
3006/120 fixture, verifies reader access and repeats setup successfully. Runtime readiness
also succeeds with writer configuration removed. Real missing-schema, empty-refund-table,
wrong-password and unavailable-port checks fail safely. A deliberately altered fixture
is refused without reset; cleanup targets only the newly created test database/role.
Original dedicated database fixtures/business data remain intact.

The four existing acceptance workflows passed through actual native HTTP and real tools
in the full suite. Failed payments were independently checked as 486 for this fixture.
These results are **REAL DATABASE VERIFIED / MOCK PROVIDER VERIFIED**, not container proof.
New container smoke independently counts failed attempts and compares returned SQL evidence
when Docker becomes available; it does not assume 486 for every database.

Native UI regression coverage still includes actual AppTest→HTTP→PostgreSQL, and isolated
frontend tests retain backend-unreachable diagnostics. Containerized UI reachability,
backend-before-init ordering, restart/volume persistence, log screening and clean shutdown
are configured but **NOT VERIFIED**. The database health probes use TCP explicitly to avoid
accepting the temporary socket-only initialization server as fully started.

### Benchmark regression policy and CI status

The baseline is derived from the saved Day 11 report and reviewed published identities;
CI never rebuilds it from current output. Unit tests demonstrate that swapping a protected
pass with a new improvement still fails despite an unchanged aggregate. Identity mismatch,
missing/duplicate cases and fully mocked mode are rejected. All 14 known failures remain
visible; no gold label, mock router or answer template was weakened to improve scores.

CI performs the same native-parity test/gate commands against an ephemeral PostgreSQL
container, then separately builds and checks the full Compose stack. Runtime backend has
only reader credentials; CI writer credentials are limited to synthetic setup/test fixtures.
No key/secret environment dump is printed. Remote status is explicitly
**CI CONFIGURED — REMOTE EXECUTION NOT VERIFIED**. Live OpenAI remains
**LIVE OPENAI NOT VERIFIED**; no paid request was made.

### Remaining blocker and next milestone

The stopped Docker daemon blocks both image builds, all four containerized workflows,
container health/outage checks, restart/persistence and shutdown verification. Exact
commands are in [containers.md](containers.md); starting Docker and rerunning them is
required before claiming Day 12 fully complete. Dockerfile syntax/dependency builds have
not been established by Compose/actionlint checks alone. GitHub CI must separately execute
after an approved push. These are verification gaps, not fabricated successes.

The user approved committing/pushing the current Day 12 work on 2026-11-11, with Docker
verification still incomplete. Publication results will be reported after execution.
Suggested groups: Dockerfiles/Compose;
initialization/configuration/readiness; GitHub CI/parity; benchmark gate/baselines;
integration tests; documentation. Do not remove any existing volume. Day 13 preview is
Deployment & End-to-End Demo; no Day 13 feature or deployment has started.

## Day 12 follow-up — Actual Docker verification (2026-11-11)

The user confirmed Docker Desktop was available and explicitly authorized verification
using only this project's isolated resources, with no commit/push. Initial Git status was
clean at `867b6d3`. The sandbox initially denied socket access; approved Docker access
confirmed daemon **29.9.3**, Compose **v5.7.0**. No existing Day 12 containers/volumes were
present. Native data and unrelated Docker resources were not touched.

### Builds and confirmed startup defect

`docker compose --env-file .env.docker build backend frontend` succeeded with the existing
lock and Dockerfiles: `querypilot-backend:day12` and `querypilot-frontend:day12`.
Initial startup failed with `invalid mount path: 'noexec' mount path must be absolute`.
The flow-style YAML tmpfs list was unquoted, so its comma-separated options became separate
mount entries. Changed only that configuration line to
`tmpfs: ["/tmp:rw,noexec,nosuid,size=64m"]`; no business/agent code was changed.
The retry `up --no-build --wait --wait-timeout 180` succeeded. The newly created volume
was preserved through this failure and every subsequent check.

### DOCKER VERIFIED / REAL DATABASE VERIFIED / MOCK PROVIDER VERIFIED

- PostgreSQL, backend and frontend were healthy; setup exited **0**. Migration revision
  is **0001**. Existing setup successfully migrated/seeded and later repeated idempotently.
- Exact six-table fixture verification passed with reference 2026-10-27, seed 42, counts
  500 customers/100 products/3000 orders/6000 items/3006 payments/120 refunds. Fixture hash
  remains `afbca1f4dbdbbb4b40913ebe417948641b26c2852447189b7cb5dacf0750d0e7`.
- Runtime UID **10001**, writer configuration absent, live disabled, transaction read-only
  **on**. The existing role audit confirmed SELECT-only privileges and prohibited ownership,
  membership, DDL and write grants were absent.
- Published `localhost:18000/health`, `/ready`, `localhost:18501/` and `/_stcore/health`
  all returned **200**. Frontend-to-backend internal routing also worked in the smoke check.
- All four acceptance workflows passed through actual backend HTTP with real SQL/BM25 tools,
  then were submitted again through published port 18000 with matching completed statuses
  and selected tools. Return policy cited `QP-RET-001#s002-c001`; combined revenue/refund
  preserved both evidence types; payment handling cited `QP-PAY-003#s002-c001` separately.
- Independent code-owned SQL returned top product IDs/revenues:
  **64/37882.39, 35/36509.32, 21/35946.86, 76/35386.60, 63/34591.86**.
  Independent SQL count confirmed **486 failed payment attempts** and matched API evidence.
- Existing benchmark gate ran inside the backend using writable `/tmp/day12-gate`:
  **38 cases, 24 passing, 14 known failures, all 24 protected cases passing, zero regressions**.
  It passed again after restart. No baseline, gold label, provider or scoring code changed.
- Stopped only this project's DB: `/health` remained **200**, `/ready` became **503**.
  Restarted DB/backend/frontend and waited for all health checks to recover. Setup again
  exited 0; all four workflows and the gate passed after recovery.
- Compared the named volume's name/creation timestamp and PostgreSQL's persistent system
  identifier before/after restart: all unchanged. Exact fixture verification also matched,
  establishing persistent storage rather than merely recreated equivalent fixture values.

### Logs, report export and clean shutdown

Bounded credential scans before/after shutdown found **no configured passwords or credential-like
patterns**. The pre-shutdown log review found zero ERROR/FATAL/traceback markers. One nonfatal Alpine initialization warning
was observed: `no usable system locales were found`. No locale-related functional failure
occurred in the verified fixture/tool results. This is log screening, not a security audit.

Two `docker compose cp` attempts could not find report files on the tmpfs mount, despite
their being readable inside the container. Recovered both via `exec cat` without code
changes; safe reports are ignored at `.local/day12-container-gate.json` and `.md`.
The storage identity snapshot is ignored at `.local/day12-docker-before.json`.

`stop --timeout 40` completed: PostgreSQL and Streamlit exited **0**; backend exited **143**
(SIGTERM). Backend logs confirmed the final lifecycle stop and Uvicorn shutdown completion
after its last start; no OOM kill or forced-kill indication occurred. This is graceful
signal termination, not an unexplained crash. The final credential scan passed again.
`down --timeout 40` then removed only the project's stopped containers/network. No project
containers remain. **The named PostgreSQL volume is retained**, created at
2026-11-11T06:17:22Z. No volume deletion command was used.

### Scope and remaining verification

Local Docker verification requested in this follow-up is complete after the tmpfs fix.
Ruff lint/format and whitespace checks passed; 121 files already formatted. A full pytest
rerun was not needed for this configuration-only fix; the prior native 456-test result is
historical, not a new test execution claim. The actual Docker runtime, four acceptance
workflows and 38-case gate supply the new evidence.

Remote GitHub CI, the separate Docker test-profile suite, manual browser acceptance and
live OpenAI were not run here and remain **NOT VERIFIED**. The stack is intentionally
shut down after verification. The one-line Compose fix and verification documentation
remain **uncommitted/unpushed**, pending explicit approval. No unrelated functionality,
deployment, image publishing or Day 13 work was introduced.

### Follow-up publication approval and remote CI inspection

The user subsequently approved organized commits/push and remote CI verification, with
an explicit requirement to keep the 14 known benchmark failures visible. The earlier
Day 10/11/12 milestone commits were already pushed; only follow-up changes require new
commits. Lint, formatting, whitespace and configured-secret checks passed; private settings
and reports remain ignored. README now explicitly states that 24/38 mock-provider passes
do not establish production-level agent accuracy. Gold labels and baseline are unchanged.

Inspected remote run 42970429230 at commit 867b6d3: the quality job passed, including
PostgreSQL tests/coverage/gate; the image build step passed but Compose smoke failed with
the same unquoted tmpfs option-list error. This is the verified local fix being published.
The new run's actual result will be reported after push, without assuming it is green.

## Day 13 — Private deployment readiness and product demo (2026-11-11)

Inspected the new brief, repository instructions/guides, actual entry points/settings,
Docker/Compose/CI, shared service, client, smoke/gate and recent Git history. Starting tree
was clean at **f43b45e**. The brief's pending/uncommitted Day 12 statements were outdated:
both remote jobs passed in run **43094636403** at that commit. That is verified historical
Day 12 evidence, not remote verification of today's uncommitted Day 13 changes.

### Plan, deployment decision and scope

Chose a private local Docker demo on existing hardware, with screen sharing/recording,
rather than public hosting. Researched current official Docker education/personal licensing,
DigitalOcean VM prices and Render free-service limitations. The deployment guide compares
cost, complexity, PostgreSQL persistence, HTTPS, secrets, sleep/resource limits and maintenance.
No provider account/credentials or paid resource was needed. A future VM requires explicit
budget/provider/host-access approval and access-control design first.

The application has no public authentication/authorization, per-client rate limiting or
public HTTPS/WSS termination; diagnostic/evidence access also needs protection. **Public
deployment is blocked** until those gaps are addressed and approved. Existing body limits,
execution budgets, CORS and container bounds are useful controls, not replacements.
No complex auth system, cloud infrastructure, image publishing or Day 14 work was added.

### Implementation and files

- Added `compose.demo.yaml`, reusing the Day 12 stack/project/volume. It adds 512 MiB memory,
  CPU ceilings, 256-PID limits and bounded log rotation. Host ports remain loopback-only;
  PostgreSQL remains internal. `QP_DEMO_API_ORIGIN` supplies the frontend's internal origin.
  Added matching Make targets and example configuration. No dependency/lockfile changes.
- Added `services/smoke.py` and public `querypilot.cli smoke-test`. Bounded system metadata
  probes plus the existing typed client validate readiness/OpenAPI/capabilities and four
  versioned mock acceptance responses. Existing scoring checks tools, evidence, ranking,
  numeric literals and citations. `--verify-database` performs exact fixture checks and
  fixed independent reader SELECTs; without it, direct DB verification is explicitly SKIP.
  No raw answers, records, credentials or origin are printed; failed prerequisites stop
  question submission and exit nonzero. No second agent/live request or writer fallback.
- Added `scripts/verify_demo_ui.py`: actual Streamlit AppTest through the published
  container backend, checking rendering, history, clear, selected-record warnings and
  unreachable-backend presentation. It is not a manual browser/WebSocket acceptance claim.
- Added 12 unit smoke cases and two real PostgreSQL API/service smoke cases. Existing
  deployment, security, SDK/protocol, injection, citation, timeout, isolation and cleanup
  tests are reused. JUnit accounting includes the new PostgreSQL module and still enforces
  all original 50 node IDs. Existing gold dataset and 24-protected-case baseline unchanged.
- Existing CI collects the new tests; the image job now configures demo-profile validation
  and the new real smoke CLI. Local actionlint passes. No workflow was dispatched or pushed.
- Added `docs/deployment.md` and `docs/demo.md`; updated README, architecture, containers,
  testing/security guides, goals, plans and instructions. Demo includes a 2–3 minute
  engineering script, separate 30–45 second recording plan and exact manual checklist.
  No LinkedIn launch text, resume bullets, recording, screenshots or fake interactions.

### Actual verification results

**LOCAL CI / REAL DATABASE / MOCK PROVIDER VERIFIED:** `scripts/run_checks.py` with the
acknowledged dedicated native test environment passed **470 tests, 0 failed/skipped** in
**23.64 seconds**, including **56 PostgreSQL tests** and every original required case.
The new focused modules passed 12 unit/two real cases. One existing Starlette TestClient/
httpx deprecation warning remains. Native doctor returned nine PASS, no FAIL and one
optional backend-URL SKIP. The full 38-case gate still reports **24 pass/14 known fail,
24 protected, zero regressions**. No failures were hidden or relabeled as production accuracy.

Measured coverage (`src/querypilot`, tests/scripts/third-party code excluded):
**2591/2882 statements (89.90%)**, **662/786 branches (84.22%)**, **88.69% combined**.
The old container smoke module and CLI paths outside the coverage invocation remain in the
denominator. The report is ignored at `.local/ci-coverage.json`.

**DOCKER VERIFIED:** the daemon was initially stopped. After explicit startup approval,
Docker Desktop started and daemon 29.9.3 was reachable. Both existing Dockerfiles rebuilt
successfully with locked dependencies and the new source. The resource-limited override
validated and the stack started healthy against its existing isolated volume; setup exited 0.
No volume or unrelated container was removed and no native business data was changed.

**REAL DATABASE / MOCK PROVIDER VERIFIED:** the new CLI ran inside the backend against
`http://backend:8000` with direct reader verification. Every required stage and all four
acceptance cases passed; **486 failed payment attempts** were independently selected and
compared with returned API evidence, after exact six-table fixture verification.

| Workflow | Actual result | Per-question HTTP time in first container smoke |
| --- | --- | ---: |
| Top five products | Real SQL ranking/reference values, bounded evidence and selected-record notice | 32.713 ms |
| Return policy | BM25, 30-calendar-day fact, valid retrieved policy citation | 15.490 ms |
| Revenue + refund policy | SQL and policy sources preserved separately | 28.150 ms |
| Failed payments + handling | Real 486 count and separate payment policy source | 25.408 ms |

Top product IDs/revenues remain 64/37882.39, 35/36509.32, 21/35946.86, 76/35386.60 and
63/34591.86 for this verified fixture. Case scoring/reference checks passed; semantic
faithfulness and claim-level entailment remain NOT EVALUATED. These are local mock timings.

The host CLI on port 18000 separately passed all four questions and API contract checks;
it correctly marked direct DB comparison SKIP because that flag was omitted. The container
probe supplied the same-database independent evidence. Reports are ignored in `.local/`.
The unchanged full benchmark gate also passed inside Docker with all 14 known failures
visible; no paid SDK call was made.

### Automated UI, manual browser and recovery

**AUTOMATED UI VERIFIED, NOT MANUAL:** AppTest submitted the four questions through actual
HTTP to the container backend/database. It rendered **8 chat messages, 3 SQL tables and
3 document citations**. Mock mode, selected-record warnings, history across reruns, clearing
history and a safe unreachable-backend message all passed. It runs the actual frontend
code on the host; it does not claim graphical interaction with the container's Streamlit
browser/WebSocket session. The container frontend root endpoint returned 200.

The first UI-script run failed because AppTest resolves relative paths against the calling
script, not the working directory. Fixed the new verification script to use the absolute
repository app path and reran successfully. Benign bare-mode ScriptRunContext warnings
were emitted; no application exception remained. Early Ruff wrapping findings were fixed.

No graphical browser-control tool was available. **MANUAL BROWSER ACCEPTANCE — NOT VERIFIED.**
No screenshot or recording is claimed. The exact 12-item checklist in `docs/demo.md` is the
user action required, covering real browser load/connectivity, mock label, submissions,
tables/citations/panels/warnings, history/clear, outage and refresh behavior.

Stopped only this project's DB: health stayed 200, the new smoke exited 1 at readiness
and submitted no questions. Stopped its backend: smoke exited 1 at liveness with safe
diagnostics. Restored the profile; all services became healthy, setup repeated successfully
and all four smoke cases/direct SQL checks passed again. Volume creation identity and
PostgreSQL system identifier matched before/after. Original data persisted.
Existing full-suite real wrong-password, missing-migration/seed tests and document/provider/
timeout/partial-result regressions also passed; no redundant failure framework was added.

The bounded container log credential scan passed before/after recovery. Existing non-root,
reader-only, no-host-DB-port, no-socket-mount and safe trace boundaries were preserved.
No formal security audit, public load test or injection-immunity claim is made.

### Performance/resource snapshot

Actual cached-image start with the existing fixture volume and private profile:
**17.283 seconds** until Compose reported all healthy. Backend readiness was observed at
**17.352 seconds**, after that wait; this is not a separately instrumented first-ready timestamp.
The first direct-database smoke function took **365.959 ms**, excluding Python CLI import/
process startup; the four question times above include HTTP/service work. Separate single
GET observations were health **30.076 ms**, readiness **36.108 ms**, frontend **6.179 ms**.
No comparison with live API latency, capacity benchmark or speedup is implied.

One near-idle post-probe Docker stats snapshot (512 MiB configured per-service limit):

| Container | Memory | CPU |
| --- | ---: | ---: |
| PostgreSQL | 56.68 MiB | 0.00% |
| Backend | 99.05 MiB | 0.27% |
| Frontend | 56.16 MiB | 0.62% |

These are snapshots, not peaks or concurrent-user sizing. The frontend had process/HTTP
health traffic, not a manually driven browser session. No monitoring stack was installed.
Measurements/safe smoke reports are ignored under `.local/day13-*`.

### CI/Git and final scope

The already approved Day 12 push **f43b45e** passed remote run **43094636403**, with both
quality and image jobs green. That result predates these new files. There is no approved
Day 13 push, so report **CI CONFIGURED — REMOTE EXECUTION NOT VERIFIED for Day 13**.
The local workflow validator passes; local success does not certify unexecuted GitHub jobs.
No commit, push, workflow dispatch or public deployment was performed.

Demo guides/operator plans are ready. The private stack is left healthy on loopback
18000/18501 so the user can perform manual acceptance; use `make demo-down` afterward to
stop it while retaining data. Pending items are manual browser acceptance, Day 13 remote
CI after explicit Git approval, and optional approved live OpenAI verification. Public
deployment remains blocked by the documented essential controls. No implementation
blocker remains for the selected private-demo strategy.

Recommended logical commits after approval: private deployment profile; smoke CLI;
security/deployment review; smoke/acceptance tests and UI verifier; demo plans; progress/
architecture/CI documentation. Day 14 preview is portfolio/documentation polish and final
presentation work; it has not started and no resume or launch copy was created.

Final checks: Ruff lint, format (**127 files already formatted**), actionlint and whitespace
passed. A configured-secret scan of **21** changed/untracked nonignored files found no
matching private credential values; settings and measurement reports are confirmed ignored.
The final resolved-policy check initially compared Compose's string-valued byte limit with
an integer; normalized the one-off verifier and confirmed actual Docker HostConfig memory
536870912 bytes, 256 PIDs and configured CPU ceilings. No application/configuration change
was needed. Final backend readiness and frontend endpoints returned 200, with the private
demo healthy for the user's manual checklist. No commit/push occurred.

### Day 13 Git publication follow-up (2026-11-12)

The user explicitly approved publishing today's Day 13 changes to the existing GitHub
repository in focused commits. Review, private credential screening and local CI checks
are being repeated before publication. Remote Day 13 CI remains pending until its actual
workflow finishes. No Day 14 work, paid API calls or public deployment is authorized.

Publication validation: the first sandboxed run passed 414 tests but could not access
PostgreSQL (56 setup errors: operation not permitted). Repeating with approved local
network access passed the full CI runner, including all 470 tests, 56 PostgreSQL cases,
Ruff, doctor and the 24-protected-case regression gate. Actionlint and whitespace checks
also pass. Credential-value screening found no private values in the 21 publication files;
the only URL-pattern matches were documented USER:ENCODED_PASSWORD placeholders.

Publication succeeded: six focused commits, 8326e72, 2271a30, 18c795d, 6501f8a,
ba5507e and 9ab3c07, were pushed to the existing origin/main without rewriting history.
The [Day 13 CI run](https://github.com/Srikarpanuganti5/querypilot_ai/actions/runs/43164942219)
was triggered by 9ab3c07. Its remote outcome must be checked directly; the earlier pending
statements above describe the original local implementation, before this approval.

Remote Day 13 verification **PASSED** at 9ab3c07 in run 43164942219: quality completed
in 1m34s and images in 1m31s. The jobs include the full test/database/gate checks, both
image builds, the new smoke CLI, existing container workflows, recovery/persistence/log
screening and clean shutdown. GitHub emitted a nonblocking Node.js 20 deprecation notice
for the existing pinned checkout/setup-python actions (forced to Node.js 24). No tests or
baseline assertions were weakened. Manual browser acceptance and live OpenAI stay unverified.
