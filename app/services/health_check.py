"""
Real-world health check implementations for all platform services.
This module provides defensive, production-grade health verification.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from redis import Redis, ConnectionError as RedisConnectionError
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE HEALTH CHECK
# ============================================================================

def verify_database_connection_is_healthy(database_session: Session) -> Dict[str, Any]:
    """
    Verify PostgreSQL database is responsive and healthy.
    Performs a simple query to check connectivity and responsiveness.

    Returns:
        Dictionary with status, latency, and error details
    """
    if database_session is None:
        return {
            "status": "unhealthy",
            "reason": "Database session is None",
            "latency_ms": None,
        }

    try:
        # Execute a simple query to verify connectivity.
        # SELECT 1 is a fast, low-overhead health check.
        query_start_time = datetime.utcnow()
        result = database_session.execute(text("SELECT 1"))
        query_end_time = datetime.utcnow()

        query_was_successful = result.scalar() == 1
        query_latency_milliseconds = (query_end_time - query_start_time).total_seconds() * 1000

        if not query_was_successful:
            logger.warning("Database health check: SELECT 1 returned unexpected result")
            return {
                "status": "unhealthy",
                "reason": "SELECT 1 query returned unexpected result",
                "latency_ms": query_latency_milliseconds,
            }

        # Check if latency is acceptable (>5 seconds is unhealthy)
        if query_latency_milliseconds > 5000:
            logger.warning(
                f"Database health check: Query latency is high ({query_latency_milliseconds}ms). "
                f"Database may be under load or experiencing issues."
            )
            return {
                "status": "degraded",
                "reason": f"Query latency too high: {query_latency_milliseconds:.0f}ms",
                "latency_ms": query_latency_milliseconds,
            }

        return {
            "status": "healthy",
            "latency_ms": query_latency_milliseconds,
        }

    except Exception as database_check_error:
        error_message = str(database_check_error)
        logger.error(f"Database health check failed: {error_message}")
        return {
            "status": "unhealthy",
            "reason": f"Database connection failed: {error_message}",
            "latency_ms": None,
        }


# ============================================================================
# REDIS HEALTH CHECK
# ============================================================================

def verify_redis_connection_is_healthy() -> Dict[str, Any]:
    """
    Verify Redis cache is responsive and healthy.
    Attempts to connect and performs a PING operation.

    Returns:
        Dictionary with status, latency, and error details
    """
    if settings.REDIS_URL is None or settings.REDIS_URL == "":
        return {
            "status": "unhealthy",
            "reason": "REDIS_URL not configured",
        }

    try:
        # Create Redis client.
        # Decode_responses=True means responses are strings, not bytes.
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,  # 5 second timeout to fail fast
            socket_keepalive=True,
        )

        # Attempt PING to verify connectivity.
        ping_start_time = datetime.utcnow()
        ping_response = redis_client.ping()
        ping_end_time = datetime.utcnow()

        ping_latency_milliseconds = (ping_end_time - ping_start_time).total_seconds() * 1000

        # Redis PING should return True or "PONG"
        if not ping_response:
            logger.warning("Redis health check: PING returned unexpected response")
            return {
                "status": "unhealthy",
                "reason": "Redis PING returned unexpected response",
                "latency_ms": ping_latency_milliseconds,
            }

        # Check if latency is acceptable (>1 second is degraded, >5 seconds is unhealthy)
        if ping_latency_milliseconds > 5000:
            logger.warning(f"Redis health check: PING latency too high ({ping_latency_milliseconds}ms)")
            return {
                "status": "unhealthy",
                "reason": f"Redis latency too high: {ping_latency_milliseconds:.0f}ms",
                "latency_ms": ping_latency_milliseconds,
            }

        if ping_latency_milliseconds > 1000:
            logger.warning(f"Redis health check: PING latency is degraded ({ping_latency_milliseconds}ms)")
            return {
                "status": "degraded",
                "reason": f"Redis latency elevated: {ping_latency_milliseconds:.0f}ms",
                "latency_ms": ping_latency_milliseconds,
            }

        return {
            "status": "healthy",
            "latency_ms": ping_latency_milliseconds,
        }

    except RedisConnectionError as redis_connection_error:
        error_message = str(redis_connection_error)
        logger.error(f"Redis health check failed: Cannot connect. Error: {error_message}")
        return {
            "status": "unhealthy",
            "reason": f"Redis connection failed: {error_message}",
            "latency_ms": None,
        }

    except Exception as unexpected_redis_error:
        error_message = str(unexpected_redis_error)
        logger.error(f"Redis health check failed: Unexpected error: {error_message}")
        return {
            "status": "unhealthy",
            "reason": f"Redis error: {error_message}",
            "latency_ms": None,
        }


# ============================================================================
# PROMETHEUS HEALTH CHECK
# ============================================================================

def verify_prometheus_connection_is_healthy() -> Dict[str, Any]:
    """
    Verify Prometheus time-series database is responsive and healthy.
    Queries the Prometheus HTTP API to verify it's accessible and responding.

    Returns:
        Dictionary with status, latency, and error details
    """
    if settings.PROMETHEUS_METRICS_ENDPOINT_URL is None or settings.PROMETHEUS_METRICS_ENDPOINT_URL == "":
        return {
            "status": "unhealthy",
            "reason": "PROMETHEUS_URL not configured",
        }

    try:
        # Query Prometheus API health endpoint.
        # The /-/healthy endpoint returns 200 if Prometheus is healthy.
        prometheus_health_url = f"{settings.PROMETHEUS_METRICS_ENDPOINT_URL}/-/healthy"

        request_start_time = datetime.utcnow()
        http_response = requests.get(
            prometheus_health_url,
            timeout=5,  # 5 second timeout to fail fast
        )
        request_end_time = datetime.utcnow()

        request_latency_milliseconds = (request_end_time - request_start_time).total_seconds() * 1000

        # Prometheus health endpoint returns 200 when healthy
        if http_response.status_code != 200:
            logger.warning(
                f"Prometheus health check: Returned status {http_response.status_code}. "
                f"Prometheus may be unhealthy or overloaded."
            )
            return {
                "status": "unhealthy",
                "reason": f"Prometheus returned HTTP {http_response.status_code}",
                "latency_ms": request_latency_milliseconds,
            }

        # Check if latency is acceptable (>5 seconds is unhealthy)
        if request_latency_milliseconds > 5000:
            logger.warning(
                f"Prometheus health check: Response latency too high ({request_latency_milliseconds}ms)"
            )
            return {
                "status": "unhealthy",
                "reason": f"Prometheus latency too high: {request_latency_milliseconds:.0f}ms",
                "latency_ms": request_latency_milliseconds,
            }

        if request_latency_milliseconds > 1000:
            logger.warning(
                f"Prometheus health check: Response latency is elevated ({request_latency_milliseconds}ms)"
            )
            return {
                "status": "degraded",
                "reason": f"Prometheus latency elevated: {request_latency_milliseconds:.0f}ms",
                "latency_ms": request_latency_milliseconds,
            }

        return {
            "status": "healthy",
            "latency_ms": request_latency_milliseconds,
        }

    except requests.exceptions.Timeout as prometheus_timeout_error:
        logger.error(f"Prometheus health check failed: Request timeout. Prometheus is not responding.")
        return {
            "status": "unhealthy",
            "reason": f"Prometheus request timeout",
            "latency_ms": None,
        }

    except requests.exceptions.ConnectionError as prometheus_connection_error:
        error_message = str(prometheus_connection_error)
        logger.error(f"Prometheus health check failed: Cannot connect. Error: {error_message}")
        return {
            "status": "unhealthy",
            "reason": f"Cannot connect to Prometheus: {error_message}",
            "latency_ms": None,
        }

    except Exception as unexpected_prometheus_error:
        error_message = str(unexpected_prometheus_error)
        logger.error(f"Prometheus health check failed: Unexpected error: {error_message}")
        return {
            "status": "unhealthy",
            "reason": f"Prometheus error: {error_message}",
            "latency_ms": None,
        }


# ============================================================================
# COMPREHENSIVE HEALTH CHECK
# ============================================================================

def perform_comprehensive_platform_health_check(database_session: Session) -> Dict[str, Any]:
    """
    Perform comprehensive health check of all platform services.

    Returns:
        Dictionary with status of all services, overall health, and timestamp
    """
    if database_session is None:
        return {
            "status": "unhealthy",
            "reason": "Database session is None",
            "overall_platform_status": "unhealthy",
            "checked_at": datetime.utcnow().isoformat(),
            "services": {},
        }

    # Check all services in parallel-like fashion (sequentially but collecting all results)
    database_health = verify_database_connection_is_healthy(database_session)
    redis_health = verify_redis_connection_is_healthy()
    prometheus_health = verify_prometheus_connection_is_healthy()

    # Determine overall platform status.
    # Platform is healthy only if all services are healthy.
    # Platform is degraded if any service is degraded.
    # Platform is unhealthy if any service is unhealthy.
    service_statuses = [
        database_health.get("status"),
        redis_health.get("status"),
        prometheus_health.get("status"),
    ]

    if "unhealthy" in service_statuses:
        overall_platform_status = "unhealthy"
    elif "degraded" in service_statuses:
        overall_platform_status = "degraded"
    else:
        overall_platform_status = "healthy"

    return {
        "status": overall_platform_status,
        "overall_platform_status": overall_platform_status,
        "checked_at": datetime.utcnow().isoformat(),
        "services": {
            "database": database_health,
            "redis": redis_health,
            "prometheus": prometheus_health,
        },
    }
