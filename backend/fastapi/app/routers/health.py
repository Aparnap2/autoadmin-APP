"""
Health check endpoints for monitoring system status
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.models.common import HealthResponse

logger = get_logger(__name__)

router = APIRouter()

# Store startup time for uptime calculation
startup_time = time.time()


@router.get("/", response_model=HealthResponse, summary="System Health Check")
async def health_check() -> HealthResponse:
    """
    Comprehensive health check for all system components

    Returns:
        HealthResponse: System health status and component status
    """
    start_time = time.time()

    # Check core services health
    services_status = {}

    # Check Redis (if configured)
    services_status["redis"] = await check_redis_health()

    # Check Database (if configured)
    if settings.DATABASE_URL:
        services_status["database"] = await check_database_health()

    # Check Firebase services
    services_status["firebase"] = await check_firebase_health()

    # Check OpenAI service
    services_status["openai"] = await check_openai_health()

    # Check Celery worker (if configured)
    services_status["celery"] = await check_celery_health()

    # Calculate overall status
    overall_status = "healthy"
    if any(status == "unhealthy" for status in services_status.values()):
        overall_status = "unhealthy"
    elif any(status == "degraded" for status in services_status.values()):
        overall_status = "degraded"

    # Calculate uptime
    uptime_seconds = time.time() - startup_time

    # Get memory usage
    memory_usage = get_memory_usage()

    # Total response time
    response_time = (time.time() - start_time) * 1000

    logger.info(
        "Health check completed",
        overall_status=overall_status,
        response_time_ms=response_time,
        services=services_status
    )

    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        services=services_status,
        uptime_seconds=uptime_seconds,
        memory_usage_mb=memory_usage
    )


@router.get("/simple", summary="Simple Health Check")
async def simple_health_check() -> Dict[str, str]:
    """
    Simple health check for load balancers and monitoring

    Returns:
        Dict with basic health status
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION
    }


@router.get("/readiness", summary="Readiness Check")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe - checks if application is ready to serve traffic

    Returns:
        Dict with readiness status
    """
    try:
        # Check critical dependencies
        ready = True
        checks = {}

        # Check Firebase (critical dependency)
        firebase_status = await check_firebase_health()
        checks["firebase"] = firebase_status
        if firebase_status != "healthy":
            ready = False

        # Check OpenAI (critical dependency)
        openai_status = await check_openai_health()
        checks["openai"] = openai_status
        if openai_status != "healthy":
            ready = False

        return {
            "ready": ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "ready": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/liveness", summary="Liveness Check")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe - checks if application is alive

    Returns:
        Dict with liveness status
    """
    return {
        "alive": "true",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - startup_time)
    }


# Health check helper functions
async def check_redis_health() -> str:
    """Check Redis connectivity"""
    try:
        # This is a placeholder - implement actual Redis health check
        # For now, just check if Redis URL is configured
        if settings.REDIS_URL:
            return "healthy"
        else:
            return "not_configured"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return "unhealthy"


async def check_database_health() -> str:
    """Check database connectivity"""
    try:
        # This is a placeholder - implement actual database health check
        # For now, just check if database URL is configured
        if settings.DATABASE_URL:
            return "healthy"
        else:
            return "not_configured"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return "unhealthy"


async def check_firebase_health() -> str:
    """Check Firebase connectivity"""
    try:
        # This is a placeholder - implement actual Firebase health check
        # Check if Firebase credentials are configured
        if all([
            settings.FIREBASE_PROJECT_ID,
            settings.FIREBASE_CLIENT_EMAIL,
            settings.FIREBASE_PRIVATE_KEY
        ]):
            return "healthy"
        else:
            return "not_configured"
    except Exception as e:
        logger.warning(f"Firebase health check failed: {e}")
        return "unhealthy"


async def check_openai_health() -> str:
    """Check OpenAI service connectivity"""
    try:
        # This is a placeholder - implement actual OpenAI health check
        # Check if OpenAI API key is configured
        if settings.OPENAI_API_KEY:
            return "healthy"
        else:
            return "not_configured"
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {e}")
        return "unhealthy"


async def check_celery_health() -> str:
    """Check Celery worker status"""
    try:
        # This is a placeholder - implement actual Celery health check
        # For now, just check if Celery is configured
        if settings.CELERY_BROKER_URL:
            return "healthy"
        else:
            return "not_configured"
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        return "unhealthy"


def get_memory_usage() -> float:
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        # psutil not available, return None
        return None
    except Exception as e:
        logger.warning(f"Failed to get memory usage: {e}")
        return None