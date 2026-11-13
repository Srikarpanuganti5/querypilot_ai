# Agent evaluation

Latest review: [final verification](final-verification.md). All 14 failed cases, verified
root causes and improvement priorities are listed in [benchmark-backlog.md](benchmark-backlog.md).
No labels, baselines or mock behavior changed during the final review.

## Reviewed regression gate

`data/evaluations/baseline_day11.json` records the reviewed Day 11 dataset/corpus/fixture
hashes, reference date/seed, source commit and explicit 24 passing/14 failing case IDs.
`.venv/bin/python -m querypilot.evaluation.gate` runs the unchanged dataset against real
tools and compares case verdicts. A previously protected pass becoming a failure blocks
CI even if another case improves and the aggregate pass rate stays unchanged. Missing or
duplicate cases, incompatible hashes/fixture/mode and infrastructure failures fail safely.

Known failures are reported explicitly and do not require a perfect score for a green gate.
New improvements are reported but become protected only through a reviewed baseline update.
Never regenerate the baseline from current outputs during CI. A baseline change requires
explicit review of identity, per-case outcomes and reasons; it must not change gold labels
to match the mock. Native gate result: 24 protected, zero regressions, 14 known failures.
This is a mock-provider regression contract, not live LLM or semantic-accuracy verification.

## Purpose and boundaries

The benchmark measures the existing application rather than a second agent. The runner
calls `services.agent.execute_question`, the same lifecycle used by FastAPI and the ask
CLI. A counted `MultiStepMockProvider` chooses tools; the normal six-tool registry executes
real PostgreSQL/document operations and closes request-owned resources. A separate
`DocumentIndex.search` probe scores retrieval without answer generation. No mock routing
or templates were changed to improve scores.

The initial gap was the absence of a unified versioned dataset, independent factual
references, retrieval/citation separation, denominator-aware failure metrics and reusable
reports. Day 10 integration tests remain the correctness baseline. Day 11 adds dataset
validation → fixture/corpus preflight → shared request execution → deterministic checks →
per-category aggregation → JSON/Markdown reporting.

**MOCK PROVIDER VERIFIED** and **REAL DATABASE VERIFIED** describe this benchmark.
**RETRIEVAL VERIFIED** describes the independent BM25 probe. Mock scores do not measure
live model accuracy. **LIVE OPENAI NOT VERIFIED**: no model requests or judges were used.
Semantic faithfulness and claim-level citation precision are **NOT EVALUATED**.
The runner itself does not establish UI verification.

## Versioned references

`data/evaluations/agent_v1.json` contains 38 cases across 14 categories: product revenue,
revenue summaries, refunds, customers, payments, documents, combined tools, ambiguity,
unsupported requests, empty results, adversarial requests, missing evidence, partial results
and execution limits. Metadata includes difficulty, required/allowed tools, ordering,
evidence kinds, statuses, abstention/partial expectations, facts, product rankings and
policy relevance judgments. All questions and records are synthetic.

`scripts/build_evaluation_dataset.py` reproduces the references with Python Decimal
aggregation over the known synthetic seed, not agent answers or analytics query builders.
References cover all five SQL operations. Policy judgments are curated against the
version-controlled documents. Rebuilding is deliberate development work: update dataset
versions and review references if changing the fixture or policy corpus.

The fixture is pinned to reference date **2026-10-27**, random seed **42**. Before any
SQL-scored run, the restricted reader compares all six tables row-for-row with generated
fixture rows, using bounded code-owned SELECTs and a read-only transaction. A different
seed is rejected before any case executes. No migration, seed, reset or writer fallback
occurs. This is stronger than merely checking counts/accounting. The fixture must remain
unchanged during the run; cases use independent request transactions, not one snapshot.

Reports record dataset and parsed-corpus SHA256 hashes, fixture hash/counts, PostgreSQL
version, Python version, evaluation settings, scenario and provider mode. The corpus hash
includes document metadata, section, citation and excerpt. It identifies content, not the
entire retrieval implementation; preserve the source revision alongside benchmark results.

## Commands and exits

From the repository root, with installed development dependencies, prepared native
PostgreSQL and a configured restricted `READER_DATABASE_URL`:

```sh
.venv/bin/python -m querypilot.cli doctor --reference-date 2026-10-27
.venv/bin/python -m querypilot.cli eval --mode mock --output reports/evaluation/day11
.venv/bin/python -m querypilot.cli eval --category documents --limit 1 --output reports/evaluation/doc-smoke
```

The dataset-builder script is a maintainer operation, not a prerequisite for running the
benchmark. Do not rebuild versioned ground truth during validation.

The full benchmark currently exits **1** because some cases fail their expectations;
reports are still saved. That is a measured benchmark outcome, not a failing pytest suite.
The one-case document command exits **0**. Exit 0 means every selected case passed; 1 means
benchmark failures or a safely reported prerequisite/reporting failure; invalid CLI usage
is 2. Reports distinguish execution and expectation failures. `--dataset`, `--category`,
`--limit` (1–100), `--k` (1–10), `--output` and `--format both|json|markdown` are supported.
Unknown categories and invalid datasets fail safely. No case or paid request is retried.
`--mode live` is explicitly rejected; a future paid evaluation requires separate approval
and implementation. Existing live ask behavior is unchanged.

For dedicated-test verification, load `.local/integration.env` as described in
[testing.md](testing.md). Document-only selection does not require a database or model key;
its reader configuration is cleared so a routing mistake cannot read an unverified database.
Generated reports are ignored under `reports/evaluation/`; their default names are
`results.json` and `results.md`. Use different output directories to preserve earlier runs.
No new project dependency was introduced.

