"""Process liveness; intentionally independent of external services."""

from fastapi import APIRouter, Request

from querypilot.schemas.system import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(service="querypilot-ai", version=request.app.version)
