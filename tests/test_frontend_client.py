"""Only in-memory HTTP transports; no live/provider requests."""

import json
import secrets

import httpx
import pytest
from pydantic import ValidationError

from querypilot.frontend.api_client import MAX_RESPONSE_BYTES, ApiClient, ClientError
from querypilot.frontend.config import FrontendSettings
from querypilot.schemas.agent import AskRequest


def make_client(handler):
    return ApiClient(
        FrontendSettings(api_base_url="http://backend.test:8000"),
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize("mode", ["mock", "live"])
def test_request_is_stateless_typed_and_never_retried(mode, document_response):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url == "http://backend.test:8000/api/v1/agent/ask"
        assert json.loads(request.content) == {"question": "Return policy?", "mode": mode}
        assert request.extensions["timeout"]["read"] == 105
        value = document_response.model_dump(mode="json")
        value["mode"] = mode
        return httpx.Response(200, json=value)

    result = make_client(handler).ask(
        AskRequest(question="Return policy?", mode=mode), execution_timeout_seconds=90
    )
    assert result.mode == mode and len(requests) == 1


@pytest.mark.parametrize("timeout", [False, True])
def test_connection_and_timeout_are_safe_and_not_retried(timeout):
    calls = []
    sentinel = secrets.token_urlsafe(30)

    def handler(request):
        calls.append(request)
        if timeout:
            raise httpx.ReadTimeout(sentinel, request=request)
        raise httpx.ConnectError(sentinel, request=request)

    with pytest.raises(ClientError) as error:
        make_client(handler).ask(
            AskRequest(question="Q", mode="live"), execution_timeout_seconds=90
        )
    assert error.value.code == ("request_timeout" if timeout else "backend_unavailable")
    assert sentinel not in str(error.value) and len(calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"answer": "made up"}),
        httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1)),
        httpx.Response(302, headers={"location": "https://example.invalid"}),
    ],
)
def test_malformed_oversized_or_redirected_response_rejected(response):
    with pytest.raises(ClientError):
        make_client(lambda request: response).ask(
            AskRequest(question="Q"), execution_timeout_seconds=90
        )


def test_mode_mismatch_rejected(document_response):
    with pytest.raises(ClientError, match="incompatible"):
        make_client(
            lambda request: httpx.Response(200, json=document_response.model_dump(mode="json"))
        ).ask(AskRequest(question="Q", mode="live"), execution_timeout_seconds=90)


def test_untrusted_http_error_text_not_displayed():
    sentinel = secrets.token_urlsafe(30)
    with pytest.raises(ClientError) as error:
        make_client(
            lambda request: httpx.Response(
                403, json={"error": {"code": "live_disabled", "message": sentinel}}
            )
        ).ask(AskRequest(question="Q"), execution_timeout_seconds=90)
    assert error.value.code == "live_disabled" and sentinel not in str(error.value)


def test_fabricated_citations_rejected_in_response(document_response):
    value = document_response.model_dump(mode="json")
    value["tools"][0]["citations"] = ["QP-FAKE-999#s001-c001"]
    with pytest.raises(ClientError):
        make_client(lambda request: httpx.Response(200, json=value)).ask(
            AskRequest(question="Q"), execution_timeout_seconds=90
        )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:password@localhost",
        "http://localhost/path",
        "http://localhost?token=x",
    ],
)
def test_frontend_url_rejects_credentials_and_non_origins(url):
    with pytest.raises(ValidationError):
        FrontendSettings(api_base_url=url)


def test_frontend_settings_ignore_backend_env_file(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=unused\nQUERYPILOT_API_BASE_URL=http://from-file.invalid\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUERYPILOT_API_BASE_URL", raising=False)
    settings = FrontendSettings()
    assert str(settings.api_base_url) == "http://127.0.0.1:8000/"
    assert not hasattr(settings, "openai_api_key")
