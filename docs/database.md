# PostgreSQL development guide

## Setup and dependencies

Day 3 adds SQLAlchemy 2.x for typed models/pooling/transactions, Psycopg 3 (binary wheel)
as the PostgreSQL driver, and Alembic for versioned DDL. No Faker dependency is needed:
Python's local `random.Random(42)` generates explicitly synthetic names and reserved
`example.invalid` email addresses. No real identities or external datasets are used.

Activate Python 3.12 and install `pip install -e '.[dev]'` or use
`uv sync --python 3.12 --extra dev --locked`. Copy `.env.example` to `.env`; choose a
local password and configure:

```dotenv
POSTGRES_USER=querypilot_owner
POSTGRES_PASSWORD=YOUR_LOCAL_PASSWORD
POSTGRES_DB=querypilot
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://querypilot_owner:YOUR_ENCODED_PASSWORD@localhost:5432/querypilot
```

Replace placeholders locally; percent-encode special characters in the URL password.
Compose reads the `POSTGRES_*` entries, while Python reads `DATABASE_URL`. Keep them
consistent. `.env` is ignored. The example deliberately supplies no password. Optional
pool settings use `QUERYPILOT_DB_POOL_SIZE`, `QUERYPILOT_DB_MAX_OVERFLOW`,
`QUERYPILOT_DB_POOL_TIMEOUT`, and `QUERYPILOT_DB_STATEMENT_TIMEOUT_MS`.

```sh
docker compose up -d db
docker compose ps
alembic upgrade head
alembic current
alembic check
python -m querypilot.db.seed --reference-date 2026-10-27 --random-seed 42
python -m querypilot.db.verify --reference-date 2026-10-27 --random-seed 42
```

Compose contains PostgreSQL 16 only, a persistent volume, loopback-only port binding, and
a readiness check. No API deployment container is introduced. Credentials initialize
only a new volume; changing `.env` does not rotate an existing role password.
`docker compose down` preserves data. Do not remove volumes unless deliberately resetting
the development dataset. A native PostgreSQL instance can be used instead by setting
`DATABASE_URL`; migrations and seed commands are identical.

There is no automatic `create_all`. Migration `0001` creates all six tables and indexes
in dependency order; downgrade reverses that order. Review generated migrations before
applying them. The offline DDL command `alembic upgrade head --sql` renders PostgreSQL
DDL without applying it. Do not downgrade a populated database unless intentionally
deleting its data.

## Schema and entity relationships

```mermaid
erDiagram
    customers ||--o{ orders : places
    orders ||--|{ order_items : contains
    products ||--o{ order_items : sold_as
    orders ||--o{ payments : attempted_for
    payments ||--o{ refunds : refunded_by
    customers {
        int customer_id PK
        string name
        string email UK
        string city
        string state
        timestamptz created_at
    }
    products {
        int product_id PK
        string name
        string category
        numeric price
        int stock_quantity
        timestamptz created_at
    }
    orders {
        int order_id PK
        int customer_id FK
        timestamptz order_date
        string status
        numeric total_amount
    }
    order_items {
        int order_item_id PK
        int order_id FK
        int product_id FK
        int quantity
        numeric unit_price
    }
    payments {
        int payment_id PK
        int order_id FK
        numeric amount
        string payment_method
        string payment_status
        timestamptz payment_date
    }
    refunds {
        int refund_id PK
        int payment_id FK
        numeric amount
        string refund_reason
        timestamptz refund_date
    }
```

Each table has an integer primary key and required fields. FKs use PostgreSQL's default
restrictive deletion behavior. Email is unique; each product occurs at most once per
order, with quantity representing repeated units. Indexes cover FK joins, product category,
order status/date, and payment status/date. A partial unique index permits at most one
successful payment per order while allowing failed attempts. Named checks enforce valid
statuses/methods, positive prices/quantities/payment/refund amounts, nonnegative stock,
and nonnegative order totals. Timestamps are `TIMESTAMP WITH TIME ZONE`; generated events
are UTC. Monetary fields are `NUMERIC(12,2)` and Python calculations use Decimal.

## Accounting contract

- Currency is USD; no tax, shipping, fees, or FX conversion is modeled.
- `total_amount = sum(quantity * unit_price)` across all items, for every order status.
  Unit prices are historical snapshots, with half-even cent-rounded synthetic discounts, independent
  of the current catalog price.
- Completed-order revenue is the total of orders whose **current** status is `completed`.
  Exclude pending, cancelled, and fully refunded orders. Monthly grouping uses UTC order
  date. Never subtract refunds again from this already-net completed-order metric.
- Gross settled cash is successful payment amounts. Net settled cash is gross settled
  cash minus refunds. Failed attempts are obligations attempted, not cash collected, and
  never count as revenue. Retry attempts must not multiply order revenue in joins.
- Completed/refunded orders have exactly one successful payment matching the order total.
  Pending orders have no successful payment and may have one failed attempt. Cancelled
  orders have no payment. Some settled orders have a failed attempt before success.
