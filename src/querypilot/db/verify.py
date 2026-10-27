"""Validate schema, exact fixture counts, foreign keys, and accounting in PostgreSQL."""

import argparse
import json
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
    inspect,
    select,
    text,
)

from querypilot.core.config import Settings
from querypilot.db.models import Base
from querypilot.db.seed import generate_dataset, reference_window
from querypilot.db.session import Database, DatabaseError, create_database


class VerificationError(ValueError):
    pass


ACCOUNTING_CHECKS = {
    "order_totals": """
        SELECT count(*) FROM orders o LEFT JOIN
          (SELECT order_id, sum(quantity * unit_price) amount FROM order_items GROUP BY order_id) i
        ON i.order_id=o.order_id WHERE i.amount IS NULL OR o.total_amount <> i.amount
    """,
    "payment_amounts": """
        SELECT count(*) FROM payments p JOIN orders o USING(order_id)
        WHERE p.amount <> o.total_amount OR p.payment_date < o.order_date
    """,
    "settlement_status": """
        SELECT count(*) FROM orders o LEFT JOIN
          (SELECT order_id, count(*) n FROM payments WHERE payment_status='successful'
           GROUP BY order_id) p USING(order_id)
        WHERE (o.status IN ('completed','refunded') AND coalesce(p.n,0) <> 1)
           OR (o.status IN ('pending','cancelled') AND coalesce(p.n,0) <> 0)
    """,
    "refund_limits": """
        SELECT count(*) FROM payments p JOIN
          (SELECT payment_id, sum(amount) amount, min(refund_date) first_refund
           FROM refunds GROUP BY payment_id) r USING(payment_id)
        WHERE p.payment_status <> 'successful' OR r.amount > p.amount
           OR r.first_refund < p.payment_date
    """,
    "refund_status": """
        SELECT count(*) FROM orders o LEFT JOIN
          (SELECT p.order_id, sum(r.amount) amount FROM refunds r
           JOIN payments p USING(payment_id) GROUP BY p.order_id) r USING(order_id)
        WHERE (o.status='refunded' AND coalesce(r.amount,0) <> o.total_amount)
           OR (o.status <> 'refunded' AND coalesce(r.amount,0) <> 0)
    """,
    "customer_chronology": """
        SELECT count(*) FROM orders o JOIN customers c USING(customer_id)
        WHERE c.created_at > o.order_date
    """,
    "product_chronology": """
        SELECT count(*) FROM order_items i JOIN orders o USING(order_id)
        JOIN products p USING(product_id) WHERE p.created_at > o.order_date
    """,
}


def verify_database(database: Database, reference_date: date, random_seed: int = 42) -> dict:
    expected = generate_dataset(reference_date, random_seed)
    with database.transaction() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        inspector = inspect(session.connection())
        names = set(inspector.get_table_names())
        counts = {}
        for table in Base.metadata.sorted_tables:
            if table.name not in names:
                raise VerificationError(f"Missing table: {table.name}")
            counts[table.name] = session.scalar(select(func.count()).select_from(table))
            if counts[table.name] != len(expected[table.name]):
                raise VerificationError(f"Unexpected row count: {table.name}")
            if set(inspector.get_pk_constraint(table.name)["constrained_columns"]) != {
                column.name for column in table.primary_key
            }:
                raise VerificationError(f"Primary key mismatch: {table.name}")
            reflected = {item["name"] for item in inspector.get_check_constraints(table.name)}
            reflected |= {item["name"] for item in inspector.get_unique_constraints(table.name)}
            reflected |= {item["name"] for item in inspector.get_foreign_keys(table.name)}
            required = {
                c.name
                for c in table.constraints
                if isinstance(c, (CheckConstraint, UniqueConstraint, ForeignKeyConstraint))
            }
            if not required <= reflected:
                raise VerificationError(f"Missing constraint: {table.name}")
            indexes = {item["name"] for item in inspector.get_indexes(table.name)}
            if not {index.name for index in table.indexes} <= indexes:
                raise VerificationError(f"Missing index: {table.name}")
            for column in table.columns:
                for fk in column.foreign_keys:
                    parent = fk.column
                    # Identifiers are code-owned metadata, never user input.
                    orphans = session.scalar(
                        text(
                            f'SELECT count(*) FROM "{table.name}" c '
                            f'LEFT JOIN "{parent.table.name}" p '
                            f'ON c."{column.name}"=p."{parent.name}" '
                            f'WHERE p."{parent.name}" IS NULL'
                        )
                    )
                    if orphans:
                        raise VerificationError(f"Orphan relationship: {table.name}")
        for name, statement in ACCOUNTING_CHECKS.items():
            if session.scalar(text(statement)):
                raise VerificationError(f"Accounting check failed: {name}")
        start, end = reference_window(reference_date)
        if session.scalar(
            text("SELECT count(*) FROM orders WHERE order_date < :start OR order_date >= :end"),
            {"start": start, "end": end},
        ):
            raise VerificationError("Orders outside the expected twelve-month window")
        for table, column in (("payments", "payment_date"), ("refunds", "refund_date")):
            if session.scalar(
                text(f"SELECT count(*) FROM {table} WHERE {column} >= :end"), {"end": end}
            ):
                raise VerificationError("Payment/refund outside reference-date cutoff")
    return {"counts": counts, "accounting": "passed", "schema": "passed", "foreign_keys": "passed"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-date", required=True, type=date.fromisoformat)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()
    database = None
    try:
        database = create_database(Settings())
        print(json.dumps(verify_database(database, args.reference_date, args.random_seed)))
    except (DatabaseError, VerificationError) as exc:
        raise SystemExit(str(exc)) from None
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    main()
