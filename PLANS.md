# Development roadmap

Days 1–5 are implemented and pushed. Day 6 adds the direct Responses API adapter,
single-round tool batch/follow-up service and mock/live CLI. Mock/protocol tests are
verified; live API behavior remains pending credentials and explicit usage approval.
The user has approved five focused Day 6 commits and a push. Day 7 and later need a separate request.
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
| 7 | Multi-step orchestration and traces | Loop bounds and evidence propagation |
| 8 | Validation, errors, timeouts, logging | Failure-path and security tests |
| 9 | Streamlit interface | Chat and evidence display |
| 10 | Broader automated tests | API, tool, and database integration coverage |
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

## Day 7 prerequisites

After a separate request, extend the single-round service into explicitly bounded multi-step
orchestration while preserving read-only privileges, budgets, safe logging and source
provenance. Verify the live adapter with approved API access before making live-operational
claims. No autonomous loop is part of Day 6.
