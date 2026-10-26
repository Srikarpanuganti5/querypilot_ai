"""Versioned API metadata."""

from fastapi import APIRouter, Request

from querypilot.schemas.system import InfoResponse

router = APIRouter(tags=["system"])


@router.get("/info", response_model=InfoResponse)
async def info(request: Request) -> InfoResponse:
    return InfoResponse(
        name=request.app.title, version=request.app.version, description=request.app.description
    )
