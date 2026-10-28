"""Lazy PostgreSQL setup and explicit per-operation transactions."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from querypilot.core.config import Settings


class DatabaseError(Exception):
    """Safe database diagnostic with no SQL, credentials, or driver text."""

    def __init__(self, message: str, *, code: str = "database_error"):
        super().__init__(message)
        self.code = code


def database_url(settings: Settings, *, reader: bool = False) -> URL:
    secret = settings.reader_database_url if reader else settings.database_url
    if secret is None or not secret.get_secret_value():
        raise DatabaseError("Set READER_DATABASE_URL." if reader else "Set DATABASE_URL.")
    try:
        url = make_url(secret.get_secret_value())
        if url.drivername != "postgresql+psycopg":
            raise DatabaseError("Use a postgresql+psycopg connection URL.")
        return url
    except (ArgumentError, ValueError):
        raise DatabaseError("Invalid PostgreSQL connection configuration.") from None


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
            if getattr(getattr(exc, "orig", None), "sqlstate", None) == "57014":
                raise DatabaseError(
                    "Database query timed out; transaction rolled back.", code="timeout"
                ) from None
            raise DatabaseError("Database operation failed; transaction rolled back.") from None

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
