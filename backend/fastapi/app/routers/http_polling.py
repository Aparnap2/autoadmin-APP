"""
HTTP Polling Router for AutoAdmin Backend
Comprehensive HTTP polling endpoints for real-time communication
Provides reliable fallback when Server-Sent Events (SSE) are not available
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi import Request
from pydantic import BaseModel, Field

from app.services.http_polling import (
    get_http_polling_service,
    HTTPPollingService,
    PollingInterval,
    ConnectionStatus,
    EventPriority,
    ErrorType,
    PollingSession
)
from app.core.logging import get_logger
from app.middleware.error_handler import ValidationException

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/polling", tags=["HTTP Polling"])

# Pydantic models
class CreatePollingSessionRequest(BaseModel):
    """Request to create HTTP polling session"""
    user_id: Optional[str] = Field(default=None, description="User ID")
    interval: Optional[str] = Field(default="NORMAL", description="Polling interval (VERY_FAST, FAST, NORMAL, SLOW, VERY_SLOW)")
    event_types: Optional[List[str]] = Field(default=None, description="Event types to subscribe to")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Event filters")
    max_buffer_size: Optional[int] = Field(default=1000, ge=10, le=10000, description="Maximum buffer size")


class UpdatePollingSessionRequest(BaseModel):
    """Request to update HTTP polling session"""
    interval: Optional[str] = Field(default=None, description="New polling interval")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Updated event filters")


class PollingRequest(BaseModel):
    """Request for HTTP polling"""
    session_id: str = Field(..., description="Session ID")
    timeout: Optional[int] = Field(default=30, ge=1, le=300, description="Poll timeout in seconds")
    max_events: int = Field(default=50, ge=1, le=200, description="Maximum events to return")
    include_metrics: bool = Field(default=True, description="Include session metrics")


class AddEventRequest(BaseModel):
    """Request to add event to polling system"""
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    priority: Optional[str] = Field(default="MEDIUM", description="Event priority (LOW, MEDIUM, HIGH, CRITICAL, URGENT)")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    task_id: Optional[str] = Field(default=None, description="Task ID")
    expires_in: Optional[int] = Field(default=None, ge=60, le=86400, description="Expiration time in seconds")


class AgentStatusEventRequest(BaseModel):
    """Request to add agent status event"""
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="Agent status")
    user_id: Optional[str] = Field(default=None, description="User ID")
    additional_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional status data")
    priority: Optional[str] = Field(default="MEDIUM", description="Event priority")


class TaskProgressEventRequest(BaseModel):
    """Request to add task progress event"""
    task_id: str = Field(..., description="Task ID")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    message: Optional[str] = Field(default=None, description="Progress message")
    priority: Optional[str] = Field(default="MEDIUM", description="Event priority")


class TaskCompletedEventRequest(BaseModel):
    """Request to add task completed event"""
    task_id: str = Field(..., description="Task ID")
    result: Dict[str, Any] = Field(..., description="Task result")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    priority: Optional[str] = Field(default="HIGH", description="Event priority")


class SystemNotificationEventRequest(BaseModel):
    """Request to add system notification event"""
    message: str = Field(..., description="Notification message")
    level: str = Field(default="info", description="Notification level")
    user_id: Optional[str] = Field(default=None, description="User ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional notification data")
    priority: Optional[str] = Field(default="LOW", description="Event priority")


class ErrorEventRequest(BaseModel):
    """Request to add error event"""
    error: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(default="UNKNOWN_ERROR", description="Error type")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    task_id: Optional[str] = Field(default=None, description="Task ID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Error context")
    priority: Optional[str] = Field(default="HIGH", description="Event priority")


# Helper functions

def parse_interval(interval_str: str) -> PollingInterval:
    """Parse interval string to enum"""
    try:
        return PollingInterval[interval_str.upper()]
    except (AttributeError, KeyError):
        raise ValidationException(
            f"Invalid polling interval: {interval_str}",
            details={"valid_intervals": [i.name for i in PollingInterval]}
        )


def parse_priority(priority_str: str) -> EventPriority:
    """Parse priority string to enum"""
    try:
        return EventPriority[priority_str.upper()]
    except (AttributeError, KeyError):
        raise ValidationException(
            f"Invalid event priority: {priority_str}",
            details={"valid_priorities": [p.name for p in EventPriority]}
        )


def parse_error_type(error_type_str: str) -> ErrorType:
    """Parse error type string to enum"""
    try:
        return ErrorType[error_type_str.upper()]
    except (AttributeError, KeyError):
        raise ValidationException(
            f"Invalid error type: {error_type_str}",
            details={"valid_error_types": [e.name for e in ErrorType]}
        )


# HTTP Polling endpoints

@router.post("/session", summary="Create HTTP Polling Session")
async def create_polling_session(
    request: CreatePollingSessionRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Create a new HTTP polling session for real-time communication

    Args:
        request: Polling session creation request
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Session information
    """
    try:
        polling_service = get_http_polling_service()

        # Parse interval
        interval = parse_interval(request.interval)

        # Create session
        session_id = polling_service.create_session(
            user_id=request.user_id,
            interval=interval,
            filters=request.filters or {},
            max_buffer_size=request.max_buffer_size
        )

        # Send welcome event
        polling_service.add_system_notification_event(
            message="HTTP polling session created successfully",
            level="info",
            user_id=request.user_id,
            priority=EventPriority.MEDIUM
        )

        # Schedule session cleanup
        async def cleanup_session():
            await asyncio.sleep(1800)  # 30 minutes timeout
            await polling_service.update_session(
                session_id=session_id,
                filters={"status": "expired"}
            )

        background_tasks.add_task(cleanup_session)

        return {
            "success": True,
            "session_id": session_id,
            "user_id": request.user_id,
            "interval": interval.name,
            "effective_interval": polling_service._sessions[session_id].get_effective_interval(),
            "filters": request.filters,
            "max_buffer_size": request.max_buffer_size,
            "poll_endpoint": "/api/v1/polling/poll",
            "message": "HTTP polling session created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to create polling session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create polling session")


