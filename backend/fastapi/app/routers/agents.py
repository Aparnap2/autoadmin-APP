"""
Agent services router for LangGraph integration and task orchestration
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
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
    AgentActionResponse
)

logger = get_logger(__name__)

router = APIRouter()

# In-memory agent storage (in production, use database)
_agents_registry = {}
_agent_tasks = {}
_agent_status = {}

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
                    TaskType.EMAIL_OUTREACH
                ],
                "max_concurrent_tasks": 3,
                "current_load": 0,
                "success_rate": 0.95,
                "average_execution_time": 180.0,
                "specialized_skills": ["content writing", "social media management", "market research"],
                "tools_available": ["tavily_search", "openai_gpt4", "hubspot_api"],
                "integration_partners": ["HubSpot", "Twitter", "LinkedIn"]
            }
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
                    TaskType.DATA_PROCESSING
                ],
                "max_concurrent_tasks": 2,
                "current_load": 0,
                "success_rate": 0.97,
                "average_execution_time": 120.0,
                "specialized_skills": ["financial analysis", "report generation", "data modeling"],
                "tools_available": ["excel_processor", "chart_generator", "financial_calculators"],
                "integration_partners": ["QuickBooks", "Stripe", "Plaid"]
            }
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
                    TaskType.DEPLOYMENT
                ],
                "max_concurrent_tasks": 4,
                "current_load": 0,
                "success_rate": 0.98,
                "average_execution_time": 90.0,
                "specialized_skills": ["docker", "kubernetes", "ci/cd", "monitoring"],
                "tools_available": ["github_api", "docker_api", "kubernetes_api"],
                "integration_partners": ["GitHub", "Docker Hub", "AWS"]
            }
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
                    TaskType.REPORT_GENERATION
                ],
                "max_concurrent_tasks": 2,
                "current_load": 0,
                "success_rate": 0.92,
                "average_execution_time": 300.0,
                "specialized_skills": ["strategic analysis", "market research", "business intelligence"],
                "tools_available": ["swot_analyzer", "market_research_tools", "competitive_analysis"],
                "integration_partners": ["Crunchbase", "Market APIs", "BI Tools"]
            }
        }
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
                "uptime": 0.0
            }
        }

# Initialize agents on startup
@router.on_event("startup")
async def startup_event():
    """Initialize agents on application startup"""
    await initialize_default_agents()
    logger.info("Default agents initialized", agent_count=len(_agents_registry))


@router.get("/", response_model=AgentListResponse, summary="List All Agents")
async def list_agents(
    agent_type: Optional[AgentType] = Query(default=None, description="Filter by agent type"),
    status: Optional[AgentStatus] = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size")
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
                "metrics": agent_status_data.get("metrics", {})
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
            returned=len(paginated_agents)
        )

        return AgentListResponse(
            items=paginated_agents,
            total=len(filtered_agents),
            page=page,
            page_size=page_size,
            total_pages=(len(filtered_agents) + page_size - 1) // page_size,
            has_next=end < len(filtered_agents),
            has_prev=page > 1
        )

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")


@router.get("/{agent_id}/status", response_model=AgentStatusResponse, summary="Get Agent Status")
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
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

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
            performance_metrics=status_data.get("metrics", {})
        )

        logger.info(
            "Retrieved agent status",
            agent_id=agent_id,
            status=response.status,
            health_score=health_score
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent status for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent status")


@router.post("/{agent_id}/tasks", response_model=AgentTaskResponse, summary="Create Agent Task")
async def create_agent_task(
    agent_id: str,
    task_request: AgentTaskRequest,
    background_tasks: BackgroundTasks
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
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        agent_data = _agents_registry[agent_id]
        status_data = _agent_status.get(agent_id, {})

        # Check agent capacity
        current_load = len(status_data.get("current_tasks", []))
        max_concurrent = agent_data["capabilities"]["max_concurrent_tasks"]

        if current_load >= max_concurrent:
            raise HTTPException(
                status_code=429,
                detail=f"Agent {agent_id} is at maximum capacity ({max_concurrent} tasks)"
            )

        # Validate task type is supported by agent
        supported_types = agent_data["capabilities"]["supported_task_types"]
        if task_request.type not in supported_types:
            raise HTTPException(
                status_code=400,
                detail=f"Agent {agent_id} does not support task type {task_request.type}"
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
            "retry_count": 0
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
            priority=task_request.priority
        )

        return AgentTaskResponse(
            success=True,
            message=f"Task created for agent {agent_id}",
            task=task
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create agent task")


@router.get("/{agent_id}/tasks", summary="List Agent Tasks")
async def list_agent_tasks(
    agent_id: str,
    status: Optional[str] = Query(default=None, description="Filter by task status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size")
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
    """
    try:
        if agent_id not in _agents_registry:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

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
            returned=len(paginated_tasks)
        )

        return {
            "items": paginated_tasks,
            "total": len(agent_tasks),
            "page": page,
            "page_size": page_size,
            "total_pages": (len(agent_tasks) + page_size - 1) // page_size,
            "has_next": end < len(agent_tasks),
            "has_prev": page > 1
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tasks for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agent tasks")


@router.post("/{agent_id}/actions", response_model=AgentActionResponse, summary="Execute Agent Action")
async def execute_agent_action(
    agent_id: str,
    action: AgentAction
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
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Validate action
        valid_actions = ["start", "stop", "restart", "pause", "resume", "configure"]
        if action.action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action. Valid actions: {valid_actions}"
            )

        # Execute action
        result = await execute_agent_action_internal(agent_id, action.action, action.parameters)

        logger.info(
            "Executed agent action",
            agent_id=agent_id,
            action=action.action,
            success=result.get("success", False)
        )

        return AgentActionResponse(
            success=True,
            message=f"Action {action.action} executed successfully",
            action_id=f"action_{uuid.uuid4().hex[:8]}",
            result=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute action {action.action} on agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute agent action")


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


async def execute_agent_action_internal(agent_id: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
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
            return {"success": False, "message": "Agent cannot be paused in current state"}

    elif action == "resume":
        if status_data.get("status") == AgentStatus.MAINTENANCE:
            status_data["status"] = AgentStatus.IDLE
            return {"success": True, "message": "Agent resumed"}
        else:
            return {"success": False, "message": "Agent cannot be resumed in current state"}

    elif action == "configure":
        # Apply configuration changes
        if "max_concurrent_tasks" in parameters:
            _agents_registry[agent_id]["capabilities"]["max_concurrent_tasks"] = parameters["max_concurrent_tasks"]
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
            task_type=task["type"]
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
            "output": f"Simulated output for {task['type']} task"
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
            execution_time=processing_time
        )

    except Exception as e:
        logger.error(f"Failed to process agent task {task_id} for agent {agent_id}: {e}")

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