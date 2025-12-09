"""
HTTP-only notifications router for real-time updates without WebSockets
Provides polling and SSE-based alternatives to WebSocket notifications
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.middleware.error_handler import (
    AutoAdminException,
    ExternalServiceException,
    ValidationException,
    ErrorCodes
)
from app.responses.sse import SSEResponse, StreamingUtils, LongPollingResponse
from services.firebase_service import get_firebase_service

logger = get_logger(__name__)

router = APIRouter()

# In-memory notification storage (in production, use Redis or database)
_notification_queue = asyncio.Queue(maxsize=1000)
_subscriber_connections = {}
_notification_history = []


@router.get("/stream", summary="Stream Notifications via SSE")
async def stream_notifications_sse(
    request: Request,
    last_event_id: Optional[str] = Query(default=None, description="Last received event ID for recovery"),
    event_types: Optional[str] = Query(default=None, description="Comma-separated list of event types to receive")
) -> StreamingResponse:
    """
    Stream real-time notifications using Server-Sent Events (SSE)
    Replaces WebSocket notifications with HTTP streaming

    Args:
        request: HTTP request object
        last_event_id: Last received event ID for recovery
        event_types: Filter notifications by event types

    Returns:
        StreamingResponse: SSE stream for real-time notifications
    """
    try:
        # Parse event types filter
        event_type_filter = None
        if event_types:
            event_type_filter = set(event_type.split(','))

        client_ip = request.client.host
        connection_id = f"{client_ip}:{id(request)}"

        logger.info(
            "Notification stream established",
            extra={
                "connection_id": connection_id,
                "client_ip": client_ip,
                "last_event_id": last_event_id,
                "event_types": event_types,
            }
        )

        # Track this connection
        _subscriber_connections[connection_id] = {
            "client_ip": client_ip,
            "connected_at": datetime.utcnow(),
            "event_types": event_type_filter,
            "last_event_id": last_event_id
        }

        async def notification_generator():
            """Generate notifications for SSE streaming"""
            try:
                # Send initial connection event
                connection_event = {
                    "event_id": f"connect_{connection_id}_{int(datetime.utcnow().timestamp())}",
                    "type": "connection_established",
                    "message": "Connected to notification stream",
                    "connection_id": connection_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "client_info": {
                        "ip": client_ip,
                        "user_agent": request.headers.get("user-agent", "unknown"),
                        "last_event_id": last_event_id
                    }
                }

                yield connection_event

                # Replay missed events if last_event_id provided
                if last_event_id:
                    try:
                        # Extract timestamp from last_event_id if possible
                        if "_" in last_event_id:
                            _, timestamp_str = last_event_id.split("_", 1)
                            try:
                                last_timestamp = float(timestamp_str)
                                cutoff_time = datetime.fromtimestamp(last_timestamp)

                                # Send missed events from history
                                missed_events = [
                                    event for event in _notification_history
                                    if datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00')) > cutoff_time
                                ]

                                for event in missed_events:
                                    # Apply event type filter
                                    if event_type_filter and event.get("type") not in event_type_filter:
                                        continue
                                    yield event

                                logger.info(
                                    "Replayed missed events",
                                    extra={
                                        "connection_id": connection_id,
                                        "missed_count": len(missed_events),
                                        "last_event_id": last_event_id
                                    }
                                )
                            except (ValueError, TypeError):
                                logger.warning(
                                    "Invalid last_event_id format",
                                    extra={
                                        "last_event_id": last_event_id,
                                        "connection_id": connection_id
                                    }
                                )
                    except Exception as e:
                        logger.error(
                            f"Error replaying missed events: {e}",
                            extra={"connection_id": connection_id}
                        )

                # Stream real-time notifications
                while True:
                    try:
                        # Wait for notification with timeout
                        notification = await asyncio.wait_for(_notification_queue.get(), timeout=10.0)

                        # Apply event type filter
                        if event_type_filter and notification.get("type") not in event_type_filter:
                            continue

                        # Add streaming metadata
                        notification["streaming"] = {
                            "connection_id": connection_id,
                            "stream_timestamp": datetime.utcnow().isoformat()
                        }

                        yield notification

                    except asyncio.TimeoutError:
                        # Send periodic heartbeat
                        yield {
                            "event_id": f"heartbeat_{connection_id}_{int(datetime.utcnow().timestamp())}",
                            "type": "heartbeat",
                            "message": "Connection active",
                            "connection_id": connection_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }

            except asyncio.CancelledError:
                # Client disconnected
                logger.info(
                    "Notification stream disconnected",
                    extra={"connection_id": connection_id}
                )

                # Send disconnection event
                yield {
                    "event_id": f"disconnect_{connection_id}_{int(datetime.utcnow().timestamp())}",
                    "type": "connection_closed",
                    "message": "Client disconnected",
                    "connection_id": connection_id,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logger.error(
                    f"Notification stream error: {e}",
                    extra={
                        "connection_id": connection_id,
                        "error": str(e)
                    }
                )

                # Send error event
                yield {
                    "event_id": f"error_{connection_id}_{int(datetime.utcnow().timestamp())}",
                    "type": "stream_error",
                    "error": str(e),
                    "connection_id": connection_id,
                    "timestamp": datetime.utcnow().isoformat()
                }

            finally:
                # Clean up connection tracking
                if connection_id in _subscriber_connections:
                    del _subscriber_connections[connection_id]

        return SSEResponse.create_event_stream(
            notification_generator(),
            event_type="notification"
        )

    except Exception as e:
        logger.error(f"Failed to create notification stream: {e}")
        raise ExternalServiceException(
            service="NotificationStreaming",
            message=f"Failed to create notification stream: {str(e)}"
        )


@router.get("/poll", summary="Poll for Notifications")
async def poll_notifications(
    request: Request,
    last_seen: Optional[str] = Query(default=None, description="Last seen timestamp or event ID"),
    timeout: float = Query(default=30.0, description="Poll timeout in seconds"),
    event_types: Optional[str] = Query(default=None, description="Comma-separated list of event types"),
    max_events: int = Query(default=10, description="Maximum events to return")
) -> Dict[str, Any]:
    """
    Poll for notifications using long polling
    Efficient alternative to SSE for client-side notification polling

    Args:
        request: HTTP request object
        last_seen: Last seen timestamp or event ID
        timeout: Maximum time to wait for notifications
        event_types: Filter notifications by event types
        max_events: Maximum number of events to return

    Returns:
        Dict: Notification data or timeout indication
    """
    try:
        client_ip = request.client.host
        connection_id = f"{client_ip}_poll_{id(request)}"

        # Parse event types filter
        event_type_filter = None
        if event_types:
            event_type_filter = set(event_types.split(','))

        logger.info(
            "Notification poll started",
            extra={
                "connection_id": connection_id,
                "client_ip": client_ip,
                "last_seen": last_seen,
                "timeout": timeout,
                "event_types": event_types,
                "max_events": max_events
            }
        )

        # Get historical events if last_seen provided
        historical_events = []
        if last_seen:
            try:
                # Try to parse as timestamp
                if last_seen.replace('.', '').isdigit():
                    cutoff_time = datetime.fromtimestamp(float(last_seen))
                else:
                    # Try to parse as ISO datetime
                    cutoff_time = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))

                # Filter historical events
                for event in _notification_history:
                    event_time = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    if event_time > cutoff_time:
                        if event_type_filter and event.get("type") not in event_type_filter:
                            continue
                        historical_events.append(event)

                # Limit historical events
                historical_events = historical_events[-max_events:]

                logger.info(
                    "Found historical events",
                    extra={
                        "connection_id": connection_id,
                        "historical_count": len(historical_events),
                        "cutoff_time": cutoff_time.isoformat()
                    }
                )

            except (ValueError, TypeError) as e:
                logger.warning(
                    "Invalid last_seen format, fetching recent events",
                    extra={
                        "last_seen": last_seen,
                        "connection_id": connection_id,
                        "error": str(e)
                    }
                )
                # Get most recent events as fallback
                historical_events = _notification_history[-max_events:]

        async def notification_collector():
            """Collect new notifications for polling"""
            notifications = []
            start_time = datetime.utcnow()

            # If we have historical events, return them immediately
            if historical_events:
                return {
                    "status": "success",
                    "notifications": historical_events,
                    "count": len(historical_events),
                    "historical": True,
                    "elapsed": 0.0
                }

            # Collect new notifications
            while True:
                try:
                    # Check timeout
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed >= timeout:
                        return {
                            "status": "timeout",
                            "notifications": [],
                            "message": "No notifications within timeout period",
                            "elapsed": elapsed
                        }

                    # Try to get notification
                    try:
                        notification = await asyncio.wait_for(_notification_queue.get(), timeout=1.0)

                        # Apply event type filter
                        if event_type_filter and notification.get("type") not in event_type_filter:
                            continue

                        notifications.append(notification)

                        # Check if we have enough notifications
                        if len(notifications) >= max_events:
                            return {
                                "status": "success",
                                "notifications": notifications,
                                "count": len(notifications),
                                "historical": False,
                                "elapsed": elapsed
                            }

                    except asyncio.TimeoutError:
                        # Continue waiting
                        continue

                except Exception as e:
                    return {
                        "status": "error",
                        "error": str(e),
                        "notifications": notifications,
                        "elapsed": (datetime.utcnow() - start_time).total_seconds()
                    }

        # Use long polling for efficient notification collection
        result = await LongPollingResponse.create_long_polling_response(
            data_generator=notification_collector,
            timeout=timeout,
            check_interval=0.5
        )

        logger.info(
            "Notification poll completed",
            extra={
                "connection_id": connection_id,
                "status": result.get("status"),
                "notification_count": len(result.get("notifications", [])),
                "elapsed": result.get("elapsed")
            }
        )

        return {
            **result,
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to poll notifications: {e}")
        raise ExternalServiceException(
            service="NotificationPolling",
            message=f"Failed to poll notifications: {str(e)}"
        )


@router.post("/broadcast", summary="Broadcast Notification")
async def broadcast_notification(
    notification_data: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Broadcast a notification to all connected clients
    HTTP-based alternative to WebSocket broadcasting

    Args:
        notification_data: Notification content to broadcast
        background_tasks: FastAPI background tasks

    Returns:
        Dict: Broadcast status and notification details
    """
    try:
        # Validate notification data
        if "type" not in notification_data:
            raise ValidationException(
                "Missing required field: type",
                details={
                    "required_fields": ["type"],
                    "provided_fields": list(notification_data.keys())
                }
            )

        # Create notification object
        notification_id = f"notif_{int(datetime.utcnow().timestamp() * 1000)}_{len(_notification_history)}"
        notification = {
            "event_id": notification_id,
            "type": notification_data["type"],
            "message": notification_data.get("message", ""),
            "data": notification_data.get("data", {}),
            "timestamp": datetime.utcnow().isoformat(),
            "broadcast_info": {
                "broadcast_id": notification_id,
                "recipients": len(_subscriber_connections),
                "broadcast_timestamp": datetime.utcnow().isoformat()
            }
        }

        # Add to notification history
        _notification_history.append(notification)

        # Limit history size
        if len(_notification_history) > 1000:
            _notification_history = _notification_history[-1000:]

        # Queue notification for streaming
        try:
            await _notification_queue.put(notification)
        except asyncio.QueueFull:
            logger.warning(
                "Notification queue is full, dropping oldest notifications"
            )
            # Make space by removing some old notifications
            try:
                _notification_queue.get_nowait()
                await _notification_queue.put(notification)
            except asyncio.QueueEmpty:
                pass

        # Schedule background task for Firebase persistence
        background_tasks.add_task(persist_notification, notification)

        # Log broadcast
        logger.info(
            "Notification broadcasted",
            extra={
                "notification_id": notification_id,
                "type": notification["type"],
                "recipients": len(_subscriber_connections),
                "queue_size": _notification_queue.qsize(),
                "history_size": len(_notification_history)
            }
        )

        return {
            "success": True,
            "message": "Notification broadcasted successfully",
            "notification_id": notification_id,
            "recipients": len(_subscriber_connections),
            "timestamp": datetime.utcnow().isoformat()
        }

    except AutoAdminException:
        raise
    except Exception as e:
        logger.error(f"Failed to broadcast notification: {e}")
        raise ExternalServiceException(
            service="NotificationBroadcast",
            message=f"Failed to broadcast notification: {str(e)}"
        )


