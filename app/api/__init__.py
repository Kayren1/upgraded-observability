from fastapi import APIRouter
from .auth import router as auth_router
from .workspaces import router as workspaces_router
from .systems import router as systems_router
from .alerts import router as alerts_router
from .metrics import router as metrics_router
from .collectors import router as collectors_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(systems_router, prefix="/systems", tags=["Systems"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])
api_router.include_router(collectors_router, prefix="/collectors", tags=["Collectors"])
