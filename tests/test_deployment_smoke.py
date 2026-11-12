"""Smoke contracts and failure safety; mocked HTTP does not prove deployment readiness."""

import json

import httpx
import pytest

from querypilot.core.config import Settings
from querypilot.services.smoke import smoke_test


def settings():
    return Settings(
        _env_file=None,
        database_url=None,
        reader_database_url=None,
        openai_api_key=None,
        openai_model=None,
    )


def systems(path):
    if path == "/health":
        return {"status": "healthy", "service": "querypilot-ai", "version": "0.1.0"}
    if path == "/ready":
        return {
            "status": "ready",
            "checks": [
                {"name": name, "status": "PASS"}
                for name in (
                    "database_connection",
                    "required_tables",
                    "restricted_reader",
                    "seed_data",
                    "documents",
                    "mock_provider",
                )
            ],
        }
    if path == "/openapi.json":
        return {
            "openapi": "3.1.0",
            "paths": {
                p: {"post" if p.endswith("/ask") else "get": {}}
                for p in ["/health", "/ready", "/api/v1/agent/capabilities", "/api/v1/agent/ask"]
            },
        }
    return {
        "live_enabled": False,
        "live_configured": False,
        "execution_timeout_seconds": 90,
        "max_iterations": 5,
        "max_tool_calls": 10,
        "max_tools_per_iteration": 5,
    }


@pytest.mark.parametrize(
    "failure,stage",
    [
        ("wrong-service", "backend_liveness"),
        ("not-ready", "backend_readiness"),
        ("ready-contradiction", "backend_readiness"),
        ("missing-contract", "api_contract"),
        ("bad-method", "api_contract"),
        ("bad-json", "backend_liveness"),
        ("redirect", "backend_liveness"),
        ("oversize", "backend_liveness"),
        ("timeout", "backend_liveness"),
        ("network", "backend_liveness"),
    ],
)
def test_smoke_failure_is_non_successful_safe_and_never_submits(failure, stage):
    seen = []

    def handler(request):
        seen.append(request.method)
        path = request.url.path
        if failure == "timeout":
            raise httpx.ReadTimeout("private transport diagnostics")
        if failure == "network":
            raise httpx.ConnectError("private transport diagnostics")
        if failure == "bad-json":
            return httpx.Response(200, content=b"bad private transport diagnostics")
        if failure == "oversize":
            return httpx.Response(200, content=b"x" * 512001)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://unused.invalid"})
        value = systems(path)
        if failure == "wrong-service" and path == "/health":
            value["service"] = "different"
        if failure == "not-ready" and path == "/ready":
            return httpx.Response(503, json={"status": "not_ready"})
        if failure == "ready-contradiction" and path == "/ready":
            value["checks"].append({"name": "migrations", "status": "FAIL"})
        if failure == "missing-contract" and path == "/openapi.json":
            value["paths"].pop("/ready")
        if failure == "bad-method" and path == "/openapi.json":
            value["paths"]["/api/v1/agent/ask"] = {"get": {}}
        return httpx.Response(200, json=value)

    report = smoke_test(
        "http://backend.invalid", settings(), transport=httpx.MockTransport(handler)
    )
    assert not report["passed"] and report["checks"][-1]["name"] == stage
    assert "POST" not in seen and "private transport diagnostics" not in json.dumps(report)
    assert report["duration_ms"] >= 0


def test_credential_bearing_backend_origin_never_leaks_or_connects():
    import secrets

    sentinel = secrets.token_hex(24)

    def unreachable(request):
        raise AssertionError("Origin must be rejected before network access")

    report = smoke_test(
        f"http://user:{sentinel}@unused.invalid",
        settings(),
        transport=httpx.MockTransport(unreachable),
    )
    assert not report["passed"] and sentinel not in json.dumps(report)


def test_smoke_cli_returns_nonzero_for_failed_required_check(monkeypatch, capsys):
    from querypilot.services.smoke import main

    monkeypatch.setattr(
        "querypilot.services.smoke.smoke_test",
        lambda *args, **kwargs: {"passed": False, "checks": []},
    )
    with pytest.raises(SystemExit) as result:
        main(["--backend-url", "http://127.0.0.1:1"])
    assert result.value.code == 1 and "false" in capsys.readouterr().out
