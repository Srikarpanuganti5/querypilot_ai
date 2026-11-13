# Final engineering verification — Day 14

Review date: **2026-11-12**. Starting tree was clean on `main` at **6135c17**, matching
`origin/main`; Days 10–13 are already committed. Day 14 is documentation/release preparation
with a local documentation validator. No runtime agent, SQL, schema, provider, dependency,
lockfile, benchmark label or baseline change is part of this review.

## Verification matrix

| Boundary | Actual latest result | Label |
| --- | --- | --- |
| Full native CI-equivalent runner | Exit 0; 470 passed, 0 failed, 0 skipped; 25.00 s | VERIFIED LOCALLY |
| Required real PostgreSQL tests | 56 passed; all original 50 required node IDs retained | REAL DATABASE VERIFIED |
| Coverage | 2591/2882 statements = 89.90%; 662/786 branches = 84.22%; combined 88.69% | VERIFIED LOCALLY |
| Docker backend and frontend builds | Both existing locked-runtime images built successfully | DOCKER VERIFIED |
| Private Compose profile | Config valid; setup exit 0; DB/backend/frontend healthy | DOCKER VERIFIED |
| Database setup | Migration 0001; six-table fixture and restricted reader verified | REAL DATABASE VERIFIED |
| Acceptance smoke | 8 required stages PASS, all four questions completed | MOCK PROVIDER VERIFIED + REAL DATABASE VERIFIED |
| Container gate | 38 cases; 24 protected passes; 14 known failures; 0 regressions | MOCK PROVIDER VERIFIED |
| Automated UI through actual HTTP | 4 workflows, 8 messages, 3 SQL tables, 3 document citations; rerun/clear/outage checks pass | VERIFIED LOCALLY; NOT MANUAL |
| Published CI baseline | Both jobs passed at 6135c17, run 43165208641 | CI REMOTE VERIFIED for Day 13 |
| Day 14 remote CI at initial review | No publication had occurred; Git publication approved 2026-11-13 | Check actual new run after push |
| Manual graphical browser | No graphical interaction tool available; checklist remains open | NOT VERIFIED |
| Live OpenAI / semantic faithfulness / load capacity | No paid requests, judge or load testing performed | NOT VERIFIED / NOT EVALUATED |
| Public deployment / media launch | No public resource, recording, screenshots or upload created | NOT VERIFIED / NOT PERFORMED |

The full suite includes existing API/provider/security/citation/cancellation/evaluation/report
regressions and real HTTP/UI workflows. One existing Starlette TestClient/httpx deprecation
warning remains. Coverage scope is `src/querypilot`; scripts/tests and third-party libraries
are excluded. No exclusion was added to inflate coverage. The direct container doctor has
8 PASS, 0 FAIL, 2 optional SKIP (writer migration URL and omitted backend URL); these are
not skipped tests. Setup independently checks migration head; smoke checks actual backend HTTP.

## Commands and actual outcomes

The full runner used the acknowledged private `.local/integration.env` in the process
environment, without printing values. The equivalent operator command is:

```sh
set -a
source .local/integration.env
set +a
.venv/bin/python scripts/run_checks.py
```

Exit **0**. This runs Ruff, the complete suite under branch coverage, JUnit mandatory-DB/skip
checks, coverage reports, doctor and the real-tool regression gate. Outputs remain ignored
in `.local/day14-ci.log`, `.local/ci-results.xml`, `.local/ci-coverage.json` and
`reports/evaluation/gate/`. The benchmark is separate from the 470-test software suite.

Docker was initially unavailable (daemon socket absent). Starting Docker Desktop was
approved; daemon **29.9.3** became reachable. Ran, with exit **0**:

```sh
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml config --quiet
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml build
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml up --no-build --wait --wait-timeout 180
make demo-smoke
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml exec -T backend python -m querypilot.evaluation.gate --output /tmp/day14-gate
docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml exec -T backend python -m querypilot.cli doctor --reference-date 2026-10-27 --json
.venv/bin/python scripts/verify_demo_ui.py --backend-url http://127.0.0.1:18000
.venv/bin/python scripts/check_compose_logs.py
```

The raw `querypilot.cli eval --mode mock --output /tmp/day14-eval` was also executed inside
the backend. Exit **1** is expected: **24/38 pass, 14 fail**, with reports written. The gate
exit **0** protects all 24 passing cases and preserves all failures. Source/reference hashes
remain unchanged; see [failure analysis](benchmark-backlog.md).

## Four containerized workflows and independent SQL

| Workflow | Actual result | Partial flag | HTTP time in the direct smoke |
| --- | --- | --- | ---: |
| Return policy | BM25 passage and `QP-RET-001#s002-c001`; 30-calendar-day fact | false | 16.479 ms |
| Top-five revenue | Approved SQL; expected ordered product IDs/revenues | true, selected records | 36.982 ms |
| Revenue plus refund policy | SQL and document evidence retained, valid sources | true, selected records | 29.586 ms |
| Failed payments plus handling | Payment SQL count and separate policy source | false | 27.159 ms |

