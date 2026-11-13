# Security and reliability boundaries

This is an engineering review with deterministic adversarial tests and a dependency
advisory check. It is not a formal security audit or penetration test. Only synthetic,
publicly shareable data is supported. Actual live OpenAI behavior remains unverified.

## Final review scope

Day 14 reuses the security regression suite, audits tracked/new public files and generated
reports for configured-secret values/credential patterns, verifies ignore rules, and checks
actual container privilege/port boundaries. Exact findings are in [final-verification.md](final-verification.md).
This is scoped engineering verification, not a formal audit or exhaustive secret/history
scanner. The older dependency advisory result below is historical, not a new vulnerability
audit. No paid requests, public resource creation or release publication are authorized.

## Public-exposure review and decision

Day 13 permits only a private/local demo. The app has no public authentication or
authorization, per-client rate limiting, HTTPS/WSS termination or protected diagnostics.
Do not expose the app/DB directly, change loopback bindings or open a public tunnel until
these essential controls are implemented, reviewed and explicitly approved. No complex
authentication system was added because the chosen strategy is local screen sharing.

Existing 65536-byte HTTP limits, strict 4000-character questions, bounded agent/tool budgets,
read-only SQL and the resource-limited demo override reduce particular risks; they are not
ingress rate limiting or a proof of isolation against all untrusted public users. CORS is
an exact-origin browser policy, not access control. Readiness/docs/capabilities/traces can
disclose operational/business information even when credentials are redacted. Restrict them
before any public launch. A future private SSH demo still requires approved host/user access.

The smoke CLI validates an operator-supplied plain HTTP(S) origin, refuses credentials or
redirects, bounds JSON responses and always requests mock mode. Direct database verification
is explicit and read-only; it must target the same backend database. Reports omit origins,
credentials, raw records and provider text and pass through SecretGuard. No live calls,
public resource creation or automatic Git publication occur. See [deployment.md](deployment.md)
for the full control matrix and prerequisites. This review is not a formal security audit.

## Container and CI boundaries

App images run as UID/GID 10001; Compose drops capabilities, prevents privilege escalation
and uses read-only root filesystems with bounded temporary storage. No host source/Docker
socket mounts, privileged containers or PostgreSQL host ports are configured. Credentials
are generated in ignored mode-0600 `.env.docker`, excluded by an allowlisted build context,
and never embedded in image layers. Resolved Compose/environment dumps must not be logged.

Only setup receives administrative runtime credentials. The backend has reader access;
frontend has only its API origin. Setup requires an explicit synthetic acknowledgement and
refuses mismatched existing data/schema rather than resetting them. Native setup tests
create/drop only their own random databases/roles. Readiness performs no writes.

CI has contents-read permissions and SHA-pinned actions. Ephemeral credentials are generated
and masked before output. Writer access is limited to synthetic CI setup/test fixtures,
never the application runtime. Live configuration is disabled; no paid request is scheduled.
The original PostgreSQL cases cannot silently skip, and the benchmark gate cannot hide a
case regression behind aggregate gains. Bounded container log checks withhold raw contents.
Container runtime and log screening were verified locally in Day 12 and repeated with the
Day 13 private profile; these checks are not a formal security audit.

## Day 10 isolation and diagnostics

Real PostgreSQL tests require matching dedicated reader/writer targets, distinct roles,
a `querypilot_` database ending `_test` or `_verify`, and explicit
`QUERYPILOT_TEST_DATABASE_ACK=allow-isolated-schemas`. Guards run before fixture DDL.
Cleanup drops only fixture-owned UUID schemas, never normal databases. All five tools
continue to use fixed parameterized SQL, role/privilege audits and read-only transactions.

The explicit native setup helper owns a new private `.local/postgres` cluster and separate
synthetic development/test databases. It preserves existing configuration and refuses
unowned storage or unexpected migrations/data rather than resetting them. Administrative
setup access is separate from agent reader access. Generated credentials and `.env` are
private ignored files and must never be committed.