## Tool metrics

Selection uses unique tool names per case; repeated attempts count once in precision and
recall but remain individual attempts in reliability and performance. Required tools are
`expected_tools`. Explicit `allowed_extra_tools` do not create false positives or extra
true positives. Other extra retrieval is penalized because the dataset defines it that way.

- Precision = correct required tools / (correct required tools + disallowed extra tools).
- Recall = correct required tools / required tools.
- F1 = harmonic mean of case precision/recall, zero when both are zero.
- Precision with no scored selection is 1; recall with no required tools is 1. Thus an
  empty expected/selected pair scores 1, while an unexpected call scores precision 0.
- Exact match means all required tools and no disallowed extras.
- Sequence accuracy applies only to ordered cases, using the required sequence as a
  subsequence so explicitly allowed retrieval may interleave. It does not prove reasoning.

Headline precision, recall and F1 are **macro means across every selected case**, not
pooled counts. Reports additionally expose correct/expected/selected unique-tool totals.
Exact/sequence metrics carry numerators and denominators. Per-category metrics retain the
same definitions. Failed cases stay in all applicable denominators.

## Independent retrieval metrics

Each labeled probe supplies a curated retrieval query and relevant document IDs. Search
requests the top 10 passages, deduplicates document IDs in rank order, then takes K (default
5). This measures document relevance within a bounded passage candidate list, not a
separate complete-document ranking algorithm. Multiple chunks of a document do not count
as separate relevant documents.

- Precision@K = relevant returned documents / K, including missing slots in the denominator.
- Recall@K = relevant returned documents / labeled relevant documents.
- Hit Rate@K = fraction of labeled queries with any relevant hit.
- MRR@K = mean reciprocal first-relevant document rank; a miss contributes zero.

Empty relevance lists produce null/N/A metrics, not free perfect scores. The no-match
probe remains disclosed per case and is excluded from labeled retrieval means. Means are
case-weighted; this dataset has 14 labeled probes but only 11 unique labeled query/label
pairs because combined workflows reuse policies. The report discloses both counts.
Each probe currently has one relevant document, so 100% recall with Precision@5 of 20%
is consistent. Relevance judgments are small and do not exhaustively label every passage.

## Facts, citations and faithfulness

SQL references compare a field in an independently identified row, using exact numeric
strings/integers. Product cases additionally check ordered IDs. Where required, an expected
literal must occur with that tool's evidence reference in the answer. Assertions check
specific literal text; they are regression checks, not semantic evaluation.

The numeric check examines citation-terminated answer spans, extracts numeric literals and
tests membership in the referenced successful tool data. Uncited numbers or references to
failed/empty evidence are rejected. It can detect unsupported literals, but cannot establish
the meaning of a number, detect all incorrect attribution inside one span, understand number
words or prove that a true number answers the question. Dates/identifiers can affect literal
matching. Zero detected unsupported numbers is not a faithfulness guarantee.

Citation checks distinguish syntax/corpus existence, actual retrieval/provenance and
claim-level support. Bracketed document IDs must exist in the corpus and map to the document
actually retrieved in successful tool evidence. Required citation coverage and required
document-source coverage use independent case labels. These coverage metrics count required
reference occurrences, not every natural-language claim. Existence/retrieval does not prove
that a source supports a claim. Semantic claim support, universal claim coverage, claim-level
citation precision and LLM-as-judge metrics are **NOT EVALUATED**.

## Reliability and performance

Reports separately count completed status, benchmark passes, partial results, abstentions,
failed tool attempts, provider failures, timeouts, execution limits and negative-case
handling. A completed response may fail the benchmark. An expected controlled failure may
pass the benchmark. Missing-reader and iteration-limit scenarios are explicit configuration
perturbations; they use the real service and are not random infrastructure faults.

Fixed failure groups separate provider configuration/failure, database availability or
permissions, validation, retrieval, citations, execution limits, tool execution and internal
errors. Counts are error events; one case can contain several events. Failure rates use
case or attempted-tool denominators as labeled. `repeated_call` counts prevented duplicates;
the benchmark observes no duplicate attempts, so opportunity/success-rate claims are N/A.
Independent protocol/security tests exercise duplicate handling and error paths.

End-to-end time uses `perf_counter` around shared request execution, including request
resource cleanup, excluding preflight and separate retrieval probes. Summary gives mean,
median, nearest-rank P95, min/max and sample count. Tool times come from existing integer-ms
registry telemetry, so very fast search can report zero. Provider calls are counted at
the mock adapter boundary. Iterations and attempted calls come from the real outcome.
Byte measurements describe the safe outcome projection and serialized tool results, not
network transfer sizes. Observed provider-input JSON bytes are a context proxy, not tokens
or full process memory. All timing is **local mock-provider performance**, not OpenAI
latency, load capacity, statistical significance or a measured optimization.

## Reports and limitations

JSON contains every case, expected/selected tools, status, scenario, check verdicts,
expected/actual fact values, citation checks, retrieval ranking, safe error codes and
timings. Markdown contains headline metrics, per-category comparisons, per-case execution
and failed checks. Neither includes raw tool arguments, prompts, reasoning, credentials,
questions, full database records or document excerpts. Existing SecretGuard screens output
again, and symlinked result files are refused.

Use the actual result snapshot and failure analysis in [progress.md](progress.md). Keep
mock selection weaknesses visible instead of rewriting gold references to match them.
Live model selection, semantic answer quality and judge calibration remain future work.