@router.get("/status", summary="Get Notification System Status")
async def get_notification_status() -> Dict[str, Any]:
    """
    Get current status of the notification system

    Returns:
        Dict: Notification system status and statistics
    """
    try:
        # Calculate statistics
        current_time = datetime.utcnow()
        active_connections = len(_subscriber_connections)

        # Calculate connection ages
        connection_ages = []
        if active_connections > 0:
            for connection_data in _subscriber_connections.values():
                age = (current_time - connection_data["connected_at"]).total_seconds()
                connection_ages.append(age)

        # Calculate notification distribution by type
        notification_types = {}
        recent_notifications = _notification_history[-100:]  # Last 100 notifications

        for notification in recent_notifications:
            notif_type = notification.get("type", "unknown")
            notification_types[notif_type] = notification_types.get(notif_type, 0) + 1

        status = {
            "system_status": "operational",
            "connections": {
                "active_connections": active_connections,
                "max_connections": 1000,  # Configurable limit
                "average_connection_age": sum(connection_ages) / len(connection_ages) if connection_ages else 0,
                "oldest_connection": max(connection_ages) if connection_ages else 0,
                "newest_connection": min(connection_ages) if connection_ages else 0
            },
            "notifications": {
                "queue_size": _notification_queue.qsize(),
                "max_queue_size": _notification_queue.maxsize,
                "history_size": len(_notification_history),
                "max_history_size": 1000,
                "recent_notification_types": notification_types
            },
            "statistics": {
                "total_notifications_broadcast": len(_notification_history),
                "notifications_per_minute": len(recent_notifications) / 10 if recent_notifications else 0,  # Rough estimate
                "average_notification_rate": len(_notification_history) / max(1, (current_time - _notification_history[0]["timestamp"] if _notification_history else current_time).total_seconds() / 60)
            },
            "timestamp": current_time.isoformat()
        }

        return status

    except Exception as e:
        logger.error(f"Failed to get notification status: {e}")
        raise ExternalServiceException(
            service="NotificationStatus",
            message=f"Failed to retrieve notification status: {str(e)}"
        )


