"""Provider-independent registry contracts and rejection before database access."""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from querypilot.core.config import Settings
from querypilot.core.logging import configure_logging
from querypilot.db.analytics import UnsafeDatabaseError, _customers
from querypilot.db.session import DatabaseError
from querypilot.schemas.analytics import CustomerInput, RevenueInput, TopProductsInput
from querypilot.tools.registry import ToolRegistry, create_registry


@pytest.fixture(autouse=True)
def isolated_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    # Do not reuse a handler bound to a prior TestClient/capsys capture stream.
    logger = logging.getLogger("querypilot")
    monkeypatch.setattr(logger, "handlers", [logging.NullHandler()])
    monkeypatch.setattr(logger, "propagate", False)


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_top_products", {"limit": 21}),
        ("get_top_products", {"limit": 0}),
        ("get_top_products", {"limit": True}),
        ("get_top_products", {"limit": "5"}),
        ("get_top_products", {"sql": "DROP TABLE orders"}),
        ("get_top_products", {"start_date": "2026-01-01'; DELETE FROM orders;--"}),
        ("get_top_products", {"start_date": 0}),
        ("get_top_products", {"start_date": datetime(2026, 1, 1)}),
        ("get_top_products", {"start_date": "2026-02-30"}),
        ("get_top_products", {"start_date": "2026-02-01", "end_date": "2026-01-01"}),
        ("get_top_products", {"start_date": "2026-01-01", "end_date": "2026-01-01"}),
        ("get_top_products", {"start_date": "2024-01-01", "end_date": "2026-01-01"}),
        ("get_revenue_summary", {"group_by": "month; DROP TABLE orders"}),
        ("get_revenue_summary", {"group_by": "year"}),
        ("get_refund_analytics", {"limit": -1}),
        ("get_customer_order_summary", {"customer_id": 0}),
        ("get_customer_order_summary", {"customer_id": -1}),
        ("get_customer_order_summary", {"customer_id": True}),
        ("get_customer_order_summary", {"customer_id": "1 OR 1=1"}),
        ("get_customer_order_summary", {"customer_id": 2147483648}),
        ("get_customer_order_summary", {"limit": 21}),
        ("get_payment_status_summary", {"limit": 100}),
        ("get_top_products", []),
        ("get_top_products", None),
    ],
)
def test_invalid_arguments_never_execute(name: str, args: object) -> None:
    repository = Mock()
    result = ToolRegistry(repository).execute(name, args)
    assert result.status == "error"
    assert result.error.code == "invalid_arguments"
    assert result.data is None
    repository.execute.assert_not_called()


@pytest.mark.parametrize(
    "name", ["execute_sql", "DELETE", "unknown", "get_top_products; DROP TABLE orders", None, []]
)
def test_unknown_tool_never_executes_or_echoes_name(name: object) -> None:
    repository = Mock()
    result = ToolRegistry(repository).execute(name, {})
    assert result.tool is None
    assert result.error.code == "unknown_tool"
    repository.execute.assert_not_called()


def test_defaults_and_allowlist() -> None:
    assert TopProductsInput().limit == 5
    assert RevenueInput().group_by == "month"
    args = TopProductsInput(start_date="2026-01-01")
    assert args.start_date == date(2026, 1, 1)
    names = ToolRegistry(Mock()).definitions()
    assert len(names) == 6
    assert "get_customer_order_summary" in names
    assert all(not item["input_schema"]["additionalProperties"] for item in names.values())


def test_money_json_and_truncation() -> None:
    repository = Mock()
    repository.execute.return_value = (
        [
            {
                "product_id": 1,
                "name": "Synthetic product",
                "category": "Home",
                "units_sold": 2,
                "revenue": Decimal("19.98"),
            }
        ],
        True,
    )
    result = ToolRegistry(repository).execute("get_top_products", {})
    assert result.status == "success"
    assert result.data.truncated is True
    assert json.loads(result.model_dump_json())["data"]["rows"][0]["revenue"] == "19.98"


@pytest.mark.parametrize(
    "exception,code",
    [
        (UnsafeDatabaseError("SECRET"), "unsafe_database"),
        (DatabaseError("SECRET", code="timeout"), "timeout"),
        (DatabaseError("SECRET"), "database_error"),
        (RuntimeError("SECRET"), "internal_error"),
    ],
)
def test_errors_are_consistent_and_sanitized(exception: Exception, code: str) -> None:
    repository = Mock()
    repository.execute.side_effect = exception
    result = ToolRegistry(repository).execute("get_top_products", {})
    assert result.status == "error"
    assert result.error.code == code
    assert "SECRET" not in result.model_dump_json()
    assert result.data is None


def test_customer_output_rejects_personal_fields() -> None:
    repository = Mock()
    repository.execute.return_value = ([{"customer_id": 1, "email": "PRIVATE"}], False)
    result = ToolRegistry(repository).execute("get_customer_order_summary", {})
    assert result.error.code == "invalid_output"
    assert "PRIVATE" not in result.model_dump_json()
    sql = str(_customers(CustomerInput(customer_id=1)).compile(dialect=postgresql.dialect()))
    assert "customers.email" not in sql
    assert "customers.name" not in sql


def test_reader_configuration_is_mandatory() -> None:
    registry = create_registry(
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://writer@localhost/db",
            reader_database_url=None,
        )
    )
    result = registry.execute("get_top_products", {})
    assert result.error.code == "configuration_error"
    assert result.data is None
    registry.close()


def test_structured_logs_do_not_contain_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    registry = ToolRegistry(Mock())
    registry.execute("get_top_products", {"sql": "SECRET_CREDENTIAL"})
    registry.execute("SECRET_TOOL_NAME", {})
    output = capsys.readouterr().err
    assert "SECRET" not in output
    records = [json.loads(line) for line in output.splitlines()]
    assert records[0]["tool"] == "get_top_products"
    assert records[0]["status"] == "error"
    assert records[1]["tool"] == "unknown"
    assert all("duration_ms" in record for record in records)


def test_output_contract_rejects_inconsistent_success() -> None:
    from querypilot.schemas.analytics import ToolResult

    with pytest.raises(ValidationError):
        ToolResult(tool="get_top_products", status="success", duration_ms=0)
