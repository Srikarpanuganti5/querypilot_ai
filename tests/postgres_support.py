"""Explicit, fail-closed prerequisites before any integration fixture creates a schema."""

import os

import pytest
from sqlalchemy.engine import make_url


def test_urls(*, require_reader: bool = True) -> tuple[str, str | None]:
    __tracebackhide__ = True
    writer, reader = os.getenv("TEST_DATABASE_URL"), os.getenv("TEST_READER_DATABASE_URL")
    if not writer or (require_reader and not reader):
        pytest.skip(
            "Configure TEST_DATABASE_URL and TEST_READER_DATABASE_URL for real PostgreSQL tests"
        )
    if os.getenv("QUERYPILOT_TEST_DATABASE_ACK") != "allow-isolated-schemas":
        pytest.fail(
            "Set QUERYPILOT_TEST_DATABASE_ACK=allow-isolated-schemas before these tests",
            pytrace=False,
        )
    try:
        admin = make_url(writer)
        if (
            admin.drivername != "postgresql+psycopg"
            or not admin.database
            or not admin.database.startswith("querypilot_")
            or not admin.database.endswith(("_test", "_verify"))
        ):
            raise ValueError
        if reader:
            restricted = make_url(reader)
            if (
                (admin.host, admin.port, admin.database)
                != (restricted.host, restricted.port, restricted.database)
                or admin.username == restricted.username
                or restricted.drivername != "postgresql+psycopg"
            ):
                raise ValueError
    except Exception:
        pytest.fail(
            "Use distinct roles on one dedicated querypilot_*_test or *_verify database; "
            "URL values are withheld",
            pytrace=False,
        )
    return writer, reader


# This is a helper, not a collected test.
test_urls.__test__ = False
