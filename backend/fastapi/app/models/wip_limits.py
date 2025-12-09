"""
WIP (Work-In-Progress) Limit Enforcement System
Enforces focus by limiting concurrent tasks and providing friction for context switching
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import uuid

from .common import BaseResponse, PaginatedResponse


class WIPLimitType(str, Enum):
    """Types of WIP limits"""

    GLOBAL = "global"  # System-wide limit
    PROJECT = "project"  # Per-project limit
    USER = "user"  # Per-user limit
    TEAM = "team"  # Per-team limit


class WIPLimitStatus(str, Enum):
    """WIP limit status"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class WIPViolationAction(str, Enum):
    """Actions to take when WIP limit is violated"""

    BLOCK = "block"  # Completely block new task creation
    WARN = "warn"  # Show warning but allow
    SUGGEST = "suggest"  # Suggest completing existing tasks
    ESCALATE = "escalate"  # Escalate to manager/team lead


class WIPLimit(BaseModel):
    """WIP limit configuration"""

    id: str = Field(description="WIP limit unique identifier")
    name: str = Field(description="Human-readable name")
    type: WIPLimitType = Field(description="Type of WIP limit")
    target_id: str = Field(description="ID of target (user, project, team)")
    max_concurrent_tasks: int = Field(
        ge=1, le=10, description="Maximum concurrent tasks allowed"
    )
    status: WIPLimitStatus = Field(
        default=WIPLimitStatus.ACTIVE, description="Limit status"
    )
    violation_action: WIPViolationAction = Field(
        default=WIPViolationAction.WARN, description="Action on violation"
    )
    created_by: str = Field(description="Creator identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator("max_concurrent_tasks")
    def validate_max_tasks(cls, v):
        """Validate maximum concurrent tasks"""
        if v < 1:
            raise ValueError("Maximum concurrent tasks must be at least 1")
        if v > 10:
            raise ValueError("Maximum concurrent tasks cannot exceed 10")
        return v


class WIPViolation(BaseModel):
    """WIP limit violation record"""

    id: str = Field(description="Violation unique identifier")
    limit_id: str = Field(description="WIP limit that was violated")
    user_id: str = Field(description="User who attempted violation")
    attempted_action: str = Field(description="Action that was attempted")
    current_active_tasks: int = Field(
        description="Number of active tasks at violation time"
    )
    limit_max_tasks: int = Field(description="Maximum allowed tasks")
    action_taken: WIPViolationAction = Field(description="Action taken in response")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Violation timestamp"
    )
    resolved: bool = Field(default=False, description="Whether violation was resolved")
    resolution_timestamp: Optional[datetime] = Field(
        default=None, description="Resolution timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class FocusSession(BaseModel):
    """Focus session tracking"""

    id: str = Field(description="Session unique identifier")
    user_id: str = Field(description="User identifier")
    task_id: str = Field(description="Active task being focused on")
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session start time"
    )
    ended_at: Optional[datetime] = Field(default=None, description="Session end time")
    duration_minutes: Optional[int] = Field(
        default=None, description="Session duration in minutes"
    )
    interruptions: int = Field(default=0, description="Number of interruptions")
    context_switches: int = Field(default=0, description="Number of context switches")
    focus_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Focus score (0-1)"
    )
    notes: Optional[str] = Field(default=None, description="Session notes")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ActiveTaskInfo(BaseModel):
    """Information about an active task"""

    task_id: str = Field(description="Task identifier")
    title: str = Field(description="Task title")
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    project_name: Optional[str] = Field(default=None, description="Project name")
    started_at: datetime = Field(description="When task became active")
    estimated_duration_minutes: Optional[int] = Field(
        default=None, description="Estimated duration"
    )
    time_spent_minutes: int = Field(default=0, description="Time spent so far")
    progress_percentage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Progress percentage"
    )
    priority: str = Field(description="Task priority")
    git_branch: Optional[str] = Field(default=None, description="Associated Git branch")
    pr_status: Optional[str] = Field(default=None, description="Pull request status")
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    next_action: Optional[str] = Field(
        default=None, description="Suggested next action"
    )


class FocusDashboardData(BaseModel):
    """Data for the focus-first dashboard"""

    active_task: Optional[ActiveTaskInfo] = Field(
        default=None, description="Currently active task"
    )
    active_tasks_count: int = Field(description="Total number of active tasks")
    wip_limit: int = Field(description="Current WIP limit")
    wip_violations_today: int = Field(description="WIP violations today")
    focus_sessions_today: int = Field(description="Focus sessions completed today")
    total_focus_time_today: int = Field(description="Total focus time today (minutes)")
    focus_score_today: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Today's focus score"
    )
    upcoming_tasks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Next priority tasks"
    )
    recent_completions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recently completed tasks"
    )
    momentum_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Weekly momentum score"
    )
    git_integration_status: Dict[str, Any] = Field(
        default_factory=dict, description="Git integration status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Data timestamp"
    )


class WIPLimitRequest(BaseModel):
    """Request to create/update WIP limit"""

    name: str = Field(description="Human-readable name")
    type: WIPLimitType = Field(description="Type of WIP limit")
    target_id: str = Field(description="ID of target (user, project, team)")
    max_concurrent_tasks: int = Field(
        ge=1, le=10, description="Maximum concurrent tasks allowed"
    )
    violation_action: WIPViolationAction = Field(
        default=WIPViolationAction.WARN, description="Action on violation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FocusSessionRequest(BaseModel):
    """Request to start/end focus session"""

    task_id: str = Field(description="Task to focus on")
    action: str = Field(description="Action: start, end, interrupt")
    notes: Optional[str] = Field(default=None, description="Session notes")
    interruption_reason: Optional[str] = Field(
        default=None, description="Reason for interruption"
    )


class TaskActivationRequest(BaseModel):
    """Request to activate a task (with WIP checking)"""

    task_id: str = Field(description="Task to activate")
    force_override: bool = Field(
        default=False, description="Override WIP limits if necessary"
    )
    reason: Optional[str] = Field(default=None, description="Reason for override")


class WIPLimitResponse(BaseResponse):
    """WIP limit response"""

    wip_limit: WIPLimit = Field(description="WIP limit details")


class WIPViolationResponse(BaseResponse):
    """WIP violation response"""

    violation: WIPViolation = Field(description="Violation details")


class FocusSessionResponse(BaseResponse):
    """Focus session response"""

    session: FocusSession = Field(description="Session details")


class FocusDashboardResponse(BaseResponse):
    """Focus dashboard response"""

    dashboard: FocusDashboardData = Field(description="Dashboard data")


class WIPLimitsListResponse(PaginatedResponse[WIPLimit]):
    """Paginated WIP limits list"""

    pass


class WIPViolationsListResponse(PaginatedResponse[WIPViolation]):
    """Paginated WIP violations list"""

    pass


class FocusSessionsListResponse(PaginatedResponse[FocusSession]):
    """Paginated focus sessions list"""

    pass


class WIPStats(BaseModel):
    """WIP system statistics"""

    total_limits: int = Field(description="Total WIP limits configured")
    active_limits: int = Field(description="Active WIP limits")
    total_violations: int = Field(description="Total violations recorded")
    violations_today: int = Field(description="Violations today")
    average_active_tasks: float = Field(description="Average active tasks per user")
    focus_sessions_today: int = Field(description="Focus sessions today")
    average_focus_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average focus score"
    )
    completion_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Task completion rate"
    )
    context_switch_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Context switch rate"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Stats timestamp"
    )
