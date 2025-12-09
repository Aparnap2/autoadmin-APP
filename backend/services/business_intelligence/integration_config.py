"""
Business Intelligence Integration Configuration
Configuration and setup instructions for integrating the business intelligence module
with the existing FastAPI application and HTTP streaming system.
"""

import logging
from typing import Dict, Any, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api_endpoints import router as bi_router
from .streaming_router import streaming_router
from .streaming_integration import start_streaming_cleanup_task
from ..middleware.sse_middleware import SSEMiddleware, HTTPPollingMiddleware, ConnectionTrackingMiddleware


def configure_business_intelligence_integration(
    app: FastAPI,
    cors_origins: List[str] = None,
    enable_sse_middleware: bool = True,
    enable_polling_middleware: bool = True,
    enable_connection_tracking: bool = True
) -> None:
    """
    Configure complete business intelligence integration with FastAPI application.

    This function sets up:
    - CORS middleware for frontend integration
    - SSE middleware for real-time streaming
    - HTTP polling middleware optimization
    - Connection tracking and monitoring
    - Business intelligence API routes
    - Streaming endpoints
    - Background tasks for maintenance

    Args:
        app: FastAPI application instance
        cors_origins: List of allowed CORS origins
        enable_sse_middleware: Enable Server-Sent Events middleware
        enable_polling_middleware: Enable HTTP polling optimization middleware
        enable_connection_tracking: Enable connection tracking middleware
    """

    logger = logging.getLogger(__name__)

    # Configure CORS for frontend integration
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "Accept",
                "Cache-Control",
                "Last-Event-ID",
                "If-Modified-Since",
                "If-None-Match",
                "X-Requested-With"
            ],
            expose_headers=[
                "ETag",
                "Last-Modified",
                "Cache-Control",
                "X-Stream-Type",
                "X-Connection-ID"
            ]
        )

    # Add streaming-specific middleware
    if enable_sse_middleware:
        app.add_middleware(SSEMiddleware)
        logger.info("SSE middleware enabled for business intelligence streaming")

    if enable_polling_middleware:
        app.add_middleware(HTTPPollingMiddleware)
        logger.info("HTTP polling middleware enabled for optimization")

    if enable_connection_tracking:
        app.add_middleware(ConnectionTrackingMiddleware)
        logger.info("Connection tracking middleware enabled")

    # Include business intelligence routes
    app.include_router(
        bi_router,
        prefix="/api/v2/business-intelligence",
        tags=["Business Intelligence"]
    )
    logger.info("Business intelligence API router included")

    # Include streaming routes
    app.include_router(
        streaming_router,
        prefix="/api/v2/business-intelligence",
        tags=["Business Intelligence Streaming"]
    )
    logger.info("Business intelligence streaming router included")

    # Add root-level streaming endpoints for easier frontend access
    @app.get("/api/v2/streaming/health")
    async def streaming_health():
        """Root-level streaming health check"""
        from .streaming_router import streaming_health_check
        return await streaming_health_check()

    @app.get("/api/v2/streaming/stats")
    async def streaming_stats():
        """Root-level streaming statistics"""
        from .streaming_router import get_streaming_stats
        return await get_streaming_stats()

    logger.info("Root-level streaming endpoints configured")


def get_integration_config() -> Dict[str, Any]:
    """
    Get the recommended configuration for business intelligence integration.

    Returns:
        Dictionary containing configuration details and recommendations
    """

    return {
        "api_version": "2.0.0",
        "base_path": "/api/v2/business-intelligence",
        "streaming_path": "/api/v2/business-intelligence/stream",
        "features": {
            "real_time_streaming": {
                "enabled": True,
                "protocol": "Server-Sent Events",
                "fallback": "HTTP Polling"
            },
            "morning_briefing": {
                "enabled": True,
                "auto_generation": True,
                "frequency": "daily"
            },
            "revenue_intelligence": {
                "enabled": True,
                "forecasting": True,
                "churn_analysis": True,
                "pricing_optimization": True
            },
            "task_delegation": {
                "enabled": True,
                "intelligent_routing": True,
                "confidence_scoring": True
            },
            "competitive_intelligence": {
                "enabled": True,
                "automated_monitoring": True,
                "market_analysis": True
            },
            "crm_intelligence": {
                "enabled": True,
                "hubspot_integration": True,
                "deal_health_scoring": True,
                "pipeline_optimization": True
            },
            "strategic_planning": {
                "enabled": True,
                "okr_tracking": True,
                "scenario_analysis": True,
                "recommendation_engine": True
            },
            "kpi_calculation": {
                "enabled": True,
                "real_time_updates": True,
                "trend_analysis": True,
                "predictive_analytics": True
            },
            "alert_system": {
                "enabled": True,
                "intelligent_detection": True,
                "escalation_workflows": True,
                "multi_channel_notifications": True
            }
        },
        "middleware": {
            "sse_middleware": {
                "enabled": True,
                "purpose": "Handle Server-Sent Events headers and configuration"
            },
            "polling_middleware": {
                "enabled": True,
                "purpose": "Optimize HTTP polling with caching and ETags"
            },
            "connection_tracking": {
                "enabled": True,
                "purpose": "Monitor active streaming connections"
            }
        },
        "endpoints": {
            "morning_briefing": {
                "rest": "/morning-briefing",
                "stream": "/stream/morning-briefing/{user_id}"
            },
            "revenue_intelligence": {
                "rest": "/revenue-analysis",
                "stream": "/stream/revenue/{user_id}"
            },
            "task_delegation": {
                "rest": "/delegate-task",
                "stream": "/stream/task-delegation/{user_id}"
            },
            "competitive_intelligence": {
                "rest": "/competitive-analysis",
                "stream": "/stream/competitive/{user_id}"
            },
            "crm_intelligence": {
                "rest": "/crm-analysis",
                "stream": "/stream/crm/{user_id}"
            },
            "strategic_plan": {
                "rest": "/strategic-plan",
                "stream": "/stream/strategic/{user_id}"
            },
            "kpis": {
                "rest": "/kpis",
                "stream": "/stream/kpi-dashboard/{dashboard_id}/{user_id}"
            },
            "alerts": {
                "rest": "/alerts",
                "stream": "/stream/alerts/{user_id}"
            },
            "executive_dashboard": {
                "rest": "/executive-dashboard",
                "stream": "/stream/dashboard/{user_id}"
            }
        },
        "performance": {
            "max_connections": 1000,
            "connection_timeout": 300,  # 5 minutes
            "heartbeat_interval": 120,  # 2 minutes
            "cleanup_interval": 300,  # 5 minutes
            "stream_buffer_size": 8192,
            "compression": False  # SSE doesn't support compression
        },
        "security": {
            "authentication_required": True,
            "user_isolation": True,
            "rate_limiting": True,
            "cors_enabled": True
        },
        "monitoring": {
            "logging_enabled": True,
            "metrics_enabled": True,
            "health_checks": True,
            "connection_monitoring": True
        },
        "frontend_integration": {
            "react_components": True,
            "typescript_support": True,
            "sse_client": True,
            "fallback_polling": True,
            "automatic_reconnection": True,
            "error_handling": True
        }
    }


