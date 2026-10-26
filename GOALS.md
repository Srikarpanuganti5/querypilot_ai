# Project goals

QueryPilot AI — Intelligent Data Agent will answer natural-language business questions
through approved tools and provide inspectable evidence. Example: “Which five products
generated the highest revenue last month?”

## Planned capabilities

- FastAPI backend with `/health` and `/api/v1/chat`.
- PostgreSQL schema and reproducible synthetic e-commerce data.
- Predefined, parameterized read-only SQL analytics tools.
- Document search with source attribution.
- Bounded multi-step OpenAI tool calling.
- Evidence-backed answers and tool execution traces.
- Input validation, sanitized errors, deadlines, and logging.
- Streamlit interface, automated tests, agent evaluations, Docker Compose, and CI.

Day 1 established the package foundation. Day 2 implements process health, API metadata,
documentation, environment configuration, JSON logging, CORS, and error handling.
Analytics, chat, database access, agent tools, and the UI remain planned.

## Quality and security

Use Python 3.12, type hints, separated responsibilities, reproducible setup, and focused
tests. All data must be synthetic and publicly shareable. Never execute arbitrary
model-generated SQL or give an agent administrative credentials. Keep secrets out of
source control. Treat retrieval as untrusted and bound tool execution.

## Day 1 acceptance criteria

- Installable src-layout package and intentional directory boundaries.
- Minimal development configuration, ignore rules, and environment template.
- Repository instructions, goals, roadmap, architecture, progress, and README.
- One package import smoke test.
- Structure, installation, smoke test, lint, and formatting validation recorded in progress.

No endpoints, database connections, tools, UI, Docker, or CI on Day 1.

## Day 2 acceptance criteria

- FastAPI starts with `uvicorn querypilot.main:app --reload`.
- `/health` and `/api/v1/info` return the specified metadata without external services.
- `/docs`, `/redoc`, and `/openapi.json` are accessible.
- Environment settings, explicit-origin CORS, sanitized JSON errors, and JSON logs work.
- Tests, lint, formatting, package imports, and actual local HTTP checks pass.
- Documentation reflects implemented behavior; Day 1 smoke test remains intact.
- No chat endpoint, database setup, LLM integration, or tools. Wait for commit approval.
