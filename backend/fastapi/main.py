"""
AutoAdmin FastAPI Backend
Production-ready async backend for AI agent orchestration and services
Replaces Netlify Functions with robust Python backend architecture
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.error_handler import add_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.sse_middleware import (
    SSEMiddleware,
    HTTPPollingMiddleware,
    ConnectionTrackingMiddleware,
)
from app.routers import (
    # agents,  # Temporarily disabled
    # ai,  # Temporarily disabled
    # webhooks,  # Temporarily disabled
    # hubspot,  # Temporarily disabled
    # memory,  # Temporarily disabled
    # tasks,  # Temporarily disabled
    # files,  # Temporarily disabled
    health,
    monitoring,
    # github,  # Temporarily disabled due to circular import
    # streaming,  # Temporarily disabled
    # http_polling,  # Temporarily disabled
    # business_intelligence,  # Temporarily disabled
)

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events"""

    # Startup
    logger.info("🚀 AutoAdmin FastAPI Backend starting up...")

    try:
        # Initialize core services here
        # - Database connections
        # - Redis connection
        # - Celery worker initialization
        # - Firebase service initialization
        # - LangGraph agent setup
        # - HTTP polling service initialization
        from backend.services.http_polling import get_http_polling_service
        from backend.services.agent_orchestrator_http import get_http_agent_orchestrator

        # Initialize HTTP polling service
        polling_service = get_http_polling_service()
        logger.info("✅ HTTP Polling Service initialized")

        # Initialize HTTP agent orchestrator
        agent_orchestrator = get_http_agent_orchestrator()
        logger.info("✅ HTTP Agent Orchestrator initialized")

        logger.info("✅ All services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 AutoAdmin FastAPI Backend shutting down...")

    try:
        # Cleanup resources here
        # - Close database connections
        # - Stop Celery workers
        # - Close streaming connections

        # Gracefully shutdown HTTP polling service
        from backend.services.http_polling import get_http_polling_service
        from backend.services.agent_orchestrator_http import get_http_agent_orchestrator

        polling_service = get_http_polling_service()
        await polling_service.graceful_shutdown()
        logger.info("✅ HTTP Polling Service shut down successfully")

        # Shutdown agent orchestrator
        agent_orchestrator = get_http_agent_orchestrator()
        # Add orchestrator cleanup if needed

        logger.info("✅ All services shut down successfully")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


# Create FastAPI application instance
app = FastAPI(
    title="AutoAdmin API",
    description="Production-ready backend for AI agent orchestration, LangGraph operations, and intelligent task automation",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
    contact={
        "name": "AutoAdmin Team",
        "email": "team@autoadmin.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add CORS middleware with HTTP-only communication support
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Cache-Control", "Content-Type", "X-Process-Time", "Last-Event-ID"],
)

# Add trusted host middleware for security
if settings.ENVIRONMENT == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Add HTTP-only real-time communication middleware
app.add_middleware(SSEMiddleware)
app.add_middleware(HTTPPollingMiddleware)
app.add_middleware(ConnectionTrackingMiddleware)

# Add custom rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add exception handlers for graceful error handling
add_exception_handlers(app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing information"""
    import time

    start_time = time.time()

    # Log request details
    logger.info(
        "📥 Incoming request",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )

    # Process request
    response = await call_next(request)

    # Calculate and log response time
    process_time = time.time() - start_time

    logger.info(
        "📤 Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
        },
    )

    # Add process time header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Include routers for different service modules
app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["Monitoring"],
    responses={404: {"description": "Not found"}},
)

# app.include_router(
#     agents.router,
#     prefix="/api/v1/agents",
#     tags=["Agents"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     ai.router,
#     prefix="/api/v1/ai",
#     tags=["AI Services"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     memory.router,
#     prefix="/api/v1/memory",
#     tags=["Memory Services"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     tasks.router,
#     prefix="/api/v1/tasks",
#     tags=["Task Management"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     webhooks.router,
#     prefix="/api/v1/webhooks",
#     tags=["Webhooks"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     files.router,
#     prefix="/api/v1/files",
#     tags=["File Management"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     github.router,
#     prefix="/api/v1/github",
#     tags=["GitHub"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     notifications.router,
#     prefix="/api/v1/notifications",
#     tags=["Notifications"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     hubspot.router,
#     prefix="/api/v1/hubspot",
#     tags=["HubSpot"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     streaming.router,
#     prefix="/api/v1/streaming",
#     tags=["Streaming"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     http_polling.router,
#     prefix="/api/v1/polling",
#     tags=["HTTP Polling"],
#     responses={404: {"description": "Not found"}},
# )

# app.include_router(
#     business_intelligence.router,
#     prefix="/api/v1/business-intelligence",
#     tags=["Business Intelligence"],
#     responses={404: {"description": "Not found"}},
# )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to AutoAdmin API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.ENVIRONMENT != "production" else None,
        "health": "/health",
        "monitoring": "/monitoring",
    }


@app.get("/api/v1", tags=["API"])
async def api_info():
    """API version information"""
    return {
        "api_version": "v1",
        "status": "active",
        "communication": "http_only",
        "realtime_support": {
            "sse": "Server-Sent Events available",
            "polling": "Long polling endpoints available",
        },
        "endpoints": {
            "agents": "/api/v1/agents",
            "ai": "/api/v1/ai",
            "memory": "/api/v1/memory",
            "tasks": "/api/v1/tasks",
            "webhooks": "/api/v1/webhooks",
            "hubspot": "/api/v1/hubspot",
            "files": "/api/v1/files",
            "github": "/api/v1/github",
            "notifications": "/api/v1/notifications",
            "streaming": "/api/v1/streaming",
            "business_intelligence": "/api/v1/business-intelligence",
        },
        "streaming_endpoints": {
            "sse_connection": "/api/v1/streaming/connect",
            "sse_events": "/api/v1/streaming/events/{client_id}",
            "chat_streaming": "/api/v1/streaming/chat/stream/{agent_type}",
            "dashboard_stream": "/api/v1/business-intelligence/dashboards/{dashboard_id}/stream",
            "agent_status_stream": "/api/v1/agents/{agent_id}/status/stream",
            "task_updates_stream": "/api/v1/agents/tasks/stream",
            "notifications_stream": "/api/v1/notifications/stream",
        },
        "polling_endpoints": {
            "polling_session": "/api/v1/streaming/polling/session",
            "poll_events": "/api/v1/streaming/polling/poll",
            "agent_status_poll": "/api/v1/agents/{agent_id}/status/poll",
            "notifications_poll": "/api/v1/notifications/poll",
            "http_polling_session": "/api/v1/polling/session",
            "http_poll_events": "/api/v1/polling/poll",
            "http_agent_poll": "/api/v1/polling/agent/{agent_id}/poll",
            "http_events": "/api/v1/polling/events",
            "http_status": "/api/v1/polling/status",
            "http_health": "/api/v1/polling/health",
            "http_metrics": "/api/v1/polling/metrics",
        },
        "documentation": "/docs" if settings.ENVIRONMENT != "production" else None,
        "features": {
            "websocket_replacement": "Replaced with SSE and HTTP polling",
            "connection_recovery": "Supports connection recovery with event replay",
            "cross_origin": "CORS enabled for HTTP-only communication",
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting AutoAdmin FastAPI server...")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
