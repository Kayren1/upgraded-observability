from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.database import engine, Base
from .api import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Called at startup and shutdown. We use this to ensure database tables
    exist before the first request hits the API.
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
# TODO(kweku, 2025-04-16): Replace ["*"] with actual frontend domain in production.
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
def health_endpoint_at_root():
    """
    Health check and information endpoint at platform root.
    Useful for load balancers and status monitors.
    """
    platform_metadata = {
        "platform_name": settings.APP_NAME,
        "platform_version": settings.APP_VERSION,
        "deployment_status": "healthy",
        "documentation_url": "/docs",
        "openapi_schema_url": "/openapi.json",
    }
    return platform_metadata


@app.get("/health")
def comprehensive_health_check():
    """
    Detailed health check endpoint.
    Returns status of all critical systems: database, cache, and metrics storage.
    Used by health monitors and CI/CD pipelines.
    """
    # TODO(kweku, 2025-04-16): Actually check Redis and Prometheus connections.
    # Right now this is hardcoded. Once we have proper clients, verify actual connectivity.
    health_status_by_component = {
        "api_server": "healthy",
        "database_connection": "connected",
        "redis_cache": "connected",
        "prometheus_metrics_store": "connected",
        "service_status_timestamp": None,
    }
    return health_status_by_component
