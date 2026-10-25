# Architecture

## Current state: Day 1

The repository contains an installable Python package, package boundaries, documentation,
and one import smoke test. No application, endpoint, database connection, LLM integration,
frontend, Docker configuration, or CI workflow is implemented.

## Planned request flow

```text
Streamlit (Day 9)
    → FastAPI routes
    → Business services / agent orchestration
    → Approved tools
        → Predefined analytics queries → restricted PostgreSQL reader
        → Document search → synthetic business documents
    → Evidence-backed response with tool execution traces
```

The model will choose among approved operations. Application code will validate arguments,
enforce limits, execute tools, and return results for response synthesis. Traces will
expose operations and evidence, not private model reasoning.

## Package responsibilities

| Directory | Intended responsibility |
| --- | --- |
| `src/querypilot/api/routes/` | HTTP routes and transport error mapping |
| `src/querypilot/agent/` | Bounded multi-step model/tool orchestration |
| `src/querypilot/tools/` | Approved analytics and document-search interfaces |
| `src/querypilot/db/` | Models, sessions, predefined parameterized queries |
| `src/querypilot/schemas/` | Pydantic request, response, tool-argument validation |
| `src/querypilot/services/` | Business workflows independent of HTTP |
| `src/querypilot/core/` | Environment configuration and shared infrastructure |
| `tests/` | Automated tests; one import smoke test on Day 1 |
| `data/sample/` | Small, publicly shareable synthetic fixtures |
| `docs/` | Architecture and milestone progress |

Dependencies should flow from routes to services/orchestration and tools to data access.
Database code must not depend on routes; orchestration should be testable with a fake
provider. Imports must not perform external I/O. The src layout requires installation
for package imports rather than relying on application code at the repository root.

## Technology and security

Python 3.12 is the baseline. Future milestones add FastAPI/Pydantic for HTTP and validation,
PostgreSQL/SQLAlchemy for persistence, OpenAI for tool calling, and Streamlit for the UI.
Pytest and Ruff are installed on Day 1; runtime libraries are added when used. Docker
Compose and GitHub Actions arrive later.

There will be no arbitrary SQL interface. Tools will accept validated business parameters
for code-owned queries. Agent credentials will be read-only and separate from setup
credentials. Secrets will come from environment variables. All data will be synthetic.
Retrieved content is untrusted and must not grant permissions. Iterations, timeouts,
and results will be bounded. Enforcement and security tests arrive with each feature.
