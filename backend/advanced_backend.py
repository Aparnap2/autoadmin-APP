#!/usr/bin/env python3
"""
AutoAdmin Backend using existing FastAPI structure with LangGraph integration
This combines the existing router structure with the LangGraph orchestrator
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import existing models and routers
from fastapi.app.models.agent import AgentTaskRequest, AgentTaskResponse, AgentResponse
from fastapi.app.models.common import BaseResponse
from fastapi.app.routers import health, multi_agent, streaming
from agents.swarm.orchestrator import AgentOrchestrator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[AgentOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator
    
    logger.info("Starting up AutoAdmin Advanced Backend...")
    
    # Initialize orchestrator
    config = {
        "ceo": {},
        "strategy": {},
        "devops": {},
        "load_balancer": {},
        "failover": {},
        "health_monitor": {}
    }
    
    orchestrator = AgentOrchestrator(config)
    await orchestrator.initialize()
    
    logger.info("Orchestrator initialized successfully")
    
    yield
    
    logger.info("Shutting down AutoAdmin Advanced Backend...")
    if orchestrator:
        await orchestrator.shutdown()


# Create FastAPI app with lifespan
app = FastAPI(
    title="AutoAdmin Advanced Backend",
    description="AutoAdmin backend with LangGraph orchestration and proper API structure",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"-> {request.method} {request.url.path} | Client: {request.client.host}:{request.client.port}")
    
    # Get request body if available
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
            logger.debug(f"Request body: {str(body)[:200]}...")
        except:
            logger.debug("Could not parse request body")
    
    response = await call_next(request)
    
    # Calculate process time
    process_time = time.time() - start_time
    logger.info(f"<- {response.status_code} {request.method} {request.url.path} | {process_time:.3f}s")
    
    return response

# Include existing routers
app.include_router(health.router, prefix="/api/v2", tags=["health"])
app.include_router(multi_agent.router, prefix="/api/v2", tags=["agents"])
app.include_router(streaming.router, prefix="/api/v2", tags=["streaming"])

# Add enhanced agent endpoints that use the orchestrator
@app.post("/api/v2/agents/chat", response_model=BaseResponse)
async def enhanced_chat_endpoint(task_request: AgentTaskRequest):
    """Enhanced chat endpoint using LangGraph orchestrator"""
    logger.info(f"Enhanced chat endpoint called: {task_request.title}")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        # Convert to orchestrator format
        task_input = {
            "message": f"{task_request.title}: {task_request.description}",
            "priority": task_request.priority,
            "agent_type": task_request.agent_type.value if task_request.agent_type else "general"
        }
        
        # Process task with orchestrator
        result = await orchestrator.process_task_with_failover(task_input)
        
        response = BaseResponse(
            success=result.get("success", True),
            message="Task processed successfully",
            data=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info("Chat task processed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Enhanced chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.get("/api/v2/orchestrator/status", response_model=BaseResponse)
async def orchestrator_status():
    """Get orchestrator status"""
    logger.info("Getting orchestrator status")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        status = await orchestrator.get_orchestrator_status()
        
        response = BaseResponse(
            success=True,
            message="Orchestrator status retrieved",
            data=status,
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info("Orchestrator status retrieved successfully")
        return response
    
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orchestrator status: {str(e)}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    print("🚀 Starting AutoAdmin Advanced Backend...")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/api/v2/health")
    print("🌐 Server will be available at: http://localhost:8000")
    print("🤖 LangGraph orchestrator with CEO, Strategy, and DevOps agents ready!")

    uvicorn.run(
        "advanced_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )