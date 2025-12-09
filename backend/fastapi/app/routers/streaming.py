"""
Enhanced HTTP Streaming Router for AutoAdmin Backend
Provides comprehensive Server-Sent Events and long polling endpoints for real-time communication
Replaces WebSocket functionality with advanced HTTP streaming featuring client management and event filtering
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Header
from fastapi.responses import StreamingResponse
from fastapi import Request
from pydantic import BaseModel, Field, validator

from app.services.http_streaming import get_streaming_service, EventType
from app.services.long_polling import get_long_polling_service
from app.services.sse_event_manager import get_sse_event_manager, EventFilter, EventFilterType
from app.services.sse_client_manager import get_sse_client_manager, ClientType, ClientStatus
from app.responses.sse import (
    SSEResponse, SSEEvent, SSEEventType, SSEPriority,
    AgentEventStream, TaskEventStream, SystemEventStream, MetricsStream
)
from app.core.logging import get_logger
from app.middleware.error_handler import ValidationException

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/streaming", tags=["Streaming"])


# Enhanced Pydantic models
class StreamConnectionRequest(BaseModel):
    """Request to create streaming connection"""
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    event_types: Optional[List[str]] = Field(default=None, description="Event types to subscribe to")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Event filters")
    client_type: str = Field(default="web", description="Client type (web, mobile, api, agent)")
    priority_threshold: str = Field(default="low", description="Minimum event priority")
    max_events_per_minute: Optional[int] = Field(default=None, description="Rate limit for events")
    buffer_size: int = Field(default=1000, description="Event buffer size")
    include_metrics: bool = Field(default=False, description="Include metrics events")

    @validator('client_type')
    def validate_client_type(cls, v):
        if v not in [ct.value for ct in ClientType]:
            raise ValueError(f"Invalid client type. Must be one of: {[ct.value for ct in ClientType]}")
        return v

    @validator('priority_threshold')
    def validate_priority(cls, v):
        if v not in [p.value for p in SSEPriority]:
            raise ValueError(f"Invalid priority. Must be one of: {[p.value for p in SSEPriority]}")
        return v


class AgentSubscriptionRequest(BaseModel):
    """Request to create agent-specific subscription"""
    agent_id: str = Field(..., description="Agent ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    include_status: bool = Field(default=True, description="Include status updates")
    include_responses: bool = Field(default=True, description="Include agent responses")
    include_thinking: bool = Field(default=True, description="Include thinking events")
    max_events_per_minute: Optional[int] = Field(default=None, description="Rate limit")


class TaskSubscriptionRequest(BaseModel):
    """Request to create task-specific subscription"""
    task_id: str = Field(..., description="Task ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    agent_id: Optional[str] = Field(default=None, description="Agent ID filter")
    include_progress: bool = Field(default=True, description="Include progress updates")
    include_completion: bool = Field(default=True, description="Include completion events")
    include_errors: bool = Field(default=True, description="Include error events")
    progress_threshold: float = Field(default=0.01, description="Minimum progress change")


class SystemSubscriptionRequest(BaseModel):
    """Request to create system-level subscription"""
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    include_notifications: bool = Field(default=True, description="Include notifications")
    include_alerts: bool = Field(default=True, description="Include system alerts")
    include_health_checks: bool = Field(default=True, description="Include health checks")
    priority_threshold: str = Field(default="normal", description="Minimum event priority")
    health_check_interval: int = Field(default=60, description="Health check interval in seconds")

    @validator('priority_threshold')
    def validate_priority(cls, v):
        if v not in [p.value for p in SSEPriority]:
            raise ValueError(f"Invalid priority. Must be one of: {[p.value for p in SSEPriority]}")
        return v


class EventBroadcastRequest(BaseModel):
    """Request to broadcast an event"""
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    priority: str = Field(default="normal", description="Event priority")
    user_id: Optional[str] = Field(default=None, description="Target user ID")
    agent_id: Optional[str] = Field(default=None, description="Target agent ID")
    task_id: Optional[str] = Field(default=None, description="Target task ID")
    expires_at: Optional[datetime] = Field(default=None, description="Event expiration time")

    @validator('event_type')
    def validate_event_type(cls, v):
        if v not in [et.value for et in SSEEventType]:
            raise ValueError(f"Invalid event type. Must be one of: {[et.value for et in SSEEventType]}")
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v not in [p.value for p in SSEPriority]:
            raise ValueError(f"Invalid priority. Must be one of: {[p.value for p in SSEPriority]}")
        return v


class LongPollingRequest(BaseModel):
    """Request for long polling"""
    session_id: str = Field(..., description="Session ID")
    timeout: Optional[int] = Field(default=30, description="Poll timeout in seconds")
    max_events: int = Field(default=50, description="Maximum events to return")


class EventNotificationRequest(BaseModel):
    """Request to send notification"""
    message: str = Field(..., description="Notification message")
    level: str = Field(default="info", description="Notification level (info, warning, error)")
    user_id: Optional[str] = Field(default=None, description="Target user ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")


class AgentStatusUpdateRequest(BaseModel):
    """Request to update agent status"""
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="New status")
    user_id: Optional[str] = Field(default=None, description="User ID")
    additional_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional status data")


class TaskProgressRequest(BaseModel):
    """Request to update task progress"""
    task_id: str = Field(..., description="Task ID")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    message: Optional[str] = Field(default=None, description="Progress message")


@router.post("/connect", summary="Create Streaming Connection")
async def create_streaming_connection(
    request: StreamConnectionRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Create a new Server-Sent Events streaming connection

    Args:
        request: Streaming connection request
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Connection information
    """
    try:
        streaming_service = get_streaming_service()

        # Convert event type strings to enum
        event_types = None
        if request.event_types:
            event_types = []
            for et in request.event_types:
                try:
                    event_types.append(EventType(et))
                except ValueError:
                    raise ValidationException(
                        f"Invalid event type: {et}",
                        details={"valid_types": [e.value for e in EventType]}
                    )

        # Create connection
        client_id = await streaming_service.create_connection(
            user_id=request.user_id,
            session_id=request.session_id,
            event_types=event_types,
            filters=request.filters or {}
        )

        # Schedule connection cleanup
        async def cleanup_connection():
            await asyncio.sleep(3600)  # 1 hour timeout
            await streaming_service.remove_connection(client_id)

        background_tasks.add_task(cleanup_connection)

        return {
            "success": True,
            "client_id": client_id,
            "session_id": request.session_id,
            "endpoint": f"/api/v1/streaming/events/{client_id}",
            "message": "Connection created successfully",
            "event_types": [et.value for et in event_types] if event_types else None,
            "filters": request.filters,
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to create streaming connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to create streaming connection")


@router.get("/events/{client_id}", summary="Server-Sent Events Stream")
async def get_event_stream(
    client_id: str,
    request: Request,
    with_history: bool = Query(default=True, description="Include historical events"),
    history_count: int = Query(default=50, ge=1, le=200, description="Number of historical events")
) -> StreamingResponse:
    """
    Get Server-Sent Events stream for real-time updates

    Args:
        client_id: Client connection ID
        request: FastAPI request object
        with_history: Whether to include historical events
        history_count: Number of historical events to include

    Returns:
        StreamingResponse: SSE stream
    """
    try:
        streaming_service = get_streaming_service()

        # Verify connection exists
        if client_id not in streaming_service._connections:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Create streaming response
        return await streaming_service.create_streaming_response(
            client_id=client_id,
            with_history=with_history,
            history_count=history_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create event stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create event stream")


@router.post("/polling/session", summary="Create Long Polling Session")
async def create_polling_session(
    user_id: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    agent_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new long polling session

    Args:
        user_id: User ID
        event_types: Event types to subscribe to
        agent_id: Agent ID filter
        task_id: Task ID filter

    Returns:
        Dict: Session information
    """
    try:
        polling_service = get_long_polling_service()

        # Create filters
        filters = {}
        if event_types:
            filters["event_types"] = event_types
        if agent_id:
            filters["agent_id"] = agent_id
        if task_id:
            filters["task_id"] = task_id

        # Create session
        session_id = polling_service.create_session(
            user_id=user_id,
            filters=filters
        )

        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "filters": filters,
            "poll_endpoint": "/api/v1/streaming/poll",
            "message": "Long polling session created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create polling session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create polling session")


@router.post("/polling/poll", summary="Poll for Events")
async def poll_events(
    request: LongPollingRequest
) -> Dict[str, Any]:
    """
    Poll for events using long polling (HTTP-based replacement for WebSockets)

    Args:
        request: Polling request

    Returns:
        Dict: Polling response with events
    """
    try:
        polling_service = get_long_polling_service()

        # Poll for events
        result = await polling_service.poll_events(
            session_id=request.session_id,
            timeout=request.timeout,
            max_events=request.max_events
        )

        return result

    except Exception as e:
        logger.error(f"Failed to poll events: {e}")
        raise HTTPException(status_code=500, detail="Failed to poll events")


@router.delete("/polling/session/{session_id}", summary="Remove Polling Session")
async def remove_polling_session(
    session_id: str
) -> Dict[str, Any]:
    """
    Remove a long polling session

    Args:
        session_id: Session ID to remove

    Returns:
        Dict: Removal confirmation
    """
    try:
        polling_service = get_long_polling_service()
        polling_service.remove_session(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "message": "Polling session removed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to remove polling session: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove polling session")


@router.post("/events/notify", summary="Send System Notification")
async def send_notification(
    request: EventNotificationRequest
) -> Dict[str, Any]:
    """
    Send a system notification to subscribed clients

    Args:
        request: Notification request

    Returns:
        Dict: Notification result
    """
    try:
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        # Send via streaming service (SSE)
        await streaming_service.send_system_notification(
            message=request.message,
            level=request.level,
            user_id=request.user_id
        )

        # Send via polling service
        polling_service.add_notification_event(
            message=request.message,
            level=request.level,
            user_id=request.user_id,
            data=request.data
        )

        return {
            "success": True,
            "message": "Notification sent successfully",
            "event_data": {
                "message": request.message,
                "level": request.level,
                "user_id": request.user_id,
                "data": request.data
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")


@router.post("/events/agent-status", summary="Send Agent Status Update")
async def send_agent_status_update(
    request: AgentStatusUpdateRequest
) -> Dict[str, Any]:
    """
    Send agent status update event

    Args:
        request: Agent status update request

    Returns:
        Dict: Update result
    """
    try:
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        # Send via streaming service (SSE)
        await streaming_service.send_agent_status_update(
            agent_id=request.agent_id,
            status=request.status,
            user_id=request.user_id,
            additional_data=request.additional_data
        )

        # Send via polling service
        polling_service.add_agent_status_event(
            agent_id=request.agent_id,
            status=request.status,
            user_id=request.user_id,
            additional_data=request.additional_data
        )

        return {
            "success": True,
            "message": "Agent status update sent successfully",
            "agent_id": request.agent_id,
            "status": request.status,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to send agent status update: {e}")
        raise HTTPException(status_code=500, detail="Failed to send agent status update")


@router.post("/events/task-progress", summary="Send Task Progress Update")
async def send_task_progress(
    request: TaskProgressRequest
) -> Dict[str, Any]:
    """
    Send task progress update event

    Args:
        request: Task progress request

    Returns:
        Dict: Update result
    """
    try:
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        # Send via streaming service (SSE)
        await streaming_service.send_task_progress(
            task_id=request.task_id,
            progress=request.progress,
            agent_id=request.agent_id,
            user_id=request.user_id,
            message=request.message
        )

        # Send via polling service
        polling_service.add_task_progress_event(
            task_id=request.task_id,
            progress=request.progress,
            agent_id=request.agent_id,
            user_id=request.user_id,
            message=request.message
        )

        return {
            "success": True,
            "message": "Task progress update sent successfully",
            "task_id": request.task_id,
            "progress": request.progress,
            "agent_id": request.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to send task progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to send task progress")


@router.get("/status", summary="Get Streaming Service Status")
async def get_streaming_status() -> Dict[str, Any]:
    """
    Get status of streaming services

    Returns:
        Dict: Service status and statistics
    """
    try:
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        return {
            "streaming_service": await streaming_service.get_connection_stats(),
            "polling_service": polling_service.get_stats(),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy"
        }

    except Exception as e:
        logger.error(f"Failed to get streaming status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get streaming status")


# Enhanced SSE endpoints

@router.post("/events/connect", summary="Create Enhanced SSE Connection")
async def create_enhanced_sse_connection(
    request: StreamConnectionRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Create a new enhanced Server-Sent Events connection with comprehensive features

    Args:
        request: Enhanced streaming connection request
        http_request: FastAPI request object
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Enhanced connection information
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Create client connection
        client = await client_manager.create_client(
            request=http_request,
            user_id=request.user_id,
            client_type=ClientType(request.client_type),
            event_filters=request.filters
        )

        # Convert event type strings to enums
        event_types = None
        if request.event_types:
            event_types = []
            for et in request.event_types:
                try:
                    event_types.append(SSEEventType(et))
                except ValueError:
                    raise ValidationException(
                        f"Invalid event type: {et}",
                        details={"valid_types": [e.value for e in SSEEventType]}
                    )

        # Create event filters
        filters = []
        if request.filters:
            for filter_key, filter_value in request.filters.items():
                if filter_key == "user_id":
                    filters.append(EventFilter(
                        filter_type=EventFilterType.USER_ID,
                        value=filter_value
                    ))
                elif filter_key == "agent_id":
                    filters.append(EventFilter(
                        filter_type=EventFilterType.AGENT_ID,
                        value=filter_value
                    ))
                elif filter_key == "task_id":
                    filters.append(EventFilter(
                        filter_type=EventFilterType.TASK_ID,
                        value=filter_value
                    ))

        # Create subscription
        subscription_id = await event_manager.create_subscription(
            client_id=client.client_id,
            event_types=event_types,
            filters=filters,
            priority_threshold=SSEPriority(request.priority_threshold),
            max_events_per_minute=request.max_events_per_minute,
            buffer_size=request.buffer_size
        )

        # Add subscription to client
        client_manager.add_subscription(client.client_id, subscription_id)

        # Schedule cleanup
        async def cleanup_connection():
            await asyncio.sleep(3600)  # 1 hour timeout
            await client_manager.remove_client(client.client_id, "timeout")
            await event_manager.remove_subscription(subscription_id)

        background_tasks.add_task(cleanup_connection)

        return {
            "success": True,
            "client_id": client.client_id,
            "subscription_id": subscription_id,
            "session_id": client.session_id,
            "endpoint": f"/api/v1/streaming/events/{subscription_id}",
            "connection_id": client.connection_id,
            "message": "Enhanced SSE connection created successfully",
            "client_type": client.client_type.value,
            "event_types": [et.value for et in event_types] if event_types else None,
            "filters": request.filters,
            "priority_threshold": request.priority_threshold,
            "buffer_size": request.buffer_size,
            "include_metrics": request.include_metrics,
            "ping_interval": client.ping_interval,
            "timeout_seconds": client.timeout_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to create enhanced SSE connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to create enhanced SSE connection")


@router.get("/events/{subscription_id}", summary="Enhanced SSE Event Stream")
async def get_enhanced_event_stream(
    subscription_id: str,
    request: Request,
    last_event_id: Optional[str] = Query(default=None, description="Last event ID for resumption"),
    include_history: bool = Query(default=True, description="Include historical events"),
    history_count: int = Query(default=50, ge=1, le=200, description="Number of historical events"),
    user_agent: Optional[str] = Header(None)
) -> StreamingResponse:
    """
    Get enhanced Server-Sent Events stream for real-time updates

    Args:
        subscription_id: Subscription ID
        request: FastAPI request object
        last_event_id: Last event ID for resuming from history
        include_history: Whether to include historical events
        history_count: Number of historical events to include
        user_agent: Client user agent

    Returns:
        StreamingResponse: Enhanced SSE stream
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Verify subscription exists
        subscription_stats = event_manager.get_subscription_stats(subscription_id)
        if not subscription_stats:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Get client information
        client = client_manager.get_client(subscription_stats['client_id'])
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Update client activity
        client_manager.update_client_activity(client.client_id)

        # Create event generator
        event_generator = event_manager.create_event_generator(
            subscription_id=subscription_id,
            last_event_id=last_event_id
        )

        # Create streaming response with enhanced features
        return await client_manager.create_client_stream(
            client=client,
            event_generator=event_generator
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create enhanced event stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create enhanced event stream")


@router.post("/events/agents/subscribe", summary="Subscribe to Agent Events")
async def subscribe_to_agent_events(
    request: AgentSubscriptionRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Create subscription for agent-specific events

    Args:
        request: Agent subscription request
        http_request: FastAPI request object
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Agent subscription information
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Create client connection
        client = await client_manager.create_client(
            request=http_request,
            user_id=request.user_id,
            client_type=ClientType.AGENT
        )

        # Create agent subscription
        subscription_id = await event_manager.create_agent_subscription(
            client_id=client.client_id,
            agent_id=request.agent_id,
            include_status=request.include_status,
            include_responses=request.include_responses,
            include_thinking=request.include_thinking
        )

        # Add subscription to client
        client_manager.add_subscription(client.client_id, subscription_id)

        # Update subscription with rate limit
        if request.max_events_per_minute:
            subscription = event_manager._subscriptions.get(subscription_id)
            if subscription:
                subscription.max_events_per_minute = request.max_events_per_minute

        # Schedule cleanup
        async def cleanup_connection():
            await asyncio.sleep(3600)
            await client_manager.remove_client(client.client_id, "timeout")
            await event_manager.remove_subscription(subscription_id)

        background_tasks.add_task(cleanup_connection)

        return {
            "success": True,
            "client_id": client.client_id,
            "subscription_id": subscription_id,
            "agent_id": request.agent_id,
            "endpoint": f"/api/v1/streaming/events/{subscription_id}",
            "message": "Agent event subscription created successfully",
            "include_status": request.include_status,
            "include_responses": request.include_responses,
            "include_thinking": request.include_thinking,
            "max_events_per_minute": request.max_events_per_minute,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create agent subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create agent subscription")


@router.post("/events/tasks/subscribe", summary="Subscribe to Task Events")
async def subscribe_to_task_events(
    request: TaskSubscriptionRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Create subscription for task-specific events

    Args:
        request: Task subscription request
        http_request: FastAPI request object
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Task subscription information
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Create client connection
        client = await client_manager.create_client(
            request=http_request,
            user_id=request.user_id,
            client_type=ClientType.WEB
        )

        # Create task subscription
        subscription_id = await event_manager.create_task_subscription(
            client_id=client.client_id,
            task_id=request.task_id,
            agent_id=request.agent_id,
            include_progress=request.include_progress,
            include_completion=request.include_completion,
            include_errors=request.include_errors
        )

        # Add subscription to client
        client_manager.add_subscription(client.client_id, subscription_id)

        # Schedule cleanup
        async def cleanup_connection():
            await asyncio.sleep(3600)
            await client_manager.remove_client(client.client_id, "timeout")
            await event_manager.remove_subscription(subscription_id)

        background_tasks.add_task(cleanup_connection)

        return {
            "success": True,
            "client_id": client.client_id,
            "subscription_id": subscription_id,
            "task_id": request.task_id,
            "agent_id": request.agent_id,
            "endpoint": f"/api/v1/streaming/events/{subscription_id}",
            "message": "Task event subscription created successfully",
            "include_progress": request.include_progress,
            "include_completion": request.include_completion,
            "include_errors": request.include_errors,
            "progress_threshold": request.progress_threshold,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create task subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task subscription")


@router.post("/events/system/subscribe", summary="Subscribe to System Events")
async def subscribe_to_system_events(
    request: SystemSubscriptionRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Create subscription for system-level events

    Args:
        request: System subscription request
        http_request: FastAPI request object
        background_tasks: FastAPI background tasks

    Returns:
        Dict: System subscription information
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Create client connection
        client = await client_manager.create_client(
            request=http_request,
            user_id=request.user_id,
            client_type=ClientType.WEB
        )

        # Create system subscription
        subscription_id = await event_manager.create_system_subscription(
            client_id=client.client_id,
            user_id=request.user_id,
            include_notifications=request.include_notifications,
            include_alerts=request.include_alerts,
            priority_threshold=SSEPriority(request.priority_threshold)
        )

        # Add subscription to client
        client_manager.add_subscription(client.client_id, subscription_id)

        # Schedule cleanup
        async def cleanup_connection():
            await asyncio.sleep(3600)
            await client_manager.remove_client(client.client_id, "timeout")
            await event_manager.remove_subscription(subscription_id)

        background_tasks.add_task(cleanup_connection)

        return {
            "success": True,
            "client_id": client.client_id,
            "subscription_id": subscription_id,
            "endpoint": f"/api/v1/streaming/events/{subscription_id}",
            "message": "System event subscription created successfully",
            "include_notifications": request.include_notifications,
            "include_alerts": request.include_alerts,
            "include_health_checks": request.include_health_checks,
            "priority_threshold": request.priority_threshold,
            "health_check_interval": request.health_check_interval,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create system subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create system subscription")


@router.post("/events/broadcast", summary="Broadcast Event to Subscribers")
async def broadcast_event(request: EventBroadcastRequest) -> Dict[str, Any]:
    """
    Broadcast an event to all matching subscribers

    Args:
        request: Event broadcast request

    Returns:
        Dict: Broadcast result
    """
    try:
        event_manager = get_sse_event_manager()

        # Create SSE event
        event = SSEEvent(
            event_type=SSEEventType(request.event_type),
            data=request.data,
            priority=SSEPriority(request.priority),
            user_id=request.user_id,
            agent_id=request.agent_id,
            task_id=request.task_id,
            expires_at=request.expires_at
        )

        # Broadcast event
        recipients_count = await event_manager.broadcast_event(event)

        return {
            "success": True,
            "message": "Event broadcast successfully",
            "event_id": event.event_id,
            "event_type": request.event_type,
            "priority": request.priority,
            "recipients": recipients_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to broadcast event: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast event")


@router.get("/events/status", summary="Get SSE System Status")
async def get_sse_status() -> Dict[str, Any]:
    """
    Get comprehensive SSE system status

    Returns:
        Dict: System status and statistics
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        return {
            "client_manager": client_manager.get_system_stats(),
            "event_manager": event_manager.get_system_stats(),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy"
        }

    except Exception as e:
        logger.error(f"Failed to get SSE status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get SSE status")


@router.get("/events/clients/{client_id}", summary="Get Client Information")
async def get_client_info(client_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a client connection

    Args:
        client_id: Client ID

    Returns:
        Dict: Client information
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Get client information
        client = client_manager.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Get client metrics
        metrics = client_manager.get_client_metrics(client_id)

        # Get subscription information
        subscription_stats = []
        for subscription_id in client.subscription_ids:
            stats = event_manager.get_subscription_stats(subscription_id)
            if stats:
                subscription_stats.append(stats)

        return {
            "client": client.to_dict(),
            "metrics": metrics,
            "subscriptions": subscription_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get client info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get client info")


@router.delete("/events/clients/{client_id}", summary="Disconnect Client")
async def disconnect_client(client_id: str) -> Dict[str, Any]:
    """
    Disconnect a client connection

    Args:
        client_id: Client ID

    Returns:
        Dict: Disconnection result
    """
    try:
        client_manager = get_sse_client_manager()
        event_manager = get_sse_event_manager()

        # Get client information
        client = client_manager.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Remove client subscriptions
        subscription_count = await event_manager.remove_client_subscriptions(client_id)

        # Remove client
        success = await client_manager.remove_client(client_id, "api_request")

        return {
            "success": success,
            "client_id": client_id,
            "user_id": client.user_id,
            "subscriptions_removed": subscription_count,
            "message": "Client disconnected successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect client: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect client")


@router.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for streaming services

    Returns:
        Dict: Health status
    """
    try:
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        # Test basic functionality
        test_event_id = None
        try:
            test_event_id = streaming_service.send_event({
                "event_id": "health_check",
                "event_type": "health_check",
                "data": {"test": True},
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.warning(f"Streaming service health check failed: {e}")

        test_polling_event_id = None
        try:
            test_polling_event_id = polling_service.add_event(
                event_type="health_check",
                data={"test": True}
            )
        except Exception as e:
            logger.warning(f"Polling service health check failed: {e}")

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "streaming": {
                    "status": "healthy" if test_event_id else "degraded",
                    "connections": len(streaming_service._connections)
                },
                "polling": {
                    "status": "healthy" if test_polling_event_id else "degraded",
                    "sessions": len(polling_service._sessions),
                    "events": len(polling_service._events)
                }
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# WebSocket replacement endpoints for existing functionality

@router.post("/chat/stream/{agent_type}", summary="Chat with Agent (HTTP Streaming)")
async def chat_with_agent_streaming(
    agent_type: str,
    message_request: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Chat with agent using HTTP streaming (WebSocket replacement)

    Args:
        agent_type: Type of agent
        message_request: Chat message request
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Chat session information
    """
    try:
        if "message" not in message_request:
            raise ValidationException("Missing required field: message")

        streaming_service = get_streaming_service()
        user_id = message_request.get("user_id")
        session_id = message_request.get("session_id")

        # Create streaming connection for chat
        client_id = await streaming_service.create_connection(
            user_id=user_id,
            session_id=session_id,
            event_types=[EventType.CHAT_MESSAGE],
            filters={"agent_type": agent_type}
        )

        # Send initial message event
        await streaming_service.send_chat_message(
            message=message_request["message"],
            agent_id=agent_type,
            user_id=user_id or "anonymous",
            session_id=session_id or client_id,
            message_type="user_message"
        )

        # Schedule agent response in background
        async def process_agent_response():
            try:
                # Simulate agent processing
                await asyncio.sleep(1)

                # Send agent response
                response_message = f"Agent {agent_type} received your message: {message_request['message']}"
                await streaming_service.send_chat_message(
                    message=response_message,
                    agent_id=agent_type,
                    user_id=user_id or "anonymous",
                    session_id=session_id or client_id,
                    message_type="agent_response"
                )
            except Exception as e:
                logger.error(f"Error processing agent response: {e}")

        background_tasks.add_task(process_agent_response)

        return {
            "success": True,
            "session_id": session_id or client_id,
            "client_id": client_id,
            "agent_type": agent_type,
            "stream_endpoint": f"/api/v1/streaming/events/{client_id}",
            "message": "Chat session created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat streaming session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")