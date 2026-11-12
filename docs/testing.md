# Local testing and verification — Days 10–13

## Day 13 smoke and acceptance

`make demo-up` applies the private resource-limited override to the existing stack.
`make demo-smoke` runs the new CLI in the backend with independent configured-reader SQL
verification. A host probe uses:

```sh
.venv/bin/python -m querypilot.cli smoke-test --backend-url http://127.0.0.1:18000
.venv/bin/python scripts/verify_demo_ui.py --backend-url http://127.0.0.1:18000
```

Smoke exit 0 requires system contract/readiness and all four acceptance references; failures
are nonzero with fixed stages. Host runs without `--verify-database` explicitly mark direct
DB verification SKIP/NOT VERIFIED. Use the flag inside the backend to avoid accidentally
comparing a different native database. The script verifies actual AppTest/HTTP evidence,
warnings/history/clear/outage behavior, but does not establish manual browser acceptance.
Follow [demo.md](demo.md) for the separate manual checklist and [deployment.md](deployment.md)
for security/hosting prerequisites.

New tests: 12 metadata/transport/credential/CLI unit cases and two real PostgreSQL smoke
cases forwarding in-process HTTP to the actual API/service/tools. They do not claim network
deployment verification; the independent Docker/AppTest operational runs supply that.
The configured full suite passed **470 tests**, including **56 PostgreSQL** and the original
50 required node IDs, with zero skips. Existing security/reliability suites are reused.
Measured coverage: **89.90% statements, 84.22% branches** across `src/querypilot`.
Current CI config collects these new tests and configures the smoke CLI for its image job;
Day 13 was pushed through 9ab3c07; its remote run is linked in progress.md.

## Day 12 CI parity and container prerequisites

Load the existing `.local/integration.env` and run `.venv/bin/python scripts/run_checks.py`
or `make ci`. It requires acknowledged distinct roles on a dedicated test target, runs all
tests under branch coverage, rejects any skipped/failed test in JUnit, verifies every
original PostgreSQL test ID and then runs doctor and the benchmark regression gate.
Coverage 7.17.2 is now an explicit locked development dependency; no temporary external
coverage path is needed. Existing package versions remain unchanged.

Native result: **456 passed, zero skipped**, including **54 PostgreSQL tests** and the full
original 50-case manifest. The 18 new tests cover setup/readiness, baseline identity and
case regressions, skip prevention and private configuration. Prior milestone counts below
are historical. Existing actual HTTP/Streamlit tests run in this full suite.

Docker tests use `compose.test.yaml` with the separate `querypilot_day12_test` project and
database. The follow-up verification on 2026-11-11 built both runtime images and verified
startup, all four workflows, benchmark gate, outage recovery, restart, persistence and
shutdown in the main isolated Compose stack. This does not claim the separate Docker test
profile or GitHub workflow ran. See [containers.md](containers.md) for commands and limits.
GitHub Actions is configured; remote execution has not occurred for these uncommitted files.

## Day 11 benchmark and tests

After native preparation and doctor verification, the normal ignored backend `.env`
supports the benchmark's real restricted reader. No HTTP server or OpenAI key is required
by this runner; it uses the same service that serves the HTTP endpoint.

```sh
.venv/bin/python -m querypilot.cli eval --mode mock --output reports/evaluation/day11
.venv/bin/python -m querypilot.cli eval --category documents --limit 1 --output reports/evaluation/doc-smoke
.venv/bin/python -m pytest -q tests/test_evaluation.py
set -a
source .local/integration.env
set +a
.venv/bin/python -m pytest -q tests/test_evaluation_postgres.py
.venv/bin/python -m pytest -q
```

The full benchmark returns 1 because **24/38** expectations pass; JSON and Markdown are
still generated. The one-case document smoke returns 0. A fixture mismatch fails safely
before SQL case execution; no migration/seed/reset is attempted. Correct the selected
reader target using the Day 10 setup guide rather than editing expected facts to fit it.

Final Day 11 configured suite: **438 passed, zero failed/skipped**, including **50 real
PostgreSQL cases** and existing real HTTP/UI smoke tests. New evaluation subset: 55 tests
(53 non-PostgreSQL, two PostgreSQL). Tests of failure metrics deliberately inject controlled
outcomes and are unit tests, distinct from the full real-tool benchmark. The original
Day 10 results below are historical. Definitions and exit codes: [evaluation.md](evaluation.md).

