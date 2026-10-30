# Secure analytics tools (Day 4)

Five predefined SQLAlchemy SELECT operations are available through a provider-independent
registry and developer CLI. There is no SQL text argument, dynamic tool-registration API,
HTTP analytics endpoint, LLM integration, or chatbot. Existing FastAPI routes are unchanged.
No new dependency is needed beyond Day 3's SQLAlchemy, Psycopg, and Pydantic stack.

```mermaid
flowchart LR
    A[User request] --> B[Tool registry]
    B --> C[Input validation]
    C --> D[Approved SQL operation]
    D --> E[Read-only PostgreSQL]
    E --> F[Validated structured results]
```

## Configure the reader

Migrate and seed with the writer URL first, following [database.md](database.md). Provision
the dedicated reader with the existing `data/sample/reader_role.sql` admin setup script.
It grants CONNECT, schema USAGE, and SELECT on the six analytics tables; revokes PUBLIC
database privileges (including TEMP) and schema CREATE; and sets read-only/timeout defaults.
Run it once as the table owner. Use the Day 3 interactive provisioning instructions;
never commit the password. Existing roles require deliberate password rotation, not a
repeat of CREATE ROLE. Default privileges apply to tables created by that owner only.

Set `.env` locally:

```dotenv
READER_DATABASE_URL=postgresql+psycopg://querypilot_reader:YOUR_ENCODED_PASSWORD@localhost:5432/querypilot
QUERYPILOT_DB_STATEMENT_TIMEOUT_MS=5000
```

Percent-encode special characters in URL credentials. The existing `READER_DATABASE_URL`
is the equivalent of a dedicated agent database URL. `DATABASE_URL` is never consulted
as a fallback. Missing reader configuration produces configuration_error when an SQL
tool is called. Since Day 5, registry creation and document search need no database
configuration; the SQL repository initializes on the first SQL operation. Importing
packages or starting FastAPI does not contact PostgreSQL. See [document search](document_search.md)
for the sixth tool, with separate result fields and no SQL execution.

Each execution sets `SET TRANSACTION READ ONLY`, applies a transaction-local server-side
statement timeout, and checks the authenticated/current role. Elevated flags, role
memberships, database CREATE/TEMP, schema CREATE, table ownership, missing SELECT, or
INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER privileges on the six tables are rejected.
The current role must equal the authenticated session role. The role should be dedicated
to this project and receive no unrelated grants. Checks cover the active analytics schema
and tables; they are not a general audit of every object in the PostgreSQL cluster.

Role/schema checks run on every execution, so privilege changes are not hidden by a
long-lived cache. PostgreSQL privileges enforce write denial even if a client turns off
its read-only default. Runtime queries use SQLAlchemy/Psycopg directly, never shell SQL.
The setup script is an administrator provisioning aid, not a tool execution path.

## Available operations

| Name | Parameters | Returned rows / ordering |
| --- | --- | --- |
| `get_top_products` | `limit=5` (1–20), optional start/end dates | Product ID, product name, category, units, revenue; revenue descending then ID |
| `get_revenue_summary` | optional start/end dates, `group_by=month` (`day`, `month`, `category`) | Bucket, distinct order count, revenue; bucket ascending |
| `get_refund_analytics` | optional start/end dates, `limit=10` (1–20) | Category, distinct refund/order counts, allocated refund amount; amount descending then category |
| `get_customer_order_summary` | optional positive `customer_id`, `limit=10` (1–20) | Customer ID, order/status counts, completed revenue; count descending then ID |
| `get_payment_status_summary` | optional start/end dates | Payment status, attempt count, amount; status ascending |

Customer outputs never select or return names, email, city, or state. A missing customer
returns `rows: []`; an existing customer without orders returns zero aggregates.

Start dates are inclusive UTC midnight; end dates are exclusive UTC midnight. Each bound
is optional independently; omission leaves that side unbounded. Values must be calendar
dates or `YYYY-MM-DD` strings, not datetimes, numeric timestamps, or SQL fragments. When
both dates are supplied, start must precede end and the interval may not exceed 366 days.
Boolean/string limits and IDs, unknown properties, and unknown groupings are rejected.
Customer IDs must fit the positive PostgreSQL integer range.

Top products, refund analytics, and customer summaries return at most the validated limit.
Revenue groups return at most 400 rows; payment status returns at most two. SQL LIMIT and
fetch bounds are applied before output validation. A single extra row detects omitted
results and sets `truncated: true`. A truncated result is not an all-data total; narrow
the question or time range to obtain the relevant groups. There is no pagination yet.

