"""Lazy PostgreSQL setup and explicit per-operation transactions."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from querypilot.core.config import Settings


class DatabaseError(Exception):
    """Safe database diagnostic with no SQL, credentials, or driver text."""

    def __init__(self, message: str, *, code: str = "database_error"):
        super().__init__(message)
        self.code = code


DATABASE_MESSAGES = {
    "reader_configuration_missing": "Configure the backend read-only database connection.",
    "database_configuration_invalid": "The database connection configuration is invalid.",
    "database_unavailable": "The analytics database cannot be reached.",
    "database_authentication_error": "The database rejected the configured credentials.",
    "database_not_found": "The configured analytics database does not exist.",
    "database_schema_missing": "Required analytics tables are missing; apply migrations.",
    "database_permission_error": "The reader lacks required analytics permissions.",
    "database_error": "Analytics database unavailable.",
    "timeout": "Query timed out.",
}


def classify_database_error(error: SQLAlchemyError) -> DatabaseError:
    original = getattr(error, "orig", None)
    state = getattr(original, "sqlstate", None)
    codes = {
        "28P01": "database_authentication_error",
        "28000": "database_authentication_error",
        "3D000": "database_not_found",
        "42P01": "database_schema_missing",
        "42501": "database_permission_error",
        "57014": "timeout",
    }
    code = codes.get(state, "database_error")
    if code == "database_error" and isinstance(error, OperationalError):
        # libpq connection failures sometimes omit SQLSTATE. Inspect only to classify;
        # never emit driver text (which may include passwords, hosts or SQL).
        detail = str(original).casefold()
        if "password authentication failed" in detail or "no password supplied" in detail:
            code = "database_authentication_error"
        elif "database" in detail and "does not exist" in detail:
            code = "database_not_found"
        else:
            code = "database_unavailable"
    return DatabaseError(DATABASE_MESSAGES[code], code=code)


def database_url(settings: Settings, *, reader: bool = False) -> URL:
    secret = settings.reader_database_url if reader else settings.database_url
    if secret is None or not secret.get_secret_value():
        raise DatabaseError(
            "Set READER_DATABASE_URL." if reader else "Set DATABASE_URL.",
            code="reader_configuration_missing" if reader else "database_configuration_invalid",
        )
    try:
        url = make_url(secret.get_secret_value())
        if url.drivername != "postgresql+psycopg":
            raise DatabaseError(
                "Use a postgresql+psycopg connection URL.", code="database_configuration_invalid"
            )
        if not url.database:
            raise DatabaseError("Configure a database name.", code="database_configuration_invalid")
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("Invalid port")
        return url
    except (ArgumentError, ValueError):
        raise DatabaseError(
            "Invalid PostgreSQL connection configuration.", code="database_configuration_invalid"
        ) from None


class Database:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.sessions = sessionmaker(engine, expire_on_commit=False, autobegin=False)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        try:
            with self.sessions.begin() as session:
                yield session
        except SQLAlchemyError as exc:
            raise classify_database_error(exc) from None

    def close(self) -> None:
        self.engine.dispose()


def create_database(settings: Settings, *, reader: bool = False) -> Database:
    options = f"-c statement_timeout={settings.db_statement_timeout_ms} -c lock_timeout=2000"
    if reader:
        options += " -c default_transaction_read_only=on"
    engine = create_engine(
        database_url(settings, reader=reader),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=1800,
        echo=False,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": options},
    )
    return Database(engine)
