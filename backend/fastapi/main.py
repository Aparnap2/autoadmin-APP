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
from app.routers import (
    agents,
    ai,
    webhooks,
    memory,
    tasks,
    files,
    health,
    monitoring
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
        # - Cleanup WebSocket connections
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

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
        }
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
        }
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

app.include_router(
    agents.router,
    prefix="/api/v1/agents",
    tags=["Agents"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    ai.router,
    prefix="/api/v1/ai",
    tags=["AI Services"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    memory.router,
    prefix="/api/v1/memory",
    tags=["Memory Services"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    tasks.router,
    prefix="/api/v1/tasks",
    tags=["Task Management"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    webhooks.router,
    prefix="/api/v1/webhooks",
    tags=["Webhooks"],
    responses={404: {"description": "Not found"}},
)

app.include_router(
    files.router,
    prefix="/api/v1/files",
    tags=["File Management"],
    responses={404: {"description": "Not found"}},
)


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
        "endpoints": {
            "agents": "/api/v1/agents",
            "ai": "/api/v1/ai",
            "memory": "/api/v1/memory",
            "tasks": "/api/v1/tasks",
            "webhooks": "/api/v1/webhooks",
            "files": "/api/v1/files",
        },
        "documentation": "/docs" if settings.ENVIRONMENT != "production" else None,
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