# Helper functions
async def persist_notification(notification: Dict[str, Any]):
    """
    Persist notification to Firebase for durability and cross-instance sharing
    Background task for async notification persistence

    Args:
        notification: Notification object to persist
    """
    try:
        firebase_service = get_firebase_service()

        # Create webhook event for persistence
        webhook_data = {
            "source": "notification_system",
            "event": notification["type"],
            "payload": notification,
            "user_id": None,  # System notification
            "agent_id": notification["data"].get("agent_id"),
            "content": notification.get("message"),
            "type": notification["type"],
            "metadata": {
                "event_id": notification["event_id"],
                "broadcast_info": notification["broadcast_info"]
            }
        }

        await firebase_service.create_webhook_event(webhook_data)

        logger.debug(
            "Notification persisted to Firebase",
            extra={"event_id": notification["event_id"]}
        )

    except Exception as e:
        logger.error(
            f"Failed to persist notification {notification.get('event_id')}: {e}"
        )
        # Continue without persistence - notification is already delivered


# Cleanup functions for graceful shutdown
async def cleanup_notification_connections():
    """Clean up all notification connections"""
    global _subscriber_connections, _notification_queue

    connection_count = len(_subscriber_connections)
    _subscriber_connections.clear()

    # Clear queue
    while not _notification_queue.empty():
        try:
            _notification_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    logger.info(f"Cleaned up {connection_count} notification connections")


# Add cleanup to lifespan management
def register_notification_cleanup(app):
    """Register notification cleanup for application lifespan"""
    @app.on_event("shutdown")
    async def shutdown_event():
        await cleanup_notification_connections()