"""Readiness is separate from process liveness; no migration or seed on HTTP requests."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from querypilot.services.doctor import diagnose

router = APIRouter(tags=["system"])


@router.get("/ready", responses={503: {"description": "Database or corpus not ready"}})
def readiness(request: Request) -> JSONResponse:
    report = diagnose(request.app.state.settings)
    return JSONResponse(
        status_code=503 if report.failed else 200,
        content={
            "status": "not_ready" if report.failed else "ready",
            "checks": [
                {"name": check.name, "status": check.status, "code": check.code}
                for check in report.checks
                if check.name != "backend"
            ],
        },
    )
