"""
Simple AutoAdmin Backend - Basic FastAPI server with Pydantic models and LangGraph integration
Simplified version that properly integrates with existing architecture
"""

import os
import sys
import logging
import time
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import existing models, fall back to manual definitions if needed
try:
    # Import existing models
    from fastapi.app.models.agent import AgentTaskRequest, AgentTaskResponse
    from fastapi.app.models.task import TaskRequest as TaskRequestModel, Task
    from fastapi.app.models.common import BaseResponse
    MODELS_AVAILABLE = True
    print("✅ Using existing Pydantic models")
except ImportError:
    # Define fallback models
    class BaseResponse(BaseModel):
        success: bool = True
        message: str = "Operation successful"
        data: Optional[Dict[str, Any]] = None
        timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class AgentTaskRequest(BaseModel):
        title: str
        description: str
        type: str = "general"
        priority: str = "medium"
        agent_type: Optional[str] = None

    class AgentTaskResponse(BaseModel):
        success: bool
        task: Dict[str, Any]
        message: str = "Task created successfully"

    MODELS_AVAILABLE = False
    print("⚠️  Using fallback Pydantic models")

# Import enhanced orchestrator
try:
    from agents.enhanced_orchestrator import EnhancedAgentOrchestrator
    ENHANCED_ORCHESTRATOR_AVAILABLE = True
    print("✅ Enhanced LangGraph orchestrator available")
except ImportError:
    ENHANCED_ORCHESTRATOR_AVAILABLE = False
    print("⚠️  Enhanced orchestrator not available")

# Fallback to original orchestrator if enhanced not available
if not ENHANCED_ORCHESTRATOR_AVAILABLE:
    try:
        from agents.swarm.orchestrator import AgentOrchestrator
        ORCHESTRATOR_AVAILABLE = True
        print("✅ Original LangGraph orchestrator available")
    except ImportError:
        ORCHESTRATOR_AVAILABLE = False
        print("⚠️  LangGraph orchestrator not available, using simple responses")

# Set up enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
load_dotenv('.env.algion')

logger.info("Environment variables loaded")
logger.debug(f"Algion API Key configured: {'Yes' if os.getenv('ALGION_API_KEY') else 'No'}")
logger.debug(f"Algion Base URL: {os.getenv('ALGION_BASE_URL', 'Not configured')}")
logger.debug(f"Algion Model: {os.getenv('ALGION_MODEL', 'Not configured')}")

# Basic FastAPI app
app = FastAPI(
    title="AutoAdmin Backend",
    description="AutoAdmin Multi-Agent Backend API with Pydantic and LangGraph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
            logger.debug(f"Request body: {str(body)[:200]}...")
        except:
            logger.debug("Could not parse request body (not JSON)")

    response = await call_next(request)

    # Calculate process time
    process_time = time.time() - start_time
    logger.info(f"<- {response.status_code} {request.method} {request.url.path} | {process_time:.3f}s")

    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = None
if ENHANCED_ORCHESTRATOR_AVAILABLE:
    try:
        logger.info("Initializing Enhanced Agent Orchestrator...")
        orchestrator = EnhancedAgentOrchestrator({
            "ceo": {}, "strategy": {}, "devops": {}
        })
        logger.info("🚀 Enhanced Orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize enhanced orchestrator: {e}", exc_info=True)
        orchestrator = None
elif ORCHESTRATOR_AVAILABLE:
    try:
        logger.info("Initializing Original Agent Orchestrator...")
        orchestrator = AgentOrchestrator({
            "ceo": {}, "strategy": {}, "devops": {},
            "load_balancer": {}, "failover": {}, "health_monitor": {}
        })
        logger.info("🤖 Original Orchestrator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize original orchestrator: {e}")
        orchestrator = None

# Basic health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    logger.info("Health check endpoint called")

    try:
        # If orchestrator is available, get real health status
        if orchestrator and (ENHANCED_ORCHESTRATOR_AVAILABLE or ORCHESTRATOR_AVAILABLE):
            status = await orchestrator.health_check()
            response_data = {
                "success": True,
                "data": status,
                "message": "Healthy with full orchestrator support"
            }
        else:
            # Fallback health status
            response_data = {
                "success": True,
                "data": {
                    "status": "healthy",
                    "backend": "autoadmin",
                    "services": {
                        "agents": 3,
                        "database": "simulated",
                        "cache": "simulated"
                    },
                    "agents": [
                        {"id": "ceo", "name": "CEO Agent", "status": "active", "type": "ceo", "capabilities": ["coordination", "decision_making", "general_assistance"], "description": "Coordinates tasks and provides general assistance"},
                        {"id": "strategy", "name": "Strategy/CMO Agent", "status": "active", "type": "strategy", "capabilities": ["market_research", "financial_analysis", "strategic_planning"], "description": "Handles market research, financial analysis, and strategic planning"},
                        {"id": "devops", "name": "DevOps/CTO Agent", "status": "active", "type": "devops", "capabilities": ["code_analysis", "ui_ux_review", "technical_decisions"], "description": "Handles code analysis, UI/UX review, and technical decisions"}
                    ]
                },
                "message": "Healthy with simulated orchestrator"
            }

        logger.info("Health check completed successfully")
        return response_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "data": {"status": "unhealthy"},
            "message": f"Health check failed: {str(e)}"
        }

# Basic agents endpoint
@app.get("/api/v1/agents")
async def list_agents():
    """List available agents"""
    logger.info("Agents endpoint called")

    try:
        # If orchestrator is available, get real agent status
        if orchestrator and (ENHANCED_ORCHESTRATOR_AVAILABLE or ORCHESTRATOR_AVAILABLE):
            agents_status = await orchestrator.get_agent_status()
            agents_data = agents_status.get("agents", {})

            # Format for API response
            formatted_agents = []
            for agent_id, agent_info in agents_data.items():
                formatted_agents.append({
                    "id": agent_id,
                    "name": agent_info.get("name", f"{agent_id.title()} Agent"),
                    "status": agent_info.get("status", "active"),
                    "type": agent_id,
                    "capabilities": agent_info.get("capabilities", []),
                    "description": agent_info.get("description", f"Handles {agent_id} related tasks")
                })
        else:
            # Fallback agent data
            formatted_agents = [
                {"id": "ceo", "name": "CEO Agent", "status": "active", "type": "ceo", "capabilities": ["coordination", "decision_making", "general_assistance"], "description": "Coordinates tasks and provides general assistance"},
                {"id": "strategy", "name": "Strategy/CMO Agent", "status": "active", "type": "strategy", "capabilities": ["market_research", "financial_analysis", "strategic_planning"], "description": "Handles market research, financial analysis, and strategic planning"},
                {"id": "devops", "name": "DevOps/CTO Agent", "status": "active", "type": "devops", "capabilities": ["code_analysis", "ui_ux_review", "technical_decisions"], "description": "Handles code analysis, UI/UX review, and technical decisions"}
            ]

        response_data = {
            "success": True,
            "data": formatted_agents
        }

        logger.info(f"Returning {len(formatted_agents)} agents")
        return response_data

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        return {
            "success": False,
            "data": [],
            "message": f"Failed to list agents: {str(e)}"
        }

# Basic chat endpoint (new - compatible with frontend)
@app.post("/api/v1/chat")
async def chat_with_agent(request: dict):
    """Chat with an agent - compatible with frontend client"""
    logger.info(f"Chat endpoint called with request: {request}")

    try:
        content = request.get('content', '')
        agent_hint = request.get('agent_hint', 'ceo')

        # If orchestrator is available, process through it
        if orchestrator and (ENHANCED_ORCHESTRATOR_AVAILABLE or ORCHESTRATOR_AVAILABLE):
            logger.info(f"Processing chat through orchestrator for agent: {agent_hint}")

            # Prepare task input for orchestrator
            task_input = {
                "message": content,
                "agent_type": agent_hint,
                "priority": "normal"
            }

            result = await orchestrator.process_task_with_failover(task_input)

            response_data = {
                "success": result.get("success", True),
                "data": {
                    "id": f"msg_{agent_hint}_{hash(str(request)) % 10000}",
                    "content": result.get("result", {}).get("summary", f"Response to: '{content}'. Processed by {agent_hint} agent via LangGraph orchestrator."),
                    "type": "assistant",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": agent_hint,
                    "metadata": result.get("workflow_steps", {})
                }
            }
        else:
            # Fallback response
            if agent_hint not in ["ceo", "strategy", "devops"]:
                logger.warning(f"Invalid agent hint '{agent_hint}', defaulting to 'ceo'")
                agent_hint = 'ceo'

            response_data = {
                "success": True,
                "data": {
                    "id": f"msg_{agent_hint}_{hash(str(request)) % 10000}",
                    "content": f"Response to: '{content}'. This is a response from the {agent_hint} agent! (Simple backend mode)",
                    "type": "assistant",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": agent_hint,
                    "metadata": {}
                }
            }

        logger.info(f"Generated response for {agent_hint} agent with message ID: {response_data['data']['id']}")
        return response_data

    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        return {
            "success": False,
            "data": {
                "id": f"error_{hash(str(request)) % 10000}",
                "content": f"Error processing your request: {str(e)}",
                "type": "assistant",
                "timestamp": datetime.utcnow().isoformat(),
                "agent": request.get('agent_hint', 'ceo'),
                "metadata": {"error": str(e)}
            }
        }

# Streaming chat endpoint (for real-time responses)
@app.post("/api/v1/chat/stream")
async def chat_with_agent_stream(request: dict):
    """Chat with an agent with streaming response"""
    logger.info(f"Streaming chat endpoint called with request: {request}")

    agent_hint = request.get('agent_hint', 'ceo')
    content = request.get('content', '')

    if agent_hint not in ["ceo", "strategy", "devops"]:
        logger.warning(f"Invalid agent hint '{agent_hint}', defaulting to 'ceo'")
        agent_hint = 'ceo'  # default to ceo if invalid

    # For now, return a response that indicates streaming capability
    # In a real implementation, this would be an actual streaming endpoint
    response_data = {
        "success": True,
        "data": {
            "id": f"msg_{agent_hint}_{hash(str(request)) % 10000}",
            "content": f"Response to: '{content}'. This is a response from the {agent_hint} agent! (streaming simulation)",
            "type": "assistant",
            "timestamp": "2025-11-29T06:30:00Z",
            "agent": agent_hint,
            "metadata": {}
        }
    }

    logger.info(f"Generated streaming response for {agent_hint} agent with message ID: {response_data['data']['id']}")
    return response_data

# Chat history endpoint (new - compatible with frontend client)
@app.get("/api/v1/chat/history")
async def get_chat_history(limit: int = 50):
    """Get chat history - compatible with frontend client"""
    logger.info(f"Chat history endpoint called with limit: {limit}")

    # In a real implementation, this would fetch from a database
    response_data = {
        "success": True,
        "data": []
    }

    logger.info(f"Returning {len(response_data['data'])} messages from history (empty for now)")
    return response_data

# Existing agent-specific chat endpoint
@app.post("/api/v1/agents/{agent_type}/chat")
async def chat_with_specific_agent(agent_type: str, request: dict):
    """Chat with an agent by type"""
    logger.info(f"Agent-specific chat endpoint called for agent: {agent_type} with request: {request}")

    if agent_type not in ["ceo", "strategy", "devops"]:
        logger.warning(f"Agent {agent_type} not found, raising 404")
        raise HTTPException(status_code=404, detail="Agent not found")

    response_data = {
        "agent_type": agent_type,
        "response": f"Hello from the {agent_type} agent! This is a basic response.",
        "message_id": f"msg_{agent_type}_{hash(str(request)) % 10000}",
        "timestamp": "2025-11-29T06:30:00Z"
    }

    logger.info(f"Generated response for {agent_type} agent with message ID: {response_data['message_id']}")
    return response_data

# Basic tasks endpoint
@app.get("/api/v1/tasks")
async def list_tasks(limit: int = 50):
    """List tasks"""
    logger.info(f"Tasks list endpoint called with limit: {limit}")

    # In a real implementation, this would fetch from a database
    response_data = {
        "success": True,
        "data": [],
    }

    logger.info(f"Returning {len(response_data['data'])} tasks (empty for now)")
    return response_data

# Create task endpoint
@app.post("/api/v1/tasks")
async def create_task(request: dict):
    """Create a new task"""
    logger.info(f"Create task endpoint called with request: {request}")

    try:
        # Try to validate request using models if available
        if MODELS_AVAILABLE:
            # Validate that required fields are present
            title = request.get('title', 'Untitled Task')
            if not title:
                raise ValueError("Task title is required")

        task_type = request.get('type', 'general')
        title = request.get('title', 'Untitled Task')
        description = request.get('description', 'No description provided')
        agent = request.get('agent', 'ceo')

        # If orchestrator is available, process through it
        if orchestrator and (ENHANCED_ORCHESTRATOR_AVAILABLE or ORCHESTRATOR_AVAILABLE):
            logger.info(f"Creating task through orchestrator: {title}")

            task_input = {
                "message": f"{title}: {description}",
                "agent_type": agent,
                "priority": request.get('priority', 'medium'),
                "type": task_type
            }

            result = await orchestrator.process_task_with_failover(task_input)

            task = {
                "id": result.get("result", {}).get("id", f"task_{hash(str(request)) % 10000}"),
                "type": task_type,
                "title": title,
                "status": result.get("status", "pending"),
                "description": description,
                "agent": agent,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "result": result.get("result", {})
            }
        else:
            # Fallback task creation
            task = {
                "id": f"task_{hash(str(request)) % 10000}",
                "type": task_type,
                "title": title,
                "status": "pending",
                "description": description,
                "agent": agent,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

        response_data = {
            "success": True,
            "data": task
        }

        logger.info(f"Created new task with ID: {task['id']}, type: {task['type']}, agent: {task['agent']}")
        return response_data

    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"Task creation failed: {str(e)}"
        }

# Get specific task endpoint
@app.get("/api/v1/tasks/{taskId}")
async def get_task(taskId: str):
    """Get a specific task by ID"""
    logger.info(f"Get task endpoint called for task ID: {taskId}")

    task = {
        "id": taskId,
        "title": f"Task {taskId}",
        "type": "general",
        "status": "completed",
        "description": f"Sample task {taskId}",
        "agent": "ceo",
        "result": "Task completed successfully",
        "error": None,
        "created_at": "2025-11-29T06:30:00Z",
        "updated_at": "2025-11-29T06:30:20Z"
    }

    response_data = {
        "success": True,
        "data": task
    }

    logger.info(f"Returning task {taskId} with status: {task['status']}")
    return response_data

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global error in {request.method} {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "type": "internal_error"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler"""
    logger.warning(f"HTTP {exc.status_code} error in {request.method} {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP error",
            "message": exc.detail,
            "type": "http_error"
        }
    )

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting AutoAdmin Backend (Simple Mode)...")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print(f"📋 Pydantic Models Available: {MODELS_AVAILABLE}")
    print(f"🚀 Enhanced Orchestrator Available: {ENHANCED_ORCHESTRATOR_AVAILABLE}")
    print(f"🤖 Original Orchestrator Available: {ORCHESTRATOR_AVAILABLE}")
    if ENHANCED_ORCHESTRATOR_AVAILABLE and orchestrator:
        print("🔄 Using ENHANCED LangGraph orchestrator with proper LLM integration")
    elif ORCHESTRATOR_AVAILABLE and orchestrator:
        print("🔄 Using original LangGraph orchestrator")
    else:
        print("🔄 Using simple mock responses (LangGraph not available)")
    print("📡 Available endpoints:")
    print("   GET  /health")
    print("   GET  /api/v1/agents")
    print("   POST /api/v1/chat")
    print("   POST /api/v1/chat/stream")
    print("   GET  /api/v1/chat/history")
    print("   POST /api/v1/tasks")
    print("   GET  /api/v1/tasks/{taskId}")
    print("   POST /api/v1/agents/{agent_type}/chat")
    print("🌐 Server will be available at: http://localhost:8000")

    uvicorn.run(
        "simple_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )