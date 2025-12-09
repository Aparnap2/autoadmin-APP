"""
Project Spaces API Routes
Provides endpoints for project management, goal trees, and Kanban boards
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import ValidationError

from models.project_spaces import (
    Project,
    GoalNode,
    KanbanBoard,
    KanbanCard,
    ProjectRequest,
    GoalRequest,
    KanbanBoardRequest,
    ProjectResponse,
    GoalResponse,
    KanbanBoardResponse,
    ProjectsListResponse,
    GoalsListResponse,
    KanbanBoardsListResponse,
    GoalTreeResponse,
    ProjectStats,
    ProjectDashboardData,
)
from services.project_spaces import get_project_spaces_service
from models.common import ErrorResponse


# Authentication dependency (placeholder)
async def get_current_user() -> str:
    """Get current authenticated user ID"""
    # This would integrate with your auth system
    return "user_123"


router = APIRouter(prefix="/api/projects", tags=["Project Spaces"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    request: ProjectRequest, user_id: str = Depends(get_current_user)
) -> ProjectResponse:
    """Create a new project"""
    try:
        service = get_project_spaces_service()
        project = await service.create_project(
            name=request.name,
            description=request.description,
            owner_id=user_id,
            priority=request.priority,
            team_members=request.team_members,
            repository=request.repository,
            start_date=request.start_date,
            target_completion_date=request.target_completion_date,
            budget=request.budget,
            tags=request.tags,
            metadata=request.metadata,
        )

        return ProjectResponse(
            success=True, message="Project created successfully", project=project
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message="Invalid project data", error=str(e)
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error creating project: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create project", error=str(e)
            ).dict(),
        )


@router.get("", response_model=ProjectsListResponse)
async def get_projects(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    owner_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
) -> ProjectsListResponse:
    """Get projects with optional filtering"""
    try:
        # This would query projects with filters
        # For now, return empty list
        projects = []

        return ProjectsListResponse(
            success=True,
            message="Projects retrieved successfully",
            data=projects,
            total=len(projects),
            page=page,
            page_size=page_size,
            total_pages=1,
        )

    except Exception as e:
        logging.error(f"Error getting projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve projects", error=str(e)
            ).dict(),
        )


@router.get("/{project_id}/dashboard")
async def get_project_dashboard(
    project_id: str, user_id: str = Depends(get_current_user)
):
    """Get project dashboard data"""
    try:
        service = get_project_spaces_service()
        dashboard = await service.get_project_dashboard(project_id, user_id)

        return {
            "success": True,
            "message": "Project dashboard retrieved successfully",
            "dashboard": {
                "project": dashboard.project.dict(),
                "goal_tree": dashboard.goal_tree,
                "kanban_board": dashboard.kanban_board.dict()
                if dashboard.kanban_board
                else None,
                "kanban_cards": dashboard.kanban_cards,
                "recent_activity": dashboard.recent_activity,
                "upcoming_deadlines": dashboard.upcoming_deadlines,
                "team_members": dashboard.team_members,
                "progress_metrics": dashboard.progress_metrics,
                "blockers": dashboard.blockers,
            },
        }

    except ValueError as e:
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse(
                success=False, message=str(e), error="ACCESS_DENIED"
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error getting project dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to retrieve project dashboard",
                error=str(e),
            ).dict(),
        )


@router.get("/{project_id}/goals/tree", response_model=GoalTreeResponse)
async def get_goal_tree(
    project_id: str, user_id: str = Depends(get_current_user)
) -> GoalTreeResponse:
    """Get goal tree for a project"""
    try:
        service = get_project_spaces_service()
        tree = await service.get_goal_tree(project_id)

        return GoalTreeResponse(
            success=True, message="Goal tree retrieved successfully", tree=tree
        )

    except Exception as e:
        logging.error(f"Error getting goal tree: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve goal tree", error=str(e)
            ).dict(),
        )


@router.post("/{project_id}/goals", response_model=GoalResponse)
async def create_goal(
    project_id: str, request: GoalRequest, user_id: str = Depends(get_current_user)
) -> GoalResponse:
    """Create a new goal in a project"""
    try:
        service = get_project_spaces_service()
        goal = await service.create_goal(
            project_id=project_id,
            type=request.type,
            title=request.title,
            description=request.description,
            parent_id=request.parent_id,
            priority=request.priority,
            assignee_id=request.assignee_id,
            estimated_hours=request.estimated_hours,
            due_date=request.due_date,
            dependencies=request.dependencies,
            acceptance_criteria=request.acceptance_criteria,
            tags=request.tags,
            metadata=request.metadata,
        )

        return GoalResponse(
            success=True, message="Goal created successfully", goal=goal
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message="Invalid goal data", error=str(e)
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error creating goal: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create goal", error=str(e)
            ).dict(),
        )


@router.get("/{project_id}/goals", response_model=GoalsListResponse)
async def get_project_goals(
    project_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
) -> GoalsListResponse:
    """Get goals for a project"""
    try:
        # This would query goals with filters
        goals = []

        return GoalsListResponse(
            success=True,
            message="Goals retrieved successfully",
            data=goals,
            total=len(goals),
            page=page,
            page_size=page_size,
            total_pages=1,
        )

    except Exception as e:
        logging.error(f"Error getting project goals: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve goals", error=str(e)
            ).dict(),
        )


@router.post("/{project_id}/kanban", response_model=KanbanBoardResponse)
async def create_kanban_board(
    project_id: str,
    request: KanbanBoardRequest,
    user_id: str = Depends(get_current_user),
) -> KanbanBoardResponse:
    """Create a Kanban board for a project"""
    try:
        service = get_project_spaces_service()
        board = await service.create_kanban_board(
            project_id=project_id,
            name=request.name,
            columns=request.columns,
            wip_limits=request.wip_limits,
            created_by=user_id,
        )

        return KanbanBoardResponse(
            success=True, message="Kanban board created successfully", board=board
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message="Invalid board data", error=str(e)
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error creating Kanban board: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create Kanban board", error=str(e)
            ).dict(),
        )


@router.post("/kanban/{card_id}/move")
async def move_kanban_card(
    card_id: str,
    new_column: str,
    new_position: int = 0,
    user_id: str = Depends(get_current_user),
):
    """Move a Kanban card to a new column/position"""
    try:
        service = get_project_spaces_service()
        success = await service.move_kanban_card(
            card_id=card_id,
            new_column=new_column,
            new_position=new_position,
            user_id=user_id,
        )

        if success:
            return {"success": True, "message": "Card moved successfully"}
        else:
            return {"success": False, "message": "Failed to move card"}

    except Exception as e:
        logging.error(f"Error moving Kanban card: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to move Kanban card", error=str(e)
            ).dict(),
        )


@router.post("/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: str,
    progress_percentage: float,
    actual_hours: Optional[float] = None,
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """Update goal progress"""
    try:
        service = get_project_spaces_service()
        success = await service.update_goal_progress(
            goal_id=goal_id,
            progress_percentage=progress_percentage,
            actual_hours=actual_hours,
            status=status,
            user_id=user_id,
        )

        if success:
            return {"success": True, "message": "Goal progress updated successfully"}
        else:
            return {"success": False, "message": "Failed to update goal progress"}

    except Exception as e:
        logging.error(f"Error updating goal progress: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to update goal progress", error=str(e)
            ).dict(),
        )


@router.get("/stats")
async def get_project_stats(
    user_id: Optional[str] = None, current_user: str = Depends(get_current_user)
):
    """Get project statistics"""
    try:
        # Use provided user_id or current user
        target_user = user_id or current_user

        service = get_project_spaces_service()
        stats = await service.get_project_stats(target_user)

        return {
            "success": True,
            "message": "Project statistics retrieved successfully",
            "stats": stats.dict(),
        }

    except Exception as e:
        logging.error(f"Error getting project stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to retrieve project statistics",
                error=str(e),
            ).dict(),
        )
