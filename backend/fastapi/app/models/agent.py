"""
Agent-related Pydantic models for API validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from .common import BaseResponse, PaginatedResponse


class AgentType(str, Enum):
    """Agent type enumeration"""

    MARKETING = "marketing"
    FINANCE = "finance"
    DEVOPS = "devops"
    STRATEGY = "strategy"
    RESEARCH = "research"
    CONTENT = "content"
    ANALYTICS = "analytics"
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    HR = "hr"


class AgentStatus(str, Enum):
    """Agent status enumeration"""

    IDLE = "idle"
    BUSY = "busy"
    PROCESSING = "processing"
    ERROR = "error"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class TaskPriority(str, Enum):
    """Task priority enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Task type enumeration"""

    RESEARCH = "research"
    ANALYSIS = "analysis"
    CONTENT_CREATION = "content_creation"
    DATA_PROCESSING = "data_processing"
    WEB_SCraping = "web_scraping"
    EMAIL_OUTREACH = "email_outreach"
    SOCIAL_MEDIA = "social_media"
    REPORT_GENERATION = "report_generation"
    AUTOMATION = "automation"
    MONITORING = "monitoring"
    CUSTOM = "custom"


class AgentCapabilities(BaseModel):
    """Agent capabilities model"""

    supported_task_types: List[TaskType] = Field(description="Supported task types")
    max_concurrent_tasks: int = Field(
        ge=1, le=50, description="Maximum concurrent tasks"
    )
    current_load: int = Field(ge=0, description="Current number of active tasks")
    success_rate: float = Field(ge=0.0, le=1.0, description="Historical success rate")
    average_execution_time: float = Field(
        ge=0, description="Average execution time in seconds"
    )
    specialized_skills: List[str] = Field(
        default_factory=list, description="Specialized skills"
    )
    tools_available: List[str] = Field(
        default_factory=list, description="Available tools"
    )
    integration_partners: List[str] = Field(
        default_factory=list, description="Integration partners"
    )

    @validator("current_load")
    def validate_current_load(cls, v, values):
        """Ensure current load doesn't exceed max concurrent tasks"""
        if "max_concurrent_tasks" in values and v > values["max_concurrent_tasks"]:
            return values["max_concurrent_tasks"]
        return v


class AgentConfig(BaseModel):
    """Agent configuration model"""

    name: str = Field(description="Agent name")
    type: AgentType = Field(description="Agent type")
    description: Optional[str] = Field(default=None, description="Agent description")
    version: str = Field(default="1.0.0", description="Agent version")
    ai_model_config: Dict[str, Any] = Field(
        default_factory=dict, description="AI model configuration"
    )
    capabilities: AgentCapabilities = Field(description="Agent capabilities")
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Custom settings"
    )
    webhooks: List[str] = Field(default_factory=list, description="Webhook URLs")
    schedule: Optional[Dict[str, Any]] = Field(
        default=None, description="Agent schedule"
    )
    auto_start: bool = Field(default=True, description="Auto-start on system startup")


class AgentTask(BaseModel):
    """Agent task model"""

    id: str = Field(description="Task unique identifier")
    title: str = Field(description="Task title")
    description: str = Field(description="Task description")
    type: TaskType = Field(description="Task type")
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Task priority"
    )
    agent_type: AgentType = Field(description="Assigned agent type")
    agent_id: Optional[str] = Field(default=None, description="Assigned agent ID")
    status: str = Field(default="pending", description="Task status")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Task parameters"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    expected_duration: Optional[int] = Field(
        default=None, description="Expected duration in seconds"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    retry_count: int = Field(default=0, ge=0, description="Current retry count")
    progress: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Task progress (0-1)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Task start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AgentRequest(BaseModel):
    """Agent creation/update request model"""

    type: AgentType = Field(description="Agent type")
    name: str = Field(description="Agent name")
    description: Optional[str] = Field(default=None, description="Agent description")
    config: Optional[AgentConfig] = Field(
        default=None, description="Agent configuration"
    )
    auto_start: bool = Field(default=False, description="Auto-start the agent")


class AgentResponse(BaseResponse):
    """Agent response model"""

    agent: Dict[str, Any] = Field(description="Agent details")


class AgentTaskRequest(BaseModel):
    """Agent task creation request model"""

    title: str = Field(description="Task title")
    description: str = Field(description="Task description")
    type: TaskType = Field(description="Task type")
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="Task priority"
    )
    agent_type: Optional[AgentType] = Field(
        default=None, description="Preferred agent type"
    )
    agent_id: Optional[str] = Field(default=None, description="Specific agent ID")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Task parameters"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    expected_duration: Optional[int] = Field(
        default=None, description="Expected duration in seconds"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    scheduled_at: Optional[datetime] = Field(
        default=None, description="Scheduled execution time"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AgentTaskResponse(BaseResponse):
    """Agent task response model"""

    task: AgentTask = Field(description="Task details")


class AgentStatusResponse(BaseModel):
    """Agent status response model"""

    agent_id: str = Field(description="Agent ID")
    status: AgentStatus = Field(description="Current status")
    current_tasks: int = Field(description="Number of current tasks")
    capabilities: AgentCapabilities = Field(description="Agent capabilities")
    uptime: Optional[float] = Field(default=None, description="Uptime in seconds")
    last_activity: Optional[datetime] = Field(
        default=None, description="Last activity timestamp"
    )
    health_score: float = Field(ge=0.0, le=1.0, description="Health score (0-1)")
    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Performance metrics"
    )


class AgentListResponse(PaginatedResponse[Dict[str, Any]]):
    """Paginated agent list response"""

    pass


class TaskListResponse(PaginatedResponse[AgentTask]):
    """Paginated task list response"""

    pass


class AgentHealthCheck(BaseModel):
    """Agent health check model"""

    agent_id: str = Field(description="Agent ID")
    status: str = Field(description="Health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    cpu_usage: Optional[float] = Field(default=None, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(
        default=None, description="Memory usage percentage"
    )
    disk_usage: Optional[float] = Field(
        default=None, description="Disk usage percentage"
    )
    response_time: Optional[float] = Field(
        default=None, description="Response time in milliseconds"
    )
    error_rate: Optional[float] = Field(
        default=None, description="Error rate percentage"
    )
    last_error: Optional[str] = Field(default=None, description="Last error message")


class AgentMetrics(BaseModel):
    """Agent metrics model"""

    agent_id: str = Field(description="Agent ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )
    tasks_completed: int = Field(ge=0, description="Total tasks completed")
    tasks_failed: int = Field(ge=0, description="Total tasks failed")
    average_completion_time: float = Field(ge=0, description="Average completion time")
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate")
    total_execution_time: float = Field(ge=0, description="Total execution time")
    resource_usage: Dict[str, float] = Field(
        default_factory=dict, description="Resource usage metrics"
    )
    custom_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metrics"
    )


class AgentAction(BaseModel):
    """Agent action model"""

    action: str = Field(description="Action type")
    agent_id: str = Field(description="Target agent ID")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Action timestamp"
    )


class AgentActionResponse(BaseResponse):
    """Agent action response model"""

    action_id: str = Field(description="Action ID")
    result: Dict[str, Any] = Field(description="Action result")