@router.put("/session/{session_id}", summary="Update HTTP Polling Session")
async def update_polling_session(
    session_id: str,
    request: UpdatePollingSessionRequest
) -> Dict[str, Any]:
    """
    Update an existing HTTP polling session

    Args:
        session_id: Session ID to update
        request: Update request

    Returns:
        Dict: Update result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse interval if provided
        interval = None
        if request.interval:
            interval = parse_interval(request.interval)

        # Update session
        success = await polling_service.update_session(
            session_id=session_id,
            interval=interval,
            filters=request.filters
        )

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get updated session info
        session_info = polling_service.get_session_info(session_id)
        effective_interval = session_info.get("effective_interval", 0) if session_info else 0

        return {
            "success": True,
            "session_id": session_id,
            "updated_fields": {
                "interval": interval.name if interval else None,
                "effective_interval": effective_interval,
                "filters": request.filters
            },
            "message": "Polling session updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to update polling session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update polling session")


@router.delete("/session/{session_id}", summary="Remove HTTP Polling Session")
async def remove_polling_session(
    session_id: str
) -> Dict[str, Any]:
    """
    Remove an HTTP polling session

    Args:
        session_id: Session ID to remove

    Returns:
        Dict: Removal result
    """
    try:
        polling_service = get_http_polling_service()

        # Get session info before removal
        session_info = polling_service.get_session_info(session_id)

        # Remove session
        polling_service.remove_session(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "session_info": session_info,
            "message": "Polling session removed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to remove polling session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove polling session")


@router.post("/poll", summary="Poll for Events")
async def poll_events(
    request: PollingRequest
) -> Dict[str, Any]:
    """
    Poll for events using HTTP long polling

    Args:
        request: Polling request

    Returns:
        Dict: Polling response with events and metadata
    """
    try:
        polling_service = get_http_polling_service()

        # Poll for events
        result = await polling_service.poll_events(
            session_id=request.session_id,
            timeout=request.timeout,
            max_events=request.max_events,
            include_metrics=request.include_metrics
        )

        return result

    except Exception as e:
        logger.error(f"Failed to poll events: {e}")
        raise HTTPException(status_code=500, detail="Failed to poll events")


@router.post("/events", summary="Add Event")
async def add_event(
    request: AddEventRequest
) -> Dict[str, Any]:
    """
    Add a new event to the HTTP polling system

    Args:
        request: Event creation request

    Returns:
        Dict: Event creation result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse priority
        priority = parse_priority(request.priority)

        # Add event
        event_id = polling_service.add_event(
            event_type=request.event_type,
            data=request.data,
            priority=priority,
            user_id=request.user_id,
            session_id=request.session_id,
            agent_id=request.agent_id,
            task_id=request.task_id,
            expires_in=request.expires_in
        )

        return {
            "success": True,
            "event_id": event_id,
            "event_type": request.event_type,
            "priority": priority.name,
            "message": "Event added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to add event: {e}")
        raise HTTPException(status_code=500, detail="Failed to add event")


