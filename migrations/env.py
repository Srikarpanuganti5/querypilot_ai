"""Alembic reads DATABASE_URL at execution time, never from a committed INI URL."""

from alembic import context

from querypilot.core.config import Settings
from querypilot.db.models import Base
from querypilot.db.session import create_database, database_url

target_metadata = Base.metadata


def run_migrations() -> None:
    settings = Settings()
    if context.is_offline_mode():
        context.configure(
            url=database_url(settings),
            target_metadata=target_metadata,
            literal_binds=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    supplied_connection = context.config.attributes.get("connection")
    if supplied_connection is not None:
        context.configure(
            connection=supplied_connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    database = create_database(settings)
    try:
        with database.engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        database.close()


run_migrations()