## Accounting rules

- Revenue includes current `completed` orders only. Pending, cancelled, and fully refunded
  orders are excluded. This is completed-order line/order value, already excluding fully
  refunded orders—not gross settled cash. Do not subtract refunds a second time.
- Top-product and category revenue use historical `quantity * unit_price`. Day/month
  summaries use one order row per order, avoiding multiplication by items/payment retries.
- Revenue dates are order dates. Day/month buckets use UTC regardless of server timezone.
  Category order counts are distinct within each category; do not sum them as a global
  order count when one order spans multiple categories.
- Refunds are filtered by **refund date**, not order date. A refund is allocated by each
  category's original line value divided by the order total. The Day 3 fixture has full
  refunds, so allocations reconcile exactly before final cent rounding. Distinct refund
  and order counts are per category and are not additive across categories. Partial refund
  item attribution remains a documented Day 3 simplification.
- Customer order/status counts include all statuses; completed revenue uses only completed
  orders. No payment/item joins inflate these aggregates.
- Payment summaries use **payment date** and count attempts. Successful amounts include
  settled payments for later-refunded orders; failed amounts represent attempted charges,
  not collected money. Never treat the sum of both statuses as revenue.
- All amounts are USD Decimal values and serialize as JSON strings, without float conversion.
  Empty aggregates return an empty row list rather than invented zero-valued periods.

## Calling and demonstrating tools

```python
from querypilot.tools.registry import create_registry

registry = create_registry()
try:
    result = registry.execute("get_top_products", {"limit": 5})
    print(result.model_dump_json())
finally:
    registry.close()
```

```sh
python -m querypilot.tools get_top_products --arguments '{"limit":5}'
python -m querypilot.tools get_revenue_summary --arguments '{"start_date":"2026-01-01","end_date":"2026-02-01","group_by":"month"}'
python -m querypilot.tools get_refund_analytics
python -m querypilot.tools get_customer_order_summary --arguments '{"customer_id":156}'
python -m querypilot.tools get_payment_status_summary
```

CLI success exits 0; structured errors exit 1. The envelope has `tool`, `status`, `data`,
`error`, and `duration_ms`. Successful data includes `operation`, `currency`, `truncated`,
and typed `rows`. An error has a stable code and safe message, with no data. Unknown
operation names return `tool: null` rather than echoing untrusted text. `definitions()`
returns descriptions and input/output JSON schemas; it does not register provider tools.

Possible error codes: unknown_tool, invalid_arguments, configuration_error (SQL or CLI setup),
unsafe_database, timeout, database_error, invalid_output, internal_error. Driver errors,
SQL strings, URLs, raw arguments, and validation input values are excluded from results.
JSON application logs include approved tool name (or `unknown`), status, and elapsed time.
The CLI configures logging; Python callers should use the application's logging setup.

The timeout is **per PostgreSQL statement**, not a hard end-to-end tool deadline. Role
checks execute several short statements before the analytics SELECT. Existing connection
and pool-wait bounds still apply. A broad historical query can scan more data than it
returns; server-side cancellation and bounded results limit that work. Tools are synchronous
developer/backend operations; no async agent scheduler or request-level budget is added yet.
The server settings follow PostgreSQL's
[statement timeout/read-only transaction semantics](https://www.postgresql.org/docs/16/runtime-config-client.html).

## Tests

```sh
# No database required:
pytest -q -m 'not postgres'
# Existing migration tests need TEST_DATABASE_URL (writer).
# New restricted-role tests additionally need TEST_READER_DATABASE_URL.
# Set both to the same expendable PostgreSQL database, with different users:
pytest -q -m postgres
# Full suite:
pytest -q
```

The writer test role needs permission to create/drop isolated schemas and grant SELECT
to the separately provisioned reader. It does not need to create/drop roles. Tests migrate
a fresh random schema, grant reader USAGE/SELECT, and remove only that schema afterward.
If either URL is missing, the corresponding integration cases explicitly skip. No public
business rows are changed by the tests. Do not use production database URLs.

Integration tests exercise all five tools with independently hand-calculated fixtures,
UTC boundaries, tie ordering, category count semantics, empty/missing customers, privacy,
result truncation, actual PostgreSQL timeout/cancellation recovery, and writer rejection.
Direct INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TEMP attempts run only in permission tests
and must fail with PostgreSQL insufficient-privilege code `42501`, even after turning
read-only mode off. No tool has a write or sleep operation. A trusted test-only query
replacement induces `pg_sleep` to verify timeout handling; callers cannot supply it.
