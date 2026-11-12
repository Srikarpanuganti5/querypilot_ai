# Deployment readiness — Day 13

## Recommended strategy

Use the existing Docker Compose stack as a **private local, mock-provider demo**, shared
through a screen-sharing session or recording. This demonstrates the real backend/database
without introducing public endpoints, recurring hosting charges or paid model calls.
No cloud resources, public URLs, image publishing or external credentials are required.
Docker Desktop's official terms include personal and education use without a subscription;
confirm eligibility if using company hardware. [Docker licensing](https://docs.docker.com/subscription-billing/desktop-license/).

Options researched on 2026-11-11:

| Strategy | Cost and resources | Operations, data and secrets | HTTPS/access/sleep | Portfolio fit |
| --- | --- | --- | --- | --- |
| Local Docker demo, recommended | No incremental hosting/model bill on existing hardware; electricity/storage remain | Existing PostgreSQL volume; private environment file; host maintenance | Loopback-only HTTP; screen share; host must stay awake | Lowest complexity, repeatable and inspectable |
| Private existing Docker host | Existing host costs, no free-hosting assumption | Same Compose/volume; restricted SSH account and secret file; operator owns backups | SSH port forwarding/encrypted transport; no public app ports; host uptime required | Good when an interviewer needs private access |
| Single cloud VM | Example DO Basic 2 GiB/1 vCPU: $12/month before backups/tax/other services; 4 GiB example $24/month | Docker/PostgreSQL co-hosted; disk persistence; manual patching/backups/firewall/secret management | SSH-only private demo is possible; public HTTPS/auth/rate limits must be added; paid VM normally stays provisioned | Simple architecture, more operational responsibility |
| Container hosting + managed PostgreSQL | Separate compute/database plans; quotas and ongoing paid costs depend on sizing | Less host administration; separate services, one-shot migration job, managed secrets and persistent DB needed | Managed TLS can help; free services may sleep and impose limits | Useful later; more platform-specific work than this milestone needs |

The VM prices are current examples, not an approved budget or a claim that a 2 GiB VM is
load-tested for this application. Builds/concurrency may need more memory. See
[DigitalOcean pricing](https://www.digitalocean.com/pricing/droplets).
Render currently documents a free preview tier, but web services idle after 15 minutes,
have cold starts/ephemeral local storage, and free PostgreSQL expires after 30 days. That
is unsuitable as a durable unattended demo database. No provider account was created.
[Render's current free-service limits](https://render.com/docs/free).

If moving to a VM later, the exact prerequisite is explicit approval of provider, region,
size, recurring budget/backups, SSH access and the access-control/HTTPS design. Do not put
provider tokens or SSH private keys into chat/Git. No such action is needed for today's demo.

## Private deployment configuration

Reuse `compose.yaml`, Dockerfiles, named data volume, setup job and reader-only backend.
`compose.demo.yaml` adds resource/log bounds: 512 MiB per service, CPU ceilings (2 backend,
1 other services), 256 PIDs, and rotated 5 MiB × 3 logs for the long-running services.
These are single-demo limits, not a concurrency/production sizing guarantee. Default host
bindings remain 127.0.0.1:18000 and 127.0.0.1:18501; PostgreSQL is internal only.

The frontend origin is environment-driven with Compose-only `QP_DEMO_API_ORIGIN`, default
`http://backend:8000`. Backend/DB existing Settings names are unchanged. No deployment URL
is hardcoded to host localhost inside this override. The CLI accepts `--backend-url`, or
uses the existing frontend `QUERYPILOT_API_BASE_URL` convention. Internal service DNS is
used inside containers; host localhost is used only to access loopback-published ports.

```sh
.venv/bin/python scripts/prepare_docker.py
make demo-up
make demo-smoke
.venv/bin/python -m querypilot.cli smoke-test --backend-url http://127.0.0.1:18000
.venv/bin/python scripts/verify_demo_ui.py --backend-url http://127.0.0.1:18000
# When finished; never add -v:
make demo-down
```

`make demo-up` builds/waits with the demo override. Startup remains DB TCP readiness →
existing Alembic/seed/reader setup → backend `/ready` → frontend. Setup refuses different
existing data. Restart preserves the volume. App roots remain read-only, non-root, with
dropped capabilities and no privilege escalation. Uvicorn/Streamlit use existing exec-form
startup and graceful-stop behavior. Mock remains the explicit mode for every smoke request;
the Compose stack forwards no OpenAI credential and disables live HTTP execution.

Secret files are ignored and mode 0600; the Docker build context is allowlisted. Operators
with Docker/host administration can inspect process environments, so protect that host
account. Do not print resolved Compose configuration, container environments, keys or URLs
containing credentials. JSON logs use existing redaction and fixed execution fields.

## Public deployment is blocked

This profile is not an Internet deployment. No public authentication/authorization,
per-client rate limiting, HTTPS termination or protected diagnostic access is implemented.
Do not change bindings to 0.0.0.0, open a public tunnel, port-forward the router or publish
these services until those controls are designed, reviewed and explicitly approved.

| Control | Current state | Decision |
| --- | --- | --- |
| Read-only SQL and isolated administrator | Real role audits/SELECT-only tools; setup alone receives runtime writer credentials | Retain and reverify after changing database/provider |
| Fixed registry/arguments/evidence | Six approved tools, parameterized SQL, strict contracts, reference checks | Keep existing regression tests; not semantic or injection immunity |
| Secrets and errors | Ignored private settings, image allowlist, redaction and fixed safe diagnostics | Do not enable raw third-party debug logs |
| Request/agent limits | 65536-byte HTTP body cap, 4000-character questions, bounded iterations/calls/context/time/results | Useful bounds, not rate limiting |
| Resource exhaustion | Demo CPU/memory/PID/log bounds | Still needs ingress rate/concurrency controls for untrusted clients |
| Authentication/authorization | Absent | Block public exposure; no complex auth system added for a loopback demo |
| HTTPS/WSS | No public termination configured | Private loopback/SSH only; trusted TLS and origin controls required for public use |
| CORS | Exact-origin configuration, empty default; no wildcard credentialed origins | CORS is not authentication and does not stop server-side requests |
| Diagnostics/traces | Public within the private demo; safe projection still exposes business evidence/status | Restrict docs, capabilities, readiness and traces before public exposure |

For an already approved private host, SSH forwarding could preserve loopback bindings:
`ssh -L 18000:127.0.0.1:18000 -L 18501:127.0.0.1:18501 user@private-host`.
This is an operator example, not an action performed or a public-hosting approval.

## Smoke-test interpretation

`querypilot.cli smoke-test` checks liveness, readiness, expected OpenAPI operations and
typed capabilities, then submits exactly four versioned acceptance questions in **mock**
mode. The existing typed HTTP client validates outcomes; existing independent references
check tools, evidence, citations, product order and numeric literals. The command does not
implement another agent, execute writes, invoke live requests or retry them.

`--verify-database` additionally uses the configured restricted reader to verify the exact
fixture and independently SELECT product revenues/payment counts, comparing them with
API evidence. Run it inside the backend container for same-database attestation. Do not
point a host-side reader at a different native DB and describe it as container verification.
Without this flag, direct DB access is explicitly SKIP/NOT VERIFIED; API evidence/reference
checks still run. The operator is responsible for matching a separately configured reader
to the backend target. No connection URL is returned in the report.

Exit 0 means all required smoke checks passed; any required failure exits 1. Optional
direct DB omission is disclosed rather than a false success. Reports contain fixed stages,
case IDs, statuses and durations, not raw answers, arguments, environment or database records.
An unreachable backend/readiness failure aborts question submission safely. Bad contract,
oversized/redirected responses and unknown citations fail checks. Deterministic literal
checks do not prove semantic faithfulness or live LLM accuracy.

## Verification boundaries

`verify_demo_ui.py` is automated Streamlit AppTest running the actual frontend code against
the container HTTP backend; it is not a graphical/manual browser session. It checks mock
mode, four workflows, evidence rendering, selected-record warnings, history, clear and safe
backend-unreachable feedback. Use the manual checklist in [demo.md](demo.md) for actual
browser/WebSocket behavior and screenshots. Manual acceptance remains pending.

The Day 12 push at f43b45e has remote CI evidence (both jobs green). Day 13 was
published in six focused commits through 9ab3c07 after explicit approval on 2026-11-12.
Its [actual GitHub Actions run](https://github.com/Srikarpanuganti5/querypilot_ai/actions/runs/43164942219)
provides the remote result; configuration alone is not proof of success. No images are
published by this workflow and no public deployment is performed.
