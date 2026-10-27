"""Deterministic synthetic fixture generation and transactional, repeat-safe loading."""

import argparse
import calendar
import json
import random
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from sqlalchemy import insert, select, text

from querypilot.core.config import Settings
from querypilot.db.models import Base
from querypilot.db.session import Database, DatabaseError, create_database

EXPECTED_COUNTS = {"customers": 500, "products": 100, "orders": 3000, "order_items": 6000}


class SeedConflict(ValueError):
    """Refuse to overwrite existing data or mix different fixture versions."""


def reference_window(reference_date: date) -> tuple[datetime, datetime]:
    end = datetime.combine(reference_date, datetime.min.time(), tzinfo=UTC)
    start = end.replace(
        year=end.year - 1, day=min(end.day, calendar.monthrange(end.year - 1, end.month)[1])
    )
    return start, end


def generate_dataset(
    reference_date: date, random_seed: int = 42
) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(random_seed)
    start, end = reference_window(reference_date)
    data: dict[str, list[dict[str, Any]]] = {
        table.name: [] for table in Base.metadata.sorted_tables
    }
    locations = [
        ("Austin", "TX"),
        ("Seattle", "WA"),
        ("Boston", "MA"),
        ("Denver", "CO"),
        ("Miami", "FL"),
        ("Portland", "OR"),
    ]
    for key in range(1, 501):
        city, state = rng.choice(locations)
        data["customers"].append(
            {
                "customer_id": key,
                "name": f"Synthetic Customer {key:04d}",
                "email": f"customer{key:04d}@example.invalid",
                "city": city,
                "state": state,
                "created_at": start - timedelta(days=rng.randint(1, 180)),
            }
        )
    categories = ["Electronics", "Home", "Sports", "Outdoors", "Office"]
    for key in range(1, 101):
        category = categories[(key - 1) % len(categories)]
        data["products"].append(
            {
                "product_id": key,
                "name": f"{category} Product {key:03d}",
                "category": category,
                "price": Decimal(rng.randint(999, 29999)) / 100,
                "stock_quantity": rng.randint(0, 500),
                "created_at": start - timedelta(days=200),
            }
        )
    statuses = ["completed"] * 2400 + ["pending"] * 300 + ["cancelled"] * 180 + ["refunded"] * 120
    line_counts = [1] * 1000 + [2] * 1000 + [3] * 1000
    rng.shuffle(statuses)
    rng.shuffle(line_counts)
    for key, (status, count) in enumerate(zip(statuses, line_counts, strict=True), 1):
        # Leave three days for payment/refund events; all events precede reference_date.
        ordered = start + timedelta(
            seconds=rng.randrange(int((end - start).total_seconds()) - 259200)
        )
        total = Decimal("0.00")
        for product in rng.sample(data["products"], count):
            quantity = rng.randint(1, 4)
            unit_price = (
                product["price"] * rng.choice([Decimal("1"), Decimal("0.95"), Decimal("0.90")])
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            total += quantity * unit_price
            data["order_items"].append(
                {
                    "order_item_id": len(data["order_items"]) + 1,
                    "order_id": key,
                    "product_id": product["product_id"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )
        data["orders"].append(
            {
                "order_id": key,
                "customer_id": rng.randint(1, 500),
                "order_date": ordered,
                "status": status,
                "total_amount": total,
            }
        )
        settled = status in ("completed", "refunded")
        attempts = []
        if (status == "pending" and rng.random() < 0.75) or (settled and rng.random() < 0.10):
            attempts.append("failed")
        if settled:
            attempts.append("successful")
        for attempt, payment_status in enumerate(attempts, 1):
            payment_id = len(data["payments"]) + 1
            paid = ordered + timedelta(hours=attempt)
            data["payments"].append(
                {
                    "payment_id": payment_id,
                    "order_id": key,
                    "amount": total,
                    "payment_method": rng.choice(["card", "bank_transfer", "wallet"]),
                    "payment_status": payment_status,
                    "payment_date": paid,
                }
            )
            if status == "refunded" and payment_status == "successful":
                data["refunds"].append(
                    {
                        "refund_id": len(data["refunds"]) + 1,
                        "payment_id": payment_id,
                        "amount": total,
                        "refund_reason": rng.choice(
                            [
                                "Synthetic damaged item",
                                "Synthetic return",
                                "Synthetic incorrect item",
                            ]
                        ),
                        "refund_date": paid + timedelta(days=2),
                    }
                )
    return data


def seed_database(database: Database, dataset: dict[str, list[dict[str, Any]]]) -> bool:
    with database.transaction() as session:
        session.execute(text("SELECT pg_advisory_xact_lock(741031)"))
        existing = {}
        for table in Base.metadata.sorted_tables:
            primary_key = list(table.primary_key.columns)[0]
            existing[table.name] = [
                dict(row) for row in session.execute(select(table).order_by(primary_key)).mappings()
            ]
        if any(existing.values()):
            if existing == dataset:
                return False
            raise SeedConflict(
                "Existing data differs from this fixture; use a separate empty database."
            )
        for table in Base.metadata.sorted_tables:
            rows = dataset[table.name]
            if rows:
                session.execute(insert(table), rows)
                primary_key = list(table.primary_key.columns)[0].name
                # Explicit fixture IDs must not leave SERIAL sequences behind.
                session.execute(
                    text("SELECT setval(pg_get_serial_sequence(:t, :c), :v, true)"),
                    {"t": table.name, "c": primary_key, "v": max(row[primary_key] for row in rows)},
                )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-date", type=date.fromisoformat, required=True)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()
    database = None
    try:
        dataset = generate_dataset(args.reference_date, args.random_seed)
        database = create_database(Settings())
        created = seed_database(database, dataset)
        print(json.dumps({"created": created, "counts": {k: len(v) for k, v in dataset.items()}}))
    except (DatabaseError, SeedConflict) as exc:
        raise SystemExit(str(exc)) from None
    finally:
        if database is not None:
            database.close()


if __name__ == "__main__":
    main()
