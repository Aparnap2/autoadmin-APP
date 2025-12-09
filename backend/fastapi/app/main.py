"""
FastAPI application with comprehensive monitoring and observability
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import os
from typing import Dict, Any

# Import our monitoring system
from monitoring.integration import (
    initialize_monitoring,
    get_monitoring_middleware,
    get_monitoring_router,
    monitor_exceptions,
    monitor_performance,
    ServiceComponent,
)
from monitoring.logger import get_logger, LogLevel

# Import existing routers
from .routers.agents import router as agents_router

# Import new PM system routers
from .routers.wip_limits import router as wip_limits_router
from .routers.atomic_tasking import router as atomic_tasking_router
from .routers.git_integration import router as git_integration_router
from .routers.project_spaces import router as project_spaces_router
from .routers.timeboxing_momentum import combined_router as timeboxing_momentum_router
from .routers.ai_execution import router as ai_execution_router

# Initialize logger
logger = get_logger("fastapi_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with monitoring initialization"""
    # Startup
    logger.info(
        "Starting AutoAdmin FastAPI application", component=ServiceComponent.API
    )

    try:
        # Initialize monitoring system
        monitoring_config = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "database": {"connection_string": os.getenv("DATABASE_URL")},
            "redis": {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "password": os.getenv("REDIS_PASSWORD"),
                "db": int(os.getenv("REDIS_DB", "0")),
            },
            "qdrant": {
                "url": os.getenv("QDRANT_URL"),
                "api_key": os.getenv("QDRANT_API_KEY"),
            },
            "metrics_collection_interval": int(os.getenv("METRICS_INTERVAL", "15")),
            "alert_evaluation_interval": int(os.getenv("ALERT_INTERVAL", "60")),
            "metrics_retention_hours": int(os.getenv("METRICS_RETENTION", "24")),
        }

        await initialize_monitoring(monitoring_config)

        logger.info(
            "AutoAdmin FastAPI application started successfully",
            component=ServiceComponent.API,
            environment=monitoring_config["environment"],
        )

        yield

    except Exception as e:
        logger.error(
            "Failed to start AutoAdmin FastAPI application",
            component=ServiceComponent.API,
            error=e,
        )
        raise

    finally:
        # Shutdown
        logger.info(
            "Shutting down AutoAdmin FastAPI application",
            component=ServiceComponent.API,
        )


# Create FastAPI application with lifespan
app = FastAPI(
    title="AutoAdmin API",
    description="AI-powered administrative assistant with comprehensive monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add monitoring middleware
monitoring_middleware = get_monitoring_middleware()
app.middleware("http")(monitoring_middleware)

# Include routers
app.include_router(agents_router, prefix="/api/v1")
app.include_router(get_monitoring_router(), tags=["monitoring"])

# Include new PM system routers
app.include_router(wip_limits_router)
app.include_router(atomic_tasking_router)
app.include_router(git_integration_router)
app.include_router(project_spaces_router)
app.include_router(timeboxing_momentum_router)
app.include_router(ai_execution_router)


# Health check endpoints (simplified versions for backward compatibility)
@app.get("/health", tags=["health"])
@monitor_performance("health_check", ServiceComponent.API)
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "service": "autoadmin-backend",
        "version": "1.0.0",
    }


@app.get("/ready", tags=["health"])
@monitor_performance("readiness_check", ServiceComponent.API)
async def readiness_check():
    """Readiness probe endpoint"""
    return {"status": "ready", "timestamp": "2024-01-01T00:00:00Z"}


@app.get("/live", tags=["health"])
@monitor_performance("liveness_check", ServiceComponent.API)
async def liveness_check():
    """Liveness probe endpoint"""
    return {"status": "alive", "timestamp": "2024-01-01T00:00:00Z"}


# Root endpoint
@app.get("/")
@monitor_performance("root_endpoint", ServiceComponent.API)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AutoAdmin API - AI-powered administrative assistant",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "agents": "/api/v1/agents",
            "monitoring": "/monitoring",
        },
    }


# Error handlers with monitoring
@app.exception_handler(Exception)
@monitor_exceptions(ServiceComponent.API)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with error tracking"""
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        component=ServiceComponent.API,
        error=exc,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(ValueError)
@monitor_exceptions(ServiceComponent.API)
async def validation_exception_handler(request: Request, exc: ValueError):
    """Validation error handler"""
    logger.warning(
        f"Validation error: {str(exc)}",
        component=ServiceComponent.API,
        method=request.method,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "message": str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    """404 error handler"""
    logger.info(
        f"404 Not Found: {request.method} {request.url.path}",
        component=ServiceComponent.API,
        method=request.method,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": f"Endpoint {request.method} {request.url.path} not found",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(
        "AutoAdmin FastAPI application startup complete", component=ServiceComponent.API
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info(
        "AutoAdmin FastAPI application shutting down", component=ServiceComponent.API
    )


# Test endpoints for monitoring
@app.post("/test/error")
async def test_error_endpoint():
    """Test endpoint to trigger different types of errors"""
    from monitoring.error_tracking import ErrorSeverity, ErrorCategory
    from monitoring import error_tracker

    try:
        # This will trigger error tracking
        raise ValueError("This is a test error for monitoring system")
    except Exception as e:
        # Track the error with specific severity and category
        context = error_tracker.ErrorContext(
            component=ServiceComponent.API,
            endpoint="/test/error",
            custom_data={"test_error": True},
        )
        await error_tracker.track_error(
            e,
            context=context,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
        )
        raise


@app.get("/test/performance")
@monitor_performance(
    "test_performance_endpoint", ServiceComponent.API, {"test": "true"}
)
async def test_performance_endpoint():
    """Test endpoint for performance monitoring"""
    import time
    import random

    # Simulate some work
    work_time = random.uniform(0.1, 0.5)
    await asyncio.sleep(work_time)

    # Simulate some metrics
    from monitoring import metrics_collector

    metrics_collector.increment(
        "test_operations_total", 1, {"endpoint": "test_performance"}
    )
    metrics_collector.gauge(
        "test_work_time_ms", work_time * 1000, {"endpoint": "test_performance"}
    )

    return {
        "message": "Performance test completed",
        "work_time_seconds": work_time,
        "timestamp": "2024-01-01T00:00:00Z",
    }


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info",
    )
