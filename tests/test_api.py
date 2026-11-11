"""Exercise the ASGI application without any external services."""

import json
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from querypilot.core.config import Settings
from querypilot.main import create_app


@pytest.fixture
def application() -> FastAPI:
    return create_app(Settings(_env_file=None, cors_origins=["http://localhost:8501"]))


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "querypilot-ai", "version": "0.1.0"}
    assert response.headers["x-request-id"]


def test_info(client: TestClient) -> None:
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    assert response.json() == {
        "name": "QueryPilot AI",
        "version": "0.1.0",
        "description": "Tool-Using LLM Agent API",
    }


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_documentation(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/openapi.json" in response.text


def test_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.")
    assert document["info"]["title"] == "QueryPilot AI"
    assert document["info"]["version"] == "0.1.0"
    assert set(document["paths"]) == {
        "/health",
        "/ready",
        "/api/v1/info",
        "/api/v1/agent/ask",
        "/api/v1/agent/capabilities",
    }
    assert document["paths"]["/health"]["get"]["responses"]["200"]["content"]


@pytest.mark.parametrize("path", ["/unknown", "/api/v1/chat"])
def test_unknown_route(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Not Found",
            "request_id": response.headers["x-request-id"],
            "details": [],
        }
    }


def test_method_not_allowed(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json()["error"]["message"] == "Method Not Allowed"
    assert "GET" in response.headers["allow"]


def test_validation_does_not_echo_input(application: FastAPI) -> None:
    @application.get("/_test/validate")
    async def validate(count: int) -> dict[str, int]:
        return {"count": count}

    with TestClient(application) as test_client:
        response = test_client.get("/_test/validate", params={"count": "SECRET_VALUE"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["request_id"] == response.headers["x-request-id"]
    assert error["details"][0]["location"] == ["query", "count"]
    assert "SECRET_VALUE" not in response.text


def test_http_exception_detail_is_sanitized(application: FastAPI) -> None:
    @application.get("/_test/http-error")
    async def fail() -> None:
        raise HTTPException(403, "SECRET_VALUE")

    with TestClient(application) as test_client:
        response = test_client.get("/_test/http-error")
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Forbidden"
    assert "SECRET_VALUE" not in response.text


def test_unexpected_error_and_logs_are_sanitized(
    application: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    @application.get("/_test/failure")
    async def fail() -> None:
        raise RuntimeError("SECRET_VALUE")

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get(
            "/_test/failure?token=SECRET_QUERY", headers={"Origin": "http://localhost:8501"}
        )
        test_client.get("/SECRET_PATH", headers={"Authorization": "Bearer SECRET_HEADER"})
    assert response.status_code == 500
    assert response.json()["error"]["message"] == "An unexpected error occurred"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:8501"
    output = capsys.readouterr().err
    for secret in ("SECRET_VALUE", "SECRET_QUERY", "SECRET_PATH", "SECRET_HEADER"):
        assert secret not in output + response.text
    records = [json.loads(line) for line in output.splitlines()]
    failure = next(record for record in records if record["event"] == "request_failed")
    assert failure["error_type"] == "RuntimeError"
    assert failure["request_id"] == response.headers["x-request-id"]
    assert any(record.get("status_code") == 500 for record in records)


def test_cors_allows_only_configured_origin(client: TestClient) -> None:
    allowed = client.get("/health", headers={"Origin": "http://localhost:8501"})
    denied = client.get("/health", headers={"Origin": "https://unconfigured.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:8501"
    assert "access-control-allow-origin" not in denied.headers


def test_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:8501", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    denied = client.options(
        "/health",
        headers={"Origin": "https://unconfigured.example", "Access-Control-Request-Method": "GET"},
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_cors_is_disabled_by_default() -> None:
    with TestClient(create_app(Settings(_env_file=None, cors_origins=[]))) as test_client:
        response = test_client.get("/health", headers={"Origin": "http://localhost:8501"})
    assert "access-control-allow-origin" not in response.headers
