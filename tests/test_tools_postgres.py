"""Real analytics/privilege tests require writer AND restricted reader URLs."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, func, insert, select, text
from sqlalchemy.exc import DBAPIError

from querypilot.core.logging import configure_logging
from querypilot.db import analytics
from querypilot.db.analytics import AnalyticsRepository
from querypilot.db.models import Base, Customer, Order
from querypilot.db.session import Database
from querypilot.tools.registry import ToolRegistry
from tests.postgres_support import test_urls

pytestmark = pytest.mark.postgres
JANUARY = {"start_date": "2026-01-01", "end_date": "2026-02-01"}


@pytest.fixture
def stores() -> Iterator[tuple[ToolRegistry, Database, Database]]:
    configure_logging("INFO")
    writer_url, reader_url = test_urls()
    admin = create_engine(writer_url, hide_parameters=True)
    schema = f"querypilot_tools_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    writer = Database(
        create_engine(
            writer_url, hide_parameters=True, connect_args={"options": f"-csearch_path={schema}"}
        )
    )
    reader = Database(
        create_engine(
            reader_url,
            hide_parameters=True,
            connect_args={
                "options": f"-csearch_path={schema} "
                "-cdefault_transaction_read_only=on -cstatement_timeout=5000"
            },
        )
    )
    try:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with writer.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with reader.engine.connect() as connection:
            role = connection.scalar(text("SELECT current_user"))
        with admin.begin() as connection:
            quoted = connection.dialect.identifier_preparer.quote(role)
            connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO {quoted}'))
            for name in Base.metadata.tables:
                connection.execute(text(f'GRANT SELECT ON "{schema}"."{name}" TO {quoted}'))
        yield ToolRegistry(AnalyticsRepository(reader)), writer, reader
    finally:
        reader.close()
        writer.close()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def _populate(database: Database) -> None:
    def when(value: str) -> datetime:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)

    created = when("2025-01-01")
    data = {
        "customers": [
            {
                "customer_id": key,
                "name": "PRIVATE_NAME",
                "email": f"private{key}@example.invalid",
                "city": "PRIVATE_CITY",
                "state": "TX",
                "created_at": created,
            }
            for key in (1, 2)
        ],
        "products": [
            {
                "product_id": key,
                "name": f"Product {key}",
                "category": category,
                "price": Decimal("10.00"),
                "stock_quantity": 10,
                "created_at": created,
            }
            for key, category in ((1, "Home"), (2, "Office"))
        ],
        "orders": [
            {
                "order_id": key,
                "customer_id": 1,
                "order_date": when(day),
                "status": status,
                "total_amount": Decimal(total),
            }
            for key, day, status, total in [
                (1, "2026-01-01", "completed", "30"),
                (2, "2026-01-31T23:59:00", "completed", "10"),
                (3, "2026-02-01", "completed", "100"),
                (4, "2026-01-15", "cancelled", "1000"),
                (5, "2026-01-10", "refunded", "20"),
                (6, "2026-01-20", "pending", "25"),
            ]
        ],
        "order_items": [
            {
                "order_item_id": key,
                "order_id": order,
                "product_id": product,
                "quantity": quantity,
                "unit_price": Decimal(price),
            }
            for key, (order, product, quantity, price) in enumerate(
                [
                    (1, 1, 2, "10"),
                    (1, 2, 1, "10"),
                    (2, 2, 1, "10"),
                    (3, 1, 1, "100"),
                    (4, 1, 1, "1000"),
                    (5, 2, 2, "10"),
                    (6, 1, 1, "25"),
                ],
                1,
            )
        ],
        "payments": [
            {
                "payment_id": key,
                "order_id": order,
                "amount": Decimal(amount),
                "payment_method": "card",
                "payment_status": status,
                "payment_date": when(day),
            }
            for key, (order, amount, status, day) in enumerate(
                [
                    (1, "30", "failed", "2026-01-01T01:00:00"),
                    (1, "30", "successful", "2026-01-01T02:00:00"),
                    (2, "10", "successful", "2026-01-31T23:59:00"),
                    (3, "100", "successful", "2026-02-01T01:00:00"),
                    (5, "20", "successful", "2026-01-10T01:00:00"),
                    (6, "25", "failed", "2026-01-20T01:00:00"),
                ],
                1,
            )
        ],
        "refunds": [
            {
                "refund_id": 1,
                "payment_id": 5,
                "amount": Decimal("20"),
                "refund_reason": "Synthetic full return",
                "refund_date": when("2026-02-02"),
            }
        ],
    }
    with database.transaction() as session:
        for table in Base.metadata.sorted_tables:
            session.execute(insert(table), data[table.name])


@pytest.fixture
def populated(stores: tuple) -> tuple:
    _populate(stores[1])
    return stores


def test_top_products_dates_ties_and_truncation(populated: tuple) -> None:
    registry, _, _ = populated
    result = registry.execute("get_top_products", JANUARY)
    assert result.status == "success", result.error
    assert [row.product_id for row in result.data.rows] == [1, 2]
    assert [row.revenue for row in result.data.rows] == [Decimal("20.00"), Decimal("20.00")]
    limited = registry.execute("get_top_products", {**JANUARY, "limit": 1})
    assert limited.data.truncated
    assert len(limited.data.rows) == 1


@pytest.mark.parametrize("group_by", ["day", "month", "category"])
def test_revenue_counts_without_payment_multiplication(populated: tuple, group_by: str) -> None:
    result = populated[0].execute("get_revenue_summary", {**JANUARY, "group_by": group_by})
    assert result.status == "success", result.error
    assert sum(row.revenue for row in result.data.rows) == Decimal("40.00")
    expected_count = 3 if group_by == "category" else 2
    assert sum(row.order_count for row in result.data.rows) == expected_count


def test_refunds_use_refund_date_and_preserve_amount(populated: tuple) -> None:
    january = populated[0].execute("get_refund_analytics", JANUARY)
    assert january.status == "success", january.error
    assert january.data.rows == []
    result = populated[0].execute("get_refund_analytics", {"start_date": "2026-02-01"})
    assert result.data.rows[0].category == "Office"
    assert result.data.rows[0].refund_amount == Decimal("20.00")
    assert result.data.rows[0].refund_count == 1


def test_customer_privacy_missing_and_zero_orders(populated: tuple) -> None:
    registry = populated[0]
    result = registry.execute("get_customer_order_summary", {"customer_id": 1})
    assert result.status == "success", result.error
    row = result.data.rows[0]
    assert row.order_count == 6
    assert row.completed_orders == 3
    assert row.completed_revenue == Decimal("140.00")
    assert row.refunded_orders == row.cancelled_orders == row.pending_orders == 1
    assert "PRIVATE" not in result.model_dump_json()
    assert registry.execute("get_customer_order_summary", {"customer_id": 999}).data.rows == []
    assert (
        registry.execute("get_customer_order_summary", {"customer_id": 2}).data.rows[0].order_count
        == 0
    )


def test_payment_attempts_and_dates(populated: tuple) -> None:
    result = populated[0].execute("get_payment_status_summary", JANUARY)
    assert result.status == "success", result.error
    rows = {row.payment_status: row for row in result.data.rows}
    assert rows["successful"].payment_count == 3
    assert rows["successful"].amount == Decimal("60.00")
    assert rows["failed"].payment_count == 2
    assert rows["failed"].amount == Decimal("55.00")


def test_empty_database_all_tools(stores: tuple) -> None:
    sql_names = [name for name in stores[0].definitions() if name != "search_business_documents"]
    assert len(sql_names) == 5
    for name in sql_names:
        result = stores[0].execute(name, {})
        assert result.status == "success", result.error
        assert result.data.rows == []


def test_revenue_result_size_is_bounded(stores: tuple) -> None:
    # An all-history query may span >400 days; it must still bound returned groups.
    with stores[1].transaction() as session:
        session.execute(
            insert(Customer),
            [
                {
                    "customer_id": 1,
                    "name": "Synthetic",
                    "email": "test@example.invalid",
                    "city": "Austin",
                    "state": "TX",
                    "created_at": datetime(2023, 1, 1, tzinfo=UTC),
                }
            ],
        )
        session.execute(
            insert(Order),
            [
                {
                    "order_id": index + 1,
                    "customer_id": 1,
                    "status": "completed",
                    "total_amount": Decimal("1.00"),
                    "order_date": datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=index),
                }
                for index in range(405)
            ],
        )
    result = stores[0].execute("get_revenue_summary", {"group_by": "day"})
    assert result.status == "success", result.error
    assert len(result.data.rows) == 400
    assert result.data.truncated


def test_writer_credentials_are_rejected(stores: tuple) -> None:
    result = ToolRegistry(AnalyticsRepository(stores[1])).execute("get_top_products", {})
    assert result.status == "error"
    assert result.error.code == "unsafe_database"


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO products(product_id,name,category,price,stock_quantity,created_at) "
        "VALUES (999,'bad','bad',1,1,now())",
        "UPDATE products SET price=1 WHERE false",
        "DELETE FROM orders WHERE false",
        "DROP TABLE products",
        "ALTER TABLE products ADD COLUMN forbidden integer",
        "CREATE TABLE forbidden (id integer)",
        "CREATE TEMP TABLE forbidden_temp (id integer)",
    ],
)
def test_reader_privileges_block_writes_even_if_readonly_disabled(
    stores: tuple, statement: str
) -> None:
    with stores[2].engine.connect() as connection:
        connection.execute(text("SET default_transaction_read_only=off"))
        connection.commit()
        with pytest.raises(DBAPIError) as error, connection.begin():
            connection.execute(text("SET TRANSACTION READ WRITE"))
            connection.execute(text(statement))
        assert error.value.orig.sqlstate == "42501"


def test_transaction_is_read_only_and_real_timeout_is_recoverable(
    stores: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = AnalyticsRepository(stores[2], timeout_ms=100)
    registry = ToolRegistry(repository)
    with stores[2].engine.connect() as connection:
        connection.execute(text("SET default_transaction_read_only=off"))
        connection.commit()
    observed = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("SELECT pg_sleep"):
            cursor.execute("SHOW transaction_read_only")
            observed.append(cursor.fetchone()[0])

    event.listen(stores[2].engine, "before_cursor_execute", observe)
    try:
        with monkeypatch.context() as patch:
            # Trusted test-only replacement; no caller-supplied SQL/query option exists.
            def slow_query(args: object) -> object:
                assert args.limit == 5
                return select(func.pg_sleep(0.3))

            patch.setitem(analytics._BUILDERS, "get_top_products", slow_query)
            result = registry.execute("get_top_products", {})
    finally:
        event.remove(stores[2].engine, "before_cursor_execute", observe)
    assert observed == ["on"]
    assert result.error.code == "timeout"
    assert stores[2].engine.pool.checkedout() == 0
    assert registry.execute("get_top_products", {}).status == "success"
