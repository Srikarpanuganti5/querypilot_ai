# QueryPilot AI — developer handoff

This guide is sufficient to begin without the original development conversation.
Review date: **2026-11-12**. Source:
[Srikarpanuganti5/querypilot_ai](https://github.com/Srikarpanuganti5/querypilot_ai).
The private mock demo uses real tools and synthetic data. Live OpenAI, manual browser
acceptance and public deployment are not verified.

## System and capabilities

A Streamlit UI sends independent questions to FastAPI. The shared request service owns
an isolated, bounded agent loop and approved tool registry. Five parameterized SQL tools
read PostgreSQL; a sixth searches local policy documents using BM25. The response includes
typed evidence, citations, safe execution traces and partial-result notices. UI history
is display-only. No persistent agent memory exists. See [architecture](architecture.md)
for request/evidence and deployment diagrams and package boundaries.

Python 3.12, FastAPI, Pydantic/Settings, Uvicorn, PostgreSQL 16, SQLAlchemy, Psycopg,
Alembic, OpenAI SDK, HTTPX and Streamlit provide runtime capabilities. Pytest, Ruff and
coverage are development tooling; uv locks dependencies; Docker Compose and GitHub Actions
exercise deployment/quality checks. No new dependency was introduced in Day 14.

## First-time private Docker setup

Install Git, Python 3.12, uv, Docker with Compose and Make. Run on a POSIX development
host; document loading requires POSIX safety support. Clone and work from the repository
root so relative corpus/migration paths resolve. This is a trusted local demo.

```sh
git clone https://github.com/Srikarpanuganti5/querypilot_ai.git
cd querypilot_ai
uv sync --python 3.12 --extra dev --locked
.venv/bin/python scripts/prepare_docker.py
make demo-up
make demo-smoke
```

No OpenAI key is needed. The helper creates private mode-0600 `.env.docker` with generated
setup/reader credentials and preserves it on repeat runs. Never commit, paste or screen-share
that file. The Compose setup job applies migration `0001` to an empty schema, seeds the
fixture (reference 2026-10-27, seed 42) and verifies the reader and corpus. Existing mismatches
are refused, never reset. Do not manually run competing schema SQL or `create_all`.

Streamlit: http://127.0.0.1:18501. FastAPI docs: http://127.0.0.1:18000/docs.
PostgreSQL is internal only. Host port overrides are `QP_BACKEND_PORT` and
`QP_FRONTEND_PORT` in `.env.docker`; Compose-only `QP_DEMO_API_ORIGIN` defaults to
`http://backend:8000`. Application settings use existing names in [.env.example](../.env.example).
Do not dump resolved Compose config, which contains credentials.

The namespace remains `querypilot_day12`; its volume is `querypilot_day12_postgres_data`.
The private profile adds resource/log bounds to the existing architecture. The separate
`querypilot_day12_test` namespace is reserved for tests. Neither uses native development data.

## Repeatable operations and permission checks

```sh
# Both image builds and bounded startup:
make demo-up
# Process liveness vs prerequisite readiness:
curl --fail http://127.0.0.1:18000/health
curl --fail http://127.0.0.1:18000/ready
# Doctor verifies restricted reader/table/corpus readiness without writes:
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml exec -T backend python -m querypilot.cli doctor --reference-date 2026-10-27
# Four acceptance questions + exact fixture + independent reader SELECTs:
make demo-smoke
# Automated UI -> actual backend HTTP -> real tools:
.venv/bin/python scripts/verify_demo_ui.py --backend-url http://127.0.0.1:18000
# Logs screened in memory; no raw credential-bearing output:
.venv/bin/python scripts/check_compose_logs.py
# Graceful shutdown; data retained:
make demo-down
```

Doctor's optional writer-migration check can SKIP in the reader-only backend; this is
expected credential isolation. Setup separately checks revision head and exact fixture.
The SELECT-only audit checks ownership, memberships, write/schema/TEMP privileges and
required table SELECTs. Tests prove write rejection with actual PostgreSQL. Provisioning
details: [database guide](database.md#read-only-role-provisioning).

For manual browser acceptance, follow every item in [demo.md](demo.md), recording browser,
date and pass/fail. Automated AppTest cannot certify a graphical WebSocket session.
No screenshot/video currently exists. Use mock mode and synthetic questions only.

## Tests and local CI parity

The full Docker test target installs locked development tools and runs Ruff, all tests,
coverage, JUnit skip/original-DB-case enforcement, doctor and the regression gate:

```sh
make docker-test
docker compose --env-file .env.docker -p querypilot_day12_test -f compose.yaml -f compose.test.yaml down --timeout 40
```

For native parity, install PostgreSQL server binaries and prepare the owned cluster:

```sh
.venv/bin/python scripts/prepare_local.py
set -a
source .local/integration.env
set +a
.venv/bin/python scripts/run_checks.py
```

Preparation uses an owned `.local/postgres` cluster on loopback 55440 and separate
synthetic dev/test databases; existing configuration/data is preserved. Integration tests
require `TEST_DATABASE_URL`, distinct matching `TEST_READER_DATABASE_URL`, a dedicated
`querypilot_*_test`/`*_verify` database and acknowledgement
`QUERYPILOT_TEST_DATABASE_ACK=allow-isolated-schemas`. Only owned temporary schemas/setup
test resources are cleaned up. Bare pytest without configuration skips DB cases; full CI
explicitly rejects skips and enforces the original 50 node IDs. [Testing](testing.md).

Check documentation after edits with `.venv/bin/python scripts/check_docs.py`.
Other standalone checks: `.venv/bin/python -m ruff check .`,
`.venv/bin/python -m ruff format --check .`, `git diff --check`.

## Benchmark and regression policy

With the demo up:

```sh
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml exec -T backend python -m querypilot.cli eval --mode mock --output /tmp/handoff-eval
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml exec -T backend python -m querypilot.evaluation.gate --output /tmp/handoff-gate
```

The raw benchmark exits **1** when expectations fail; reports are still written. The gate
exits **0** if all reviewed passing cases remain passing with matching identity. Current
result is **24/38**; all 14 known failures remain visible. Do not change labels, mock plans
or baselines to inflate the score. `/tmp` container reports are ephemeral. Host reports
belong under ignored `reports/evaluation/` or `.local/`, never tracked private data.
[Metric definitions](evaluation.md) · [All failures and next-work priorities](benchmark-backlog.md).

## Verified state and limitations

Latest local automated suite: **470 passed, 0 failed, 0 skipped**, including **56 real
PostgreSQL cases**. Statement coverage **89.90%**, branch coverage **84.22%**. Four real-tool
mock acceptance workflows, Docker builds/readiness and the 24-protected-case gate pass.
Exact commands/results and commit boundaries: [final verification](final-verification.md).
Historical Day 13 startup/latency numbers are snapshots, not production performance claims.

The latest published baseline is `6135c17`; both jobs passed in
[remote run 43165208641](https://github.com/Srikarpanuganti5/querypilot_ai/actions/runs/43165208641).
Day 14 Git publication was approved on 2026-11-13; check the actual new CI run after
pushing. No release tag is authorized. No public URL,
cloud resources, published container images, LinkedIn post or paid model run was created.

Public access is blocked pending authentication, authorization, rate limiting, HTTPS/WSS,
protected diagnostics, monitoring/alerts, backups and operator review. CORS is not access
control. Threads cannot be forcibly stopped; cleanup may exceed await deadlines. Citation
membership/numeric checks are not semantic proof. There is no verified live LLM accuracy,
concurrent-user capacity or manual browser acceptance. [Security](security.md).

## Recovery and next steps

If liveness succeeds but readiness fails, check reader configuration, role permissions,
schema/fixture and documents with doctor. The normal-startup issue was absent reader
configuration, not server downtime. Restart native backend processes after configuration
changes. Restore matching private credentials; changing an environment password alone does
not rotate the persisted DB role. Never erase a volume to bypass a mismatch.

After a DB outage, restore only this stack with `make demo-up`, recheck `/ready` and run
`make demo-smoke`. Frontend process health does not prove backend chat works. Do not
switch to fabricated SQL evidence or remove partial warnings to make a demo look healthy.

Next work should start with the documented routing/filter/abstention backlog, independent
semantic evaluation and approved live verification. Complete manual browser acceptance
and capture genuine demo assets. Review portfolio/LinkedIn drafts with the user. Git publication was approved on 2026-11-13. Separate approval remains required for
release tagging, paid calls, deployment or posting.

## Proposed Git review groups

Days 10–13 are already committed; do not recommit or rewrite that history. The initial
Day 14 tree was clean. Suggested focused groups for the new local work:

1. README, architecture diagrams and documentation navigation.
2. Benchmark failure analysis and current operational/security guidance.
3. Documentation validator and final verification records.
4. Portfolio, interview and unpublished launch assets.
5. Final handoff and milestone goals/plans/progress.

Before approval: review the entire diff, scan tracked/new reports for secrets, exclude
private/generated files and stage only intended content. No commit/push/tag is performed
automatically during Day 14. After an approved push, check actual CI for that exact commit.
