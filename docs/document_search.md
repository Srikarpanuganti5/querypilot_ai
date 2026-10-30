# Local business document search (Day 5)

`search_business_documents` is the sixth approved tool. It retrieves real Markdown passages
from a local synthetic business collection; it does not generate an answer, execute text,
connect to an external service, or modify PostgreSQL. No dependency was added: the BM25
implementation uses Python's standard library and existing Pydantic schemas.

## Collection and accounting consistency

`data/documents/` contains ten fictional QueryPilot Demo Store policies, indexed into
40 heading-based chunks. Each file has `document_id`, `title`, and `category` metadata
between `---` delimiters, followed by Markdown headings and actual content.

| Category | Document ID | Subject |
| --- | --- | --- |
| refunds | QP-RET-001 | Return window, full refunds, refund reporting |
| shipping | QP-SHP-002 | Fictional delivery targets and missing shipment data |
| payments | QP-PAY-003 | Failed attempts, successful settlement, cash versus revenue |
| cancellations | QP-CAN-004 | Pending cancellations and paid-order reversals |
| products | QP-CAT-005 | Five product categories and historical unit prices |
| support | QP-SUP-006 | Fictional support cases, privacy and escalation |
| discounts | QP-DSC-007 | Generator's 0/5/10-percent pricing and Decimal rounding |
| fraud | QP-FRD-008 | Illustrative manual review and sensitive-data handling |
| inventory | QP-INV-009 | Stock snapshots, proposed reorder threshold, missing ledger |
| faq | QP-FAQ-010 | Explicit reference dates, metric meanings and capability limits |

Policies preserve Day 3 assumptions: USD item totals, completed-only revenue, full-order
refunds against successful payments, failed attempts excluded from cash received, and
nonnegative inventory snapshots without a movement ledger. Delivery/support/fraud rules
are expressly illustrative: no tracking, ticket or fraud-event records are fabricated.
The 30-day return policy is not claimed to be inferable from the existing schema.

## Calling the tool

Run from the repository root after the normal editable installation:

```sh
python -m querypilot.tools search_business_documents --arguments '{"query":"What is the return window for products?"}'
python -m querypilot.tools search_business_documents --arguments '{"query":"How are failed payments handled?","top_k":1}'
python -m querypilot.tools search_business_documents --arguments '{"query":"When can customers cancel an order?","category":"cancellations"}'
```

```python
from querypilot.tools.registry import create_registry

registry = create_registry()
try:
    result = registry.execute(
        "search_business_documents",
        {"query": "What is the refund policy?", "top_k": 5, "category": "refunds"},
    )
    print(result.model_dump_json())
finally:
    registry.close()
```

Arguments: nonblank string `query` (maximum 500 characters), strict integer `top_k`
(default 5, range 1–10), and optional category from the table above. Extra keys such as
`path`, `documents_path`, or `sql` are rejected. Unknown tool names remain rejected.

The existing success/error envelope is retained. Search data contains `operation`,
`matches`, index document/chunk counts, and `content_trust: "untrusted"`. Each hit contains
document ID/title/category, section heading, an original-text excerpt, a positive BM25
score and a citation such as `QP-RET-001#s002-c001`. Currency and analytics rows are not
invented for document results. Invalid arguments yield invalid_arguments; an unavailable
or malformed collection yields document_error, without filesystem paths or raw content.

Search requires neither DATABASE_URL nor READER_DATABASE_URL. Registry creation is now
lazy for both index and SQL repository. An SQL call still requires the restricted reader
and fails with configuration_error when absent; it never falls back to writer credentials.
All five existing SQL operations and their privilege checks are retained. Document failures
do not prevent SQL dispatch, and database configuration is not consulted during search.

## Ingestion and filesystem boundary

The trusted operator configures `QUERYPILOT_DOCUMENTS_PATH` (default `data/documents`).
The tool accepts no directory, filename, citation-as-path, or URL. Run from the repository
root or configure the absolute approved corpus location. Documents are repository assets,
not bundled into the Python wheel; a wheel-only deployment must supply its own approved
copy and configuration. No upload endpoint or network downloader is introduced.

