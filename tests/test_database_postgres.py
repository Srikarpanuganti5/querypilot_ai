"""Real PostgreSQL tests use a fresh disposable schema per test, never SQLite."""

import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from querypilot.db.models import Base
from querypilot.db.seed import SeedConflict, generate_dataset, seed_database
from querypilot.db.session import Database, DatabaseError
from querypilot.db.verify import VerificationError, verify_database

pytestmark = pytest.mark.postgres
REFERENCE = date(2026, 10, 27)


def migrate(database: Database, action: str, revision: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, action)(config, revision)


@pytest.fixture
def database() -> Iterator[Database]:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to enable isolated-schema PostgreSQL tests")
    admin = create_engine(url, hide_parameters=True)
    schema = f"querypilot_test_{uuid4().hex}"
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(
            url,
            hide_parameters=True,
            connect_args={"options": f"-csearch_path={schema} -cstatement_timeout=10000"},
        )
        db = Database(engine)
        try:
            migrate(db, "upgrade", "head")
            yield db
        finally:
            db.close()
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    finally:
        admin.dispose()


def test_migration_round_trip_and_model_agreement(database: Database) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    with database.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    migrate(database, "downgrade", "base")
    assert set(inspect(database.engine).get_table_names()) <= {"alembic_version"}
    migrate(database, "upgrade", "head")
    assert set(Base.metadata.tables) <= set(inspect(database.engine).get_table_names())


def test_seed_idempotency_and_full_verification(database: Database) -> None:
    dataset = generate_dataset(REFERENCE)
    assert seed_database(database, dataset) is True
    assert seed_database(database, dataset) is False
    result = verify_database(database, REFERENCE)
    assert result["counts"] == {name: len(rows) for name, rows in dataset.items()}
    with pytest.raises(SeedConflict):
        seed_database(database, generate_dataset(REFERENCE, random_seed=43))
    assert verify_database(database, REFERENCE)["accounting"] == "passed"


def test_transaction_commit_rollback_close_and_redaction(database: Database) -> None:
    with database.transaction() as session:
        session.execute(text("CREATE TABLE transaction_probe (id integer PRIMARY KEY)"))
    with pytest.raises(RuntimeError):
        with database.transaction() as session:
            session.execute(text("INSERT INTO transaction_probe VALUES (1)"))
            raise RuntimeError("abort")
    assert database.engine.pool.checkedout() == 0
    with database.transaction() as session:
        assert session.scalar(text("SELECT count(*) FROM transaction_probe")) == 0
        session.execute(text("INSERT INTO transaction_probe VALUES (2)"))
    with pytest.raises(DatabaseError) as error:
        with database.transaction() as session:
            session.execute(text("INSERT INTO SECRET_MISSING_TABLE VALUES (1)"))
    assert "SECRET" not in str(error.value)
    assert database.engine.pool.checkedout() == 0
    with database.transaction() as session:
        assert session.scalar(text("SELECT count(*) FROM transaction_probe")) == 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE order_items SET quantity=0 WHERE order_item_id=1",
        "UPDATE products SET stock_quantity=-1 WHERE product_id=1",
        "UPDATE products SET price=-1 WHERE product_id=1",
        "UPDATE orders SET status='invalid' WHERE order_id=1",
        "UPDATE orders SET customer_id=999999 WHERE order_id=1",
        "UPDATE customers SET email=(SELECT email FROM customers WHERE customer_id=1) "
        "WHERE customer_id=2",
        "UPDATE refunds SET amount=-1 WHERE refund_id=1",
        "UPDATE payments SET payment_status='invalid' WHERE payment_id=1",
    ],
)
def test_constraints_reject_bad_writes(database: Database, statement: str) -> None:
    seed_database(database, generate_dataset(REFERENCE))
    with pytest.raises(DatabaseError):
        with database.transaction() as session:
            session.execute(text(statement))


@pytest.mark.parametrize(
    "statement,check",
    [
        ("UPDATE orders SET total_amount=total_amount+1 WHERE order_id=1", "order_totals"),
        ("UPDATE refunds SET amount=amount+1 WHERE refund_id=1", "refund_limits"),
    ],
)
def test_verifier_detects_cross_row_inconsistency(
    database: Database, statement: str, check: str
) -> None:
    seed_database(database, generate_dataset(REFERENCE))
    with database.transaction() as session:
        session.execute(text(statement))
    with pytest.raises(VerificationError, match=check):
        verify_database(database, REFERENCE)


def test_sample_analytics_queries(database: Database) -> None:
    dataset = generate_dataset(REFERENCE)
    seed_database(database, dataset)
    path = Path(__file__).resolve().parents[1] / "data/sample/analytics.sql"
    content = "\n".join(line for line in path.read_text().splitlines() if not line.startswith("--"))
    statements = [sql for sql in content.split(";") if sql.strip()]
    with database.transaction() as session:
        rows = [session.execute(text(sql)).all() for sql in statements]
        assert len(rows) == 5
        # A rolling twelve-month window spans two partial months plus eleven whole months.
        assert len(rows[0]) == 13
        assert len(rows[1]) == 5
        assert len(rows[2]) == 5
        assert len(rows[3]) == 500
        assert sum(row[1] for row in rows[4]) > 0
        assert sum(row[1] for row in rows[0]) == sum(
            order["total_amount"] for order in dataset["orders"] if order["status"] == "completed"
        )
        assert sum(row[1] for row in rows[2]) == sum(
            refund["amount"] for refund in dataset["refunds"]
        )
        assert sum(row[2] for row in rows[3]) == 3000
