"""REAL DATABASE + MOCK PROVIDER; local_http cases also use actual TCP HTTP/UI."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from querypilot.db.analytics import AnalyticsRepository
from querypilot.db.seed import generate_dataset
from querypilot.db.session import Database, create_database
from querypilot.frontend.api_client import ApiClient
from querypilot.frontend.config import FrontendSettings
from querypilot.main import create_app
from querypilot.schemas.agent import AskRequest
from querypilot.services.doctor import diagnose
from querypilot.tools.registry import ToolRegistry, create_registry

pytestmark = pytest.mark.postgres
TOP_FIVE = [
    (64, "37882.39"),
    (35, "36509.32"),
    (21, "35946.86"),
    (76, "35386.60"),
    (63, "34591.86"),
]
QUESTIONS = [
    "What is our return policy?",
    "What are our top five products by revenue?",
    "Which products generated the most revenue, and what is our refund policy?",
    "How many failed payments occurred, and how are failed payments handled?",
]
SEQUENCES = [
    ["search_business_documents"],
    ["get_top_products"],
    ["get_top_products", "search_business_documents"],
    ["get_payment_status_summary", "search_business_documents"],
]


@pytest.mark.parametrize(
    "name",
    [
        "get_top_products",
        "get_revenue_summary",
        "get_refund_analytics",
        "get_customer_order_summary",
        "get_payment_status_summary",
    ],
)
def test_all_analytics_match_independent_seed_oracle(name, integration_settings):
    dataset = generate_dataset(date(2026, 10, 27))
    registry = create_registry(integration_settings)
    try:
        result = registry.execute(
            name, {"customer_id": 1} if name == "get_customer_order_summary" else {}
        )
        assert result.status == "success", result.error
        if name == "get_top_products":
            assert [(row.product_id, str(row.revenue)) for row in result.data.rows] == TOP_FIVE
        elif name == "get_revenue_summary":
            expected = sum(
                order["total_amount"]
                for order in dataset["orders"]
                if order["status"] == "completed"
            )
            assert sum(row.revenue for row in result.data.rows) == expected
        elif name == "get_refund_analytics":
            products = {row["product_id"]: row for row in dataset["products"]}
            orders = {row["order_id"]: row for row in dataset["orders"]}
            payments = {row["payment_id"]: row for row in dataset["payments"]}
            expected = {}
            for refund in dataset["refunds"]:
                order = orders[payments[refund["payment_id"]]["order_id"]]
                for item in dataset["order_items"]:
                    if item["order_id"] == order["order_id"]:
                        category = products[item["product_id"]]["category"]
                        expected[category] = (
                            expected.get(category, Decimal(0))
                            + refund["amount"]
                            * item["quantity"]
                            * item["unit_price"]
                            / order["total_amount"]
                        )
            assert {row.category: row.refund_amount for row in result.data.rows} == {
                key: value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                for key, value in expected.items()
            }
        elif name == "get_customer_order_summary":
            orders = [row for row in dataset["orders"] if row["customer_id"] == 1]
            assert result.data.rows[0].order_count == len(orders)
            assert result.data.rows[0].completed_revenue == sum(
                row["total_amount"] for row in orders if row["status"] == "completed"
            )
        else:
            rows = {row.payment_status: row for row in result.data.rows}
            assert rows["failed"].payment_count == 486
            assert rows["successful"].payment_count == 2520
            for status, row in rows.items():
                assert row.amount == sum(
                    payment["amount"]
                    for payment in dataset["payments"]
                    if payment["payment_status"] == status
                )
        assert registry._repository.database.engine.pool.checkedout() == 0
    finally:
        registry.close()


def verify_workflow(value, index):
    assert value["status"] == "completed" and value["mode"] == "mock"
    assert [trace["tool"] for trace in value["tools"]] == SEQUENCES[index]
    assert value["grounding_checks"] == "passed"
    assert all(trace["result"]["status"] == "success" for trace in value["tools"])
    if index in (1, 2):
        rows = value["tools"][0]["result"]["data"]["rows"]
        assert [(row["product_id"], row["revenue"]) for row in rows] == TOP_FIVE
        assert value["partial"] and "truncated_evidence" in value["limitations"]
    if index in (0, 2):
        document = value["tools"][-1]
        assert document["citations"] == ["QP-RET-001#s002-c001"]
        assert document["citations"][0] in value["answer"] and "30 calendar days" in value["answer"]
    if index == 3:
        assert "486 failed payment attempts [E1]" in value["answer"]
        assert value["tools"][1]["citations"] == ["QP-PAY-003#s002-c001"]
        assert "[E2]" in value["answer"]
    assert all("arguments" not in trace and "call_id" not in trace for trace in value["tools"])


@pytest.mark.parametrize("index", range(4))
def test_fastapi_shared_lifecycle_real_tools(index, integration_settings):
    with TestClient(create_app(integration_settings)) as client:
        response = client.post(
            "/api/v1/agent/ask", json={"question": QUESTIONS[index], "mode": "mock"}
        )
    assert response.status_code == 200
    value = response.json()
    assert value["request_id"] == response.headers["x-request-id"]
    verify_workflow(value, index)


@pytest.mark.local_http
def test_four_workflows_over_real_http(integration_backend):
    client = ApiClient(FrontendSettings(api_base_url=integration_backend))
    capabilities = client.capabilities()
    for index, question in enumerate(QUESTIONS):
        response = client.ask(
            AskRequest(question=question, mode="mock"),
            execution_timeout_seconds=capabilities.execution_timeout_seconds,
        )
        verify_workflow(response.model_dump(mode="json"), index)


@pytest.mark.local_http
def test_streamlit_real_http_to_postgresql(integration_backend, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("QUERYPILOT_API_BASE_URL", integration_backend)
    path = Path(__file__).resolve().parents[1] / "src/querypilot/frontend/app.py"
    app = AppTest.from_file(str(path), default_timeout=30).run()
    assert not app.exception
    for index, question in enumerate(QUESTIONS):
        app.chat_input[0].set_value(question).run(timeout=30)
        assert not app.exception
        verify_workflow(app.session_state.history[-1].response.model_dump(mode="json"), index)
    assert len(app.chat_message) == 8 and len(app.dataframe) == 3
    assert len(app.code) == 3
    assert not app.error
    app.run()
    assert len(app.session_state.history) == 4  # Rerun did not submit again.
    app.button[0].click().run()
    assert not app.session_state.history


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("authentication", "database_authentication_error"),
        ("missing_database", "database_not_found"),
        ("connection", "database_unavailable"),
    ],
)
def test_real_connection_failures_are_specific_and_safe(failure, expected, integration_settings):
    import secrets

    url = make_url(integration_settings.reader_database_url.get_secret_value())
    sentinel = secrets.token_urlsafe(30)
    if failure == "authentication":
        url = url.set(password=sentinel)
    elif failure == "missing_database":
        url = url.set(database="querypilot_absent_database_test")
    else:
        # Port 1 is closed in this dedicated local environment; no database is mocked.
        url = url.set(port=1)
    settings = integration_settings.model_copy(
        update={"reader_database_url": SecretStr(url.render_as_string(hide_password=False))}
    )
    registry = create_registry(settings)
    try:
        result = registry.execute("get_top_products", {})
        assert result.error.code == expected
        assert (
            sentinel not in result.model_dump_json()
            and "postgresql://" not in result.model_dump_json()
        )
    finally:
        registry.close()


def test_read_only_doctor_and_full_fixture(integration_settings):
    report = diagnose(integration_settings, reference_date=date(2026, 10, 27))
    assert not report.failed
    assert {check.name for check in report.checks if check.status == "PASS"} >= {
        "database_connection",
        "required_tables",
        "restricted_reader",
        "seed_data",
        "fixture",
        "migrations",
        "documents",
        "mock_provider",
    }
    # Doctor did not change the known data or leave a checked-out connection.
    database = create_database(integration_settings, reader=True)
    try:
        from querypilot.db.verify import verify_database

        assert verify_database(database, date(2026, 10, 27))["counts"]["orders"] == 3000
        assert database.engine.pool.checkedout() == 0
    finally:
        database.close()


def test_real_missing_tables_error_is_safe_and_connection_returns_to_pool(integration_settings):
    # Mutations are restricted to a newly generated schema in the acknowledged test DB.
    schema = "querypilot_missing_" + uuid4().hex
    writer_url = integration_settings.database_url.get_secret_value()
    reader_url = integration_settings.reader_database_url.get_secret_value()
    admin = create_engine(writer_url, hide_parameters=True)
    reader = Database(
        create_engine(
            reader_url,
            hide_parameters=True,
            connect_args={"options": f"-csearch_path={schema} -cdefault_transaction_read_only=on"},
        )
    )
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            with reader.engine.connect() as reader_connection:
                role = reader_connection.scalar(text("SELECT current_user"))
            quoted = connection.dialect.identifier_preparer.quote(role)
            connection.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO {quoted}'))
        result = ToolRegistry(AnalyticsRepository(reader), settings=integration_settings).execute(
            "get_top_products", {}
        )
        assert result.error.code == "database_schema_missing"
        assert schema not in result.model_dump_json() and "SELECT" not in result.model_dump_json()
        assert reader.engine.pool.checkedout() == 0
    finally:
        reader.close()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()
