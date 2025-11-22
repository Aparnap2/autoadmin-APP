"""
Monitoring and metrics endpoints
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.models.common import MetricsResponse

logger = get_logger(__name__)

router = APIRouter()

# Store metrics in memory (in production, use proper metrics system like Prometheus)
_metrics_store = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "response_times": [],
    "errors_total": 0,
    "agents_active": 0,
    "tasks_completed": 0,
    "tasks_failed": 0,
    "start_time": time.time(),
}


@router.get("/metrics", response_model=MetricsResponse, summary="Application Metrics")
async def get_metrics(
    include_system: bool = Query(default=False, description="Include system-level metrics")
) -> MetricsResponse:
    """
    Get application and system metrics

    Args:
        include_system: Whether to include system-level metrics

    Returns:
        MetricsResponse: Current application metrics
    """
    app_metrics = get_application_metrics()
    system_metrics = get_system_metrics() if include_system else {}

    logger.info(
        "Metrics requested",
        include_system=include_system,
        metrics_count=len(app_metrics)
    )

    return MetricsResponse(
        timestamp=datetime.utcnow(),
        metrics=app_metrics,
        system_metrics=system_metrics
    )


@router.get("/metrics/agents", summary="Agent Metrics")
async def get_agent_metrics() -> Dict[str, Any]:
    """
    Get agent-specific metrics

    Returns:
        Dict: Agent performance metrics
    """
    # This is a placeholder - implement actual agent metrics collection
    agent_metrics = {
        "total_agents": 4,  # marketing, finance, devops, strategy
        "active_agents": _metrics_store["agents_active"],
        "agent_types": {
            "marketing": {"active": 1, "tasks_completed": 45, "success_rate": 0.95},
            "finance": {"active": 0, "tasks_completed": 23, "success_rate": 0.91},
            "devops": {"active": 1, "tasks_completed": 67, "success_rate": 0.98},
            "strategy": {"active": 0, "tasks_completed": 12, "success_rate": 0.88}
        },
        "total_tasks_completed": _metrics_store["tasks_completed"],
        "total_tasks_failed": _metrics_store["tasks_failed"],
        "average_task_duration": 125.5,  # seconds
        "agent_health_score": 0.93
    }

    return agent_metrics


@router.get("/metrics/ai", summary="AI Services Metrics")
async def get_ai_metrics() -> Dict[str, Any]:
    """
    Get AI/LLM service metrics

    Returns:
        Dict: AI service performance metrics
    """
    # This is a placeholder - implement actual AI metrics collection
    ai_metrics = {
        "openai": {
            "requests_total": 1234,
            "requests_today": 89,
            "tokens_used": 156789,
            "average_response_time_ms": 1250,
            "success_rate": 0.98,
            "cost_today_usd": 2.45,
            "rate_limit_remaining": 4500
        },
        "embeddings": {
            "requests_total": 456,
            "vectors_generated": 789,
            "average_dimension": 1536,
            "cache_hit_rate": 0.73
        },
        "vector_search": {
            "searches_total": 234,
            "average_search_time_ms": 45,
            "average_results_count": 8.5
        }
    }

    return ai_metrics


@router.get("/metrics/performance", summary="Performance Metrics")
async def get_performance_metrics(
    period: str = Query(default="1h", description="Time period (1h, 24h, 7d)")
) -> Dict[str, Any]:
    """
    Get performance metrics for a time period

    Args:
        period: Time period for metrics

    Returns:
        Dict: Performance metrics
    """
    # Calculate time period
    periods = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7)
    }

    time_delta = periods.get(period, timedelta(hours=1))

    # This is a placeholder - implement actual performance metrics collection
    performance_metrics = {
        "period": period,
        "timestamp": datetime.utcnow(),
        "requests": {
            "total": _metrics_store["requests_total"],
            "requests_per_minute": calculate_requests_per_minute(time_delta),
            "average_response_time_ms": calculate_average_response_time(),
            "p95_response_time_ms": calculate_p95_response_time(),
            "error_rate": calculate_error_rate()
        },
        "endpoints": _metrics_store["requests_by_endpoint"],
        "status_codes": {
            "200": _metrics_store["requests_total"] - _metrics_store["errors_total"],
            "4xx": int(_metrics_store["errors_total"] * 0.3),
            "5xx": int(_metrics_store["errors_total"] * 0.7)
        }
    }

    return performance_metrics


@router.post("/metrics/record", summary="Record Custom Metric")
async def record_metric(
    metric_name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Record a custom metric

    Args:
        metric_name: Name of the metric
        value: Metric value
        tags: Optional tags for the metric

    Returns:
        Dict: Recording result
    """
    try:
        # This is a placeholder - implement actual metric recording
        logger.info(
            "Custom metric recorded",
            metric_name=metric_name,
            value=value,
            tags=tags
        )

        return {
            "status": "recorded",
            "metric": metric_name,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to record metric {metric_name}: {e}")
        return {
            "status": "error",
            "metric": metric_name,
            "error": str(e)
        }


@router.get("/status/components", summary="Component Status")
async def get_component_status() -> Dict[str, Any]:
    """
    Get status of all system components

    Returns:
        Dict: Component status information
    """
    components = {
        "api_server": {
            "status": "healthy",
            "uptime_seconds": int(time.time() - _metrics_store["start_time"]),
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        },
        "database": {
            "status": "healthy",  # Placeholder - implement actual check
            "connection_pool": {"active": 5, "idle": 15, "total": 20}
        },
        "redis": {
            "status": "healthy",  # Placeholder - implement actual check
            "memory_usage": "45MB",
            "connected_clients": 3
        },
        "celery": {
            "status": "healthy",  # Placeholder - implement actual check
            "active_workers": 2,
            "pending_tasks": 0,
            "active_tasks": 3
        },
        "firebase": {
            "status": "healthy",  # Placeholder - implement actual check
            "project_id": settings.FIREBASE_PROJECT_ID
        },
        "openai": {
            "status": "healthy",  # Placeholder - implement actual check
            "rate_limit_remaining": "unknown"
        }
    }

    return components


# Helper functions for metrics calculation
def get_application_metrics() -> Dict[str, Any]:
    """Get application-level metrics"""
    return {
        "requests_total": _metrics_store["requests_total"],
        "errors_total": _metrics_store["errors_total"],
        "uptime_seconds": int(time.time() - _metrics_store["start_time"]),
        "agents_active": _metrics_store["agents_active"],
        "tasks_completed": _metrics_store["tasks_completed"],
        "tasks_failed": _metrics_store["tasks_failed"],
        "average_response_time_ms": calculate_average_response_time(),
        "error_rate": calculate_error_rate()
    }


def get_system_metrics() -> Dict[str, Any]:
    """Get system-level metrics"""
    try:
        import psutil
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            "process_count": len(psutil.pids())
        }
    except ImportError:
        return {}
    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        return {}


