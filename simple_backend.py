"""
Simplified FastAPI Backend for PM System Testing
Minimal version with just the PM system routes for testing
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import only the PM system routers
from backend.fastapi.app.routers.wip_limits import router as wip_limits_router
from backend.fastapi.app.routers.atomic_tasking import router as atomic_tasking_router
from backend.fastapi.app.routers.git_integration import router as git_integration_router
from backend.fastapi.app.routers.project_spaces import router as project_spaces_router
from backend.fastapi.app.routers.timeboxing_momentum import (
    combined_router as timeboxing_momentum_router,
)
from backend.fastapi.app.routers.ai_execution import router as ai_execution_router

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    logger.info("🚀 PM System Test Backend starting...")
    yield
    logger.info("🛑 PM System Test Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title="PM System Test Backend",
    description="Simplified backend for testing the Next-Gen PM System",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include PM system routers
app.include_router(wip_limits_router)
app.include_router(atomic_tasking_router)
app.include_router(git_integration_router)
app.include_router(project_spaces_router)
app.include_router(timeboxing_momentum_router)
app.include_router(ai_execution_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PM System Test Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "wip": "/api/wip/",
            "atomic": "/api/atomic/",
            "git": "/api/git/",
            "projects": "/api/projects/",
            "timeboxing": "/api/timeboxing/",
            "ai": "/api/ai-execution/",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pm-system-test-backend",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    print("🎯 Starting PM System Test Backend...")
    print("📍 Server will run on http://localhost:8000")
    print("🎯 Ready for Maestro E2E tests")

    uvicorn.run(
        "simple_backend:app", host="0.0.0.0", port=8000, reload=False, log_level="info"
    )
