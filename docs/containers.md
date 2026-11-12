# Containers and CI — Day 12

## Status and scope

**DOCKER VERIFIED on 2026-11-11:** the user made Docker Desktop available and authorized
isolated verification. Both images built, all four workflows and the protected benchmark
cases passed, and outage/restart/persistence/shutdown checks passed. An unquoted tmpfs
option list required a one-line quoting fix. The stack is now shut down with its database
volume retained. Details and nonfatal warnings are in [progress.md](progress.md).
Day 12's follow-up CI passed remotely on f43b45e. Day 13 was pushed through 9ab3c07; see
[its workflow run](https://github.com/Srikarpanuganti5/querypilot_ai/actions/runs/43164942219)
for the actual remote status. **LIVE OPENAI NOT VERIFIED**;
containers and CI default to deterministic mock mode.
No cloud deployment or image publishing is included.

## Day 13 private-demo override

Use `make demo-up`, `make demo-smoke` and `make demo-down` to apply `compose.demo.yaml`
without a second deployment architecture. It retains the existing project/volume and
loopback-only published ports. CPU/memory/PID/log bounds and `QP_DEMO_API_ORIGIN` apply to
this private profile; internal HTTP defaults to `http://backend:8000`. No public auth/TLS
configuration is added. Public deployment is blocked as described in [deployment.md](deployment.md).

The host-facing command is `python -m querypilot.cli smoke-test --backend-url http://127.0.0.1:18000`.
The container-facing `make demo-smoke` uses the internal origin and `--verify-database` so
the restricted reader and tested backend target the same containerized PostgreSQL database.
The previous smoke module remains compatible. Volume credentials are preserved; different
fixtures still fail rather than being overwritten. Day 13 recovery/persistence verification
and measured limits are recorded in progress. Manual browser checklist: [demo.md](demo.md).

## Quick start

Install/start Docker with Compose support, then from the repository root:

```sh
.venv/bin/python scripts/prepare_docker.py
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up --build --wait --wait-timeout 180
docker compose --env-file .env.docker ps
curl http://127.0.0.1:18000/health
curl http://127.0.0.1:18000/ready
docker compose --env-file .env.docker exec -T backend python -m querypilot.services.container_smoke
```

Backend: **http://127.0.0.1:18000**, docs `/docs`; frontend:
**http://127.0.0.1:18501**. These alternate host ports avoid the existing native 8000/8501
services. Change `QP_BACKEND_PORT`/`QP_FRONTEND_PORT` in private `.env.docker` if occupied.
Inside Docker, backend listens on 8000 and Streamlit on 8501; frontend uses
`QUERYPILOT_API_BASE_URL=http://backend:8000`, never host localhost. PostgreSQL has no
published host port. Named project `querypilot_day12` owns its own `postgres_data` volume;
it does not attach the former Day 3 volume or native `.local/postgres` cluster.

`prepare_docker.py` creates random URL-safe setup/reader passwords with mode 0600, prints
no values, preserves existing files and leaves native `.env` untouched. `QP_*` variables
are Compose substitution inputs; the application still receives its existing Settings
names. Do not print `docker compose config` without `--quiet`, environment dumps or inspect
container environments: resolved values include credentials. Changing an environment file
does not rotate an existing PostgreSQL role password. Restore its matching configuration
or review credential rotation explicitly; do not delete a volume to work around it.

## Images and privilege boundaries

`docker/Dockerfile.backend` and `docker/Dockerfile.frontend` use Python 3.12.16 slim-bookworm
and uv 0.13.5. Builder stages install the existing lock with `--locked --no-dev`, then
install the project non-editably. Runtime stages copy the virtual environment, avoiding uv
and development tools. BuildKit caches dependency layers. Both runtimes run as UID/GID
10001 with exec-form commands; no reload/debug server is enabled. The backend has a separate
`test` target containing locked dev tooling, test fixtures and scripts.

Both runtime images currently share the project's one runtime dependency graph, including
Streamlit in the backend. This preserves the authoritative lock and avoids introducing a
second dependency specification solely for image size. No image-size reduction is claimed.
The image tags are version-pinned, not digest-pinned; reproducibility of base OS layers is
therefore bounded by registry tag stability. Actual image builds are now verified locally.
`.dockerignore` is an allowlist: no `.env`, credentials, `.local`, virtual
environments, Git metadata, private data or generated benchmark reports enter the context.

Compose application services use read-only root filesystems, dropped capabilities,
`no-new-privileges`, a bounded `/tmp` tmpfs, an init process and graceful-stop timeouts.
They have no host source mounts or Docker socket mount. PostgreSQL uses its standard image
entrypoint to initialize volume ownership and runs the server under its normal postgres
account; it is not a privileged container. Application restarts are `unless-stopped`;
the setup job has no automatic restart. API endpoints still lack public authentication and
rate limiting, so published ports bind only loopback.

## Initialization and readiness

Startup order is PostgreSQL connection health → successful one-shot `setup` → backend
`/ready` → frontend. Compose uses `service_healthy` and `service_completed_successfully`.
The setup container alone receives `DATABASE_URL` administrative access. Backend receives
only `READER_DATABASE_URL`; frontend gets neither. Runtime does not inherit setup secrets
or paid API configuration. Containers are intentionally mock-only in the default file.

`python -m querypilot.db.bootstrap` requires `QUERYPILOT_SETUP_ACK=synthetic-only`, distinct
roles on one `querypilot_` database and explicit credentials. On an empty schema it invokes
the existing Alembic migration through a supplied connection, then existing seed/verify
functions for reference 2026-10-27, seed 42. Existing databases must already be at head;
different schemas/data are refused rather than automatically upgraded/reset. Identical
seeding is a no-op. The reader is created only if absent, granted SELECT on the six business
tables, audited for prohibited privileges and checked using the exact fixture and corpus.
Existing roles/passwords are not silently rotated or stripped of unexpected privileges.
This is development synthetic setup, not a general migration/production provisioning system.

`/health` remains process liveness. New `/ready` calls read-only doctor checks: configured
reader connectivity, tables, restricted permissions, nonempty seed tables, corpus and mock
readiness. It returns 503 for failures, 200 for readiness, with fixed names/status/codes only.
Runtime readiness is not a full row-for-row benchmark check; setup/evaluation perform that
stronger check. Migration metadata is checked when explicit setup access exists; the backend
does not gain writer access to perform that check. All database/network waits have existing
connection/statement bounds; health retries and Compose startup have explicit deadlines.
Restart policies may continue retrying a failed process, but setup itself never loops forever.

## Test stack and local CI parity

The test override uses a different database and project namespace. This command starts only
the test runner and its setup/database dependencies, avoiding application port conflicts:

```sh
docker compose --env-file .env.docker -p querypilot_day12_test -f compose.yaml -f compose.test.yaml run --build --rm tests
docker compose --env-file .env.docker -p querypilot_day12_test -f compose.yaml -f compose.test.yaml down --timeout 40
```

It preserves its test volume. Do not run `down -v` without explicit authorization.
For native parity with the already prepared dedicated test database:

```sh
set -a
source .local/integration.env
set +a
.venv/bin/python scripts/run_checks.py
```

This runs Ruff, the complete suite under branch coverage, JUnit verification, coverage
report/JSON, doctor and the reviewed regression gate. It maps evaluation to the acknowledged
test target and disables live mode. `check_ci_results.py` rejects every skipped/failed test,
requires at least 50 actual PostgreSQL cases and checks the exact original 50 node IDs in
`data/evaluations/postgres_required.json`. This prevents a green run that simply excludes
the database suite. Test guards still require distinct reader/writer roles, a dedicated
name and explicit `QUERYPILOT_TEST_DATABASE_ACK=allow-isolated-schemas`.

Make targets provide the same commands: `make lint`, `test`, `ci`, `gate`, `doctor`,
`docker-env`, `build`, `up`, `smoke`, `docker-test`, `down`. Native `make test` permits explicit
skips; `make ci` rejects them. Source the integration environment for `make ci`.

## GitHub Actions

`.github/workflows/ci.yml` triggers on PRs and pushes to main, has contents-read permission,
SHA-pinned checkout/setup-python actions, no retained checkout credential and job deadlines.
The quality job installs `uv sync --locked --extra dev`. Coverage 7.17.2 is the sole new
dev dependency; all pre-existing versions are unchanged.

An isolated PostgreSQL 16 Docker container is used as the allowed service-container
equivalent. `scripts/ci_database.py` generates random credentials, masks them before any
output, selects a random loopback host port, waits at most 60 readiness attempts and writes
private settings through `GITHUB_ENV`. Administrative access is confined to synthetic
CI setup/test fixtures, not the application runtime.
The parity script then runs all tests, coverage and the gate. Cleanup removes only that
CI-created container; no existing database/volume is targeted.

The image job builds both runtime images without login/push/registry credentials. It
configures a fresh Compose project, verifies actual HTTP workflows and frontend health,
checks stopped-database liveness/readiness, restarts services, compares volume creation
identity and re-verifies exact fixture data, scans bounded logs without echoing them and
shuts down without removing volumes. This job is configured, not remotely verified.

## Failure diagnosis and recovery

- Daemon socket absent: start Docker Desktop yourself, wait for `docker info`, then rerun
  configuration/build/start commands. CLI configuration success is not runtime proof.
- Setup exits nonzero: backend dependency remains blocked. Check credentials, migration
  head and fixture identity with protected local diagnostics. Do not reset existing data.
- Reader missing/wrong, tables missing, empty fixture or database stopped: `/ready` fails;
  `/health` can still succeed. Existing tests exercise those distinct states with real PG.
- Frontend cannot reach backend: retain `http://backend:8000` internally, verify backend
  health and the Compose network. Frontend process health alone does not prove chat works.
- Port conflict: change only host-side `QP_*_PORT` values and restart through Compose.
- Workflow gate fails: review exact case regressions, fixture/corpus/dataset hashes and
  prerequisite failures; never regenerate expected answers or accept all current output.

Repeat runtime/persistence checks when Docker becomes available:

```sh
make smoke
docker compose --env-file .env.docker stop db
docker compose --env-file .env.docker exec -T backend python -m querypilot.services.container_smoke --unavailable
docker compose --env-file .env.docker restart db backend frontend
docker compose --env-file .env.docker up --wait --wait-timeout 180
make smoke
.venv/bin/python scripts/check_compose_logs.py
make down
```

Shutdown preserves named data. The CI workflow additionally compares volume creation times
across restart. Workflows/recovery/persistence are **DOCKER VERIFIED** as of the follow-up
run on 2026-11-11; the commands above are also useful
for future rechecks. Native and Docker results are recorded in [progress.md](progress.md).

References: [Compose startup conditions](https://docs.docker.com/compose/how-tos/startup-order/),
[uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/),
[GitHub PostgreSQL service guidance](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
