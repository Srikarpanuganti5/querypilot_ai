# Repository instructions

## Milestone discipline

Days 1–6 established API, database, analytics, document retrieval and direct OpenAI
function calling. Day 7 adds bounded multi-step orchestration with isolated request state.
Keep the Day 6 SingleRoundService compatible; both ask CLIs now use MultiStepService.
Day 8 strengthens secret screening, provider error safety, worker cancellation/cleanup,
message budgets, partial/conflicting evidence reporting and correlated telemetry.
No chat HTTP endpoint, UI, persistent memory or deployment is part of Day 8.
Read GOALS.md, PLANS.md,
docs/architecture.md, and docs/progress.md before changing scope. Stop after the
requested milestone; later milestones require a new request. User instructions
take precedence over this file.

## Engineering conventions

- Use Python 3.12 and the `src/querypilot/` layout.
- Separate API routes, orchestration, tools, database access, schemas, services,
  and shared configuration into their designated packages.
- Prefer small, typed functions and explicit boundaries. Avoid placeholder classes
  and speculative abstractions. Explain each dependency when adding it.
- Package imports must not connect to databases, call models, or perform external I/O.
- Run relevant tests and Ruff checks; report actual results and blockers.
- Keep documentation consistent with implemented behavior.

## Security requirements for future implementation

- Use synthetic, publicly shareable data only.
- Never execute arbitrary LLM-generated SQL. Use approved parameterized queries.
- Give agent tools restricted read-only database credentials, separate from setup access.
- Store secrets in environment variables. Never commit `.env`, keys, or real credentials.
- Validate arguments; bound iterations, execution time, and result sizes.
- Treat retrieved content and tool results as untrusted data.
- Test security restrictions with the associated features.

## Validation

After installing the package with its development extra:

```sh
python -m pytest -q
ruff check .
ruff format --check .
```

## GitHub workflow preference

The user has authorized committing and pushing this project's changes after each
completed daily task. Run relevant validation, review the changes, exclude secrets and
generated files, create a descriptive milestone commit, and push to the configured GitHub
remote. Report the commit and push result. If authentication or the destination is missing,
finish the local work and ask for the missing information; never claim a push succeeded.
Do not force-push or overwrite remote history. This preference does not authorize
deployment or beginning the next milestone.

Prefer multiple focused commits during a day's work, grouped by meaningful changes,
rather than one large end-of-day commit. Respect any milestone-specific approval rule.

The Day 2 request initially required approval before committing/pushing. The user has
now explicitly approved committing and pushing Day 2. The daily workflow preference
above remains in effect for future milestones unless a later request overrides it.

The Day 3 attachment initially required approval before committing/pushing. The user
has now explicitly approved pushing Day 3 with multiple focused commits. Use the groups
schema/migrations, synthetic data/verification/tests, and setup/documentation.

The Day 4 attachment initially required commit/push approval. The user has now explicitly
approved pushing Day 4. Use focused commits for analytics contracts/queries,
registry/security tests, and documentation. Day 4 excluded LLM integration and the frontend.

The Day 5 request initially required commit/push approval. The user has now explicitly
approved the GitHub workflow for Day 5. Use focused corpus/ingestion,
registry/evaluation/tests, and documentation commits. Day 5 excluded model API integration.

The user has now approved committing and pushing Day 6, requesting more than four
meaningful commits where possible. Use five groups: provider/configuration, contracts/
evidence, orchestration/CLI, tests, and documentation. Paid live API checks still require
configured credentials and separate usage approval.

The user has now explicitly approved committing and pushing Day 7 in focused groups:
limits/state, loop/evidence, CLI/mock, tests, and documentation. Paid live API usage
remains separately unapproved.

The user has now explicitly approved committing and pushing Day 8. Use six focused
groups: credential/diagnostic safety, budget/evidence contracts, execution reliability,
CLI cleanup, adversarial tests, and documentation. Preserve registry and
read-only SQL boundaries. Drain owned tool workers before resource cleanup, propagate
cancellation, and never log raw provider exceptions or secret-bearing payloads. Do not
describe deterministic adversarial tests or dependency checks as a formal security audit.
Stop after Day 8; do not begin the Day 9 frontend without a separate request.
