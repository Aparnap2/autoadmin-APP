"""
Task management related Pydantic models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from .common import BaseResponse, PaginatedResponse


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    PAUSED = "paused"


class TaskPriority(str, Enum):
    """Task priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Task type enumeration"""
    AGENT_TASK = "agent_task"
    DATA_PROCESSING = "data_processing"
    FILE_OPERATION = "file_operation"
    WEBHOOK_PROCESSING = "webhook_processing"
    SCHEDULING = "scheduling"
    CLEANUP = "cleanup"
    MONITORING = "monitoring"
    REPORT_GENERATION = "report_generation"
    BACKUP = "backup"
    IMPORT_EXPORT = "import_export"
    CUSTOM = "custom"


class Task(BaseModel):
    """Task model"""
    id: str = Field(description="Task unique identifier")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    type: TaskType = Field(description="Task type")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    created_by: Optional[str] = Field(default=None, description="Creator identifier")
    assigned_to: Optional[str] = Field(default=None, description="Assigned user/agent identifier")
    team: Optional[str] = Field(default=None, description="Team identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Task progress (0-1)")
    progress_message: Optional[str] = Field(default=None, description="Progress message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion timestamp")
    due_at: Optional[datetime] = Field(default=None, description="Task due timestamp")
    scheduled_at: Optional[datetime] = Field(default=None, description="Scheduled execution timestamp")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, description="Timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_count: int = Field(default=0, ge=0, description="Current retry count")
    retry_delay_seconds: int = Field(default=60, ge=0, description="Delay between retries")
    parent_task_id: Optional[str] = Field(default=None, description="Parent task ID")
    child_task_ids: List[str] = Field(default_factory=list, description="Child task IDs")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    estimated_duration_seconds: Optional[int] = Field(default=None, ge=0, description="Estimated duration")
    actual_duration_seconds: Optional[int] = Field(default=None, ge=0, description="Actual duration")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage metrics")
    execution_logs: List[str] = Field(default_factory=list, description="Execution logs")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")
    notification_settings: Dict[str, Any] = Field(default_factory=dict, description="Notification settings")


class TaskRequest(BaseModel):
    """Task creation request model"""
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    type: TaskType = Field(description="Task type")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    assigned_to: Optional[str] = Field(default=None, description="Assigned user/agent identifier")
    team: Optional[str] = Field(default=None, description="Team identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    due_at: Optional[datetime] = Field(default=None, description="Task due timestamp")
    scheduled_at: Optional[datetime] = Field(default=None, description="Scheduled execution timestamp")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, description="Timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=60, ge=0, description="Delay between retries")
    parent_task_id: Optional[str] = Field(default=None, description="Parent task ID")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    estimated_duration_seconds: Optional[int] = Field(default=None, ge=0, description="Estimated duration")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")
    notification_settings: Dict[str, Any] = Field(default_factory=dict, description="Notification settings")


class TaskResponse(BaseResponse):
    """Task response model"""
    task: Task = Field(description="Task details")


class TaskCreateRequest(TaskRequest):
    """Task creation request with additional fields"""
    # Inherits all fields from TaskRequest
    pass


class TaskUpdateRequest(BaseModel):
    """Task update request model"""
    title: Optional[str] = Field(default=None, description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    status: Optional[TaskStatus] = Field(default=None, description="Task status")
    priority: Optional[TaskPriority] = Field(default=None, description="Task priority")
    assigned_to: Optional[str] = Field(default=None, description="Assigned user/agent identifier")
    team: Optional[str] = Field(default=None, description="Team identifier")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Task parameters")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Error message")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Task progress")
    progress_message: Optional[str] = Field(default=None, description="Progress message")
    due_at: Optional[datetime] = Field(default=None, description="Task due timestamp")
    scheduled_at: Optional[datetime] = Field(default=None, description="Scheduled execution timestamp")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, description="Timeout in seconds")
    parent_task_id: Optional[str] = Field(default=None, description="Parent task ID")
    child_task_ids: Optional[List[str]] = Field(default=None, description="Child task IDs")
    dependencies: Optional[List[str]] = Field(default=None, description="Task dependencies")
    tags: Optional[List[str]] = Field(default=None, description="Task tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    estimated_duration_seconds: Optional[int] = Field(default=None, ge=0, description="Estimated duration")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")
    notification_settings: Optional[Dict[str, Any]] = Field(default=None, description="Notification settings")


class TaskBulkRequest(BaseModel):
    """Bulk task operations request model"""
    operation: str = Field(description="Operation type (create, update, delete, cancel)")
    task_ids: Optional[List[str]] = Field(default=None, description="Task IDs for update/delete/cancel")
    tasks: Optional[List[TaskCreateRequest]] = Field(default=None, description="Tasks for create")
    updates: Optional[Dict[str, Any]] = Field(default=None, description="Updates for bulk update")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters for bulk operations")

    @validator("operation")
    def validate_operation(cls, v):
        """Validate operation type"""
        valid_operations = ["create", "update", "delete", "cancel", "retry", "pause", "resume"]
        if v not in valid_operations:
            raise ValueError(f"Invalid operation. Must be one of: {valid_operations}")
        return v

    @validator("task_ids")
    def validate_task_ids(cls, v, values):
        """Validate task_ids for relevant operations"""
        operation = values.get("operation")
        if operation in ["update", "delete", "cancel", "retry", "pause", "resume"] and not v:
            raise ValueError(f"task_ids is required for operation: {operation}")
        return v

    @validator("tasks")
    def validate_tasks(cls, v, values):
        """Validate tasks for create operation"""
        if values.get("operation") == "create" and not v:
            raise ValueError("tasks is required for create operation")
        return v

    @validator("updates")
    def validate_updates(cls, v, values):
        """Validate updates for update operation"""
        if values.get("operation") == "update" and not v:
            raise ValueError("updates is required for update operation")
        return v


class TaskBulkResponse(BaseResponse):
    """Bulk task operations response model"""
    operation: str = Field(description="Operation performed")
    total: int = Field(description="Total number of tasks processed")
    successful: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(description="Detailed results")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class TaskListResponse(PaginatedResponse[Task]):
    """Paginated task list response"""
    pass


class TaskStats(BaseModel):
    """Task statistics model"""
    total_tasks: int = Field(description="Total number of tasks")
    tasks_by_status: Dict[TaskStatus, int] = Field(description="Tasks by status")
    tasks_by_priority: Dict[TaskPriority, int] = Field(description="Tasks by priority")
    tasks_by_type: Dict[TaskType, int] = Field(description="Tasks by type")
    average_completion_time: float = Field(description="Average completion time in seconds")
    success_rate: float = Field(description="Success rate (0-1)")
    failure_rate: float = Field(description="Failure rate (0-1)")
    retry_rate: float = Field(description="Retry rate (0-1)")
    overdue_tasks: int = Field(description="Number of overdue tasks")
    tasks_due_today: int = Field(description="Number of tasks due today")
    tasks_due_this_week: int = Field(description="Number of tasks due this week")
    resource_utilization: Dict[str, float] = Field(default_factory=dict, description="Resource utilization")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Stats timestamp")


class TaskExecutionLog(BaseModel):
    """Task execution log model"""
    id: str = Field(description="Log entry ID")
    task_id: str = Field(description="Task ID")
    level: str = Field(description="Log level (debug, info, warning, error)")
    message: str = Field(description="Log message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional log data")
    source: str = Field(description="Log source component")


class TaskDependency(BaseModel):
    """Task dependency model"""
    task_id: str = Field(description="Task ID")
    depends_on: str = Field(description="Dependency task ID")
    dependency_type: str = Field(default="finish_to_start", description="Dependency type")
    description: Optional[str] = Field(default=None, description="Dependency description")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class TaskSchedule(BaseModel):
    """Task schedule model"""
    id: str = Field(description="Schedule ID")
    task_template: TaskCreateRequest = Field(description="Task template")
    schedule_type: str = Field(description="Schedule type (cron, interval, once)")
    schedule_expression: str = Field(description="Schedule expression")
    timezone: str = Field(default="UTC", description="Timezone")
    enabled: bool = Field(default=True, description="Schedule enabled")
    next_run: Optional[datetime] = Field(default=None, description="Next run time")
    last_run: Optional[datetime] = Field(default=None, description="Last run time")
    run_count: int = Field(default=0, description="Number of runs")
    max_runs: Optional[int] = Field(default=None, description="Maximum runs")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")