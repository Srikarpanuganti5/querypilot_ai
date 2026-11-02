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
Day 3 adds the PostgreSQL schema, migrations, explicit database transactions, a synthetic
dataset, developer queries, and verification. API startup and health remain independent
of the database. Day 4 adds five approved read-only analytics tools and a provider-neutral
registry. Day 5 adds local BM25 retrieval with citations as the sixth approved tool.
Day 6 adds the official OpenAI Responses adapter and one bounded tool batch plus a final
answer request, with mock verification. Day 7 adds bounded multi-step orchestration,
isolated state, repeated-call handling and context/time/tool limits. Live API validation
remains pending. Chat endpoints and the UI remain planned.

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

## Day 3 acceptance criteria

- Six related PostgreSQL tables, named constraints/indexes, UTC timestamps, Decimal money.
- Explicit engine/session configuration, bounded pooling, sanitized DB failures.
- Alembic initial migration; no automatic table creation.
- Reproducible seed: 500 customers, 100 products, 3,000 orders, approximately 6,000 items,
  applicable payment/refund scenarios with reconciled amounts and repeat-safe loading.
- PostgreSQL-only Compose configuration, optional distinct SELECT-only reader role.
- Database verifier, sample developer SQL, Mermaid ER diagram, documented accounting.
- Independent unit tests and clearly marked real PostgreSQL integration tests.
- Actual migration/seed/query/test results and unavailable checks reported honestly.
- No agent tools, LLM integration, UI, or new API routes. Wait for commit approval.

## Day 4 acceptance criteria

- Five approved analytics operations with validated inputs and typed, bounded outputs.
- No caller SQL, dynamic SQL identifiers, writer fallback, or customer personal fields.
- Dedicated reader credentials, per-call role checks, read-only transactions, DB timeouts.
- Accurate completed revenue, product contributions, refunds, customer and payment aggregates.
- Consistent safe errors and structured tool name/status/duration logs without arguments.
- Actual PostgreSQL integration tests for accounting, permissions, cancellation and recovery.
- Existing Day 1–3 behavior retained; documentation and real demonstrations recorded.
- No LLM, function calling, chat, or UI. Wait for commit approval and stop before Day 5.

## Day 5 acceptance criteria

- Ten synthetic Markdown policies with IDs, titles, categories and section headings.
- Safe bounded local ingestion, deterministic BM25 passage search and source citations.
- Sixth registry tool `search_business_documents`, independent of PostgreSQL.
- Validated query/category/top-k, sanitized errors/logs, untrusted-content handling.
- At least 15 relevance questions with measured Hit Rate@5 and MRR@5.
- CLI demonstrations, filesystem/retrieval tests and SQL/API regression checks.
- Updated architecture/setup/progress documentation with actual results and limits.
- No AI answers, embeddings, external search, model API, agent loop or frontend.
- Prepare focused changes, wait for commit approval, and stop before Day 6.

## Day 6 acceptance criteria

- Official async OpenAI SDK with environment-only key/model, bounded timeout and retries.
- All six function schemas derive from existing Pydantic registry definitions.
- One selection request, a bounded batch, and at most one tools-disabled follow-up.
- Correct call-ID correlation and complete stateless output/reasoning replay.
- Structured outcomes with bounded evidence, safe errors, citations and trace IDs.
- Deterministic mock CLI using real tools; explicit live mode with no fallback.
- Mocked SDK/protocol, grounding-reference, privacy and existing regression tests.
- No live-operational claim without approved actual API checks; no model key in logs.
- No Day 7 loop, new API endpoint, frontend or deployment; wait for commit approval.

## Day 7 acceptance criteria

- Multiple model/tool rounds, multiple calls per round, all six existing tools accessible.
- Configurable iteration, total/per-round call, duration, payload and context bounds.
- Request-local state with IDs, messages, evidence/citations, errors and elapsed time.
- Safe recovery from malformed/failed/empty calls, repeated-call suppression and deadlines.
- Original call IDs and full stateless replay, including reasoning, across every round.
- Grounded-reference checks and honest uncertainty; no semantic correctness guarantee.
- Mock/live CLI with optional traces, deterministic offline fixtures and no live fallback.
- Mock A–D demos with real tools, protocol/state/security and existing regressions verified.
- No new dependency, HTTP chat route, frontend, persistent memory or deployment.
- Live verification pending until approved requests succeed; wait for commit/push approval.
