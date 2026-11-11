"""Explicit synthetic-only setup job; never imported or executed by API startup."""

import os
from datetime import date

import psycopg
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import inspect, text

from querypilot.core.config import Settings
from querypilot.db.seed import generate_dataset, seed_database
from querypilot.db.session import create_database, database_url
from querypilot.db.verify import verify_database
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.runner import verify_fixture
from querypilot.services.doctor import diagnose


def bootstrap(settings: Settings, *, acknowledged: bool) -> None:
    if not acknowledged:
        raise ValueError("Explicit synthetic-only setup acknowledgement required")
    writer, reader = database_url(settings), database_url(settings, reader=True)
    if (
        (writer.host, writer.port, writer.database) != (reader.host, reader.port, reader.database)
        or writer.username == reader.username
        or not reader.username
        or not reader.password
        or not writer.database
        or not writer.database.startswith("querypilot_")
    ):
        raise ValueError("Distinct roles on one dedicated querypilot_ database required")
    database = create_database(settings)
    try:
        with database.engine.connect() as connection:
            names = inspect(connection).get_table_names()
            cfg = Config("alembic.ini")
            if names:
                if "alembic_version" not in names:
                    raise ValueError("Existing schema is not migration-owned; refusing changes")
                revisions = set(
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
                )
                if revisions != set(ScriptDirectory.from_config(cfg).get_heads()):
                    raise ValueError("Existing migration differs; review upgrade explicitly")
        if not names:
            # Supply the connection to the existing Alembic environment; never emit URLs.
            with database.engine.begin() as connection:
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")
        seed_database(database, generate_dataset(date(2026, 10, 27), 42))
        verify_database(database, date(2026, 10, 27), 42)
        print("PASS migration and synthetic fixture; existing different data is never replaced")
        # Code-owned identifiers and safely composed password literals, never subprocess argv.
        connection_url = writer.set(drivername="postgresql").render_as_string(hide_password=False)
        with psycopg.connect(connection_url, autocommit=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (reader.username,)
            ).fetchone()
            if not exists:
                connection.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOINHERIT NOBYPASSRLS NOREPLICATION"
                    ).format(sql.Identifier(reader.username), sql.Literal(reader.password))
                )
            # Existing roles are audited, not silently re-privileged or password-rotated.
            connection.execute(
                sql.SQL("REVOKE CREATE, TEMP ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(writer.database)
                )
            )
            connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(writer.database), sql.Identifier(reader.username)
                )
            )
            connection.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                    sql.Identifier(reader.username)
                )
            )
            connection.execute(
                sql.SQL(
                    "GRANT SELECT ON customers, products, orders, order_items, "
                    "payments, refunds TO {}"
                ).format(sql.Identifier(reader.username))
            )
            connection.execute(
                sql.SQL("ALTER ROLE {} SET default_transaction_read_only=on").format(
                    sql.Identifier(reader.username)
                )
            )
            connection.execute(
                sql.SQL("ALTER ROLE {} SET statement_timeout='5s'").format(
                    sql.Identifier(reader.username)
                )
            )
        dataset, _ = load_dataset()
        verify_fixture(settings, dataset)
        if diagnose(settings, reference_date=dataset.reference_date).failed:
            raise ValueError("Reader or document readiness failed")
        print("PASS restricted reader, exact six-table fixture and policy corpus")
    finally:
        database.close()


def main() -> None:
    try:
        bootstrap(Settings(), acknowledged=os.getenv("QUERYPILOT_SETUP_ACK") == "synthetic-only")
    except Exception:
        raise SystemExit(
            "Setup failed safely. Check credentials, database availability, schema "
            "and fixture identity; existing data was not reset."
        ) from None


if __name__ == "__main__":
    main()
