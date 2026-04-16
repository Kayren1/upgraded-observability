from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    All settings have safe defaults suitable for local development.
    In production, override with actual .env values.
    """

    # ============================================================================
    # APPLICATION METADATA
    # ============================================================================

    APP_NAME: str = "Upgraded Observability Platform"
    APP_VERSION: str = "1.0.0"

    # Enable debug mode only in development.
    # This exposes stack traces and should NEVER be True in production.
    DEBUG_MODE_IS_ENABLED: bool = False

    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/observability"
    )
    # We use pool_pre_ping to avoid "connection lost" errors from dropped idle connections.
    # See: https://docs.sqlalchemy.org/en/20/core/pooling.html#pool-pre-ping
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_POOL_OVERFLOW: int = 20

    # ============================================================================
    # REDIS / CACHING CONFIGURATION
    # ============================================================================

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Redis is used for:
    # - Celery task queue (collector jobs)
    # - Rate limiting counters
    # - Session caching (future)

    # ============================================================================
    # JWT / AUTHENTICATION CONFIGURATION
    # ============================================================================

    # Secret key for signing JWT tokens. MUST be changed in production.
    # Generate a new one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    JWT_SECRET_KEY_FOR_SIGNING: str = os.getenv(
        "SECRET_KEY",
        "your-super-secret-key-change-in-production-INSECURE"
    )
    JWT_SIGNING_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRATION_MINUTES: int = 30
    # TODO(kweku, 2025-04-16): Implement refresh tokens for better security.
    # Right now we only have short-lived access tokens. A refresh token system
    # would allow long sessions with automatic token rotation.

    # ============================================================================
    # PROMETHEUS CONFIGURATION
    # ============================================================================

    PROMETHEUS_METRICS_ENDPOINT_URL: str = os.getenv(
        "PROMETHEUS_URL",
        "http://localhost:9090"
    )

    # ============================================================================
    # GRAFANA CONFIGURATION
    # ============================================================================

    GRAFANA_DASHBOARD_URL: str = os.getenv(
        "GRAFANA_URL",
        "http://localhost:3001"
    )

    # ============================================================================
    # CORS / FRONTEND CONFIGURATION
    # ============================================================================

    # Allowed origins for CORS. In production, restrict to your frontend domain.
    # Example: ["https://app.observability.com", "https://admin.observability.com"]
    CORS_ALLOWED_ORIGINS_LIST: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # Local API docs
    ]

    # Expose as property for backwards compatibility with existing code.
    @property
    def CORS_ORIGINS(self) -> list:
        return self.CORS_ALLOWED_ORIGINS_LIST

    class Config:
        env_file = ".env"


# Singleton instance used throughout the app.
# Import this with: from .core.config import settings
settings = Settings()

# Log configuration at startup (but only non-sensitive values).
logger.info(f"Loaded configuration: {settings.APP_NAME} v{settings.APP_VERSION}")
if settings.DEBUG_MODE_IS_ENABLED:
    logger.warning("⚠️  DEBUG MODE IS ENABLED. This should never happen in production.")