The smoke verifies the exact fixture with the configured restricted reader, runs independent
fixed SELECTs and compares those with API evidence. A separate direct SQL query against the
containerized database rechecks migration and numeric values; no count is hardcoded into a
query. Current failed attempts: **486**. Top product IDs/revenues in USD:
**64/37882.39, 35/36509.32, 21/35946.86, 76/35386.60, 63/34591.86**.
These values belong to the pinned fixture, not every database or month.

Fixture reference **2026-10-27**, seed **42**; six-table counts: 500 customers, 100 products,
3000 orders, 6000 order_items, 3006 payments, 120 refunds. Exact SHA256:
`afbca1f4dbdbbb4b40913ebe417948641b26c2852447189b7cb5dacf0750d0e7`.
Dataset version `agent-v1.0`, SHA256
`fda07773f85c4d8e77f37504dce8884167ebdf913d9f4ca9ffc5598f30c09d29`.

The smoke function took **404.519 ms** excluding Python startup/import; per-question times
include HTTP/service work. These are single-run local mock observations, not load/production
performance or speedup claims. Day 13's 17.28-second startup and 365.96-ms smoke are historical
measurements and are not reused as today's timings.

AppTest ran actual frontend code on the host through container backend HTTP and real tools.
It verified mock labeling, evidence/table/citation rendering, selected-record warnings,
history across reruns, clear and unreachable-backend messaging. This is not a graphical
session with the container Streamlit WebSocket UI. No screenshot/recording was fabricated.
Complete the [manual checklist](demo.md#manual-browser-acceptance--not-verified) separately.

## Review findings and security boundaries

The initial documentation audit found outdated planned-feature wording, an absent proposed
chat route, obsolete Docker/CI limitations, unnecessary reference-rebuild setup steps and
conflicting historical test counts. Current guides now identify actual APIs/commands and
separate historical measurements. No missing local Markdown targets were found before edits.
No duplicate application implementation was removed and no user files/data were deleted.

Release review checks public tracked/new files, generated evaluation reports and ignored
credential boundaries, alongside actual non-root/private-port/reader-only container policies.
The bounded Compose log credential scan passed. Public-file screening reviewed **155**
tracked/new nonignored files with no configured-private-value or high-confidence key
pattern findings. The first generated report/log pass reviewed **16** files; the additional
container evaluation JSON was separately parsed and screened. Intentional documentation
USER/ENCODED_PASSWORD placeholders are not real credentials. Ignore checks confirmed
`.env`, `.env.docker`, `.local/` outputs and evaluation reports are excluded.

Actual container inspection confirmed healthy app services, UID/GID 10001, read-only app
roots, dropped capabilities, no privilege escalation, no privileged/socket mounts, loopback
application ports and no host DB port. The backend has no writer URL or OpenAI key. Recent
logs contained zero checked error/traceback/fatal markers; this bounded marker check is
not proof that every possible error string is absent.

Local documentation validation checked **24** Markdown files for relative targets, GitHub-style
heading fragments and balanced fences, with no failures. Isolated positive/negative probes
confirmed missing targets/anchors and broken fences are rejected. This does not test remote
URLs or render Mermaid diagrams. Ruff lint passed and format reported **134 files already
formatted**. Actionlint and `git diff --check` passed. No staged files or commits were created. No real private business data is used.
The scan is scoped pattern/configured-value screening, not proof of an exhaustive history
scan, a formal audit or immunity to all leakage. The old dependency advisory result in the
security guide is historical; no new dependency/OS vulnerability audit is claimed.

The API has no authentication/authorization or per-user rate limiting. Its host bindings
are loopback, with no published PostgreSQL port. Public exposure remains blocked pending
access control, HTTPS/WSS, protected diagnostics, monitoring, backup/recovery and operational
review. Existing credential screening, safe logging, reader permissions and execution limits
remain enforced. See [security.md](security.md).

## Remote and release boundary

Read-only `gh run view 43165208641` confirmed both jobs succeeded at exactly `6135c17`:
[remote evidence](https://github.com/Srikarpanuganti5/querypilot_ai/actions/runs/43165208641).
No new workflow dispatch, commit, push, release tag, image publication or deployment was
performed during Day 14. Current local documentation cannot be called remotely verified.
Pinned actions have a known nonblocking Node.js 20 deprecation annotation; modernization
is future maintenance, not a silently changed dependency in this review.

The private stack is left healthy at 18000/18501 for manual browser acceptance. Stop with
`make demo-down` when finished; never add `-v`. Its existing volume and unrelated containers,
volumes and native databases are preserved. The separate full Docker test profile is a
supported command; this review ran the full suite natively and runtime acceptance in Docker,
not a separate claim that the Docker test profile ran today.

Pending release work: manual browser review, genuine screenshots/video, user review of
portfolio/launch drafts and explicit Git approval followed by CI on the approved publication.
Live model and semantic-quality verification require separately approved work/budget.

## Publication follow-up — 2026-11-13

The user approved focused Day 14 commits and push to the existing GitHub repository.
Documentation links/anchors/fences, Ruff lint/format, actionlint and whitespace checks
were repeated successfully before publication. Existing local full-suite/Docker results
above retain their 2026-11-12 measurement date; GitHub will rerun the complete quality and
image checks after the approved push. Review the new workflow result for its exact commit.
No release tag, paid request, public deployment or launch-content upload is authorized.
