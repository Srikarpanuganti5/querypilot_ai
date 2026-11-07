"""Regression checks for the observed setup failure and mixed payment question."""

import asyncio
import json
import secrets

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from querypilot.agent.mock import MultiStepMockProvider
from querypilot.agent.tool_schemas import function_schemas
from querypilot.core.config import Settings
from querypilot.db.session import classify_database_error
from querypilot.services import doctor
from querypilot.tools.registry import ToolRegistry
from tests.postgres_support import test_urls


def test_missing_reader_has_database_specific_diagnostic():
    registry = ToolRegistry(settings=Settings(_env_file=None, reader_database_url=None))
    result = registry.execute("get_top_products", {"limit": 5})
    assert result.error.code == "reader_configuration_missing"


def test_count_and_handling_question_selects_payment_analytics_first():
    async def scenario():
        provider = MultiStepMockProvider()
        return await provider.respond(
            "",
            [
                {
                    "role": "user",
                    "content": "How many failed payments occurred, "
                    "and how are failed payments handled?",
                }
            ],
            function_schemas(ToolRegistry().definitions()),
        )

    turn = asyncio.run(scenario())
    assert turn.output[0]["name"] == "get_payment_status_summary"


@pytest.mark.parametrize(
    "state,code",
    [
        ("28P01", "database_authentication_error"),
        ("3D000", "database_not_found"),
        ("42P01", "database_schema_missing"),
        ("42501", "database_permission_error"),
        ("57014", "timeout"),
    ],
)
def test_driver_sqlstate_classification_never_serializes_private_details(state, code):
    sentinel = secrets.token_urlsafe(30)
    original = RuntimeError(sentinel)
    original.sqlstate = state
    error = classify_database_error(ProgrammingError("PRIVATE_QUERY", {}, original))
    assert error.code == code and sentinel not in str(error)


def test_connection_failure_without_sqlstate_is_safe():
    error = classify_database_error(
        OperationalError("PRIVATE_QUERY", {}, RuntimeError("PRIVATE_URL"))
    )
    assert error.code == "database_unavailable" and "PRIVATE" not in str(error)


def test_doctor_missing_database_is_fail_with_dependent_skips():
    report = doctor.diagnose(
        Settings(
            _env_file=None,
            database_url=None,
            reader_database_url=None,
            openai_api_key=None,
            openai_model=None,
        )
    )
    assert report.failed
    assert any(
        check.status == "FAIL" and check.code == "reader_configuration_missing"
        for check in report.checks
    )
    assert any(check.status == "SKIP" and check.name == "seed_data" for check in report.checks)
    assert any(check.status == "PASS" and check.name == "documents" for check in report.checks)
    assert any(check.status == "PASS" and check.name == "mock_provider" for check in report.checks)


def test_doctor_cli_json_omits_secrets_and_unsafe_backend_url(monkeypatch, capsys):
    sentinel = secrets.token_urlsafe(30)
    settings = Settings(
        _env_file=None, database_url=None, reader_database_url=None, openai_api_key=sentinel
    )
    monkeypatch.setattr(doctor, "Settings", lambda: settings)
    with pytest.raises(SystemExit) as error:
        doctor.main(["--json", "--backend-url", "http://user:" + sentinel + "@localhost"])
    assert error.value.code == 1
    output = capsys.readouterr().out
    assert sentinel not in output
    checks = json.loads(output)["checks"]
    assert {item["status"] for item in checks} == {"PASS", "FAIL", "SKIP"}


@pytest.mark.parametrize("kind", ["no_ack", "development_database", "target_mismatch", "same_role"])
def test_integration_safety_rejects_unsafe_targets(kind, monkeypatch):
    writer = "postgresql+psycopg://admin@localhost/querypilot_local_test"
    reader = "postgresql+psycopg://reader@localhost/querypilot_local_test"
    monkeypatch.setenv("TEST_DATABASE_URL", writer)
    monkeypatch.setenv("TEST_READER_DATABASE_URL", reader)
    monkeypatch.setenv("QUERYPILOT_TEST_DATABASE_ACK", "allow-isolated-schemas")
    if kind == "no_ack":
        monkeypatch.delenv("QUERYPILOT_TEST_DATABASE_ACK")
    elif kind == "development_database":
        monkeypatch.setenv("TEST_DATABASE_URL", writer.replace("_test", "_dev"))
    elif kind == "target_mismatch":
        monkeypatch.setenv("TEST_READER_DATABASE_URL", reader.replace("localhost", "other.invalid"))
    else:
        monkeypatch.setenv("TEST_READER_DATABASE_URL", reader.replace("reader@", "admin@"))
    with pytest.raises(pytest.fail.Exception):
        test_urls()
