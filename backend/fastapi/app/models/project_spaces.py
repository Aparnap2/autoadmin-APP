"""
Project Spaces and Goal Tree Management
Hierarchical project structure with outcomes, milestones, and tasks
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
import uuid

from .common import BaseResponse, PaginatedResponse


class ProjectStatus(str, Enum):
    """Project status"""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPriority(str, Enum):
    """Project priority"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GoalType(str, Enum):
    """Goal tree node types"""

    OUTCOME = "outcome"  # High-level business outcome
    MILESTONE = "milestone"  # Major milestone
    EPIC = "epic"  # Large feature/epic
    TASK = "task"  # Individual task


class GoalStatus(str, Enum):
    """Goal status"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class KanbanColumn(str, Enum):
    """Kanban board columns"""

    BACKLOG = "backlog"
    SPRINT = "sprint"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"


class Project(BaseModel):
    """Project model"""

    id: str = Field(description="Project unique identifier")
    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    status: ProjectStatus = Field(
        default=ProjectStatus.PLANNING, description="Project status"
    )
    priority: ProjectPriority = Field(
        default=ProjectPriority.MEDIUM, description="Project priority"
    )
    owner_id: str = Field(description="Project owner user ID")
    team_members: List[str] = Field(
        default_factory=list, description="Team member user IDs"
    )
    repository: Optional[str] = Field(
        default=None, description="Git repository URL/name"
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Project start date"
    )
    target_completion_date: Optional[datetime] = Field(
        default=None, description="Target completion date"
    )
    actual_completion_date: Optional[datetime] = Field(
        default=None, description="Actual completion date"
    )
    budget: Optional[float] = Field(default=None, ge=0, description="Project budget")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class GoalNode(BaseModel):
    """Goal tree node"""

    id: str = Field(description="Goal unique identifier")
    project_id: str = Field(description="Parent project ID")
    parent_id: Optional[str] = Field(default=None, description="Parent goal ID")
    type: GoalType = Field(description="Goal type")
    title: str = Field(description="Goal title")
    description: Optional[str] = Field(default=None, description="Goal description")
    status: GoalStatus = Field(
        default=GoalStatus.NOT_STARTED, description="Goal status"
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Priority (1-10, 10 highest)"
    )
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    estimated_hours: Optional[float] = Field(
        default=None, ge=0, description="Estimated hours"
    )
    actual_hours: Optional[float] = Field(
        default=None, ge=0, description="Actual hours spent"
    )
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )
    progress_percentage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Progress percentage"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Dependent goal IDs"
    )
    children: List[str] = Field(default_factory=list, description="Child goal IDs")
    acceptance_criteria: List[str] = Field(
        default_factory=list, description="Acceptance criteria"
    )
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    tags: List[str] = Field(default_factory=list, description="Goal tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    @validator("children", "dependencies")
    def validate_no_self_reference(cls, v, values):
        """Validate no self-references in children or dependencies"""
        if "id" in values and values["id"] in v:
            raise ValueError("Goal cannot reference itself")
        return v


class KanbanBoard(BaseModel):
    """Kanban board configuration"""

    id: str = Field(description="Board unique identifier")
    project_id: str = Field(description="Parent project ID")
    name: str = Field(description="Board name")
    columns: List[KanbanColumn] = Field(description="Board columns")
    wip_limits: Dict[str, int] = Field(
        default_factory=dict, description="WIP limits per column"
    )
    is_active: bool = Field(default=True, description="Board is active")
    created_by: str = Field(description="Creator user ID")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class KanbanCard(BaseModel):
    """Kanban card representing a goal/task"""

    id: str = Field(description="Card unique identifier")
    board_id: str = Field(description="Parent board ID")
    goal_id: str = Field(description="Associated goal ID")
    column: KanbanColumn = Field(description="Current column")
    position: int = Field(default=0, description="Position in column")
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    labels: List[str] = Field(default_factory=list, description="Card labels")
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    priority: int = Field(default=5, ge=1, le=10, description="Priority")
    estimated_hours: Optional[float] = Field(
        default=None, ge=0, description="Estimated hours"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class ProjectRequest(BaseModel):
    """Project creation/update request"""

    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    priority: ProjectPriority = Field(
        default=ProjectPriority.MEDIUM, description="Project priority"
    )
    team_members: List[str] = Field(
        default_factory=list, description="Team member user IDs"
    )
    repository: Optional[str] = Field(
        default=None, description="Git repository URL/name"
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Project start date"
    )
    target_completion_date: Optional[datetime] = Field(
        default=None, description="Target completion date"
    )
    budget: Optional[float] = Field(default=None, ge=0, description="Project budget")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class GoalRequest(BaseModel):
    """Goal creation/update request"""

    project_id: str = Field(description="Parent project ID")
    parent_id: Optional[str] = Field(default=None, description="Parent goal ID")
    type: GoalType = Field(description="Goal type")
    title: str = Field(description="Goal title")
    description: Optional[str] = Field(default=None, description="Goal description")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1-10)")
    assignee_id: Optional[str] = Field(default=None, description="Assigned user ID")
    estimated_hours: Optional[float] = Field(
        default=None, ge=0, description="Estimated hours"
    )
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    dependencies: List[str] = Field(
        default_factory=list, description="Dependent goal IDs"
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list, description="Acceptance criteria"
    )
    tags: List[str] = Field(default_factory=list, description="Goal tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class KanbanBoardRequest(BaseModel):
    """Kanban board creation request"""

    project_id: str = Field(description="Parent project ID")
    name: str = Field(description="Board name")
    columns: List[KanbanColumn] = Field(description="Board columns")
    wip_limits: Dict[str, int] = Field(
        default_factory=dict, description="WIP limits per column"
    )


class ProjectResponse(BaseResponse):
    """Project response"""

    project: Project = Field(description="Project details")


class GoalResponse(BaseResponse):
    """Goal response"""

    goal: GoalNode = Field(description="Goal details")


class KanbanBoardResponse(BaseResponse):
    """Kanban board response"""

    board: KanbanBoard = Field(description="Board details")


class ProjectsListResponse(PaginatedResponse[Project]):
    """Paginated projects list"""

    pass


class GoalsListResponse(PaginatedResponse[GoalNode]):
    """Paginated goals list"""

    pass


class KanbanBoardsListResponse(PaginatedResponse[KanbanBoard]):
    """Paginated Kanban boards list"""

    pass


class GoalTreeResponse(BaseResponse):
    """Goal tree response"""

    tree: Dict[str, Any] = Field(description="Goal tree structure")


class ProjectStats(BaseModel):
    """Project statistics"""

    total_projects: int = Field(description="Total number of projects")
    active_projects: int = Field(description="Number of active projects")
    completed_projects: int = Field(description="Number of completed projects")
    total_goals: int = Field(description="Total number of goals")
    completed_goals: int = Field(description="Number of completed goals")
    in_progress_goals: int = Field(description="Number of goals in progress")
    blocked_goals: int = Field(description="Number of blocked goals")
    average_completion_time: Optional[float] = Field(
        default=None, description="Average goal completion time in hours"
    )
    on_time_completion_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="On-time completion rate"
    )
    team_utilization: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Team utilization rate"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Stats timestamp"
    )


class ProjectDashboardData(BaseModel):
    """Project dashboard data"""

    project: Project = Field(description="Project details")
    goal_tree: Dict[str, Any] = Field(description="Goal tree structure")
    kanban_board: Optional[KanbanBoard] = Field(
        default=None, description="Kanban board if exists"
    )
    kanban_cards: List[Dict[str, Any]] = Field(
        default_factory=list, description="Kanban cards"
    )
    recent_activity: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recent activity"
    )
    upcoming_deadlines: List[Dict[str, Any]] = Field(
        default_factory=list, description="Upcoming deadlines"
    )
    team_members: List[Dict[str, Any]] = Field(
        default_factory=list, description="Team members"
    )
    progress_metrics: Dict[str, Any] = Field(description="Progress metrics")
    blockers: List[str] = Field(default_factory=list, description="Current blockers")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Data timestamp"
    )
