# LinkedIn launch assets — drafts for user review

**Not published or uploaded.** Final wording, carousel content and video script require
user review after Day 14. No screenshots or recording have been captured. Use the latest
[verification](final-verification.md) before making any metric public.

## Launch post draft

I built QueryPilot AI as a Python backend engineering project: business questions enter a
FastAPI API, approved tools query PostgreSQL or retrieve policy passages, and Streamlit
shows the answer with inspectable evidence.

The work covered more than the answer-generation path: API contracts, Alembic migrations,
read-only database permissions, bounded tool orchestration, safe errors, reproducible
fixtures, Docker Compose and GitHub Actions.

One useful debugging lesson was a configuration gap: separately configured tests worked,
but the normal backend had no reader credentials. Distinguishing liveness from readiness
and making setup reproducible helped diagnose the actual failure.

The current suite passes 470 tests, including 56 real PostgreSQL tests. A separate 38-case
mock-provider benchmark passes 24 cases. The 14 failures remain documented; the regression
gate protects the existing passes. That score is not live LLM accuracy.

The demo uses synthetic data and a deterministic mock selector with real SQL and document
retrieval. It runs privately in Docker; live OpenAI and manual browser acceptance remain
pending. Public hosting needs additional access controls and operational work.

Source: https://github.com/Srikarpanuganti5/querypilot_ai

My next engineering priorities are filter handling, routing/abstention and independently
reviewed answer-support evaluation. Feedback on the backend design and test strategy is welcome.

## Five-slide carousel outline

| Slide | Content | Evidence to use |
| --- | --- | --- |
| 1 — QueryPilot AI | Business analytics with inspectable SQL/policy evidence; label private mock demo | Genuine application viewport after manual review |
| 2 — Architecture | Streamlit → FastAPI → bounded agent → registry → PostgreSQL/BM25 → evidence | Mermaid diagram in architecture.md; no invented cloud components |
| 3 — Engineering and reliability | Typed contracts, fixed SQL, reader role, deadlines, 470 tests/56 PG, Docker and CI | Latest verification and actual CI run, with source revision/date |
| 4 — Debugging challenge | Healthy process plus missing reader settings; readiness and repeatable setup exposed it | Safe diagnostic explanation; no environment/credential screenshot |
| 5 — Outcome and next steps | Private working tools, 24/38 mock benchmark, 14 known failures, live/manual pending | Repository link and honest limitation/backlog labels |

This is an outline, not a rendered carousel. Keep text readable, preserve qualifiers and
review final slide metrics before export or upload.

## 30–45 second video script draft

| Time | Actual action | Suggested narration |
| --- | --- | --- |
| 0–5 s | Show Streamlit with Mock demo label | “QueryPilot connects business questions to approved backend tools.” |
| 5–17 s | Submit top-five revenue question and expand SQL table | “These results come from the real synthetic PostgreSQL fixture through read-only analytics.” |
| 17–28 s | Ask the return-policy question; show exact citation | “Policy retrieval returns the supporting passage and source ID.” |
| 28–36 s | Briefly show tool trace and architecture | “FastAPI owns validation, execution limits and evidence checks.” |
| 36–45 s | Show reviewed test summary and source link | “470 tests include 56 PostgreSQL checks. Private mock demo; live model quality is unverified.” |

Capture real interactions and label edited waits. Retain the selected-record warning. Do
not show environment files, raw container inspection or fabricated outputs. The separate
24/38 benchmark limitation must stay visible in the post/carousel even if the clip is short.

## Exact screenshots to capture later

1. Top-five revenue answer with ranked table and limited-selection notice.
2. Return policy passage with `QP-RET-001#s002-c001` visible.
3. Combined question expanded to show both SQL and document evidence/tool status.
4. Architecture diagram exported from actual repository Markdown.
5. Safe test/CI summary showing commit and result, never logs with environment values.

Use only the app viewport or reviewed diagrams. Store captures in an ignored private
location until reviewed; screenshots are not evidence of uncaptured interactions.

## Launch checklist

- [ ] Recheck final counts, coverage, fixture and benchmark against the source revision.
- [ ] Review repository diff and all public assets for credentials/private data.
- [ ] Obtain approval to commit/push Day 14; no such approval is assumed.
- [ ] Verify GitHub Actions for the latest published commit after that push.
- [ ] Complete and record the manual browser checklist in demo.md.
- [ ] Capture genuine demo video and screenshots; review edits/qualifiers.
- [ ] Prepare and review the five slides.
- [ ] Review the final LinkedIn wording with the user.
- [ ] State private local access, synthetic data and mock/live boundaries clearly.
- [ ] Obtain explicit publication approval before any upload/post.
