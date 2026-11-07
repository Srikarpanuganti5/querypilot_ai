"""Prepare an owned local PostgreSQL cluster and separate synthetic dev/test databases.

Run from the repository root: python scripts/prepare_local.py
Never resets an existing database or overwrites an existing .env.
"""

import json
import os
import secrets
import shutil
import subprocess
from datetime import date
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

from querypilot.core.config import Settings
from querypilot.db.seed import generate_dataset, seed_database
from querypilot.db.session import Database
from querypilot.db.verify import verify_database
from querypilot.tools.registry import create_registry

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
PORT = 55440
REFERENCE = date(2026, 10, 27)
DATABASES = ("querypilot_local_dev", "querypilot_local_test")


def binary(name: str) -> str:
    value = shutil.which(name)
    fallback = Path("/opt/homebrew/bin") / name
    if value:
        return value
    if fallback.is_file():
        return str(fallback)
    raise RuntimeError("Install PostgreSQL server tools; see docs/testing.md.")


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)


def private_file(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        os.chmod(path, 0o600)
        handle.write(content)


def prepare() -> None:
    if LOCAL.is_symlink():
        raise RuntimeError("Local directory must not be a symlink.")
    LOCAL.mkdir(mode=0o700, exist_ok=True)
    cluster, credentials = LOCAL / "postgres", LOCAL / "credentials.json"
    if cluster.is_symlink() or credentials.is_symlink():
        raise RuntimeError("Local setup files must not be symlinks.")
    if cluster.exists() and not credentials.is_file():
        raise RuntimeError("Existing cluster is not owned by this setup; refusing changes.")
    if not credentials.exists():
        private_file(
            credentials,
            json.dumps({"admin": secrets.token_urlsafe(30), "reader": secrets.token_urlsafe(30)}),
        )
    passwords = json.loads(credentials.read_text())
    if not cluster.exists():
        pwfile = LOCAL / ".init-password"
        private_file(pwfile, passwords["admin"] + "\n")
        try:
            run(
                [
                    binary("initdb"),
                    "-D",
                    str(cluster),
                    "-A",
                    "scram-sha-256",
                    "-U",
                    "querypilot_admin",
                    "--pwfile",
                    str(pwfile),
                    "--no-locale",
                    "--encoding=UTF8",
                ]
            )
        finally:
            pwfile.unlink(missing_ok=True)
    status = subprocess.run([binary("pg_ctl"), "-D", str(cluster), "status"], capture_output=True)
    if status.returncode:
        run(
            [
                binary("pg_ctl"),
                "-D",
                str(cluster),
                "-l",
                str(LOCAL / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {PORT} -k {LOCAL}",
                "-w",
                "start",
            ]
        )
    print("PASS owned PostgreSQL cluster ready")
    admin = URL.create(
        "postgresql",
        username="querypilot_admin",
        password=passwords["admin"],
        host="127.0.0.1",
        port=PORT,
        database="postgres",
    )
    with psycopg.connect(
        admin.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        if not connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname='querypilot_reader'"
        ).fetchone():
            connection.execute(
                sql.SQL(
                    "CREATE ROLE querypilot_reader LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
                ).format(sql.Literal(passwords["reader"]))
            )
        for name in DATABASES:
            if not connection.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (name,)
            ).fetchone():
                connection.execute(
                    sql.SQL("CREATE DATABASE {} OWNER querypilot_admin").format(
                        sql.Identifier(name)
                    )
                )
    urls = {}
    for name in DATABASES:
        writer_url = admin.set(drivername="postgresql+psycopg", database=name)
        reader_url = writer_url.set(username="querypilot_reader", password=passwords["reader"])
        database = Database(
            create_engine(writer_url, hide_parameters=True, connect_args={"connect_timeout": 5})
        )
        try:
            names = set(inspect(database.engine).get_table_names())
            config = Config(str(ROOT / "alembic.ini"))
            with database.engine.begin() as connection:
                config.attributes["connection"] = connection
                if not names:
                    command.upgrade(config, "head")
                else:
                    # Existing tables are verified, not upgraded or reset automatically.
                    from alembic.runtime.migration import MigrationContext
                    from alembic.script import ScriptDirectory

                    if set(MigrationContext.configure(connection).get_current_heads()) != set(
                        ScriptDirectory.from_config(config).get_heads()
                    ):
                        raise RuntimeError(
                            "Existing database revision differs; refusing automatic changes."
                        )
            seed_database(database, generate_dataset(REFERENCE))
            verify_database(database, REFERENCE)
            with psycopg.connect(
                admin.set(database=name).render_as_string(hide_password=False), autocommit=True
            ) as connection:
                connection.execute(
                    sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name))
                )
                connection.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO querypilot_reader").format(
                        sql.Identifier(name)
                    )
                )
                connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
                connection.execute("GRANT USAGE ON SCHEMA public TO querypilot_reader")
                connection.execute(
                    "GRANT SELECT ON customers,products,orders,order_items,payments,refunds "
                    "TO querypilot_reader"
                )
                connection.execute(
                    "ALTER ROLE querypilot_reader SET default_transaction_read_only=on"
                )
                connection.execute("ALTER ROLE querypilot_reader SET statement_timeout='5s'")
                connection.execute("ALTER ROLE querypilot_reader SET lock_timeout='2s'")
            registry = create_registry(
                Settings(
                    _env_file=None,
                    reader_database_url=reader_url.render_as_string(hide_password=False),
                )
            )
            try:
                result = registry.execute("get_top_products", {"limit": 5})
                if result.status != "success" or len(result.data.rows) != 5:
                    raise RuntimeError("Reader verification failed.")
            finally:
                registry.close()
            urls[name] = (
                writer_url.render_as_string(hide_password=False),
                reader_url.render_as_string(hide_password=False),
            )
            print(f"PASS {name}: migrated synthetic fixture and restricted reader verified")
        finally:
            database.close()
    dev, test = urls[DATABASES[0]], urls[DATABASES[1]]
    dev_content = (
        f"DATABASE_URL={dev[0]}\nREADER_DATABASE_URL={dev[1]}\n"
        "QUERYPILOT_AGENT_LIVE_ENABLED=false\n"
    )
    test_content = (
        f"TEST_DATABASE_URL={test[0]}\nTEST_READER_DATABASE_URL={test[1]}\n"
        "QUERYPILOT_TEST_DATABASE_ACK=allow-isolated-schemas\n"
    )
    for path, content in (
        (LOCAL / "development.env", dev_content),
        (LOCAL / "integration.env", test_content),
        (ROOT / ".env", dev_content),
    ):
        if path.exists():
            print(f"SKIP existing {path.relative_to(ROOT)} preserved")
        else:
            private_file(path, content)
            print(f"PASS wrote ignored {path.relative_to(ROOT)}")
    print("Restart FastAPI to load the local configuration. No API key is required for mock mode.")


if __name__ == "__main__":
    try:
        prepare()
    except Exception:
        raise SystemExit(
            "FAIL local setup. Existing data was not reset. "
            "Check docs/testing.md; credentials are never printed."
        ) from None
