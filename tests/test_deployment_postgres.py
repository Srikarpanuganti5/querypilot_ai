"""REAL PostgreSQL: all setup mutations are limited to a newly owned temporary database."""

import asyncio
import secrets
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy.engine import make_url

from querypilot.db.bootstrap import bootstrap
from querypilot.db.seed import SeedConflict
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.gate import BASELINE, Baseline, compare
from querypilot.evaluation.runner import run_evaluation
from querypilot.main import create_app

pytestmark = pytest.mark.postgres


@pytest.fixture
def owned_database(integration_settings):
    admin = make_url(integration_settings.database_url.get_secret_value()).set(
        drivername="postgresql"
    )
    name = "querypilot_day12_" + uuid4().hex + "_verify"
    role = "qp_reader_" + uuid4().hex
    password = secrets.token_hex(24)
    with psycopg.connect(
        admin.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    writer = admin.set(database=name)
    reader = writer.set(username=role, password=password)
    settings = integration_settings.model_copy(
        update={
            "database_url": SecretStr(
                writer.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
            ),
            "reader_database_url": SecretStr(
                reader.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
            ),
        }
    )
    try:
        yield settings, writer
    finally:
        # Only the database/role created above, never an existing user's target.
        with psycopg.connect(
            admin.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))


def test_fresh_migration_seed_reader_idempotence_and_recovery(owned_database, integration_settings):
    settings, writer = owned_database
    # A missing schema is not ready, even though the FastAPI process is alive.
    existing_reader = make_url(integration_settings.reader_database_url.get_secret_value()).set(
        database=writer.database
    )
    empty_settings = settings.model_copy(
        update={
            "reader_database_url": SecretStr(existing_reader.render_as_string(hide_password=False))
        }
    )
    with TestClient(create_app(empty_settings)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
        assert response.status_code == 503
        assert any(c["code"] == "database_schema_missing" for c in response.json()["checks"])
    bootstrap(settings, acknowledged=True)
    bootstrap(settings, acknowledged=True)
    # The application needs only reader access; no administrator configuration at runtime.
    runtime = settings.model_copy(update={"database_url": None})
    with TestClient(create_app(runtime)) as client:
        assert client.get("/ready").status_code == 200
    with psycopg.connect(
        writer.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute("TRUNCATE refunds")
    with TestClient(create_app(runtime)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert any(c["code"] == "seed_missing" for c in response.json()["checks"])
    with pytest.raises(SeedConflict):
        bootstrap(settings, acknowledged=True)


@pytest.mark.parametrize("failure", ["unavailable", "authentication"])
def test_readiness_safe_failure_codes(failure, integration_settings):
    url = make_url(integration_settings.reader_database_url.get_secret_value())
    url = url.set(port=1) if failure == "unavailable" else url.set(password=secrets.token_hex(24))
    settings = integration_settings.model_copy(
        update={"reader_database_url": SecretStr(url.render_as_string(hide_password=False))}
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
    assert response.status_code == 503
    assert "postgresql" not in response.text


def test_reviewed_baseline_gate_against_real_tools(integration_settings):
    dataset, checksum = load_dataset()
    report = asyncio.run(run_evaluation(dataset, integration_settings, dataset_hash=checksum))
    verdict = compare(report, Baseline.model_validate_json(BASELINE.read_text()))
    assert verdict["passed"] and verdict["protected_cases"] == 24
    assert len(verdict["known_failures"]) == 14
