# Development roadmap

Days 1–3 are implemented and pushed. Day 4 adds the approved analytics registry and
restricted PostgreSQL execution; verification results are recorded in docs/progress.md.
Docker container startup remains pending because the daemon is unavailable. Day 4 changes
have explicit commit/push approval from the user's follow-up. Day 5 and later milestones need a new request.
The master brief ended during Day 6; the remaining sequence is proposed and respects
the requested Day 9 interface and later Docker/CI milestones.

| Day | Scope | Intended validation |
| --- | --- | --- |
| 1 | Foundation, specifications, docs, import smoke test | Install, import, Pytest, Ruff, tree |
| 2 | FastAPI, `/health`, `/api/v1/info`, config, errors, logging, CORS | 24 tests and local HTTP checks passed |
| 3 | Six-table schema, Alembic, synthetic data, verifier, PostgreSQL-only Compose | Native PostgreSQL migration/seed/accounting and regression tests; see progress |
| 4 | Five validated analytics operations, registry, CLI, reader role audit and timeouts | Accounting, rejection, privacy, bounds, actual PostgreSQL permission/timeout tests |
| 5 | Document search and sources | Relevant retrieval and bounded excerpts |
| 6 | OpenAI integration and tool schemas | Mocked protocol tests; opt-in live checks |
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

## Day 5 preparation

After a separate request, add document search over synthetic business documents with
bounded excerpts and source identifiers. Treat retrieved text as untrusted. No document
search, LLM/provider integration, or UI is included in Day 4.
