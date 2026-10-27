# Development roadmap

Days 1 and 2 are implemented and pushed. Day 3 database implementation is present and
verified against native PostgreSQL; Docker container startup remains unverified because
the Docker daemon is unavailable. The user has approved focused Day 3 commits and a push. Day 4 and later
milestones require a new request; no agent implementation has begun.
The master brief ended during Day 6; the remaining sequence is proposed and respects
the requested Day 9 interface and later Docker/CI milestones.

| Day | Scope | Intended validation |
| --- | --- | --- |
| 1 | Foundation, specifications, docs, import smoke test | Install, import, Pytest, Ruff, tree |
| 2 | FastAPI, `/health`, `/api/v1/info`, config, errors, logging, CORS | 24 tests and local HTTP checks passed |
| 3 | Six-table schema, Alembic, synthetic data, verifier, PostgreSQL-only Compose | Native PostgreSQL migration/seed/accounting and regression tests; see progress |
| 4 | Restricted predefined SQL tools | Totals, arguments, write denial |
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

## Day 4 prerequisites

After a separate request, introduce approved parameterized read-only analytics operations
using the separate reader role. Use the documented completed-order revenue definition,
validate time windows and result limits, and test privilege denials and execution bounds.
