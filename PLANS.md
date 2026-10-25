# Development roadmap

Only Day 1 is authorized in this task. Each later milestone needs a new request.
The master brief ended during Day 6; the remaining sequence is proposed and respects
the requested Day 9 interface and later Docker/CI milestones.

| Day | Scope | Intended validation |
| --- | --- | --- |
| 1 | Foundation, specifications, docs, import smoke test | Install, import, Pytest, Ruff, tree |
| 2 | FastAPI application and `/health` | Endpoint tests without PostgreSQL or LLM calls |
| 3 | PostgreSQL schema and synthetic e-commerce data | Constraints and repeatable seeding |
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

## Day 2 boundary

After a separate request, add FastAPI, Pydantic, and Uvicorn with dependency explanations.
Build a minimal application and `/health`; add endpoint tests and a test HTTP client
if needed. Keep PostgreSQL for Day 3, OpenAI for Day 6, and Streamlit for Day 9.