Coverage was measured with existing temporary external coverage 7.17.2, leaving project
dependencies unchanged. The executed equivalent after loading the integration environment:

```sh
PYTHONPATH=/private/tmp/querypilot-day10-coverage .venv/bin/python -m coverage run --branch --source=src/querypilot -m pytest -q --tb=short
PYTHONPATH=/private/tmp/querypilot-day10-coverage .venv/bin/python -m coverage json -o .local/day11-coverage.json
```

This external path is specific to this workstation; install coverage in an isolated
developer tooling location if reproducing elsewhere. Actual measured scope `src/querypilot`:
**92.1% statements, 85.1% branches, 90.6% combined**. Scripts/tests/third-party code excluded.
The project interpreter was repaired to Python 3.12.16 after its earlier temporary
installation lost standard-library files; no committed runtime path or dependency changed.

## Verified boundaries

| Category | Result and limits |
| --- | --- |
| Unit and protocol tests | Deterministic assertions; do not establish external service readiness |
| Mocked integration | MOCK PROVIDER VERIFIED / MOCK HTTP VERIFIED where provider or transport is replaced |
| PostgreSQL integration | REAL DATABASE VERIFIED: 48 cases, actual PostgreSQL, restricted reader and synthetic data |
| Local HTTP | MOCK PROVIDER VERIFIED + REAL DATABASE VERIFIED: actual TCP FastAPI requests, real tools |
| Streamlit | UI VERIFIED: isolated AppTest plus AppTest using actual HTTP and PostgreSQL; no manual browser review claimed |
| Live OpenAI | NOT VERIFIED: no paid requests, no inference about live selection or answer quality |

Full configured suite: **383 passed, zero failed/skipped**. Without integration variables:
**335 passed, 48 skipped**, explicitly identifying database prerequisites. Both runs emit
one existing Starlette TestClient/httpx deprecation warning. Coverage across
`src/querypilot` measured **90.9% statements**, **82.7% branches**, **89.1% combined**.
Tests, setup scripts and third-party code are outside that coverage scope. Coverage 7.17.2
was installed temporarily outside the project; no dependency or lockfile change was needed.

## Diagnosed failure

The normal backend had no configured `READER_DATABASE_URL`; `.env` was absent. The mock
provider selected `get_top_products` correctly, but configuration failed before any
connection. PostgreSQL was running, so downtime was not the root cause. Earlier temporary
verification supplied its own reader URL and did not establish normal-startup readiness.
After preparing local credentials, the already-running backend retained old settings and
required a restart. The original question then returned actual synthetic rankings.

The generic configuration error also incorrectly suggested model credentials in mock mode.
Missing reader settings now have a dedicated code and actionable frontend message.
A second regression suppressed payment analytics when a question included “handled”. The
mock selector now recognizes quantitative wording in the combined count/policy question.
Both defects received failing tests before their fixes; real provider behavior is unchanged.

## Repeatable native setup

Prerequisites: installed development dependencies and native PostgreSQL binaries (`initdb`,
`pg_ctl`, `psql`), discovered on PATH or in `/opt/homebrew/bin`. Docker was unavailable in
this environment; the existing PostgreSQL engine and Alembic infrastructure were used.
From the repository root:

```sh
.venv/bin/python scripts/prepare_local.py
.venv/bin/python -m querypilot.cli doctor --reference-date 2026-10-27
.venv/bin/uvicorn querypilot.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Run the backend in its own terminal. Restart an already-running backend after changing
environment configuration. The helper owns `.local/postgres`, listens on loopback port
55440 and creates separate `querypilot_local_dev` and `querypilot_local_test` databases.
It generates private credentials, applies existing migrations to empty databases, loads
the deterministic fixture (reference date 2026-10-27, seed 42), verifies accounting and
checks the restricted reader through the real analytics registry. An existing database
must already match the migration head and expected fixture; it is never reset.

The helper refuses unowned clusters and symlinked storage. Existing `.env` and generated
environment files are preserved. `.local/` and `.env` are ignored; credentials are private
local files, never values to paste into documentation or commit. Existing PostgreSQL
instances/databases on other ports are left untouched. The helper succeeded twice,
including repeat verification with existing data and preserved environment files.

## Doctor

```sh
.venv/bin/python -m querypilot.cli doctor --reference-date 2026-10-27 --backend-url http://127.0.0.1:8000
```

This invocation produced **10 PASS, 0 FAIL, 0 SKIP**: configuration, reader connection,
required tables, restricted role, seed presence, exact fixture, migration revision,
document corpus, mock selection readiness and backend capabilities. Doctor uses read-only
transactions; it does not migrate, seed, provision or call OpenAI. Migration metadata is
checked only through an explicitly configured setup URL targeting the same database.
Agent tools never use that writer URL. Missing prerequisites produce FAIL and dependent
SKIP checks; optional omitted checks are SKIP. `--json` provides machine-readable output.
Backend capabilities alone prove reachability, not successful SQL execution.

## Real integration suite

In another terminal, load the generated **test** environment:

```sh
set -a
source .local/integration.env
set +a
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/test_real_workflows.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
git diff --check
```

The workflow module passed **16 tests**. `postgres` selects database cases; `local_http`
selects the actual HTTP and UI-to-database checks. With no integration variables, database
tests skip rather than substituting SQLite or mocked rows.

Mutation fixtures require `TEST_DATABASE_URL`, `TEST_READER_DATABASE_URL`, and explicit
`QUERYPILOT_TEST_DATABASE_ACK=allow-isolated-schemas`. The target name must start
`querypilot_` and end `_test` or `_verify`; reader/writer targets must match and roles must
differ. Guard failures stop before fixture DDL. Existing migration/query tests create
UUID-named schemas and clean up only their own schema. Real workflow tests read the
verified deterministic fixture; the missing-schema regression owns a separate empty schema.

All five SQL tools are checked against independent fixture expectations. Existing tests
retain filtering, argument validation, empty results, injection resistance, rejected writes,
role audits, timeouts and cleanup. New real connection cases exercise wrong passwords,
nonexistent databases, unavailable ports and missing tables without exposing driver text.

Backend tests separately use in-process TestClient and actual TCP HTTP. The local HTTP
fixture binds an ephemeral loopback socket, starts the real FastAPI application and closes
its owned server at teardown. Streamlit AppTest uses the actual typed client against that
server; it does not replace HTTP or database results. The provider remains deterministic.

## Four actual workflows

| Question | Verified result |
| --- | --- |
| What is our return policy? | Document tool; 30 calendar days; `QP-RET-001#s002-c001` |
| What are our top five products by revenue? | SQL tool; product IDs 64, 35, 21, 76, 63; revenues 37882.39, 36509.32, 35946.86, 35386.60, 34591.86 |
| Which products generated the most revenue, and what is our refund policy? | SQL and document tools; separate evidence and valid citations |
| How many failed payments occurred, and how are failed payments handled? | 486 failed attempts from SQL; handling policy from `QP-PAY-003#s002-c001` |

These passed against both the isolated test backend and the repaired normal backend on
port 8000, with real tools and mock provider. AppTest through actual HTTP rendered eight
chat messages, three SQL tables and three document citations with zero exceptions; reruns
did not resubmit and clearing removed history. The existing UI on 8501 remained healthy.
Top-five output may still correctly carry a limited-selection notice because additional
products exist; that is distinct from the repaired retrieval failure.

## Safe errors and remaining limits

Fixed categories distinguish missing/invalid configuration, connection availability,
authentication, missing database, missing schema, permissions and timeout. Raw driver text,
URLs, SQL and credentials are not returned. Classification uses SQLSTATE when available,
with conservative internal matching for connection failures that lack SQLSTATE. See the
[PostgreSQL error-code reference](https://www.postgresql.org/docs/16/errcodes-appendix.html)
and [SQLAlchemy error documentation](https://docs.sqlalchemy.org/en/21/errors.html).

No live OpenAI, manual browser acceptance, public deployment or formal security audit was
performed. Existing grounding, credential-screening and cancellation limitations remain
documented in the agent and security guides. Day 11 evaluation work has not started.