Doctor performs read-only checks and never provisions, migrates, seeds or calls OpenAI.
Its optional migration check uses configured setup access only for the same database;
tools never fall back to that access. Safe fixed errors distinguish missing reader settings,
unavailable servers, authentication, missing databases/tables, permissions and timeouts.
Raw driver exceptions, connection URLs and SQL are not public diagnostics. Real failure
tests cover unavailable ports, incorrect passwords, nonexistent databases and missing
tables; synthetic SQLSTATE tests cover remaining classifications. See [testing.md](testing.md).

## Gap analysis and changes

| Existing control | Day 8 gap | Strengthening |
| --- | --- | --- |
| Fixed tools, strict Pydantic arguments, parameterized SELECTs, read-only role audit | Instruction-shaped data could still influence model selection | Test malicious documents/fake authority against the real registry; reject non-assistant provider message roles |
| SecretStr settings and fixed application log events | Valid product/passage text or a custom provider diagnostic could carry a credential | Screen configured credentials and patterns at data boundaries; canonical provider errors; log/output redaction backup |
| Per-provider/tool/overall await deadlines | Cancelled to_thread work could outlive its request and race resource cleanup | Own/shield/drain workers before return or cancellation propagation; stop later batch work |
| Byte/row/call/iteration limits | No independent message-count cap; padded questions normalized before raw bound | Bound raw questions, message counts and predictable batch-result slots before expensive work |
| Citation membership and numeric checks | Document IDs could disagree with citations; duplicate citations and changed record versions were accepted | Validate citation provenance/uniqueness; detect structural conflicts across rounds |
| Prior traces retained on failure | Limited answers could look complete; in-flight batch calls were implicit | partial/limitations/pending_tool_calls, deterministic notices and safe no-answer error exits |
| Safe count/status logs | Tool records lacked per-request correlation and terminal iteration/error categories | Correlated agent_tool_execution and terminal records using generated IDs |

## Threat model and structural boundaries

Attackers may control a user question, indexed document text, returned SQL string values,
or model-requested arguments. Text may impersonate a system/developer message, demand
secrets, request destructive SQL, disable restrictions or propose an external destination.
Operator settings, application code, registry definitions and database provisioning are
trusted. Corpus root/ancestor ownership is trusted as documented in the search guide.

Instructions originate only in code. User text stays in a user message; retrieved text
stays inside JSON function-output data marked untrusted. JSON that says role=developer
inside an excerpt is still an excerpt. It is never appended as a new authority-bearing
message. Top-level provider output roles other than assistant are rejected. All prior
output/reasoning items and call IDs are replayed according to the Responses protocol;
replay never grants permissions to document text.

All six executable operations come from the fixed registry. Names such as execute_sql,
send_http, read_environment, delete_customers and get_configuration are unavailable.
No shell, arbitrary SQL, network destination, file path or configuration-reflection
argument exists. Arguments validate before database/retrieval I/O; SQL operations still
use bound values, a restricted reader, role checks, read-only transactions and server
timeouts. No tool side effects or tool retries were introduced. SDK transport retries
remain bounded to 0–2 inside the existing logical deadlines.

Tests deliberately let a scripted model request unauthorized actions after seeing a
malicious passage. The registry rejects them and the application never executes them.
The same tests allow a legitimate answer quoting "Ignore previous instructions" with
its actual source citation. There is no instruction-keyword blacklist. These tests
establish application-controlled capability boundaries, not live-model attack immunity.
An injected instruction may still steer the model toward a different **approved** read
operation or a misleading answer. There is no per-user authorization/tenant isolation
layer yet; the data is public synthetic data. Day 9 adds a local-development agent HTTP
endpoint with an explicit live-mode gate. It has no authentication or rate limiting and
must stay on loopback/private development infrastructure; it is not a public production API.

## Credential and diagnostic handling

