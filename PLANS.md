# Development roadmap

Days 1–9 are implemented and pushed. Day 10 diagnoses SQL setup, adds safe readiness
checks and repeatable local dev/test preparation, and automates actual PostgreSQL/HTTP/UI
verification. Results are recorded in docs/progress.md. Live OpenAI behavior remains
separately pending. The user has approved Day 10 commits and push to the existing repository.
The master brief ended during Day 6; the remaining sequence is proposed and respects
the requested Day 9 interface and later Docker/CI milestones.

| Day | Scope | Intended validation |
| --- | --- | --- |
| 1 | Foundation, specifications, docs, import smoke test | Install, import, Pytest, Ruff, tree |
| 2 | FastAPI, `/health`, `/api/v1/info`, config, errors, logging, CORS | 24 tests and local HTTP checks passed |
| 3 | Six-table schema, Alembic, synthetic data, verifier, PostgreSQL-only Compose | Native PostgreSQL migration/seed/accounting and regression tests; see progress |
| 4 | Five validated analytics operations, registry, CLI, reader role audit and timeouts | Accounting, rejection, privacy, bounds, actual PostgreSQL permission/timeout tests |
| 5 | Ten policies, safe ingestion, BM25, sixth tool and citations | Filesystem/retrieval tests, 20-question metrics, SQL/API regressions |
| 6 | Async SDK, six strict schemas, one tool batch/follow-up, evidence bounds, CLI | Mocked SDK/protocol/error/grounding tests; actual API checks remain opt-in |
| 7 | Bounded multi-step orchestration, state, traces and CLI | Mock A–D demos, SDK replay, limits/recovery/isolation and regressions |
| 8 | Credential/trust boundaries, cancellation, budgets, evidence integrity and telemetry | Adversarial and prior SQL/API/provider/search regressions; dependency advisory check |
| 9 | Local Streamlit chat and safe agent HTTP integration | API/client/AppTest, startup and actual mock HTTP/database demonstrations |
| 10 | Completed real integration coverage, SQL diagnostics and local readiness | 383 passed; 48 real PostgreSQL cases; actual HTTP/UI workflows; live OpenAI unverified |
| 11 | Agent evaluations | Tool choice, factual support, injection scenarios |
| 12 | Docker Compose | Startup and restricted credentials |
| 13 | GitHub Actions and deployment docs | CI and reproducible setup |
| 14 | Portfolio review and demonstration | Acceptance review and documented limitations |

## Day 1 plan

1. Review existing files and remove implementation beyond Day 1.
2. Establish packages and sample-data/documentation directories.
3. Configure packaging, Pytest, Ruff, ignore rules, and the environment template.
4. Document vision, architecture, security requirements, roadmap, and setup.
5. Install/synchronize development dependencies and run the one smoke test and checks.
6. Record actual results, show the final tree, and stop.

## Day 2 completion

FastAPI, Pydantic, Pydantic Settings, Uvicorn, and a development-only HTTP client are
configured. The application exposes health, versioned info, and generated documentation.
It uses validated environment settings, explicit CORS origins, sanitized errors, request
IDs, and structured logs. The Day 1 test remains unchanged. See docs/progress.md for
actual verification results. Approval to commit and push Day 2 has now been received.

## Day 3 implementation and review groups

1. Schema/migrations: SQLAlchemy models, database settings/sessions, initial Alembic DDL.
2. Synthetic data/verification: reproducible generator, repeat-safe loader, accounting
   verifier, example queries, and independent/PostgreSQL tests.
3. Development setup/docs: PostgreSQL-only Compose, reader-role SQL, environment template,
   ER diagram, accounting contract, instructions and actual progress.

Keep these as focused commit groups, in line with the user's preference. The user has
now explicitly approved committing and pushing Day 3.

## Day 4 implementation and review groups

1. Analytics contracts and queries: typed schemas, fixed SELECT builders, role audit and
   safe timeout classification in the existing session layer.
2. Registry, developer CLI, structured logging fields and unit/PostgreSQL security tests.
3. Tool contracts, setup/accounting guidance, architecture, roadmap and actual progress.

The user has approved committing and pushing Day 4. Keep these as focused commits.

## Day 5 review groups

1. Corpus/ingestion: ten policies, literal metadata, bounded sections, safe local loading,
   BM25 index and typed search schemas.
2. Registry/evaluation/tests: sixth operation, lazy resources, CLI, 20-question relevance
   set, measured metrics and safety/regression tests.
