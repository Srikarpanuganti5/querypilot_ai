# QueryPilot AI operator and interview demo — Day 13

This is a private local Docker demonstration using synthetic data and a deterministic
mock provider. It demonstrates backend engineering and evidence flow. It is not a publicly
deployed service or a verified live LLM product. Draft portfolio/launch materials are in [portfolio.md](portfolio.md) and
[linkedin-launch.md](linkedin-launch.md); neither is published.

Latest metrics/verification: [final-verification.md](final-verification.md). No screenshot
or recording is supplied; the capture plan below remains future operator work.

## Operator checklist

1. Start Docker Desktop and verify `docker info`. Keep native/other project data untouched.
2. From the repository root run `.venv/bin/python scripts/prepare_docker.py` and `make demo-up`.
   The helper preserves existing private settings. Never show `.env`/`.env.docker` on screen.
3. Run `make demo-smoke`; require exit 0 and all four acceptance cases passing. This checks
   the exact fixture through the container reader and independently verifies SQL counts.
4. Run `.venv/bin/python scripts/verify_demo_ui.py --backend-url http://127.0.0.1:18000`
   for automated UI/HTTP evidence. This does not replace the manual checklist below.
5. Open http://127.0.0.1:18501, choose **Mock demo**, clear old conversation and use a clean
   browser window. Backend docs are on http://127.0.0.1:18000/docs.
6. Keep the architecture and evaluated limitations available in a separate clean tab.
   The protected gate can be run with:
   `docker compose --env-file .env.docker -f compose.yaml -f compose.demo.yaml exec -T backend python -m querypilot.evaluation.gate --output /tmp/demo-gate`.
7. A slow/unhealthy stack is a failed prerequisite. Diagnose readiness/configuration first;
   never switch to fabricated rows, hide warnings or claim an offline recording is live.
8. At the end run `make demo-down` if no further manual checks are needed. Never use `down -v`.
   Stop screen sharing before inspecting any private diagnostics or credentials.

## 2–3 minute technical script

| Time | Action and explanation |
| --- | --- |
| 0:00–0:20 | “Business questions often need both transaction data and policy documents. QueryPilot combines approved analytics and policy retrieval with inspectable evidence.” |
| 0:20–0:40 | Show Streamlit → FastAPI → shared agent → allowlisted registry → PostgreSQL/BM25. Explain that this run uses deterministic mock selection; actual tools and data are real. |
| 0:40–1:05 | Ask “What are our top five products by revenue?” Show the real ranked table and evidence trace. Explain the selected-record warning instead of hiding it. |
| 1:05–1:25 | Ask “What is our return policy?” Show the 30-calendar-day statement and exact `QP-RET-001#s002-c001` citation. |
| 1:25–1:50 | Ask “Which products generated the most revenue, and what is our refund policy?” Expand execution details and show SQL/document evidence retained separately. |
| 1:50–2:15 | Explain fixed parameterized SELECTs, a SELECT-only DB role, isolated setup credentials, strict arguments, deadlines, safe errors and bounded responses. Show the local smoke command or test summary. |
| 2:15–2:40 | State “The deterministic mock benchmark passes 24 of 38 cases. Fourteen failures remain visible, including routing, filters and abstention. This is not measured live LLM accuracy or semantic faithfulness.” Mention Docker and show the actual Day 13 CI run status; do not infer success from a workflow file. |
| 2:40–3:00 | Optional payments question, independently verified for the current fixture. Explain the next improvement target and stop. Do not claim an arbitrary fixture always has 486 failures. |

If time is short, omit the optional payment interaction, not the evaluation limitations.
The exact synthetic fixture's top IDs are 64, 35, 21, 76 and 63; re-run smoke if the database
changes. A citation proves provenance/membership checks, not automatic semantic correctness.

## 30–45 second recording plan

This is a future capture plan, not a recording or a LinkedIn post.

- 0–5 seconds: show the real localhost interface and **Mock demo** label.
- 5–16 seconds: submit the top-five revenue question; show the actual SQL table/evidence.
- 16–27 seconds: submit the return-policy question; show the policy fact and citation.
- 27–35 seconds: briefly show the architecture and read-only/allowlist boundaries.
- 35–45 seconds: show the verified **local Day 13** test summary (470 tests, 56 PostgreSQL
  checks), then a short on-screen qualifier: local Docker, synthetic data, mock provider.

Use actual interactions. If editing out waits, label cuts and retain limitations/partial
warnings. Do not fabricate screenshots, fake product replies, display credentials, imply
public hosting or present 24/38 as production-level accuracy. Recheck metrics before capture.

## Manual browser acceptance — NOT VERIFIED

No graphical browser-control tool was available in this session. AppTest and HTTP health
checks do not establish actual browser/WebSocket operation. Complete this checklist yourself
at http://127.0.0.1:18501 and record date/browser plus pass/fail for every item:

1. Page loads without browser-console errors; private/local origin is visible.
2. Sidebar backend availability is correct; it changes appropriately during an outage.
3. **Mock demo** is selected and clearly labeled; changing modes alone submits nothing.
4. Enter/send the return-policy question; a user and assistant message appear.
5. Submit top-five revenue; confirm table order and values match a fresh `make demo-smoke`.
6. Confirm document citations display as exact IDs, including `QP-RET-001#s002-c001`.
7. Expand tool/execution panels; verify real operation/status/evidence details are accessible.
8. Confirm selected top-five evidence produces the partial/limited-record notice.
9. Submit the combined and failed-payments questions; verify separate SQL/document evidence.
10. Confirm conversation history survives normal UI reruns; **Clear conversation** removes it.
11. Stop only the backend with the same Compose demo files, rerun the page/submit, and confirm
    a useful safe failure message. Restore with `make demo-up`; verify reconnect.
12. Refresh the browser and confirm no question is automatically resubmitted. Session-only
    history may reset on a new browser session; it is not persistent agent memory.

If screenshots are captured, capture only the application viewport with no secrets/other
windows visible. Suggested shots: ranked SQL table, exact policy citation, combined-tool
trace and partial warning. Store privately/ignored until reviewed; no screenshots were
generated or claimed in this milestone.
