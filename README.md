# QueryPilot AI — Intelligent Data Agent

QueryPilot AI is a Python portfolio project for an evidence-backed business analytics
assistant. The planned application will translate natural-language questions into approved
tool calls, retrieve synthetic business information, and explain answers with evidence.

Example: **“Which five products generated the highest revenue last month?”**

**Current status: Day 1 repository foundation.** The package can be installed and imported.
API endpoints, database access, LLM tools, and the interface are not implemented. No
database, API key, Docker installation, or paid service is needed for this milestone.

## Planned features

- FastAPI backend with `/health` and `/api/v1/chat`.
- Synthetic e-commerce data in PostgreSQL.
- Predefined, parameterized read-only SQL analytics tools.
- Document search, multi-step LLM tool calling, and evidence-backed answers.
- Tool traces, input validation, errors, timeouts, and logging.
- Streamlit interface, automated tests, evaluations, Docker Compose, and CI.

## Planned architecture

```text
Streamlit → FastAPI routes → Services / Agent → Approved tools
                                               ├── Analytics → PostgreSQL
                                               └── Document search → Synthetic documents
```

The src-layout package separates routes, orchestration, tools, database access, schemas,
services, and configuration. See [architecture](docs/architecture.md) for boundaries.

## Technology stack

| Technology | Purpose | Milestone |
| --- | --- | --- |
| Python 3.12 | Language and development baseline | Day 1 |
| Hatchling | Build/install the src-layout package | Day 1 build dependency |
| Pytest | Automated tests, starting with package import | Day 1 development dependency |
| Ruff | Linting, import sorting, formatting | Day 1 development dependency |
| FastAPI, Pydantic, Uvicorn | HTTP API, validation, server | Day 2 |
| PostgreSQL, SQLAlchemy, Psycopg | Database, models, driver | Day 3 |
| OpenAI Python SDK | LLM function/tool calling | Day 6 |
| Streamlit | Interactive analytics interface | Day 9 |
| Docker Compose, GitHub Actions | Service orchestration and CI | Later milestones |

Day 1 has **no runtime dependencies**. Future libraries will be added when used.

## Setup and validation

Install Python 3.12, then run from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c "import querypilot; print(querypilot.__name__)"
python -m pytest -q
ruff check .
ruff format --check .
```

On Windows, activate with `.venv\Scripts\activate` instead. `-e` installs in editable
mode; `[dev]` adds Pytest and Ruff. Hatchling builds package metadata for the installer.
The smoke test imports the installed package without modifying Python's import path.

Alternatively, with uv already installed:

```sh
uv sync --python 3.12 --extra dev --locked
uv run --extra dev python -m pytest -q
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
```

`uv.lock` records resolved versions for uv users. The pip workflow uses compatible
ranges in `pyproject.toml`. Neither workflow starts an application.

Optionally copy `.env.example` to `.env` for future local settings. Empty values are
documentation only on Day 1; no loader reads them. Never commit `.env`, API keys,
passwords, customer data, or production exports.

## Development roadmap

Day 1 establishes the foundation. Day 2 adds FastAPI and health; Day 3 introduces
PostgreSQL and synthetic data; Days 4–5 add analytics and document tools; Day 6 introduces
LLM tool calling; Days 7–8 add orchestration and reliability; Day 9 adds Streamlit.
Later milestones cover broader tests, evaluations, Docker, CI, and deployment docs.
See [PLANS.md](PLANS.md) for the detailed proposed sequence.

## Project documents

- [AGENTS.md](AGENTS.md): contributor conventions and milestone boundaries.
- [GOALS.md](GOALS.md): product scope, security goals, Day 1 acceptance criteria.
- [PLANS.md](PLANS.md): roadmap and implementation plan.
- [docs/architecture.md](docs/architecture.md): planned components and dependencies.
- [docs/progress.md](docs/progress.md): implementation and verification status.
- [data/sample/](data/sample/README.md): fixture policy; dataset planned for Day 3.

## Security principles

The eventual agent must use approved parameterized operations, never arbitrary
LLM-generated SQL. Tools must use restricted read-only credentials, validate inputs,
and cap iterations, time, and results. Retrieved content must be treated as untrusted.
These requirements will be implemented and tested with their associated features.
Only synthetic, publicly shareable data belongs in this repository.