def setup_background_tasks(app: FastAPI) -> None:
    """
    Setup background tasks for business intelligence maintenance.

    Args:
        app: FastAPI application instance
    """

    @app.on_event("startup")
    async def startup_event():
        """Initialize background tasks on application startup"""
        try:
            # Start streaming connection cleanup task
            cleanup_task = start_streaming_cleanup_task()

            logging.info(
                "Business intelligence background tasks started",
                extra={
                    "streaming_cleanup": "started",
                    "config": get_integration_config()
                }
            )

        except Exception as e:
            logging.error(f"Error starting background tasks: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on application shutdown"""
        try:
            # Cancel background tasks
            # Note: In a real implementation, you'd store task references and cancel them here

            logging.info("Business intelligence background tasks stopped")

        except Exception as e:
            logging.error(f"Error stopping background tasks: {e}")


def validate_integration() -> Dict[str, Any]:
    """
    Validate the business intelligence integration setup.

    Returns:
        Dictionary containing validation results
    """

    logger = logging.getLogger(__name__)

    try:
        validation_results = {
            "status": "unknown",
            "checks": {},
            "issues": [],
            "recommendations": []
        }

        # Check required dependencies
        try:
            import fastapi
            validation_results["checks"]["fastapi"] = {
                "status": "pass",
                "version": fastapi.__version__
            }
        except ImportError:
            validation_results["checks"]["fastapi"] = {
                "status": "fail",
                "error": "FastAPI not installed"
            }
            validation_results["issues"].append("FastAPI is required for business intelligence integration")

        # Check streaming dependencies
        try:
            import asyncio
            validation_results["checks"]["asyncio"] = {
                "status": "pass",
                "available": True
            }
        except ImportError:
            validation_results["checks"]["asyncio"] = {
                "status": "fail",
                "error": "Asyncio not available"
            }
            validation_results["issues"].append("Asyncio is required for streaming functionality")

        # Check BI module components
        try:
            from .morning_briefing import MorningBriefingGenerator
            validation_results["checks"]["morning_briefing"] = {
                "status": "pass",
                "available": True
            }
        except ImportError as e:
            validation_results["checks"]["morning_briefing"] = {
                "status": "fail",
                "error": str(e)
            }
            validation_results["issues"].append("Morning briefing module not available")

        # Check configuration
        config = get_integration_config()
        validation_results["checks"]["configuration"] = {
            "status": "pass",
            "api_version": config["api_version"],
            "features_enabled": len([f for f in config["features"] if config["features"][f]["enabled"]])
        }

        # Determine overall status
        if not validation_results["issues"]:
            validation_results["status"] = "pass"
            validation_results["recommendations"].append("All checks passed - integration ready")
        else:
            validation_results["status"] = "fail"

        logger.info(
            f"Business intelligence integration validation: {validation_results['status']}",
            extra=validation_results
        )

        return validation_results

    except Exception as e:
        logger.error(f"Error during integration validation: {e}")
        return {
            "status": "error",
            "error": str(e),
            "checks": {},
            "issues": ["Validation error occurred"],
            "recommendations": ["Check error logs and fix dependencies"]
        }


# Export configuration functions
__all__ = [
    "configure_business_intelligence_integration",
    "get_integration_config",
    "setup_background_tasks",
    "validate_integration"
]