SecretGuard knows the configured API key, full writer/reader URLs, and raw/URL-encoded
database passwords. It also recognizes common OpenAI/GitHub token forms, Basic/Bearer
authorization, credential-bearing URLs, password/key/token assignments and private-key
blocks. Sensitive configuration keys are filtered recursively. Tests generate meaningless
sentinels at runtime; they contain no real credentials or committed secret snapshots.

- A credential-bearing question is rejected before a provider call, with a redacted
  question in its safe outcome. Raw length validation runs first.
- Provider text/output and decoded argument objects are checked before replay/dispatch.
  Escaped JSON credentials in arguments are checked after decoding too. Sensitive output
  is withheld; it is not turned into an answer or a trace argument.
- Validated registry output is screened before returning evidence. The shared executor
  repeats screening using its request settings, including for injected registries.
  A secret-bearing result becomes a safe sensitive_output error with no data.
- ProviderError normalizes known and unknown diagnostic codes/messages. SDK failures,
  settings errors, cleanup failures and unexpected execution exceptions serialize fixed
  human-readable diagnostics without raw exception text or stack traces.
- Logging uses fixed application events, allowlisted metadata and redaction as a backup.
  API/CLI initialization supplies the actual settings instance to its formatter. No
  authorization header, environment mapping or whole Settings object is logged.
- Default CLI output omits questions, arguments and result bodies. Verbose output remains
  screened; it never includes internal messages, provider reasoning or settings. Existing
  HTTP errors already use sanitized envelopes and omit submitted validation values.

An exact-copy check additionally withholds long trusted instruction lines in final
provider text. It is only a supplemental check: paraphrases, fragments and arbitrary
encodings are not generally detected. Secret screening is not a comprehensive data-loss
prevention system; it may produce false positives, particularly with short/common local
passwords, and can miss unknown formats or transformed secrets. Arbitrary user-entered
personal information is not automatically anonymized. Raw third-party SDK/HTTP/SQL debug
logging is outside the application formatter; do not enable it when handling credentials.

## Cancellation, deadlines and partial batches

run_tool owns a Task for the synchronous worker and awaits it through asyncio.shield.
On cancellation, it drains the retained worker, consumes any worker exception and then
re-raises CancelledError. Repeated cancellation during that drain does not abandon it.
The CLI closes provider and registry only after run exits; cleanup exceptions are handled
independently so a provider-close failure does not prevent registry cleanup.

Cancellation of a provider coroutine propagates directly. An external cancellation
emits a safe terminal status=cancelled/request_cancelled record and raises to the caller;
it is not converted into a successful outcome. The CLI handles KeyboardInterrupt with
request_cancelled and exit 130. Per-tool/overall timeouts use safe error outcomes and
preserve previously recorded bounded evidence. Later batch members are not launched.

Python cannot terminate a thread safely. Draining can take longer than the execution
deadline. Existing SQL connection/pool/lock/statement timeouts and bounded local file
loading limit the supported work, but are not a hard whole-process wall-clock proof.
An unsupported hung extension, unresponsive filesystem or forceful process termination
can defeat graceful cleanup. No new process-isolation infrastructure was introduced.
Native resource-level cancellation/isolation can be revisited if future tools need it.
The approach follows Python's [cancellation and shielding guidance](https://docs.python.org/3.12/library/asyncio-task.html#shielding-from-cancellation).

The existing [agent limit table](agent.md) remains authoritative. AGENT_MAX_MESSAGES
adds a default of 128 and hard bound of 256; minimum is 2. Before tool I/O, the agent
reserves message slots for every member of the returned batch. UTF-8 context/evidence
caps, argument JSON limits, whole-record truncation, total/per-round call limits,
iteration count and provider/tool/overall deadlines remain independently enforced.
No evidence/citation string is sliced mid-record, and final answers are never silently
cut to make a limitation notice fit. Oversized answers with notices are rejected safely.

## Evidence and outcome semantics