@router.post("/events/agent-status", summary="Add Agent Status Event")
async def add_agent_status_event(
    request: AgentStatusEventRequest
) -> Dict[str, Any]:
    """
    Add agent status update event

    Args:
        request: Agent status event request

    Returns:
        Dict: Event creation result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse priority
        priority = parse_priority(request.priority)

        # Add agent status event
        event_id = polling_service.add_agent_status_event(
            agent_id=request.agent_id,
            status=request.status,
            user_id=request.user_id,
            additional_data=request.additional_data,
            priority=priority
        )

        return {
            "success": True,
            "event_id": event_id,
            "agent_id": request.agent_id,
            "status": request.status,
            "priority": priority.name,
            "message": "Agent status event added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to add agent status event: {e}")
        raise HTTPException(status_code=500, detail="Failed to add agent status event")


@router.post("/events/task-progress", summary="Add Task Progress Event")
async def add_task_progress_event(
    request: TaskProgressEventRequest
) -> Dict[str, Any]:
    """
    Add task progress update event

    Args:
        request: Task progress event request

    Returns:
        Dict: Event creation result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse priority
        priority = parse_priority(request.priority)

        # Add task progress event
        event_id = polling_service.add_task_progress_event(
            task_id=request.task_id,
            progress=request.progress,
            agent_id=request.agent_id,
            user_id=request.user_id,
            message=request.message,
            priority=priority
        )

        return {
            "success": True,
            "event_id": event_id,
            "task_id": request.task_id,
            "progress": request.progress,
            "priority": priority.name,
            "message": "Task progress event added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to add task progress event: {e}")
        raise HTTPException(status_code=500, detail="Failed to add task progress event")


@router.post("/events/task-completed", summary="Add Task Completed Event")
async def add_task_completed_event(
    request: TaskCompletedEventRequest
) -> Dict[str, Any]:
    """
    Add task completed event

    Args:
        request: Task completed event request

    Returns:
        Dict: Event creation result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse priority
        priority = parse_priority(request.priority)

        # Add task completed event
        event_id = polling_service.add_task_completed_event(
            task_id=request.task_id,
            result=request.result,
            agent_id=request.agent_id,
            user_id=request.user_id,
            priority=priority
        )

        return {
            "success": True,
            "event_id": event_id,
            "task_id": request.task_id,
            "priority": priority.name,
            "message": "Task completed event added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to add task completed event: {e}")
        raise HTTPException(status_code=500, detail="Failed to add task completed event")


@router.post("/events/system-notification", summary="Add System Notification Event")
async def add_system_notification_event(
    request: SystemNotificationEventRequest
) -> Dict[str, Any]:
    """
    Add system notification event

    Args:
        request: System notification event request

    Returns:
        Dict: Event creation result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse priority
        priority = parse_priority(request.priority)

        # Add system notification event
        event_id = polling_service.add_system_notification_event(
            message=request.message,
            level=request.level,
            user_id=request.user_id,
            priority=priority
        )

        return {
            "success": True,
            "event_id": event_id,
            "message": request.message,
            "level": request.level,
            "priority": priority.name,
            "message": "System notification event added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to add system notification event: {e}")
        raise HTTPException(status_code=500, detail="Failed to add system notification event")


@router.post("/events/error", summary="Add Error Event")
async def add_error_event(
    request: ErrorEventRequest
) -> Dict[str, Any]:
    """
    Add error event

    Args:
        request: Error event request

    Returns:
        Dict: Event creation result
    """
    try:
        polling_service = get_http_polling_service()

        # Parse priority and error type
        priority = parse_priority(request.priority)
        error_type = parse_error_type(request.error_type)

        # Add error event
        event_id = polling_service.add_error_event(
            error=request.error,
            error_type=error_type,
            user_id=request.user_id,
            session_id=request.session_id,
            agent_id=request.agent_id,
            task_id=request.task_id,
            context=request.context,
            priority=priority
        )

        return {
            "success": True,
            "event_id": event_id,
            "error": request.error,
            "error_type": error_type.name,
            "priority": priority.name,
            "message": "Error event added successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to add error event: {e}")
        raise HTTPException(status_code=500, detail="Failed to add error event")


@router.get("/session/{session_id}", summary="Get Session Information")
async def get_session_info(
    session_id: str
) -> Dict[str, Any]:
    """
    Get detailed information about a polling session

    Args:
        session_id: Session ID

    Returns:
        Dict: Session information
    """
    try:
        polling_service = get_http_polling_service()

        # Get session info
        session_info = polling_service.get_session_info(session_id)

        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "success": True,
            "session": session_info,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session info")


