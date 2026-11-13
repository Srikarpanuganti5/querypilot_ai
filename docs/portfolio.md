# QueryPilot AI — SDE portfolio and interview preparation

Draft material for review. Metrics were rechecked locally on 2026-11-12; see
[verification](final-verification.md). This is a synthetic-data, private Docker demo with
mock-provider acceptance, not a public production service or a verified live model.

## Project summary

QueryPilot AI is a Python/FastAPI business analytics application that connects a bounded
tool-using agent to PostgreSQL analytics and BM25 policy retrieval. The backend validates
approved operations, enforces read-only access and returns inspectable evidence to a
Streamlit interface. The project includes Alembic migrations, deterministic fixtures,
real database/HTTP tests, Docker Compose, GitHub Actions and a case-level evaluation gate.

Source: [Srikarpanuganti5/querypilot_ai](https://github.com/Srikarpanuganti5/querypilot_ai).
Use this summary for a portfolio, application or LinkedIn Featured description with a
source link. A recording has not been captured and no public demo is hosted.

## Three resume bullets

- Built a modular Python/FastAPI REST backend integrating PostgreSQL, SQLAlchemy and
  Alembic, with five parameterized analytics tools, reproducible synthetic fixtures and
  separate setup/SELECT-only database credentials.
- Implemented bounded multi-step tool orchestration and BM25 policy retrieval with typed
  argument/evidence validation, citation provenance checks, execution limits and safe
  failure handling, exposed through a Streamlit interface.
- Validated the system with 470 automated tests, including 56 real PostgreSQL cases,
  89.90% statement coverage and Docker/GitHub Actions checks; added a 38-case mock-provider
  benchmark with 24 protected passes and 14 documented failures.

These describe software verification, not production usage, live LLM accuracy, throughput
or an invented business/latency improvement. Recheck counts before using the bullets later.

## 30-second explanation

“I built QueryPilot AI to explore the backend engineering behind a business analytics
agent. FastAPI routes questions through a bounded tool loop to approved PostgreSQL queries
or policy search, then returns evidence to Streamlit. I focused on read-only database
access, failure handling and repeatable tests. The private demo uses a mock selector with
real tools; live OpenAI quality is still unverified.”

## 90-second explanation

“An analytics question can require both transaction data and policy text. QueryPilot uses
FastAPI for the API, PostgreSQL for synthetic business data, and BM25 for policy passages.
The agent chooses from six approved tools. It cannot submit arbitrary SQL, and each request
gets isolated state, call limits and deadlines.

The frontend displays rows, citations and limitations. I tested the actual boundaries:
reader permissions, migrations, HTTP requests, UI behavior and Docker startup. One real
failure was that the normal backend had no reader configuration even though separately
configured tests worked. Readiness diagnostics and reproducible setup made that distinction
visible.

The suite passes 470 tests, including 56 PostgreSQL tests. A separate mock benchmark passes
24 of 38 cases; its routing and abstention failures remain visible and protected passes
cannot silently regress. Live model and manual browser verification remain pending.”

## 2–3 minute technical explanation

Start with a concrete question: “Which products generated the most revenue, and what is
our refund policy?” Explain that Streamlit sends one independent request to FastAPI; UI
history is display-only. The shared service owns the provider and registry for that request
and closes resources after execution.

Walk through the bounded loop. The provider proposes a function name and JSON arguments.
The application checks its allowlist, schemas and remaining budget before dispatch. SQL
comes from fixed SQLAlchemy queries with bound values and a restricted reader transaction.
Document retrieval uses approved local Markdown with exact chunk citations and treats
retrieved passages as untrusted data. Evidence returns to the agent for subsequent rounds.
The response boundary checks references, numeric membership and source provenance, then
projects safe traces and partial-result notices to the client. Explain that these checks
do not prove semantic entailment.

Describe deployment: PostgreSQL health gates a setup container using Alembic and existing
seed verification; setup success gates FastAPI readiness, then Streamlit. Only loopback
application ports are published, with no database port. App containers are non-root and
setup credentials are absent from the backend. The public API still needs authentication,
authorization, rate limiting and HTTPS before Internet exposure.

Finish with evidence: real PostgreSQL/HTTP/AppTest checks, 470 passing tests, both remote
CI jobs at 6135c17, and the separate 24/38 mock benchmark. Explain one known failure:
customer ID filters are ignored by the mock plan. The SQL tool itself is independently
tested; correct tool execution does not imply correct selection. Close with the scoped
backlog rather than claiming that a passing software suite establishes live agent quality.

## Engineering challenges and what I learned

| Challenge | Diagnosis and engineering response |
| --- | --- |
| SQL integration configuration | Normal startup lacked `READER_DATABASE_URL`; configured test backends masked that environment gap. Added specific safe diagnostics, repeatable setup and readiness; restarted the process to reload settings. |
| Read-only permissions | Transaction flags alone were insufficient evidence. Audited privileges/ownership/memberships and tested rejected writes with actual PostgreSQL, including disabled session defaults. |
| Multi-step orchestration | Preserve original call IDs and provider history while bounding calls/context. Track state per request, suppress duplicates, drain owned workers before cleanup and retain prior evidence on limits. |
| Citation validation | Validate exact passage/document relationships and provenance, then keep semantic support explicitly unevaluated. Reject conflicts instead of merging incompatible evidence. |
| Benchmark limitations | Separate software tests from agent expectations. Expose omitted filters and wrong routing, preserve original labels and gate individual previously passing cases. |
| Docker and CI | A real Compose run exposed an unquoted tmpfs list that builds alone missed. Corrected the mount, then verified workflows, restart, persistence and shutdown locally and remotely. |

## System design discussion

**Why FastAPI?** Typed request/response contracts and dependency injection fit a small
Python backend with clear service boundaries. Async provider calls coexist with bounded
synchronous-tool workers; async alone does not make the database path unlimited.

**Why PostgreSQL?** Transactions, NUMERIC accounting, relational constraints and actual
role permissions match this workload. SQLite tests would not prove the PostgreSQL security
and timeout behavior we depend on.

**How do you prevent unsafe SQL?** The registry accepts named business operations and
validated parameters. Code owns SQL structure, while the separate reader role and
read-only transaction enforce the database boundary. There is no execute-SQL tool.

**How does the agent choose tools?** The implemented live adapter supplies tool schemas
to the model, validates returned calls and replays results through a bounded loop. The
verified demo substitutes a deterministic mock selector; its behavior is not evidence
about a live model's choices.

**How do you validate evidence?** Typed outputs, bounded rows/passages, evidence IDs,
source/document coherence, exact citations and numeric-membership checks. Users can
inspect evidence and partial notices. This catches particular errors but is not semantic proof.

**What happens if PostgreSQL is unavailable?** Liveness can remain healthy while readiness
fails. SQL returns safe database diagnostics, and the client presents a useful failure;
there is no fabricated revenue or writer fallback. Prior evidence may be retained with a
partial/failed outcome. Restore the same database and recheck readiness and smoke.

**How would you scale it?** First measure concurrent-request behavior. Stateless request
services permit multiple API instances, but database connection budgets and tool workers
need coordinated caps. I would review ingress concurrency/rate limits, deployment readiness,
shared data versions and observability before adding replicas or caches. Those changes
have not been implemented or load-tested here.

**What must change before public deployment?** Authentication, authorization, ingress rate
limits, HTTPS/WSS, protected diagnostics, monitoring/alerts, backups and reviewed operational
access. Paid live runs need an explicit budget. The existing profile is private by design.
