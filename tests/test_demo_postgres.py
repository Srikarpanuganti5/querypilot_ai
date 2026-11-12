"""Real PostgreSQL + actual FastAPI service through isolated in-process HTTP transport."""

import httpx
import pytest
from fastapi.testclient import TestClient

from querypilot.main import create_app
from querypilot.services.smoke import smoke_test

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("direct", [False, True])
def test_smoke_existing_service_and_independent_reader_checks(integration_settings, direct):
    submitted = []
    with TestClient(create_app(integration_settings)) as client:

        def forward(request):
            if request.method == "POST":
                submitted.append(request.content)
            response = client.request(
                request.method,
                request.url.path,
                content=request.content,
                headers={"Content-Type": "application/json"},
            )
            return httpx.Response(response.status_code, content=response.content)

        report = smoke_test(
            "http://backend.test",
            integration_settings,
            verify_database=direct,
            transport=httpx.MockTransport(forward),
        )
    assert report["passed"] and len(report["cases"]) == 4
    assert len(submitted) == 4 and all(b'"mode":"mock"' in raw for raw in submitted)
    assert report["direct_database"] == ("REAL DATABASE VERIFIED" if direct else "NOT VERIFIED")
    if direct:
        check = next(c for c in report["checks"] if c["name"] == "direct_database")
        assert check["failed_payment_attempts"] == 486