The loader opens the directory once, enumerates only immediate `.md` files, and uses
descriptor-relative `O_NOFOLLOW` opening for files and the final directory component.
It rejects symlinks, hard-linked entries, directories, devices/FIFOs, unsupported types,
invalid UTF-8 and oversized files. Files are read through the checked descriptor, avoiding
the usual resolve-then-open leaf-symlink race. Ancestor directories and the configured root
are trusted operator infrastructure, not an untrusted user choice. This safe loader
requires POSIX descriptor-relative/no-follow support and fails closed without it.

Limits: 50 Markdown candidates, 64,000 bytes per file, 500 indexed chunks, 1,200 characters
per excerpt, 120 per title, and 200 per section heading. The collection is deliberately
small and nonrecursive. Empty/unsupported/unsafe files are skipped with an internal count;
malformed nonempty metadata, duplicate document IDs or collection-limit violations fail
the index build. A missing directory returns document_error; an existing empty directory
is a valid empty index and searches return no hits.

Metadata parsing is a small literal key/value format, not YAML object loading. It requires
exact approved fields and categories. Sections are split at Markdown headings outside
fenced code; long sections split at paragraph/space boundaries, with a hard character
fallback. Section text is preserved apart from line-ending/edge-whitespace normalization.
IDs/citations derive
from validated metadata and deterministic section/part ordinals, never filesystem paths.
They identify passages within an index snapshot, not immutable references across edits.

The first valid search loads a snapshot cached on that registry instance. Recreate the
registry to reindex after edits. There is no background watcher, persistent index, or
cross-process cache. Importing packages or starting FastAPI does not build the index.

## Ranking

Tokenization uses Unicode NFKC, case folding, ASCII alphanumeric tokens, and a fixed English
stopword list. Title, section heading and excerpt form each indexed passage. There is no
stemming, synonym expansion, spelling correction or semantic model.

BM25 uses k1=1.5, b=0.75 and positive smoothed IDF
`log(1 + (N - df + 0.5)/(df + 0.5))`. Query terms are deduplicated. Category filtering limits
candidate passages while keeping whole-corpus statistics. Zero-overlap and stopword-only
queries return empty results. Scores sort descending, then by citation for ties, and are
rounded to eight decimal places in the response. The same corpus/pipeline produces the
same rankings. The method follows the BM25 framework described by
[Robertson and Zaragoza](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf),
with the positive-IDF variant stated explicitly here.

Several chunks from the same document can appear in the top results; no per-document
deduplication is applied. Scores are ranking signals, not confidence probabilities.
Lexical overlap alone cannot guarantee that a passage answers every part of a question.

## Security and untrusted content

Retrieved text is always data. It is never passed to a shell, Python evaluator, database
executor, network API or model. The search branch never creates a database engine. A
document containing command-like instructions is returned only as an untrusted quotation.
Day 6 must preserve this boundary when adding model instructions; retrieval is not
authorization and no prompt-injection immunity is claimed.

Execution logs include only approved tool name, status and elapsed time; no query or
document content. Results intentionally expose approved corpus passages, so the corpus
must contain synthetic, publicly shareable material only. Filesystem restrictions are
not a content classifier or a sandbox against a compromised operator account.

## Tests and evaluation

```sh
pytest -q -m 'not postgres'
python -m querypilot.services.evaluate_search
# With the existing TEST_DATABASE_URL and TEST_READER_DATABASE_URL configured:
pytest -q
ruff check .
ruff format --check .
```

The fixed `data/evaluations/document_search.json` has 20 questions and expected relevant
document IDs. The evaluator runs actual registry searches at k=5. Hit Rate@5 is the
fraction of questions having a relevant document among the first five passages. MRR@5
averages the reciprocal rank of the first relevant passage, or zero for a miss. Duplicate
chunks from one document occupy real rank positions. Unknown relevance IDs fail evaluation.

Measured on this authored collection: **Hit Rate@5 = 1.0, MRR@5 = 1.0 (20 questions)**.
These are small curated regression results, not a held-out benchmark or a claim about
general business questions. Tests enforce a modest baseline and independently verify
metric arithmetic; actual per-question ranks are printed by the evaluation command.