@router.get("/status", summary="Get HTTP Polling Service Status")
async def get_polling_service_status() -> Dict[str, Any]:
    """
    Get status and statistics for HTTP polling service

    Returns:
        Dict: Service status and metrics
    """
    try:
        polling_service = get_http_polling_service()

        # Get service metrics
        service_metrics = polling_service.get_service_metrics()
        performance_metrics = polling_service.get_performance_metrics()
        error_metrics = polling_service.get_error_metrics()

        return {
            "success": True,
            "service": service_metrics,
            "performance": performance_metrics,
            "errors": error_metrics,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get polling service status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get polling service status")


@router.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for HTTP polling service

    Returns:
        Dict: Health status
    """
    try:
        polling_service = get_http_polling_service()

        # Test basic functionality
        test_event_id = None
        try:
            test_event_id = polling_service.add_event(
                event_type="health_check",
                data={"test": True},
                priority=EventPriority.LOW,
                expires_in=60  # 1 minute
            )
        except Exception as e:
            logger.warning(f"HTTP polling health check failed: {e}")

        # Get service stats
        service_metrics = polling_service.get_service_metrics()

        return {
            "status": "healthy" if test_event_id else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "http_polling",
            "test_event_id": test_event_id,
            "metrics": service_metrics,
            "endpoints": [
                "/api/v1/polling/session",
                "/api/v1/polling/poll",
                "/api/v1/polling/events",
                "/api/v1/polling/status",
                "/api/v1/polling/health"
            ]
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/metrics", summary="Get Service Metrics")
async def get_service_metrics(
    include_sessions: bool = Query(default=False, description="Include individual session data")
) -> Dict[str, Any]:
    """
    Get comprehensive service metrics

    Args:
        include_sessions: Whether to include individual session data

    Returns:
        Dict: Service metrics
    """
    try:
        polling_service = get_http_polling_service()

        # Get service metrics
        service_metrics = polling_service.get_service_metrics()
        performance_metrics = polling_service.get_performance_metrics()
        error_metrics = polling_service.get_error_metrics()

        response = {
            "success": True,
            "service": service_metrics,
            "performance": performance_metrics,
            "errors": error_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Include session data if requested
        if include_sessions:
            sessions = {}
            for session_id in service_metrics.get("total_sessions", {}):
                session_info = polling_service.get_session_info(session_id)
                if session_info:
                    sessions[session_id] = session_info
            response["sessions"] = sessions

        return response

    except Exception as e:
        logger.error(f"Failed to get service metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service metrics")


# Agent-specific endpoints for compatibility

@router.post("/agent/{agent_id}/poll", summary="Agent Polling Endpoint")
async def agent_poll(
    agent_id: str,
    timeout: Optional[int] = Query(default=30, ge=1, le=300),
    max_events: int = Query(default=50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Agent-specific polling endpoint for compatibility with existing agent orchestrator

    Args:
        agent_id: Agent ID
        timeout: Poll timeout in seconds
        max_events: Maximum events to return

    Returns:
        Dict: Polling response
    """
    try:
        from ..services.agent_orchestrator_http import get_http_agent_orchestrator

        agent_orchestrator = get_http_agent_orchestrator()

        # Use agent orchestrator's poll method
        response = await agent_orchestrator.agent_poll(
            agent_id=agent_id,
            timeout=timeout,
            max_events=max_events
        )

        return response

    except Exception as e:
        logger.error(f"Failed to handle agent poll for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle agent poll")


@router.post("/agent/{agent_id}/heartbeat", summary="Agent Heartbeat")
async def agent_heartbeat(
    agent_id: str,
    heartbeat_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Agent heartbeat endpoint for maintaining connection health

    Args:
        agent_id: Agent ID
        heartbeat_data: Optional heartbeat data

    Returns:
        Dict: Heartbeat response
    """
    try:
        polling_service = get_http_polling_service()

        # Add heartbeat event
        event_id = polling_service.add_event(
            event_type="agent_heartbeat",
            data={
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(heartbeat_data or {})
            },
            priority=EventPriority.LOW,
            agent_id=agent_id
        )

        return {
            "success": True,
            "event_id": event_id,
            "agent_id": agent_id,
            "message": "Heartbeat received",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to handle agent heartbeat for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle agent heartbeat")


# Cleanup endpoint for maintenance

@router.post("/cleanup", summary="Cleanup Expired Sessions and Events")
async def cleanup_service(
    force: bool = Query(default=False, description="Force cleanup of all expired items")
) -> Dict[str, Any]:
    """
    Cleanup expired sessions and events (maintenance endpoint)

    Args:
        force: Force cleanup of all expired items

    Returns:
        Dict: Cleanup results
    """
    try:
        polling_service = get_http_polling_service()

        # Perform cleanup
        await polling_service.cleanup_inactive_sessions()

        # Get metrics before and after
        before_metrics = polling_service.get_service_metrics()

        return {
            "success": True,
            "message": "Cleanup completed successfully",
            "force": force,
            "metrics_after": polling_service.get_service_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to cleanup service: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup service")


export default router