def calculate_requests_per_minute(time_delta: timedelta) -> float:
    """Calculate requests per minute"""
    # Placeholder implementation
    return _metrics_store["requests_total"] / max(1, time_delta.total_seconds() / 60)


def calculate_average_response_time() -> float:
    """Calculate average response time"""
    response_times = _metrics_store["response_times"]
    if not response_times:
        return 0.0
    return sum(response_times) / len(response_times)


def calculate_p95_response_time() -> float:
    """Calculate 95th percentile response time"""
    response_times = sorted(_metrics_store["response_times"])
    if not response_times:
        return 0.0
    index = int(len(response_times) * 0.95)
    return response_times[min(index, len(response_times) - 1)]


def calculate_error_rate() -> float:
    """Calculate error rate"""
    if _metrics_store["requests_total"] == 0:
        return 0.0
    return _metrics_store["errors_total"] / _metrics_store["requests_total"]


# Metric recording function (to be called by middleware)
def record_request(endpoint: str, response_time: float, status_code: int):
    """Record request metrics"""
    _metrics_store["requests_total"] += 1
    _metrics_store["response_times"].append(response_time)

    # Keep only last 1000 response times for memory efficiency
    if len(_metrics_store["response_times"]) > 1000:
        _metrics_store["response_times"] = _metrics_store["response_times"][-1000:]

    # Track by endpoint
    if endpoint not in _metrics_store["requests_by_endpoint"]:
        _metrics_store["requests_by_endpoint"][endpoint] = 0
    _metrics_store["requests_by_endpoint"][endpoint] += 1

    # Track errors
    if status_code >= 400:
        _metrics_store["errors_total"] += 1


def record_agent_activity(active_count: int):
    """Record agent activity metrics"""
    _metrics_store["agents_active"] = active_count


def record_task_completion(success: bool):
    """Record task completion metrics"""
    if success:
        _metrics_store["tasks_completed"] += 1
    else:
        _metrics_store["tasks_failed"] += 1