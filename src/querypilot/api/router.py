"""Keep process health unversioned and business API metadata under v1."""

from fastapi import APIRouter

from querypilot.api.routes.agent import router as agent_router
from querypilot.api.routes.health import router as health_router
from querypilot.api.routes.info import router as info_router

router = APIRouter()
router.include_router(health_router)
router.include_router(info_router, prefix="/api/v1")
router.include_router(agent_router, prefix="/api/v1")