Each citation must belong to its returned document; duplicate passage IDs in one result
are invalid. Across rounds, different excerpts for an identical citation or different
values for the same SQL operation/filter scope/row identity trigger evidence_conflict.
Changing a limit does not create a new SQL scope; distinct date/grouping/filter scopes
do. The check is structural and does not detect semantic disagreement between distinct
documents or prove snapshot consistency under concurrent database changes.

All reference/source/numeric checks remain in force. Failed/empty evidence cannot support
a citation. Selected/truncated evidence is flagged even when the model omits a caveat.
Top-N tools mark that additional rows exist; the flag does not mean the requested top-N
ranking is wrong, but those rows must not establish whole-catalog totals.

| Outcome field | Meaning |
| --- | --- |
| status=completed | The loop produced an answer passing mechanical checks; no factual/coverage guarantee |
| partial | Some evidence is failed, empty, selected/truncated, or execution stopped after tool attempts |
| limitations | Stable categories: tool_errors, truncated_evidence, empty_results, execution_stopped |
| pending_tool_calls | Accepted batch calls without a recorded outcome; may include a drained interrupted call |
| status=no_evidence | No successful nonempty evidence, with distinct empty-result versus tool-failure uncertainty |
| status=error | No final answer; prior bounded traces remain inspectable |

Errors preserve useful evidence without claiming that the complete request succeeded.
Important remaining limits: numeric/reference membership is not semantic entailment;
wrong relationships, number words and misleading interpretations may pass. Conflicting
records are not reconciled automatically. There is no factual correctness guarantee.

## Safe failure categories and telemetry

| Trigger | Safe category / behavior |
| --- | --- |
| Missing key/model | configuration_error; no fallback from live to mock |
| Authentication / rate limit / unavailable provider | authentication_error / rate_limit / network_error or provider_error |
| Provider / tool / overall deadline | provider_timeout / tool_timeout / agent_timeout; prior evidence retained |
| Unknown name / invalid JSON or arguments | unknown_tool / invalid_json / invalid_arguments; no unauthorized I/O |
| Database / document failure | database_error or timeout / document_error; safe tool error may be recovered |
| Sensitive content | sensitive_input or sensitive_output; withhold credential-bearing content |
| Exhausted iterations / calls / messages / bytes | iteration_limit / tool_limit / message_limit / context_limit or evidence_limit |
| Invalid citations / conflicting records | grounding_error / evidence_conflict; suppress final answer |
| Caller cancellation / resource-close failure | propagated CancelledError and request_cancelled telemetry / cleanup_error |

Correlated agent_tool_execution and llm_execution events contain generated trace IDs,
mode, status, approved names, iteration/tool counts, duration, error category, limit
reason and pending count where applicable. They exclude questions, raw call IDs,
arguments, document/database bodies, stack traces and provider diagnostic text.

## Verification scope

tests/test_guardrails.py adds deterministic security/reliability cases. Event-based
cancellation tests prove that workers finish before request resource cleanup; they do
not depend on narrow elapsed-time assertions. The existing SDK MockTransport, SQL
permission/cancellation, BM25 filesystem/search, API and Day 6/7 tests remain in use.
No paid OpenAI request is part of the default suite.

Day 9's public HTTP projection removes raw tool arguments/provider call IDs and keeps
credential screening server-side. Streamlit never loads the backend .env or requires
an OpenAI key. Its HTTP client validates responses and bounds bytes, disables redirects
and automatic retries, and displays fixed diagnostics. Retrieved text is rendered as
plain text rather than active HTML/Markdown images. User-entered unknown sensitive data
is still outside a comprehensive anonymization guarantee; use synthetic input only.

Day 8 pip-audit checked 36 installed third-party packages and found no known advisories;
the editable local project was explicitly skipped. The audit utility ran in a temporary
tool environment, without changing project dependencies/lockfile. This checks the
available advisory database at that time, not all vulnerabilities, package provenance,
OS/PostgreSQL/Docker security or application logic. See [progress.md](progress.md) for
actual commands, results, environment repairs, skipped checks and live-verification status.
