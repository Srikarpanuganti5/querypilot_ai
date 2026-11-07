"""Actual Streamlit AppTest runs; API responses use real mock document evidence."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from querypilot.frontend.api_client import ClientError
from querypilot.schemas.agent import AgentCapabilities

APP = Path(__file__).resolve().parents[1] / "src/querypilot/frontend/app.py"


class FakeApi:
    def __init__(self, outcome):
        self.outcome, self.requests, self.error = outcome, [], None
        self.cap_error = None
        self.cap = AgentCapabilities(
            live_enabled=True,
            live_configured=True,
            execution_timeout_seconds=90,
            max_iterations=5,
            max_tool_calls=10,
            max_tools_per_iteration=5,
        )

    def capabilities(self):
        if self.cap_error:
            raise self.cap_error
        return self.cap

    def ask(self, request, *, execution_timeout_seconds):
        self.requests.append(request.model_dump())
        if self.error:
            raise self.error
        return self.outcome.model_copy(update={"mode": request.mode, "question": request.question})


@pytest.fixture
def ui(document_response, monkeypatch):
    api = FakeApi(document_response)
    monkeypatch.setattr("querypilot.frontend.api_client.ApiClient", lambda config: api)
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not app.exception
    return app, api


def test_initial_empty_state_and_example_does_not_submit(ui):
    app, api = ui
    assert app.title[0].value == "QueryPilot AI" and not api.requests
    app.button(key="example_1").click().run()
    assert app.chat_input[0].value == "What is our return policy?"
    assert not api.requests


def test_chat_persists_and_rerun_never_resubmits(ui):
    app, api = ui
    app.chat_input[0].set_value("Return policy?").run()
    assert not app.exception
    assert len(api.requests) == 1 and len(app.chat_message) == 2
    assert api.requests[0] == {"question": "Return policy?", "mode": "mock"}
    assert any("30 calendar days" in item.value for item in app.text)
    assert any(item.value == "QP-RET-001#s002-c001" for item in app.code)
    app.run()
    assert len(api.requests) == 1 and len(app.chat_message) == 2
    app.chat_input[0].set_value("Another policy question?").run()
    assert len(api.requests) == 2 and "history" not in api.requests[1]
    app.button[0].click().run()  # Clear conversation
    assert not app.chat_message and not app.session_state.history
    assert len(api.requests) == 2


def test_live_mode_selection_never_calls_agent(ui):
    app, api = ui
    app.selectbox[0].set_value("Live OpenAI").run()
    assert not api.requests
    app.chat_input[0].set_value("Return policy?").run()
    assert api.requests == [{"question": "Return policy?", "mode": "live"}]
    assert any("Live OpenAI execution" in item.value for item in app.caption)


@pytest.mark.parametrize("configured", [False, True])
def test_live_unavailable_disables_submission(configured, ui):
    app, api = ui
    api.cap.live_enabled = configured
    api.cap.live_configured = False
    app.selectbox[0].set_value("Live OpenAI").run()
    assert app.chat_input[0].disabled and not api.requests
    assert app.warning


def test_processing_disables_duplicate_submission(ui):
    app, api = ui
    app.session_state.busy = True
    app.run()
    assert app.chat_input[0].disabled and app.button[0].disabled
    assert not api.requests


def test_backend_failure_is_safe_and_reconnectable(ui):
    app, api = ui
    api.cap_error = ClientError("backend_unavailable")
    app.run()
    assert app.chat_input[0].disabled and app.error and not app.exception
    api.cap_error = None
    app.run()
    assert not app.chat_input[0].disabled and not api.requests


@pytest.mark.parametrize("code", ["request_timeout", "invalid_response", "rate_limit"])
def test_request_errors_allow_manual_retry(code, ui):
    app, api = ui
    api.error = ClientError(code)
    app.chat_input[0].set_value("Return policy?").run()
    assert app.error and not app.exception and not app.session_state.busy
    assert len(api.requests) == 1
    api.error = None
    app.chat_input[0].set_value("Return policy?").run()
    assert len(api.requests) == 2


def test_partial_and_conflicting_evidence_warning(ui):
    from querypilot.schemas.llm import ExecutionError

    app, api = ui
    api.outcome = api.outcome.model_copy(
        update={
            "partial": True,
            "status": "error",
            "answer": None,
            "errors": [ExecutionError(code="evidence_conflict", message="not rendered")],
        }
    )
    app.chat_input[0].set_value("Return policy?").run()
    assert any("Partial" in item.value for item in app.warning)
    assert any("Conflicting" in item.value for item in app.error)
    assert any(item.value == "QP-RET-001#s002-c001" for item in app.code)
    assert not app.exception


def test_sql_table_and_truncation_notice_render(ui):
    from querypilot.schemas.agent import AgentResponse

    app, api = ui
    value = api.outcome.model_dump(mode="json")
    value.update(
        answer="Synthetic product: USD 19.98 [E1]", partial=True, limitations=["truncated_evidence"]
    )
    value["tools"] = [
        {
            "evidence_id": "E1",
            "iteration": 1,
            "tool": "get_top_products",
            "status": "success",
            "duration_ms": 4,
            "citations": [],
            "output_truncated": True,
            "result": {
                "tool": "get_top_products",
                "status": "success",
                "duration_ms": 4,
                "data": {
                    "operation": "get_top_products",
                    "truncated": True,
                    "rows": [
                        {
                            "product_id": 1,
                            "name": "Synthetic product",
                            "category": "Home",
                            "units_sold": 2,
                            "revenue": "19.98",
                        }
                    ],
                },
            },
        }
    ]
    api.outcome = AgentResponse.model_validate(value)
    app.chat_input[0].set_value("Top products?").run()
    assert not app.exception and len(app.dataframe) == 1
    assert app.dataframe[0].value.iloc[0]["revenue"] == "19.98"
    assert any("truncated" in item.value for item in app.warning)


def test_empty_evidence_and_missing_answer_render(ui):
    app, api = ui
    api.outcome = api.outcome.model_copy(
        update={
            "status": "no_evidence",
            "answer": None,
            "tools": [],
            "grounding_checks": "not_applicable",
        }
    )
    app.chat_input[0].set_value("Missing data?").run()
    assert not app.exception
    assert any("No successful nonempty evidence" in item.value for item in app.info)


def test_untrusted_narrative_is_rendered_as_text_not_html_or_images(ui):
    app, api = ui
    text = '<img src="https://example.invalid/track"> ![image](https://example.invalid/pixel)'
    api.outcome = api.outcome.model_copy(update={"answer": text})
    app.chat_input[0].set_value("Return policy?").run()
    assert any(item.value == text for item in app.text)
    assert not any(text in item.value for item in app.markdown)
    assert not app.exception


def test_unexpected_client_failure_does_not_expose_traceback(ui):
    app, api = ui
    api.error = RuntimeError("UNSAFE_INTERNAL_DIAGNOSTIC")
    app.chat_input[0].set_value("Return policy?").run()
    assert not app.exception and not app.session_state.busy
    assert not any("UNSAFE_INTERNAL_DIAGNOSTIC" in item.value for item in app.error)


def test_missing_reader_has_database_specific_setup_advice(ui):
    from fastapi.testclient import TestClient

    from querypilot.core.config import Settings
    from querypilot.main import create_app
    from querypilot.schemas.agent import AgentResponse

    app, api = ui
    settings = Settings(_env_file=None, database_url=None, reader_database_url=None)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/agent/ask", json={"question": "Top products by revenue?", "mode": "mock"}
        )
    api.outcome = AgentResponse.model_validate(response.json())
    app.chat_input[0].set_value("Top products by revenue?").run()
    assert not app.exception
    assert any("reader database" in item.value for item in app.warning)
    assert not any("model credentials" in item.value for item in app.warning)
