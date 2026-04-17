from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import engine, Base, get_database_session
from .api import api_router
from .services.health_check import perform_comprehensive_platform_health_check

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Called at startup and shutdown. We use this to initialize the database
    and verify all external service connections before the first request.
    """
    logger.info("🚀 Starting Upgraded Observability Platform...")
    try:
        # Create all database tables from SQLAlchemy models.
        # This is idempotent — if tables exist, this is a no-op.
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables initialized")
    except Exception as database_initialization_error:
        logger.error(
            f"Failed to initialize database at startup. Error: {database_initialization_error}. "
            f"Check DATABASE_URL in .env and ensure PostgreSQL is running."
        )
        raise

    # TODO(kweku, 2025-04-16): Add startup verification of Redis and Prometheus connections.
    # If any critical service is unreachable, fail fast and don't start the application.
    # This prevents silent failures after deployment.

    yield

    logger.info("🛑 Shutting down gracefully...")
    # TODO(kweku, 2025-04-16): Add cleanup for background tasks if we add Celery workers.
    # Currently, we're stateless, so there's nothing to clean up.


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-grade, multi-tenant observability platform for monitoring distributed systems",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Add CORS middleware. In production, this should be restricted to specific origins.
# TODO(kweku, 2025-04-16): Replace CORS_ORIGINS with actual frontend domain(s) in production.
# Allowing all origins is a security risk. We're only doing this for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include versioned API routes.
# All endpoints are under /api/v1 for forward compatibility.
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def platform_root_endpoint():
    """
    Platform root endpoint providing metadata and documentation links.
    Used by load balancers, browsers, and API clients.
    """
    platform_metadata_response = {
        "platform_name": settings.APP_NAME,
        "platform_version": settings.APP_VERSION,
        "documentation_url": "/docs",
        "openapi_schema_url": "/openapi.json",
        "health_check_url": "/health",
    }
    return platform_metadata_response


@app.get("/health")
def real_time_platform_health_check(database_session=Depends(get_database_session)):
    """
    Real-time health check endpoint.

    Returns comprehensive status of all critical platform services:
    - PostgreSQL database
    - Redis cache
    - Prometheus metrics storage

    Used by:
    - Load balancers for availability detection
    - Kubernetes for liveness/readiness probes
    - Monitoring systems for uptime verification
    - CI/CD pipelines for deployment validation

    Response statuses:
    - healthy: All services operational
    - degraded: Services operational but experiencing latency
    - unhealthy: One or more services down or unresponsive
    """
    if database_session is None:
        logger.error("Health check endpoint: Database session is None")
        return {
            "status": "unhealthy",
            "reason": "Internal server error: Database session unavailable",
            "checked_at": None,
        }

    try:
        comprehensive_health_status = perform_comprehensive_platform_health_check(database_session)
        return comprehensive_health_status
    except Exception as health_check_error:
        logger.error(f"Health check failed with exception: {health_check_error}")
        return {
            "status": "unhealthy",
            "reason": f"Health check error: {str(health_check_error)}",
            "checked_at": None,
        }