3. Documentation: categories, accounting consistency, filesystem trust, index lifecycle,
   evaluation limits, architecture and actual progress.

The user has now approved committing and pushing Day 5. Keep the commit groups focused.

## Day 6 implementation and review groups

1. Provider/schemas: official SDK, configuration/retry/deadline adapter, synchronized strict
   function schemas and structured execution contracts.
2. Orchestration/tests/CLI: one batch plus one follow-up, protocol replay, bounded evidence,
   citation/numeric checks, deterministic mock mode and mocked SDK tests.
3. Documentation: configuration, live opt-in, security/grounding limits, actual results.

The user has now approved committing and pushing Day 6, requesting more than four commits
where meaningful. Split the implementation into provider/configuration, contracts/evidence,
orchestration/CLI, tests, and documentation commits.

## Day 7 implementation and review groups

1. Configuration/state: validated hard limits, bounded execution contracts, ephemeral state.
2. Loop/evidence: multi-round provider replay, sequential registry execution, recovery,
   repeated-call suppression, deadlines, context/evidence caps and citation checks.
3. CLI/mock: public querypilot.cli entry point, compatible tools ask, deterministic mock
   fixtures, trace option and execution-limit overrides.
4. Tests: loop/state/recovery/security/CLI and official SDK multi-round protocol contracts.
5. Documentation: setup, architecture, safety/grounding limits and actual verification.

No new dependency or schema migration is needed. Preserve existing SQL privileges,
retrieval, APIs and Day 6 single-round behavior. The user has now approved committing/pushing Day 7 in focused groups. Day 8 starts only after a separate request and covers advanced
guardrails and reliability; no frontend, persistent memory or deployment is included today.

## Day 8 implementation and review groups

1. Credential/trust boundaries: configured-secret and credential-pattern screening,
   safe provider error catalog, log filtering and private-output handling.
2. Reliability: retained/drained synchronous workers, cancellation propagation,
   resource cleanup and safe terminal/error telemetry.
3. Budgets/evidence: message-count reservation, raw input bounds, provenance validation,
   scoped conflict detection and explicit partial-result metadata/notices.
4. Tests: deterministic adversarial fixtures, event-driven cancellation and retained
   Day 6/7, SQL, API and BM25 regressions; temporary dependency advisory tooling.
5. Documentation: threat model, limitations, actual results and Day 9 preparation.

No new project dependency is needed. The user has now explicitly approved
Day 8 commits/push in six focused groups: credential safety, contracts, execution,
CLI, tests and documentation. Day 9, after a separate request, adds the Streamlit interface using
the established safe outcomes, tool summaries and partial/limitation indicators.

## Day 9 implementation and review groups

1. API/service contracts: shared lifecycle, safe ask/capabilities endpoints, public trace
   projection, bounded request bodies, live HTTP opt-in and GET/POST CORS.
2. Frontend/client: Streamlit chat, server-only execution, typed bounded HTTP transport,
   fixed diagnostics, session history, evidence/metadata rendering and restrained theme.
3. Tests: API validation/security, client protocol/error paths, Streamlit AppTest and
   four real mock UI→HTTP→PostgreSQL/document demonstrations; preserve old regressions.
4. Documentation: exact startup/setup, dependencies, local-only boundaries, actual results.

Streamlit is the sole new direct dependency. HTTPX moves from dev-only to runtime for
the frontend client; no additional HTTP library is needed. Prepare focused commits and
push after the user’s explicit Day 9 approval, now received. No persistent memory,
public hosting or Day 10 infrastructure is added.

## Day 10 implementation and review groups

1. Diagnostics/selector fixes: specific safe database failure categories, actionable UI
   advice and quantitative-plus-policy mock dispatch, each backed by regressions.
2. Local prerequisites: owned native PostgreSQL preparation, preserved private configuration,
   distinct synthetic dev/test databases and a read-only doctor command.
3. Integration safety: explicit mutation acknowledgement, dedicated database validation,
   UUID schema cleanup and consistent writer/reader targets.
4. Real verification: all five SQL tools against an independent seed oracle, actual
   FastAPI/shared service, real TCP HTTP and Streamlit smoke scenarios.
5. Documentation: verified matrix, exact setup/doctor/testing commands, actual coverage
   scope and limits. Prepare focused commits; wait for approval before committing/pushing.

Day 11 preview is Agent Evaluation & Performance Metrics; no evaluation/benchmark
framework or optimization work is included in Day 10.
