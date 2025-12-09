#!/usr/bin/env python3
"""
Production AutoAdmin Backend - LangGraph + Pydantic + FastAPI
Full-featured backend with proper agent orchestration and validation
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import existing models
from fastapi.app.models.agent import (
    AgentType, AgentStatus, AgentTaskRequest, AgentTaskResponse,
    AgentTask, AgentResponse, AgentStatusResponse
)
from fastapi.app.models.task import TaskRequest as TaskRequestModel, Task
from fastapi.app.models.common import BaseResponse

# Import agents and orchestrator
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
    
    logger.info("Starting up AutoAdmin Production Backend...")
    
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
    
    logger.info("Shutting down AutoAdmin Production Backend...")
    if orchestrator:
        await orchestrator.shutdown()


# Create FastAPI app with lifespan
app = FastAPI(
    title="AutoAdmin Production Backend",
    description="Full-featured AutoAdmin backend with LangGraph orchestration",
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
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
            logger.debug(f"Request body: {body}")
        except:
            logger.debug("Could not parse request body (not JSON)")
    
    response = await call_next(request)
    
    # Calculate process time
    process_time = time.time() - start_time
    logger.info(f"<- {response.status_code} {request.method} {request.url.path} | {process_time:.3f}s")
    
    return response


@app.get("/health", response_model=BaseResponse)
async def health_check():
    """Comprehensive health check"""
    logger.info("Health check endpoint called")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        health = await orchestrator.health_check()
        
        response = BaseResponse(
            success=True,
            data=health,
            message="Health check successful",
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info("Health check completed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/api/v2/agents", response_model=AgentResponse)
async def list_agents():
    """List all available agents"""
    logger.info("Listing agents endpoint called")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        agents_status = await orchestrator.get_agent_status()
        
        response = AgentResponse(
            success=True,
            message=f"Retrieved {len(agents_status.get('agents', {}))} agents",
            data={"agents": agents_status.get("agents", {})}
        )
        
        logger.info(f"Returned {len(agents_status.get('agents', {}))} agents")
        return response
    
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@app.post("/api/v2/agents/tasks", response_model=AgentTaskResponse)
async def create_task(task_request: AgentTaskRequest):
    """Create a new agent task"""
    logger.info(f"Creating task: {task_request.title}")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        # Convert Pydantic request to dict for orchestrator
        task_input = {
            "message": task_request.description,
            "priority": task_request.priority.value,
            "agent_type": task_request.agent_type.value if task_request.agent_type else "general"
        }
        
        # Process task with orchestrator
        result = await orchestrator.process_task_with_failover(task_input)
        
        # Create task object from result
        task_data = AgentTask(
            id=result.get("result", {}).get("id", "temp-id"),
            title=task_request.title,
            description=task_request.description,
            type=task_request.type,
            priority=task_request.priority,
            agent_type=task_request.agent_type or AgentType.STRATEGY,
            progress=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status=result.get("status", "pending")
        )
        
        response = AgentTaskResponse(
            success=result.get("success", True),
            message=result.get("message", "Task created successfully"),
            data={"task": task_data.dict()}
        )
        
        logger.info(f"Created task {task_data.id} successfully")
        return response
    
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.get("/api/v2/agents/{agent_type}/status", response_model=AgentStatusResponse)
async def get_agent_status(agent_type: str):
    """Get specific agent status"""
    logger.info(f"Getting status for agent: {agent_type}")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        # Get all agents status
        all_status = await orchestrator.get_agent_status()
        agents = all_status.get("agents", {})
        
        if agent_type not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_type} not found")
        
        agent_info = agents[agent_type]
        
        response = AgentStatusResponse(
            agent_id=agent_info.get("name", agent_type),
            status=AgentStatus.BUSY if agent_info.get("status") == "active" else AgentStatus.IDLE,
            current_tasks=0,  # Placeholder - would need to track this
            capabilities=agent_info.get("capabilities", []),
            health_score=0.9,  # Placeholder - would come from health monitor
            performance_metrics={}
        )
        
        logger.info(f"Retrieved status for agent {agent_type}")
        return response
    
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")


@app.get("/api/v2/agents/orchestrator/status", response_model=BaseResponse)
async def get_orchestrator_status():
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


@app.post("/api/v2/chat", response_model=BaseResponse)
async def chat_endpoint(request: Dict[str, Any]):
    """Chat with the agent system"""
    logger.info(f"Chat endpoint called with message: {request.get('message', 'No message')[:50]}...")
    
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        # Process the chat message
        result = await orchestrator.process_task_with_failover(request)
        
        response = BaseResponse(
            success=result.get("success", True),
            message="Chat processed successfully",
            data={"response": result},
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info("Chat processed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


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
    print("🚀 Starting AutoAdmin Production Backend...")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("📡 Available endpoints:")
    print("   GET  /health")
    print("   GET  /api/v2/agents")
    print("   POST /api/v2/agents/tasks")
    print("   GET  /api/v2/agents/{agent_type}/status")
    print("   GET  /api/v2/agents/orchestrator/status")
    print("   POST /api/v2/chat")
    print("🌐 Server will be available at: http://localhost:8000")
    print("🤖 LangGraph orchestrator with CEO, Strategy, and DevOps agents ready!")

    uvicorn.run(
        "production_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )