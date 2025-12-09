"""
Agent services router for LangGraph integration and task orchestration
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from app.responses.sse import SSEResponse, StreamingUtils, LongPollingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.error_handler import (
    AutoAdminException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    RateLimitException,
    ExternalServiceException,
    DatabaseException,
    ErrorCodes,
)
from app.models.agent import (
    AgentRequest,
    AgentResponse,
    AgentTaskRequest,
    AgentTaskResponse,
    AgentStatusResponse,
    AgentListResponse,
    AgentType,
    AgentStatus,
    TaskType,
    TaskPriority,
    AgentAction,
    AgentActionResponse,
)

# Import our swarm system
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
from backend.agents.swarm import AgentOrchestrator

logger = get_logger(__name__)

router = APIRouter()

# Global swarm orchestrator instance
_swarm_orchestrator: Optional[AgentOrchestrator] = None

# In-memory agent storage (in production, use database)
_agents_registry = {}
_agent_tasks = {}
_agent_status = {}


# Initialize swarm orchestrator
async def initialize_swarm_orchestrator():
    """Initialize the agent swarm orchestrator"""
    global _swarm_orchestrator

    try:
        config = {
            "ceo": {
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "temperature": 0.3,
                "max_tokens": 2000,
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
            },
            "strategy": {
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "temperature": 0.2,
                "max_tokens": 2000,
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "tavily_api_key": os.getenv("TAVILY_API_KEY"),
            },
            "devops": {
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "temperature": 0.1,
                "max_tokens": 2000,
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
            },
        }

        _swarm_orchestrator = AgentOrchestrator(config)
        logger.info("Swarm orchestrator initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize swarm orchestrator: {e}")
        # Continue without swarm system
        _swarm_orchestrator = None


# Initialize default agents
async def initialize_default_agents():
    """Initialize default agent configurations"""
    default_agents = [
        {
            "id": "marketing-001",
            "type": AgentType.MARKETING,
            "name": "Marketing Agent",
            "description": "Handles marketing tasks, content creation, and campaign management",
            "status": AgentStatus.IDLE,
            "capabilities": {
                "supported_task_types": [
                    TaskType.CONTENT_CREATION,
                    TaskType.RESEARCH,
                    TaskType.SOCIAL_MEDIA,
                    TaskType.EMAIL_OUTREACH,
                ],
                "max_concurrent_tasks": 3,
                "current_load": 0,
                "success_rate": 0.95,
                "average_execution_time": 180.0,
                "specialized_skills": [
                    "content writing",
                    "social media management",
                    "market research",
                ],
                "tools_available": ["tavily_search", "openai_gpt4", "hubspot_api"],
                "integration_partners": ["HubSpot", "Twitter", "LinkedIn"],
            },
        },
        {
            "id": "finance-001",
            "type": AgentType.FINANCE,
            "name": "Finance Agent",
            "description": "Handles financial analysis, reporting, and budget management",
            "status": AgentStatus.IDLE,
            "capabilities": {
                "supported_task_types": [
                    TaskType.ANALYSIS,
                    TaskType.REPORT_GENERATION,
                    TaskType.DATA_PROCESSING,
                ],
                "max_concurrent_tasks": 2,
                "current_load": 0,
                "success_rate": 0.97,
                "average_execution_time": 120.0,
                "specialized_skills": [
                    "financial analysis",
                    "report generation",
                    "data modeling",
                ],
                "tools_available": [
                    "excel_processor",
                    "chart_generator",
                    "financial_calculators",
                ],
                "integration_partners": ["QuickBooks", "Stripe", "Plaid"],
            },
        },
        {
            "id": "devops-001",
            "type": AgentType.DEVOPS,
            "name": "DevOps Agent",
            "description": "Handles deployment, monitoring, and infrastructure management",
            "status": AgentStatus.IDLE,
            "capabilities": {
                "supported_task_types": [
                    TaskType.MONITORING,
                    TaskType.AUTOMATION,
                    TaskType.DEPLOYMENT,
                ],
                "max_concurrent_tasks": 4,
                "current_load": 0,
                "success_rate": 0.98,
                "average_execution_time": 90.0,
                "specialized_skills": ["docker", "kubernetes", "ci/cd", "monitoring"],
                "tools_available": ["github_api", "docker_api", "kubernetes_api"],
                "integration_partners": ["GitHub", "Docker Hub", "AWS"],
            },
        },
        {
            "id": "strategy-001",
            "type": AgentType.STRATEGY,
            "name": "Strategy Agent",
            "description": "Handles strategic planning, analysis, and decision support",
            "status": AgentStatus.IDLE,
            "capabilities": {
                "supported_task_types": [
                    TaskType.ANALYSIS,
                    TaskType.RESEARCH,
                    TaskType.REPORT_GENERATION,
                ],
                "max_concurrent_tasks": 2,
                "current_load": 0,
                "success_rate": 0.92,
                "average_execution_time": 300.0,
                "specialized_skills": [
                    "strategic analysis",
                    "market research",
                    "business intelligence",
                ],
                "tools_available": [
                    "swot_analyzer",
                    "market_research_tools",
                    "competitive_analysis",
                ],
                "integration_partners": ["Crunchbase", "Market APIs", "BI Tools"],
            },
        },
    ]

    for agent_data in default_agents:
        _agents_registry[agent_data["id"]] = agent_data
        _agent_status[agent_data["id"]] = {
            "status": agent_data["status"],
            "last_heartbeat": datetime.utcnow(),
            "current_tasks": [],
            "metrics": {
                "tasks_completed": 0,
                "tasks_failed": 0,
                "average_task_time": 0.0,
                "uptime": 0.0,
            },
        }


# Initialize agents on startup
@router.on_event("startup")
async def startup_event():
    """Initialize agents on application startup"""
    await initialize_default_agents()
    await initialize_swarm_orchestrator()
    logger.info("Default agents initialized", agent_count=len(_agents_registry))


@router.get("/", response_model=AgentListResponse, summary="List All Agents")
async def list_agents(
    agent_type: Optional[AgentType] = Query(
        default=None, description="Filter by agent type"
    ),
    status: Optional[AgentStatus] = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> AgentListResponse:
    """
    Get a list of all available agents with optional filtering

    Args:
        agent_type: Filter by agent type
        status: Filter by status
        page: Page number for pagination
        page_size: Number of items per page

    Returns:
        AgentListResponse: Paginated list of agents
    """
    try:
        # Filter agents
        filtered_agents = []
        for agent_id, agent_data in _agents_registry.items():
            agent_status_data = _agent_status.get(agent_id, {})

            # Apply filters
            if agent_type and agent_data["type"] != agent_type:
                continue
            if status and agent_status_data.get("status") != status:
                continue

            # Create agent response data
            agent_response = {
                **agent_data,
                "id": agent_id,
                "current_status": agent_status_data.get("status"),
                "last_heartbeat": agent_status_data.get("last_heartbeat"),
                "current_tasks": agent_status_data.get("current_tasks", []),
                "metrics": agent_status_data.get("metrics", {}),
            }
            filtered_agents.append(agent_response)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_agents = filtered_agents[start:end]

        logger.info(
            "Listed agents",
            total=len(filtered_agents),
            page=page,
            page_size=page_size,
            returned=len(paginated_agents),
        )

        return AgentListResponse(
            items=paginated_agents,
            total=len(filtered_agents),
            page=page,
            page_size=page_size,
            total_pages=(len(filtered_agents) + page_size - 1) // page_size,
            has_next=end < len(filtered_agents),
            has_prev=page > 1,
        )

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise DatabaseException(f"Failed to retrieve agents: {str(e)}")


@router.get(
    "/{agent_id}/status", response_model=AgentStatusResponse, summary="Get Agent Status"
)
async def get_agent_status(agent_id: str) -> AgentStatusResponse:
    """
    Get detailed status information for a specific agent

    Args:
        agent_id: ID of the agent

    Returns:
        AgentStatusResponse: Detailed agent status
    """
    try:
        if agent_id not in _agents_registry:
            raise ResourceNotFoundException("Agent", agent_id)

        agent_data = _agents_registry[agent_id]
        status_data = _agent_status.get(agent_id, {})

        # Calculate health score based on recent performance
        health_score = calculate_agent_health_score(agent_id)

        # Calculate uptime
        uptime = None
        if status_data.get("last_heartbeat"):
            uptime = (datetime.utcnow() - status_data["last_heartbeat"]).total_seconds()

        response = AgentStatusResponse(
            agent_id=agent_id,
            status=status_data.get("status", AgentStatus.OFFLINE),
            current_tasks=len(status_data.get("current_tasks", [])),
            capabilities=agent_data["capabilities"],
            uptime=uptime,
            last_activity=status_data.get("last_heartbeat"),
            health_score=health_score,
            performance_metrics=status_data.get("metrics", {}),
        )

        logger.info(
            "Retrieved agent status",
            agent_id=agent_id,
            status=response.status,
            health_score=health_score,
        )

        return response

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent status for {agent_id}: {e}")
        raise DatabaseException(f"Failed to retrieve agent status: {str(e)}")


@router.post(
    "/{agent_id}/tasks", response_model=AgentTaskResponse, summary="Create Agent Task"
)
async def create_agent_task(
    agent_id: str, task_request: AgentTaskRequest, background_tasks: BackgroundTasks
) -> AgentTaskResponse:
    """
    Create a new task for a specific agent

    Args:
        agent_id: ID of the target agent
        task_request: Task creation request
        background_tasks: FastAPI background tasks

    Returns:
        AgentTaskResponse: Created task information
    """
    try:
        # Validate agent exists
        if agent_id not in _agents_registry:
            raise ResourceNotFoundException("Agent", agent_id)

        agent_data = _agents_registry[agent_id]
        status_data = _agent_status.get(agent_id, {})

        # Check agent capacity
        current_load = len(status_data.get("current_tasks", []))
        max_concurrent = agent_data["capabilities"]["max_concurrent_tasks"]

        if current_load >= max_concurrent:
            raise RateLimitException(
                f"Agent {agent_id} is at maximum capacity ({max_concurrent} tasks)"
            )

        # Validate task type is supported by agent
        supported_types = agent_data["capabilities"]["supported_task_types"]
        if task_request.type not in supported_types:
            raise ValidationException(
                f"Agent {agent_id} does not support task type {task_request.type}",
                details={
                    "agent_id": agent_id,
                    "task_type": task_request.type,
                    "supported_types": [t.value for t in supported_types],
                },
            )

        # Create task
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "agent_id": agent_id,
            "title": task_request.title,
            "description": task_request.description,
            "type": task_request.type,
            "priority": task_request.priority,
            "status": "pending",
            "parameters": task_request.parameters,
            "context": task_request.context,
            "created_at": datetime.utcnow(),
            "progress": 0.0,
            "max_retries": task_request.max_retries,
            "retry_count": 0,
        }

        # Store task
        if agent_id not in _agent_tasks:
            _agent_tasks[agent_id] = []
        _agent_tasks[agent_id].append(task)

        # Add to current tasks
        if "current_tasks" not in status_data:
            status_data["current_tasks"] = []
        status_data["current_tasks"].append(task_id)

        # Update agent status
        if status_data.get("status") == AgentStatus.IDLE:
            status_data["status"] = AgentStatus.BUSY

        # Schedule task processing
        background_tasks.add_task(process_agent_task, agent_id, task_id)

        logger.info(
            "Created agent task",
            agent_id=agent_id,
            task_id=task_id,
            task_type=task_request.type,
            priority=task_request.priority,
        )

        return AgentTaskResponse(
            success=True, message=f"Task created for agent {agent_id}", task=task
        )

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task for agent {agent_id}: {e}")
        raise DatabaseException(f"Failed to create agent task: {str(e)}")


@router.get(
    "/{agent_id}/tasks",
    summary="List Agent Tasks",
    responses={
        404: {
            "description": "Agent not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Agent not found with identifier: agent-123",
                            "status_code": 404,
                            "timestamp": "2024-01-01T00:00:00Z",
                            "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                            "details": {"resource": "Agent", "identifier": "agent-123"},
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "DATABASE_ERROR",
                            "message": "Database error: Failed to retrieve agent tasks",
                            "status_code": 500,
                            "timestamp": "2024-01-01T00:00:00Z",
                            "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        }
                    }
                }
            },
        },
    },
)
async def list_agent_tasks(
    agent_id: str,
    status: Optional[str] = Query(default=None, description="Filter by task status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> Dict[str, Any]:
    """
    List tasks for a specific agent

    Args:
        agent_id: ID of the agent
        status: Filter by task status
        page: Page number for pagination
        page_size: Number of items per page

    Returns:
        Dict: Paginated list of agent tasks

    Raises:
        ResourceNotFoundException: If agent is not found
        DatabaseException: If database operation fails
    """
    try:
        if agent_id not in _agents_registry:
            raise ResourceNotFoundException("Agent", agent_id)

        agent_tasks = _agent_tasks.get(agent_id, [])

        # Apply status filter
        if status:
            agent_tasks = [task for task in agent_tasks if task["status"] == status]

        # Sort by creation time (newest first)
        agent_tasks.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_tasks = agent_tasks[start:end]

        logger.info(
            "Listed agent tasks",
            agent_id=agent_id,
            total=len(agent_tasks),
            page=page,
            page_size=page_size,
            returned=len(paginated_tasks),
        )

        return {
            "items": paginated_tasks,
            "total": len(agent_tasks),
            "page": page,
            "page_size": page_size,
            "total_pages": (len(agent_tasks) + page_size - 1) // page_size,
            "has_next": end < len(agent_tasks),
            "has_prev": page > 1,
        }

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tasks for agent {agent_id}: {e}")
        raise DatabaseException(f"Failed to retrieve agent tasks: {str(e)}")


@router.post(
    "/{agent_id}/actions",
    response_model=AgentActionResponse,
    summary="Execute Agent Action",
)
async def execute_agent_action(
    agent_id: str, action: AgentAction
) -> AgentActionResponse:
    """
    Execute a specific action on an agent

    Args:
        agent_id: ID of the target agent
        action: Action to execute

    Returns:
        AgentActionResponse: Action execution result
    """
    try:
        if agent_id not in _agents_registry:
            raise ResourceNotFoundException("Agent", agent_id)

        # Validate action
        valid_actions = ["start", "stop", "restart", "pause", "resume", "configure"]
        if action.action not in valid_actions:
            raise ValidationException(
                f"Invalid action. Valid actions: {valid_actions}",
                details={
                    "provided_action": action.action,
                    "valid_actions": valid_actions,
                },
            )

        # Execute action
        result = await execute_agent_action_internal(
            agent_id, action.action, action.parameters
        )

        logger.info(
            "Executed agent action",
            agent_id=agent_id,
            action=action.action,
            success=result.get("success", False),
        )

        return AgentActionResponse(
            success=True,
            message=f"Action {action.action} executed successfully",
            action_id=f"action_{uuid.uuid4().hex[:8]}",
            result=result,
        )

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to execute action {action.action} on agent {agent_id}: {e}"
        )
        raise DatabaseException(f"Failed to execute agent action: {str(e)}")


# Helper functions
def calculate_agent_health_score(agent_id: str) -> float:
    """Calculate health score for an agent (0.0-1.0)"""
    try:
        status_data = _agent_status.get(agent_id, {})
        metrics = status_data.get("metrics", {})

        # Base score from status
        base_score = 0.5
        status = status_data.get("status", AgentStatus.OFFLINE)

        if status == AgentStatus.IDLE:
            base_score = 1.0
        elif status == AgentStatus.BUSY:
            base_score = 0.9
        elif status == AgentStatus.PROCESSING:
            base_score = 0.8
        elif status == AgentStatus.ERROR:
            base_score = 0.2
        elif status == AgentStatus.OFFLINE:
            base_score = 0.0

        # Adjust based on success rate
        total_tasks = metrics.get("tasks_completed", 0) + metrics.get("tasks_failed", 0)
        if total_tasks > 0:
            success_rate = metrics.get("tasks_completed", 0) / total_tasks
            base_score = base_score * (0.5 + success_rate * 0.5)

        return max(0.0, min(1.0, base_score))

    except Exception as e:
        logger.warning(f"Failed to calculate health score for agent {agent_id}: {e}")
        return 0.5


async def execute_agent_action_internal(
    agent_id: str, action: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Internal function to execute agent actions"""
    status_data = _agent_status.get(agent_id, {})

    if action == "start":
        status_data["status"] = AgentStatus.IDLE
        status_data["last_heartbeat"] = datetime.utcnow()
        return {"success": True, "message": "Agent started"}

    elif action == "stop":
        status_data["status"] = AgentStatus.OFFLINE
        status_data["current_tasks"] = []
        return {"success": True, "message": "Agent stopped"}

    elif action == "restart":
        status_data["status"] = AgentStatus.IDLE
        status_data["last_heartbeat"] = datetime.utcnow()
        status_data["current_tasks"] = []
        return {"success": True, "message": "Agent restarted"}

    elif action == "pause":
        if status_data.get("status") == AgentStatus.BUSY:
            status_data["status"] = AgentStatus.MAINTENANCE
            return {"success": True, "message": "Agent paused"}
        else:
            return {
                "success": False,
                "message": "Agent cannot be paused in current state",
            }

    elif action == "resume":
        if status_data.get("status") == AgentStatus.MAINTENANCE:
            status_data["status"] = AgentStatus.IDLE
            return {"success": True, "message": "Agent resumed"}
        else:
            return {
                "success": False,
                "message": "Agent cannot be resumed in current state",
            }

    elif action == "configure":
        # Apply configuration changes
        if "max_concurrent_tasks" in parameters:
            _agents_registry[agent_id]["capabilities"]["max_concurrent_tasks"] = (
                parameters["max_concurrent_tasks"]
            )
        return {"success": True, "message": "Configuration updated"}

    else:
        return {"success": False, "message": f"Unknown action: {action}"}


