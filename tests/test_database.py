"""Database unit tests: no PostgreSQL or SQLite connections."""

from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import DateTime, Numeric
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable

from querypilot.core.config import Settings
from querypilot.db.models import Base, Customer, Order, OrderItem, Payment, Product, Refund
from querypilot.db.seed import EXPECTED_COUNTS, generate_dataset, reference_window
from querypilot.db.session import DatabaseError, create_database

REFERENCE = date(2026, 10, 27)


def test_models_have_types_relationships_and_constraints() -> None:
    assert set(Base.metadata.tables) == {
        "customers",
        "products",
        "orders",
        "order_items",
        "payments",
        "refunds",
    }
    configure_mappers()
    assert Customer.orders.property.back_populates == "customer"
    assert Order.items.property.back_populates == "order"
    assert Product.order_items.property.back_populates == "product"
    assert Payment.refunds.property.back_populates == "payment"
    for table in Base.metadata.tables.values():
        assert len(table.primary_key.columns) == 1
        assert all(constraint.name for constraint in table.constraints)
        assert "CREATE TABLE" in str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for column in table.columns:
            assert not column.nullable
            if isinstance(column.type, DateTime):
                assert column.type.timezone
            if isinstance(column.type, Numeric):
                assert column.type.scale == 2
    assert len(OrderItem.__table__.foreign_keys) == 2
    assert len(Refund.__table__.foreign_keys) == 1
    assert any(index.unique for index in Payment.__table__.indexes)


def test_seed_reproducibility_and_target_counts() -> None:
    first = generate_dataset(REFERENCE)
    assert first == generate_dataset(REFERENCE)
    assert first != generate_dataset(REFERENCE, random_seed=43)
    for name, count in EXPECTED_COUNTS.items():
        assert len(first[name]) == count
    assert len({row["email"] for row in first["customers"]}) == 500
    assert all(row["email"].endswith("@example.invalid") for row in first["customers"])
    assert Counter(row["status"] for row in first["orders"]) == {
        "completed": 2400,
        "pending": 300,
        "cancelled": 180,
        "refunded": 120,
    }


def test_seed_money_references_and_event_order() -> None:
    data = generate_dataset(REFERENCE)
    orders = {row["order_id"]: row for row in data["orders"]}
    totals = defaultdict(lambda: Decimal("0.00"))
    for item in data["order_items"]:
        assert 1 <= item["product_id"] <= 100
        assert isinstance(item["unit_price"], Decimal)
        totals[item["order_id"]] += item["quantity"] * item["unit_price"]
    start, end = reference_window(REFERENCE)
    for order in orders.values():
        assert order["total_amount"] == totals[order["order_id"]]
        assert 1 <= order["customer_id"] <= 500
        assert start <= order["order_date"] < end
        assert order["order_date"].tzinfo == UTC
    payments = {row["payment_id"]: row for row in data["payments"]}
    for payment in payments.values():
        order = orders[payment["order_id"]]
        assert payment["amount"] == order["total_amount"]
        assert order["order_date"] <= payment["payment_date"] < end
    refunded = defaultdict(lambda: Decimal("0.00"))
    for refund in data["refunds"]:
        payment = payments[refund["payment_id"]]
        assert payment["payment_status"] == "successful"
        assert payment["payment_date"] <= refund["refund_date"] < end
        refunded[payment["payment_id"]] += refund["amount"]
    assert all(amount <= payments[key]["amount"] for key, amount in refunded.items())


def test_reference_window_clamps_leap_day() -> None:
    start, end = reference_window(date(2024, 2, 29))
    assert start == datetime(2023, 2, 28, tzinfo=UTC)
    assert end == datetime(2024, 2, 29, tzinfo=UTC)


def test_connection_is_lazy_and_secrets_redacted() -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://u:SECRET@localhost/db")
    assert "SECRET" not in repr(settings)
    database = create_database(settings)
    try:
        assert database.engine.pool.checkedout() == 0
        assert database.engine.hide_parameters
        assert database.engine.pool.size() == settings.db_pool_size
    finally:
        database.close()


@pytest.mark.parametrize("url", [None, "", "sqlite://", "not a connection URL"])
def test_missing_or_unsupported_url_is_safe(url: str | None) -> None:
    with pytest.raises(DatabaseError):
        create_database(Settings(_env_file=None, database_url=url))


def test_reader_requires_distinct_configuration() -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://writer@localhost/db")
    with pytest.raises(DatabaseError, match="READER_DATABASE_URL"):
        create_database(settings, reader=True)
