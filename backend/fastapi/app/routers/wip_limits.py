"""
WIP Limit Enforcement API Routes
Provides endpoints for managing WIP limits, focus sessions, and dashboard data
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import ValidationError

from models.wip_limits import (
    WIPLimit,
    WIPViolation,
    FocusSession,
    FocusDashboardData,
    WIPLimitRequest,
    FocusSessionRequest,
    TaskActivationRequest,
    WIPLimitResponse,
    WIPViolationResponse,
    FocusSessionResponse,
    FocusDashboardResponse,
    WIPLimitsListResponse,
    WIPViolationsListResponse,
    FocusSessionsListResponse,
    WIPStats,
)
from models.common import ErrorResponse
from services.wip_limit_enforcement import get_wip_limit_enforcement_service
from services.firebase_service import get_firebase_service


# Authentication dependency (placeholder)
async def get_current_user() -> str:
    """Get current authenticated user ID"""
    # This would integrate with your auth system
    return "user_123"


router = APIRouter(prefix="/api/wip", tags=["WIP Limits"])
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=FocusDashboardResponse)
async def get_focus_dashboard(
    user_id: str = Depends(get_current_user),
) -> FocusDashboardResponse:
    """Get focus-first dashboard data"""
    try:
        service = get_wip_limit_enforcement_service()
        dashboard_data = await service.get_focus_dashboard_data(user_id)

        return FocusDashboardResponse(
            success=True,
            message="Dashboard data retrieved successfully",
            dashboard=dashboard_data,
        )

    except Exception as e:
        logger.error(f"Error getting focus dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve dashboard data", error=str(e)
            ).dict(),
        )


@router.post("/check-limit")
async def check_wip_limit(
    project_id: Optional[str] = None,
    team_id: Optional[str] = None,
    additional_task: bool = True,
    user_id: str = Depends(get_current_user),
):
    """Check if starting a new task would violate WIP limits"""
    try:
        service = get_wip_limit_enforcement_service()
        result = await service.check_wip_limit(
            user_id=user_id,
            project_id=project_id,
            team_id=team_id,
            additional_task=additional_task,
        )

        return {
            "success": True,
            "allowed": result.allowed,
            "reason": result.reason,
            "active_tasks_count": result.active_tasks_count,
            "limit": result.limit,
            "violations_today": result.violations_today,
            "suggested_actions": result.suggested_actions,
        }

    except Exception as e:
        logger.error(f"Error checking WIP limit: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to check WIP limit", error=str(e)
            ).dict(),
        )


@router.post("/enforce-limit")
async def enforce_wip_limit(
    action: str,
    project_id: Optional[str] = None,
    team_id: Optional[str] = None,
    force_override: bool = False,
    user_id: str = Depends(get_current_user),
):
    """Enforce WIP limits for a specific action"""
    try:
        service = get_wip_limit_enforcement_service()
        result = await service.enforce_wip_limit(
            user_id=user_id,
            action=action,
            project_id=project_id,
            team_id=team_id,
            force_override=force_override,
        )

        return {
            "success": True,
            "allowed": result.allowed,
            "reason": result.reason,
            "active_tasks_count": result.active_tasks_count,
            "limit": result.limit,
            "violations_today": result.violations_today,
            "suggested_actions": result.suggested_actions,
        }

    except Exception as e:
        logger.error(f"Error enforcing WIP limit: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to enforce WIP limit", error=str(e)
            ).dict(),
        )


@router.post("/focus/start", response_model=FocusSessionResponse)
async def start_focus_session(
    request: FocusSessionRequest, user_id: str = Depends(get_current_user)
) -> FocusSessionResponse:
    """Start a new focus session"""
    try:
        service = get_wip_limit_enforcement_service()
        session = await service.start_focus_session(
            user_id=user_id, task_id=request.task_id, project_id=request.project_id
        )

        return FocusSessionResponse(
            success=True, message="Focus session started successfully", session=session
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message=str(e), error="INVALID_REQUEST"
            ).dict(),
        )
    except Exception as e:
        logger.error(f"Error starting focus session: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to start focus session", error=str(e)
            ).dict(),
        )


@router.post("/focus/end", response_model=FocusSessionResponse)
async def end_focus_session(
    session_id: str,
    notes: Optional[str] = None,
    user_id: str = Depends(get_current_user),
) -> FocusSessionResponse:
    """End a focus session"""
    try:
        service = get_wip_limit_enforcement_service()
        session = await service.end_focus_session(
            user_id=user_id, session_id=session_id, notes=notes
        )

        return FocusSessionResponse(
            success=True, message="Focus session ended successfully", session=session
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message=str(e), error="INVALID_REQUEST"
            ).dict(),
        )
    except Exception as e:
        logger.error(f"Error ending focus session: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to end focus session", error=str(e)
            ).dict(),
        )


@router.post("/focus/interrupt")
async def record_interruption(
    session_id: str,
    reason: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """Record an interruption in the current focus session"""
    try:
        service = get_wip_limit_enforcement_service()
        session = await service.record_interruption(
            user_id=user_id, session_id=session_id, reason=reason
        )

        return {
            "success": True,
            "message": "Interruption recorded successfully",
            "session_id": session.id,
            "interruptions": session.interruptions,
            "focus_score": session.focus_score,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message=str(e), error="INVALID_REQUEST"
            ).dict(),
        )
    except Exception as e:
        logger.error(f"Error recording interruption: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to record interruption", error=str(e)
            ).dict(),
        )


@router.post("/limits", response_model=WIPLimitResponse)
async def create_wip_limit(
    request: WIPLimitRequest, user_id: str = Depends(get_current_user)
) -> WIPLimitResponse:
    """Create a new WIP limit"""
    try:
        service = get_wip_limit_enforcement_service()
        limit = await service.create_wip_limit(
            name=request.name,
            limit_type=request.type,
            target_id=request.target_id,
            max_concurrent_tasks=request.max_concurrent_tasks,
            created_by=user_id,
            violation_action=request.violation_action,
        )

        return WIPLimitResponse(
            success=True, message="WIP limit created successfully", wip_limit=limit
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message="Invalid request data", error=str(e)
            ).dict(),
        )
    except Exception as e:
        logger.error(f"Error creating WIP limit: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create WIP limit", error=str(e)
            ).dict(),
        )


@router.get("/limits", response_model=WIPLimitsListResponse)
async def get_wip_limits(
    limit_type: Optional[str] = None,
    target_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
) -> WIPLimitsListResponse:
    """Get WIP limits with optional filtering"""
    try:
        # This would query Firebase with filters
        # For now, return empty list
        limits = []

        return WIPLimitsListResponse(
            success=True,
            message="WIP limits retrieved successfully",
            data=limits,
            total=len(limits),
            page=page,
            page_size=page_size,
            total_pages=1,
        )

    except Exception as e:
        logger.error(f"Error getting WIP limits: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve WIP limits", error=str(e)
            ).dict(),
        )


@router.get("/violations", response_model=WIPViolationsListResponse)
async def get_wip_violations(
    resolved: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
) -> WIPViolationsListResponse:
    """Get WIP violations with optional filtering"""
    try:
        # This would query Firebase for violations
        violations = []

        return WIPViolationsListResponse(
            success=True,
            message="WIP violations retrieved successfully",
            data=violations,
            total=len(violations),
            page=page,
            page_size=page_size,
            total_pages=1,
        )

    except Exception as e:
        logger.error(f"Error getting WIP violations: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve WIP violations", error=str(e)
            ).dict(),
        )


@router.get("/sessions", response_model=FocusSessionsListResponse)
async def get_focus_sessions(
    active_only: bool = False,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
) -> FocusSessionsListResponse:
    """Get focus sessions with optional filtering"""
    try:
        # This would query Firebase for sessions
        sessions = []

        return FocusSessionsListResponse(
            success=True,
            message="Focus sessions retrieved successfully",
            data=sessions,
            total=len(sessions),
            page=page,
            page_size=page_size,
            total_pages=1,
        )

    except Exception as e:
        logger.error(f"Error getting focus sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve focus sessions", error=str(e)
            ).dict(),
        )


@router.get("/stats")
async def get_wip_stats(
    user_id: Optional[str] = None, current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get WIP system statistics"""
    try:
        # Use provided user_id or current user
        target_user = user_id or current_user

        service = get_wip_limit_enforcement_service()
        stats = await service.get_wip_stats(target_user)

        return {
            "success": True,
            "message": "WIP statistics retrieved successfully",
            "stats": stats.dict(),
        }

    except Exception as e:
        logger.error(f"Error getting WIP stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve WIP statistics", error=str(e)
            ).dict(),
        )


@router.post("/activate-task")
async def activate_task(
    request: TaskActivationRequest, user_id: str = Depends(get_current_user)
):
    """Activate a task with WIP limit checking"""
    try:
        service = get_wip_limit_enforcement_service()

        # Check WIP limits
        result = await service.enforce_wip_limit(
            user_id=user_id,
            action=f"activate_task_{request.task_id}",
            force_override=request.force_override,
        )

        if not result.allowed:
            return {
                "success": False,
                "allowed": False,
                "reason": result.reason,
                "suggested_actions": result.suggested_actions,
            }

        # Start focus session for the task
        session = await service.start_focus_session(
            user_id=user_id, task_id=request.task_id
        )

        return {
            "success": True,
            "message": "Task activated successfully",
            "task_id": request.task_id,
            "session_id": session.id,
            "focus_started": True,
        }

    except Exception as e:
        logger.error(f"Error activating task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to activate task", error=str(e)
            ).dict(),
        )


@router.get("/active-session")
async def get_active_session(user_id: str = Depends(get_current_user)):
    """Get the currently active focus session"""
    try:
        service = get_wip_limit_enforcement_service()
        session = await service._get_active_focus_session(user_id)

        if session:
            return {"success": True, "active": True, "session": session.dict()}
        else:
            return {
                "success": True,
                "active": False,
                "message": "No active focus session",
            }

    except Exception as e:
        logger.error(f"Error getting active session: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to get active session", error=str(e)
            ).dict(),
        )