async def process_agent_task(agent_id: str, task_id: str):
    """Process an agent task in the background"""
    try:
        # Find task
        agent_tasks = _agent_tasks.get(agent_id, [])
        task = next((t for t in agent_tasks if t["id"] == task_id), None)

        if not task:
            logger.error(f"Task {task_id} not found for agent {agent_id}")
            return

        # Update task status
        task["status"] = "running"
        task["started_at"] = datetime.utcnow()

        logger.info(
            "Started processing agent task",
            agent_id=agent_id,
            task_id=task_id,
            task_type=task["type"],
        )

        # Simulate task processing (in production, use actual LangGraph execution)
        processing_time = simulate_task_execution(task["type"])

        # Update progress periodically
        for i in range(0, 101, 20):
            await asyncio.sleep(processing_time / 5)
            task["progress"] = i / 100.0

        # Complete task
        task["status"] = "completed"
        task["completed_at"] = datetime.utcnow()
        task["progress"] = 1.0
        task["result"] = {
            "message": f"Task {task_id} completed successfully",
            "execution_time": processing_time,
            "output": f"Simulated output for {task['type']} task",
        }

        # Update agent metrics
        status_data = _agent_status.get(agent_id, {})
        metrics = status_data.get("metrics", {})
        metrics["tasks_completed"] = metrics.get("tasks_completed", 0) + 1

        # Remove from current tasks
        if task_id in status_data.get("current_tasks", []):
            status_data["current_tasks"].remove(task_id)

        # Update agent status if no more tasks
        if not status_data.get("current_tasks"):
            status_data["status"] = AgentStatus.IDLE

        logger.info(
            "Completed agent task",
            agent_id=agent_id,
            task_id=task_id,
            execution_time=processing_time,
        )

    except Exception as e:
        logger.error(
            f"Failed to process agent task {task_id} for agent {agent_id}: {e}"
        )

        # Update task status to failed
        if task:
            task["status"] = "failed"
            task["error"] = str(e)
            task["completed_at"] = datetime.utcnow()

        # Update agent metrics
        status_data = _agent_status.get(agent_id, {})
        metrics = status_data.get("metrics", {})
        metrics["tasks_failed"] = metrics.get("tasks_failed", 0) + 1


def simulate_task_execution(task_type: TaskType) -> float:
    """Simulate task execution time based on task type"""
    # Simulate different execution times for different task types
    execution_times = {
        TaskType.RESEARCH: 300.0,  # 5 minutes
        TaskType.ANALYSIS: 180.0,  # 3 minutes
        TaskType.CONTENT_CREATION: 240.0,  # 4 minutes
        TaskType.DATA_PROCESSING: 150.0,  # 2.5 minutes
        TaskType.WEB_SCAPING: 120.0,  # 2 minutes
        TaskType.EMAIL_OUTREACH: 60.0,  # 1 minute
        TaskType.SOCIAL_MEDIA: 90.0,  # 1.5 minutes
        TaskType.REPORT_GENERATION: 200.0,  # 3.33 minutes
    }

    return execution_times.get(task_type, 180.0)


# ===== SWARM SYSTEM ENDPOINTS =====


@router.get("/swarm/status", summary="Get Swarm System Status")
async def get_swarm_status() -> Dict[str, Any]:
    """
    Get the status of the agent swarm system

    Returns:
        Dict: Swarm system status including orchestrator and agent health
    """
    try:
        if not _swarm_orchestrator:
            logger.warning("Swarm orchestrator not initialized")
            return {
                "status": "not_initialized",
                "message": "Swarm orchestrator is not initialized",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Get swarm health check
        swarm_health = await _swarm_orchestrator.health_check()
        agent_status = await _swarm_orchestrator.get_agent_status()

        return {
            "status": "active",
            "swarm_health": swarm_health,
            "agent_status": agent_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get swarm status: {e}")
        raise ExternalServiceException(
            service="SwarmOrchestrator",
            message=f"Failed to retrieve swarm status: {str(e)}",
        )


@router.post("/swarm/process", summary="Process Task with Swarm")
async def process_task_with_swarm(task_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a task using the agent swarm system

    Args:
        task_request: Task processing request with message and context

    Returns:
        Dict: Task processing result from the swarm
    """
    try:
        if not _swarm_orchestrator:
            raise ExternalServiceException(
                service="SwarmOrchestrator",
                message="Swarm orchestrator is not initialized",
                details={"service_status": "not_initialized"},
            )

        # Validate required fields
        if "message" not in task_request:
            raise ValidationException(
                "Missing required field: message",
                details={
                    "required_fields": ["message"],
                    "provided_fields": list(task_request.keys()),
                },
            )

        # Process the task through the swarm
        result = await _swarm_orchestrator.process_task(task_request)

        logger.info(
            "Processed task with swarm",
            success=result.get("success", False),
            status=result.get("status", "unknown"),
        )

        return result

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to process task with swarm: {e}")
        raise ExternalServiceException(
            service="SwarmOrchestrator",
            message=f"Failed to process task with swarm: {str(e)}",
        )


@router.post("/swarm/chat/{agent_type}", summary="Chat with Specific Agent")
async def chat_with_agent(
    agent_type: str, message_request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Chat directly with a specific agent in the swarm

    Args:
        agent_type: Type of agent (ceo, strategy, devops)
        message_request: Chat message request

    Returns:
        Dict: Agent response
    """
    try:
        if not _swarm_orchestrator:
            raise ExternalServiceException(
                service="SwarmOrchestrator",
                message="Swarm orchestrator is not initialized",
                details={"service_status": "not_initialized"},
            )

        # Validate agent type
        valid_agents = ["ceo", "strategy", "devops"]
        if agent_type not in valid_agents:
            raise ValidationException(
                f"Invalid agent type. Valid types: {valid_agents}",
                details={
                    "provided_agent_type": agent_type,
                    "valid_agent_types": valid_agents,
                },
            )

        # Get the specific agent
        agent = _swarm_orchestrator.agents.get(agent_type)
        if not agent:
            raise ResourceNotFoundException("Swarm Agent", agent_type)

        # Process message with the specific agent
        if "message" not in message_request:
            raise ValidationException(
                "Missing required field: message",
                details={
                    "required_fields": ["message"],
                    "provided_fields": list(message_request.keys()),
                },
            )

        # Create task input for specific agent
        task_input = {
            "messages": [{"type": "human", "content": message_request["message"]}],
            "direct_agent_request": True,
        }

        # Process with the specific agent
        result = await agent.process_task(task_input)

        logger.info(
            "Chat with agent",
            agent_type=agent_type,
            success=result.get("error") is None,
        )

        return {
            "agent_type": agent_type,
            "message": message_request["message"],
            "response": result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to chat with agent {agent_type}: {e}")
        raise ExternalServiceException(
            service="SwarmAgent",
            message=f"Failed to chat with agent {agent_type}: {str(e)}",
        )


@router.get("/swarm/agents", summary="List Swarm Agents")
async def list_swarm_agents() -> Dict[str, Any]:
    """
    List all agents in the swarm system

    Returns:
        Dict: List of swarm agents with their capabilities
    """
    try:
        if not _swarm_orchestrator:
            raise ExternalServiceException(
                service="SwarmOrchestrator",
                message="Swarm orchestrator is not initialized",
                details={"service_status": "not_initialized"},
            )

        agents_info = {}
        for agent_name, agent in _swarm_orchestrator.agents.items():
            agents_info[agent_name] = {
                "name": agent.name,
                "type": agent.__class__.__name__,
                "capabilities": _swarm_orchestrator.agent_capabilities.get(
                    agent_name, []
                ),
                "health": await agent.health_check(),
            }

        return {
            "swarm_agents": agents_info,
            "total_agents": len(agents_info),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to list swarm agents: {e}")
        raise ExternalServiceException(
            service="SwarmOrchestrator",
            message=f"Failed to list swarm agents: {str(e)}",
        )


# ===== HTTP-ONLY REAL-TIME ENDPOINTS =====


@router.get("/{agent_id}/status/stream", summary="Stream Agent Status via SSE")
async def stream_agent_status_sse(agent_id: str) -> StreamingResponse:
    """
    Stream agent status updates using Server-Sent Events (SSE)
    Replaces WebSocket functionality with HTTP streaming

    Args:
        agent_id: ID of the agent to stream status for

    Returns:
        StreamingResponse: SSE stream for real-time agent status
    """
    try:
        if agent_id not in _agents_registry:
            raise ResourceNotFoundException("Agent", agent_id)

        async def status_generator():
            """Generate status updates for the agent"""
            while True:
                try:
                    # Get current agent status
                    agent_data = _agents_registry[agent_id]
                    status_data = _agent_status.get(agent_id, {})

                    # Calculate health score
                    health_score = calculate_agent_health_score(agent_id)

                    status_payload = {
                        "agent_id": agent_id,
                        "status": status_data.get("status", "offline"),
                        "current_tasks": len(status_data.get("current_tasks", [])),
                        "capabilities": agent_data["capabilities"],
                        "health_score": health_score,
                        "performance_metrics": status_data.get("metrics", {}),
                        "last_heartbeat": status_data.get(
                            "last_heartbeat", ""
                        ).isoformat()
                        if status_data.get("last_heartbeat")
                        else None,
                        "uptime": (
                            datetime.utcnow() - status_data["last_heartbeat"]
                        ).total_seconds()
                        if status_data.get("last_heartbeat")
                        else None,
                    }

                    yield status_payload

                    # Wait before next update
                    await asyncio.sleep(1.0)

                except Exception as e:
                    yield {
                        "agent_id": agent_id,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await asyncio.sleep(5.0)  # Longer wait on error

        return SSEResponse.create_agent_status_stream(agent_id, status_generator())

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to create status stream for agent {agent_id}: {e}")
        raise ExternalServiceException(
            service="AgentStatusStreaming",
            message=f"Failed to create status stream: {str(e)}",
        )


@router.get("/{agent_id}/status/poll", summary="Poll Agent Status")
async def poll_agent_status(
    agent_id: str,
    last_seen: Optional[str] = Query(
        default=None,
        description="Last seen timestamp to avoid returning unchanged data",
    ),
    timeout: float = Query(default=30.0, description="Poll timeout in seconds"),
) -> Dict[str, Any]:
    """
    Poll for agent status updates using long polling
    Efficient alternative to SSE for client-side polling

    Args:
        agent_id: ID of the agent
        last_seen: Last known timestamp to detect changes
        timeout: Maximum time to wait for changes

    Returns:
        Dict: Agent status data or timeout indication
    """
    try:
        if agent_id not in _agents_registry:
            raise ResourceNotFoundException("Agent", agent_id)

        async def status_change_detector():
            """Detect if agent status has changed since last_seen"""
            status_data = _agent_status.get(agent_id, {})
            last_heartbeat = status_data.get("last_heartbeat")

            if not last_seen:
                return True  # First request, always return data

            if not last_heartbeat:
                return True  # No heartbeat, return current state

            # Check if heartbeat is newer than last_seen
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                if last_heartbeat > last_seen_dt:
                    return True
            except (ValueError, AttributeError):
                return True  # Invalid last_seen format, return data

            return False  # No changes

        async def status_data_provider():
            """Provide current status data when changes are detected"""
            agent_data = _agents_registry[agent_id]
            status_data = _agent_status.get(agent_id, {})
            health_score = calculate_agent_health_score(agent_id)

            return {
                "agent_id": agent_id,
                "status": status_data.get("status", "offline"),
                "current_tasks": len(status_data.get("current_tasks", [])),
                "capabilities": agent_data["capabilities"],
                "health_score": health_score,
                "performance_metrics": status_data.get("metrics", {}),
                "last_heartbeat": status_data.get("last_heartbeat", "").isoformat()
                if status_data.get("last_heartbeat")
                else None,
                "uptime": (
                    datetime.utcnow() - status_data["last_heartbeat"]
                ).total_seconds()
                if status_data.get("last_heartbeat")
                else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Define async data generator function
        async def data_generator():
            if await status_change_detector():
                return await status_data_provider()
            return None

        # Use long polling for efficient status updates
        result = await LongPollingResponse.create_long_polling_response(
            data_generator=data_generator, timeout=timeout, check_interval=0.5
        )

        logger.info(
            "Agent status poll completed",
            agent_id=agent_id,
            status=result.get("status"),
            elapsed=result.get("elapsed"),
        )

        return result

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to poll agent status for {agent_id}: {e}")
        raise ExternalServiceException(
            service="AgentStatusPolling",
            message=f"Failed to poll agent status: {str(e)}",
        )


@router.get("/tasks/stream", summary="Stream Task Updates via SSE")
async def stream_task_updates_sse(
    agent_type: Optional[AgentType] = Query(
        default=None, description="Filter by agent type"
    ),
    status: Optional[str] = Query(default=None, description="Filter by task status"),
) -> StreamingResponse:
    """
    Stream task updates using Server-Sent Events (SSE)
    Replaces WebSocket task streaming with HTTP streaming

    Args:
        agent_type: Optional filter by agent type
        status: Optional filter by task status

    Returns:
        StreamingResponse: SSE stream for task updates
    """
    try:

        async def task_update_generator():
            """Generate task updates"""
            last_task_states = {}  # Track last known states

            while True:
                try:
                    # Get all tasks based on filters
                    current_tasks = []

                    for agent_id, agent_tasks in _agent_tasks.items():
                        if agent_type:
                            agent_data = _agents_registry.get(agent_id, {})
                            if agent_data.get("type") != agent_type:
                                continue

                        for task in agent_tasks:
                            if status and task.get("status") != status:
                                continue

                            # Create unique task identifier
                            task_key = f"{task['id']}_{task.get('status', 'unknown')}"

                            # Only include if status changed or it's a new task
                            if task_key not in last_task_states or last_task_states[
                                task_key
                            ] != task.get("progress"):
                                current_tasks.append(
                                    {
                                        **task,
                                        "agent_id": agent_id,
                                        "last_heartbeat": _agent_status.get(
                                            agent_id, {}
                                        )
                                        .get("last_heartbeat", "")
                                        .isoformat()
                                        if _agent_status.get(agent_id, {}).get(
                                            "last_heartbeat"
                                        )
                                        else None,
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                )

                                # Update last known state
                                last_task_states[task_key] = task.get("progress")

                    if current_tasks:
                        yield {
                            "type": "task_updates",
                            "tasks": current_tasks,
                            "total_updates": len(current_tasks),
                        }

                    # Cleanup old completed tasks from tracking
                    cutoff_time = datetime.utcnow().timestamp() - 300  # 5 minutes ago
                    last_task_states = {
                        key: state
                        for key, state in last_task_states.items()
                        if key.endswith("_completed") or key.endswith("_failed")
                    }

                    await asyncio.sleep(2.0)  # Check for updates every 2 seconds

                except Exception as e:
                    yield {
                        "type": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await asyncio.sleep(5.0)

        return SSEResponse.create_task_progress_stream(
            "task_stream", task_update_generator()
        )

    except Exception as e:
        logger.error(f"Failed to create task update stream: {e}")
        raise ExternalServiceException(
            service="TaskStreaming",
            message=f"Failed to create task update stream: {str(e)}",
        )


@router.get("/notifications/stream", summary="Stream System Notifications via SSE")
async def stream_notifications_sse() -> StreamingResponse:
    """
    Stream system notifications using Server-Sent Events (SSE)
    Provides real-time system updates and agent events

    Returns:
        StreamingResponse: SSE stream for system notifications
    """
    try:

        async def notification_generator():
            """Generate system notifications"""
            notification_queue = asyncio.Queue()

            # Add initial connection notification
            await notification_queue.put(
                {
                    "type": "connection",
                    "message": "Connected to notification stream",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Start background task to monitor agent changes
            async def monitor_agent_changes():
                """Monitor agent status changes and create notifications"""
                last_agent_states = {}

                while True:
                    try:
                        current_notifications = []

                        # Check each agent for changes
                        for agent_id, agent_data in _agents_registry.items():
                            status_data = _agent_status.get(agent_id, {})
                            current_state = {
                                "status": status_data.get("status"),
                                "current_tasks": len(
                                    status_data.get("current_tasks", [])
                                ),
                                "health_score": calculate_agent_health_score(agent_id),
                            }

                            # Compare with last state
                            if agent_id in last_agent_states:
                                last_state = last_agent_states[agent_id]
                                if current_state["status"] != last_state["status"]:
                                    await notification_queue.put(
                                        {
                                            "type": "agent_status_change",
                                            "agent_id": agent_id,
                                            "agent_type": agent_data.get("type"),
                                            "old_status": last_state["status"],
                                            "new_status": current_state["status"],
                                            "timestamp": datetime.utcnow().isoformat(),
                                        }
                                    )

                                if (
                                    current_state["current_tasks"]
                                    != last_state["current_tasks"]
                                ):
                                    await notification_queue.put(
                                        {
                                            "type": "agent_task_count_change",
                                            "agent_id": agent_id,
                                            "agent_type": agent_data.get("type"),
                                            "old_count": last_state["current_tasks"],
                                            "new_count": current_state["current_tasks"],
                                            "timestamp": datetime.utcnow().isoformat(),
                                        }
                                    )

                            last_agent_states[agent_id] = current_state

                        await asyncio.sleep(3.0)  # Check for changes every 3 seconds

                    except Exception as e:
                        await notification_queue.put(
                            {
                                "type": "monitoring_error",
                                "error": str(e),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                        await asyncio.sleep(10.0)

            # Start monitoring task
            monitor_task = asyncio.create_task(monitor_agent_changes())

            try:
                while True:
                    try:
                        # Wait for notification with timeout
                        notification = await asyncio.wait_for(
                            notification_queue.get(), timeout=5.0
                        )
                        yield notification
                    except asyncio.TimeoutError:
                        # Send periodic heartbeat
                        yield {
                            "type": "heartbeat",
                            "timestamp": datetime.utcnow().isoformat(),
                        }

            except asyncio.CancelledError:
                # Client disconnected
                monitor_task.cancel()
                yield {
                    "type": "disconnection",
                    "message": "Client disconnected",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return SSEResponse.create_notification_stream(notification_generator())

    except Exception as e:
        logger.error(f"Failed to create notification stream: {e}")
        raise ExternalServiceException(
            service="NotificationStreaming",
            message=f"Failed to create notification stream: {str(e)}",
        )


@router.post(
    "/swarm/chat/{agent_type}/stream", summary="Stream Chat with Specific Agent"
)
async def stream_chat_with_agent(
    agent_type: str, message_request: Dict[str, Any]
) -> StreamingResponse:
    """
    Chat with a specific agent and stream responses using SSE
    Replaces WebSocket chat with HTTP streaming

    Args:
        agent_type: Type of agent (ceo, strategy, devops)
        message_request: Chat message request

    Returns:
        StreamingResponse: SSE stream for agent chat responses
    """
    try:
        if not _swarm_orchestrator:
            raise ExternalServiceException(
                service="SwarmOrchestrator",
                message="Swarm orchestrator is not initialized",
                details={"service_status": "not_initialized"},
            )

        # Validate agent type
        valid_agents = ["ceo", "strategy", "devops"]
        if agent_type not in valid_agents:
            raise ValidationException(
                f"Invalid agent type. Valid types: {valid_agents}",
                details={
                    "provided_agent_type": agent_type,
                    "valid_agent_types": valid_agents,
                },
            )

        # Get the specific agent
        agent = _swarm_orchestrator.agents.get(agent_type)
        if not agent:
            raise ResourceNotFoundException("Swarm Agent", agent_type)

        # Validate message
        if "message" not in message_request:
            raise ValidationException(
                "Missing required field: message",
                details={
                    "required_fields": ["message"],
                    "provided_fields": list(message_request.keys()),
                },
            )

        async def chat_response_generator():
            """Generate streaming chat responses"""
            try:
                # Send initial acknowledgment
                yield {
                    "type": "chat_started",
                    "agent_type": agent_type,
                    "message": "Processing your message...",
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Process message with the specific agent
                task_input = {
                    "messages": [
                        {"type": "human", "content": message_request["message"]}
                    ],
                    "direct_agent_request": True,
                }

                # Simulate streaming response (in production, integrate with actual agent streaming)
                result = await agent.process_task(task_input)

                # Send final response
                yield {
                    "type": "chat_response",
                    "agent_type": agent_type,
                    "original_message": message_request["message"],
                    "response": result,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Send completion
                yield {
                    "type": "chat_complete",
                    "agent_type": agent_type,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                yield {
                    "type": "chat_error",
                    "agent_type": agent_type,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return SSEResponse.create_event_stream(
            chat_response_generator(), event_type="chat_message"
        )

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat stream for agent {agent_type}: {e}")
        raise ExternalServiceException(
            service="AgentChatStreaming",
            message=f"Failed to create chat stream: {str(e)}",
        )
