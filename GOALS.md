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

These capabilities are planned; none is operational on Day 1.

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
