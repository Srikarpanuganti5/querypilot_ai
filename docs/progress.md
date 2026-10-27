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