- Refunds reference successful payments, occur after payment, and aggregate to no more
  than that payment's amount. This fixture uses **full-order refunds only**: `refunded`
  orders refund the entire settled amount; other orders have no refund. Partial refunds
  and per-item return records are intentionally deferred.
- Refund totals by category allocate each refund in proportion to original line revenue.
  With full-order refunds, this reconciles exactly to the refunded line values. General
  partial-refund rounding/allocation would need an explicit extension.
- Stock is a synthetic current snapshot, not an inventory ledger. No stock decrement,
  shipment workflow, partial capture, duplicate payment settlement, or accounting ledger
  is modeled. Status-based monthly revenue is an as-of-state view, not historical cash flow.

Row-local rules and relationships are database-enforced. Cross-row amount reconciliation,
event chronology, required item counts, and status/settlement consistency are enforced by
the seed and verifier, **not by database triggers**. Future write workflows must preserve
these invariants transactionally; arbitrary manual admin updates can violate them.

## Reproducibility and rerun behavior

Reference date is mandatory, not read from the system clock. The window is the preceding
twelve calendar months `[reference_date minus one year, reference_date)` in UTC, clamping
February 29 to February 28 when necessary. Orders leave three days before the cutoff for
payment/refund events; every generated event precedes the reference date. A rolling
twelve-month interval can span 13 calendar month buckets, with partial first/last months.

For reference `2026-10-27` and seed `42`, the fixture contains 500 customers, 100 products,
3,000 orders, exactly 6,000 items, 3,006 payments, and 120 refunds. Order status counts are
2,400 completed, 300 pending, 180 cancelled, and 120 refunded. Categories and six US
locations provide variation; identities and product labels are explicitly synthetic.

Generation is pure and repeatable for the same inputs/version. Loading takes one
transaction and a transaction-scoped advisory lock. An exact existing fixture is a no-op;
partial, edited, different-date, or different-seed contents are refused without overwriting
data. Use a separate empty migrated database for a different fixture. Explicit IDs are
followed by SERIAL sequence advancement so future inserts cannot reuse fixture IDs.
Sequence counters themselves are PostgreSQL nontransactional state and may advance if
an insertion fails; row changes still roll back atomically.

## Read-only role provisioning

Migration/seeding uses a writer role. Future agent access must use the distinct
`querypilot_reader` role and `READER_DATABASE_URL`. Day 4's approved tools use this
configuration; see [tools.md](tools.md). Day 3's SQL examples remain developer-only.
After migrations, connect as the table owner/admin using psql's PG environment variables
or local connection options. `psql` needs a `postgresql://` URL, not SQLAlchemy's
`postgresql+psycopg://` URL.

```sh
# Set PGHOST, PGPORT, PGDATABASE, PGUSER and local authentication securely first.
# Prompt interactively so the password is not stored in shell history.
psql -v ON_ERROR_STOP=1
```

Inside psql:

```text
\prompt 'Reader password: ' reader_password
\i data/sample/reader_role.sql
\quit
```

The script safely quotes the password variable, grants CONNECT/schema USAGE/SELECT,
revokes public database privileges (including TEMP) and schema CREATE, and sets reader
read-only/statement-timeout defaults. It is a **one-time** role provisioning script, not
an idempotent role/password reset. Run as the future table owner for default privileges;
defaults apply only to tables created by that owner in public. The database-wide PUBLIC
revocation is intended for this dedicated project database; review it for shared databases.
Future sensitive tables should live outside this analytics-readable scope.

Update `READER_DATABASE_URL` locally with the reader's encoded password. The reader owns
no tables and receives no sequence or write privileges. `create_database(..., reader=True)`
also requests read-only sessions; privileges remain the enforceable boundary even if a
client disables that session default. Never substitute the migration writer URL.

## Verification and developer queries

`querypilot.db.verify` checks all tables, exact generated counts, required PK/FK/unique/check
and index names, orphan references, order totals, settlement/refund amounts, chronology,
and reference-date bounds. It runs in a read-only transaction. It validates the fixture's
accounting, not every business value against a cryptographic snapshot.

```sh
# These tests need no database; Day 1 and Day 2 tests remain included.
pytest -q -m 'not postgres'
# With TEST_DATABASE_URL set to a disposable PostgreSQL database URL:
pytest -q -m postgres
# Or run everything with that variable set:
pytest -q
```

Integration tests create a random isolated schema for each test, apply actual Alembic
migrations, exercise data/constraints, and drop only their own schemas. The test role needs
CREATE SCHEMA permission. No public tables are truncated or dropped. Without
`TEST_DATABASE_URL` these tests are explicitly skipped. Do not use a production database.

Developer-only SQL examples in `data/sample/analytics.sql` cover monthly completed-order
revenue, top products, refund allocation, customer order counts, and failed attempts:

```sh
psql -v ON_ERROR_STOP=1 -f data/sample/analytics.sql
```

Use your PG environment/local authentication for psql. These queries are not registered
as LLM-accessible tools. Day 4's separate registry provides approved, parameterized,
read-only analytics operations with execution/result bounds; it has no LLM integration.
