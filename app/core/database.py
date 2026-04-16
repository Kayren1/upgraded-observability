from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

from .config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE ENGINE SETUP
# ============================================================================

try:
    # Create SQLAlchemy engine with connection pooling optimizations.
    # pool_pre_ping=True ensures we don't get "connection lost" errors from idle connections.
    # QueuePool is the default and works well for multi-threaded/async scenarios.
    database_engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_pre_ping=True,  # Test connection before reusing from pool
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_POOL_OVERFLOW,
        echo=settings.DEBUG_MODE_IS_ENABLED,  # Log SQL queries in debug mode
    )

    logger.info(f"✓ Database engine initialized: {settings.DATABASE_URL}")

except Exception as database_engine_creation_error:
    error_message = (
        f"FATAL: Failed to create database engine. "
        f"DATABASE_URL: {settings.DATABASE_URL}. "
        f"Error: {database_engine_creation_error}. "
        f"Ensure PostgreSQL is running and the connection string is valid."
    )
    logger.critical(error_message)
    raise RuntimeError(error_message) from database_engine_creation_error


# Create ORM base class for all models to inherit from.
MetadataBase = declarative_base()

# Create session factory. Sessions are NOT thread-safe, so do NOT reuse across requests.
SessionFactory = sessionmaker(
    bind=database_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=True,  # Expire objects after commit to force lazy-loaded refresh
)


def get_database_session():
    """
    Dependency injection function for FastAPI.
    Yields a new database session for each request, then automatically closes it.

    This is a generator function used with fastapi.Depends().
    The database session is automatically rolled back on exception.
    """
    newly_created_database_session = SessionFactory()
    try:
        yield newly_created_database_session
    except Exception as session_usage_error:
        # Rollback on error to prevent partial transactions.
        newly_created_database_session.rollback()
        logger.error(f"Database session error (rolled back): {session_usage_error}")
        raise
    finally:
        # Always close the session, even if an error occurred.
        newly_created_database_session.close()


# Aliases for backwards compatibility and clarity.
engine = database_engine
Base = MetadataBase
get_db = get_database_session

