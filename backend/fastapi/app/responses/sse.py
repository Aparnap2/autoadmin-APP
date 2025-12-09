"""
Server-Sent Events (SSE) response utilities for HTTP-only real-time communication
Provides comprehensive streaming capabilities as WebSocket replacement
Enhanced with advanced client management, event filtering, and production features
"""

import json
import asyncio
import uuid
import time
from typing import Any, Dict, AsyncGenerator, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from fastapi.responses import StreamingResponse
from fastapi import HTTPException, Request
import logging

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    EventSourceResponse = None

logger = logging.getLogger(__name__)


class SSEPriority(Enum):
    """Event priority levels for SSE"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SSEEventType(Enum):
    """Comprehensive SSE event types"""
    AGENT_STATUS_UPDATE = "agent_status_update"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    SYSTEM_NOTIFICATION = "system_notification"
    SYSTEM_ALERT = "system_alert"
    CHAT_MESSAGE = "chat_message"
    CHAT_TYPING = "chat_typing"
    HEALTH_CHECK = "health_check"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    CONNECTION_STATUS = "connection_status"
    USER_ACTIVITY = "user_activity"
    METRICS_UPDATE = "metrics_update"
    FILE_UPLOAD_PROGRESS = "file_upload_progress"
    AGENT_RESPONSE = "agent_response"
    AGENT_THINKING = "agent_thinking"
    WORKFLOW_UPDATE = "workflow_update"
    BATCH_OPERATION = "batch_operation"


@dataclass
class SSEEvent:
    """Comprehensive SSE event structure"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: SSEEventType = SSEEventType.SYSTEM_NOTIFICATION
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: SSEPriority = SSEPriority.NORMAL
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    connection_id: Optional[str] = None
    retry: Optional[int] = None
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "connection_id": self.connection_id,
            "retry": self.retry,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    def is_expired(self) -> bool:
        """Check if event has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class SSEResponse:
    """
    Enhanced Server-Sent Events response handler for real-time updates
    Replaces WebSocket functionality with advanced HTTP streaming
    """

    @staticmethod
    def create_event_stream(
        generator: AsyncGenerator[SSEEvent, None],
        default_retry: int = 3000,
        ping_interval: int = 15,
        max_duration: Optional[int] = None,
        include_metrics: bool = False
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """
        Create an enhanced SSE event stream with comprehensive features

        Args:
            generator: Async generator yielding SSEEvent objects
            default_retry: Default reconnection interval in milliseconds
            ping_interval: Interval for ping messages in seconds
            max_duration: Maximum duration in seconds (None for unlimited)
            include_metrics: Whether to include periodic metrics events

        Returns:
            EventSourceResponse or StreamingResponse configured for streaming
        """
        async def event_generator():
            """Enhanced internal generator with comprehensive features"""
            start_time = time.time()
            last_ping = time.time()
            last_metrics = time.time()
            event_count = 0

            try:
                # Send initial connection event
                yield {
                    "event": SSEEventType.CONNECTION_STATUS.value,
                    "data": json.dumps({
                        "status": "connected",
                        "message": "SSE stream established",
                        "timestamp": datetime.utcnow().isoformat(),
                        "ping_interval": ping_interval,
                        "retry": default_retry
                    }),
                    "id": f"conn_{int(start_time)}",
                    "retry": default_retry
                }

                async for sse_event in generator:
                    # Check duration limit
                    if max_duration and (time.time() - start_time) >= max_duration:
                        yield {
                            "event": SSEEventType.CONNECTION_STATUS.value,
                            "data": json.dumps({
                                "status": "timeout",
                                "message": "Stream duration limit reached",
                                "duration": time.time() - start_time,
                                "events_sent": event_count,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        }
                        break

                    # Skip expired events
                    if sse_event.is_expired():
                        continue

                    # Send ping if needed
                    current_time = time.time()
                    if current_time - last_ping >= ping_interval:
                        yield {
                            "event": SSEEventType.HEARTBEAT.value,
                            "data": json.dumps({
                                "ping": True,
                                "uptime": current_time - start_time,
                                "events_sent": event_count,
                                "timestamp": datetime.utcnow().isoformat()
                            }),
                            "id": f"ping_{int(current_time)}"
                        }
                        last_ping = current_time

                    # Send metrics if enabled
                    if include_metrics and current_time - last_metrics >= 60:  # Every minute
                        yield {
                            "event": SSEEventType.METRICS_UPDATE.value,
                            "data": json.dumps({
                                "uptime": current_time - start_time,
                                "events_sent": event_count,
                                "avg_event_rate": event_count / (current_time - start_time) if current_time > start_time else 0,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        }
                        last_metrics = current_time

                    # Format and send the event
                    event_data = sse_event.to_dict()
                    event_id = sse_event.event_id
                    retry = sse_event.retry or default_retry

                    yield {
                        "event": sse_event.event_type.value,
                        "data": json.dumps(event_data),
                        "id": event_id,
                        "retry": retry
                    }

                    event_count += 1

            except Exception as e:
                # Send comprehensive error event
                logger.error(f"SSE stream error: {e}")
                yield {
                    "event": SSEEventType.ERROR.value,
                    "data": json.dumps({
                        "error": str(e),
                        "type": "stream_error",
                        "events_sent": event_count,
                        "uptime": time.time() - start_time,
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    "retry": 5000  # Longer retry for errors
                }

            finally:
                # Send disconnection event
                yield {
                    "event": SSEEventType.CONNECTION_STATUS.value,
                    "data": json.dumps({
                        "status": "disconnected",
                        "message": "SSE stream closed",
                        "total_events": event_count,
                        "uptime": time.time() - start_time,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }

        # Use EventSourceResponse if available, otherwise fallback to StreamingResponse
        if EventSourceResponse:
            return EventSourceResponse(event_generator())
        else:
            # Fallback implementation using standard StreamingResponse
            async def format_sse_events():
                """Format events as standard SSE text"""
                async for event_dict in event_generator():
                    # Format according to SSE specification
                    lines = []
                    if 'id' in event_dict:
                        lines.append(f"id: {event_dict['id']}")
                    if 'event' in event_dict:
                        lines.append(f"event: {event_dict['event']}")
                    if 'data' in event_dict:
                        lines.append(f"data: {event_dict['data']}")
                    if 'retry' in event_dict:
                        lines.append(f"retry: {event_dict['retry']}")
                    lines.append("")  # Empty line
                    lines.append("\n")
                    yield "\n".join(lines)

            return StreamingResponse(
                format_sse_events(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control, Last-Event-ID"
                }
            )

    @staticmethod
    def create_agent_status_stream(
        agent_id: str,
        status_generator: AsyncGenerator[Dict[str, Any], None],
        include_heartbeat: bool = True,
        heartbeat_interval: int = 30
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create enhanced agent status specific SSE stream"""
        async def agent_event_generator():
            try:
                # Send initial connection event
                yield SSEEvent(
                    event_type=SSEEventType.AGENT_STATUS_UPDATE,
                    data={
                        "agent_id": agent_id,
                        "status": "connected",
                        "message": "Agent stream established"
                    },
                    priority=SSEPriority.HIGH,
                    agent_id=agent_id
                )

                last_heartbeat = time.time()

                async for status_update in status_generator:
                    current_time = time.time()

                    # Send periodic heartbeat if enabled
                    if include_heartbeat and (current_time - last_heartbeat) >= heartbeat_interval:
                        yield SSEEvent(
                            event_type=SSEEventType.HEARTBEAT,
                            data={
                                "agent_id": agent_id,
                                "status": "alive",
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            agent_id=agent_id
                        )
                        last_heartbeat = current_time

                    # Determine event type based on status
                    if status_update.get("status") == "thinking":
                        event_type = SSEEventType.AGENT_THINKING
                    elif status_update.get("status") in ["completed", "failed", "success"]:
                        event_type = SSEEventType.AGENT_RESPONSE
                    else:
                        event_type = SSEEventType.AGENT_STATUS_UPDATE

                    # Determine priority based on status
                    priority = SSEPriority.NORMAL
                    if status_update.get("status") in ["error", "failed", "critical"]:
                        priority = SSEPriority.CRITICAL
                    elif status_update.get("status") in ["thinking", "processing"]:
                        priority = SSEPriority.HIGH

                    yield SSEEvent(
                        event_type=event_type,
                        data={
                            "agent_id": agent_id,
                            **status_update
                        },
                        priority=priority,
                        agent_id=agent_id
                    )

            except Exception as e:
                logger.error(f"Agent stream error for {agent_id}: {e}")
                yield SSEEvent(
                    event_type=SSEEventType.ERROR,
                    data={
                        "agent_id": agent_id,
                        "error": str(e),
                        "message": "Agent stream encountered an error"
                    },
                    priority=SSEPriority.CRITICAL,
                    agent_id=agent_id
                )

        return SSEResponse.create_event_stream(
            agent_event_generator(),
            default_retry=2000,
            ping_interval=heartbeat_interval,
            include_metrics=True
        )

    @staticmethod
    def create_task_progress_stream(
        task_id: str,
        progress_generator: AsyncGenerator[Dict[str, Any], None],
        agent_id: Optional[str] = None,
        include_milestones: bool = True
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create enhanced task progress specific SSE stream"""
        async def task_event_generator():
            try:
                # Send initial task event
                yield SSEEvent(
                    event_type=SSEEventType.TASK_PROGRESS,
                    data={
                        "task_id": task_id,
                        "status": "streaming_started",
                        "progress": 0.0,
                        "message": "Task progress stream established"
                    },
                    priority=SSEPriority.NORMAL,
                    task_id=task_id,
                    agent_id=agent_id
                )

                last_progress = 0.0
                milestone_sent = set()

                async for progress_update in progress_generator:
                    progress = progress_update.get("progress", 0.0)

                    # Create milestone events if enabled
                    if include_milestones:
                        milestones = [0.25, 0.5, 0.75, 0.9]
                        for milestone in milestones:
                            if progress >= milestone and milestone not in milestone_sent:
                                yield SSEEvent(
                                    event_type=SSEEventType.TASK_PROGRESS,
                                    data={
                                        "task_id": task_id,
                                        "progress": milestone,
                                        "message": f"Milestone reached: {int(milestone * 100)}%"
                                    },
                                    priority=SSEPriority.HIGH,
                                    task_id=task_id,
                                    agent_id=agent_id
                                )
                                milestone_sent.add(milestone)

                    # Determine event type and priority based on progress/status
                    event_type = SSEEventType.TASK_PROGRESS
                    priority = SSEPriority.NORMAL

                    status = progress_update.get("status")
                    if status == "completed":
                        event_type = SSEEventType.TASK_COMPLETED
                        priority = SSEPriority.HIGH
                    elif status == "failed":
                        event_type = SSEEventType.TASK_FAILED
                        priority = SSEPriority.CRITICAL
                    elif status == "cancelled":
                        event_type = SSEEventType.TASK_CANCELLED
                        priority = SSEPriority.HIGH
                    elif progress > 0 and progress > last_progress:
                        priority = SSEPriority.HIGH if progress >= 0.8 else SSEPriority.NORMAL

                    yield SSEEvent(
                        event_type=event_type,
                        data={
                            "task_id": task_id,
                            **progress_update
                        },
                        priority=priority,
                        task_id=task_id,
                        agent_id=agent_id
                    )

                    last_progress = progress

                    # Break if task is completed/failed/cancelled
                    if status in ["completed", "failed", "cancelled"]:
                        break

            except Exception as e:
                logger.error(f"Task stream error for {task_id}: {e}")
                yield SSEEvent(
                    event_type=SSEEventType.TASK_FAILED,
                    data={
                        "task_id": task_id,
                        "error": str(e),
                        "message": "Task stream encountered an error"
                    },
                    priority=SSEPriority.CRITICAL,
                    task_id=task_id,
                    agent_id=agent_id
                )

        return SSEResponse.create_event_stream(
            task_event_generator(),
            default_retry=1000,
            ping_interval=10,
            max_duration=3600  # 1 hour max for tasks
        )

    @staticmethod
    def create_system_notification_stream(
        notification_generator: AsyncGenerator[Dict[str, Any], None],
        user_id: Optional[str] = None,
        priority_threshold: SSEPriority = SSEPriority.NORMAL
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create enhanced system notification SSE stream"""
        async def notification_event_generator():
            try:
                # Send welcome notification
                yield SSEEvent(
                    event_type=SSEEventType.SYSTEM_NOTIFICATION,
                    data={
                        "type": "connection",
                        "message": "Connected to system notification stream",
                        "level": "info"
                    },
                    priority=SSEPriority.LOW,
                    user_id=user_id
                )

                async for notification in notification_generator:
                    # Determine event type based on notification
                    notification_level = notification.get("level", "info")
                    if notification_level in ["critical", "emergency"]:
                        event_type = SSEEventType.SYSTEM_ALERT
                        priority = SSEPriority.CRITICAL
                    elif notification_level in ["warning", "error"]:
                        priority = SSEPriority.HIGH
                    else:
                        event_type = SSEEventType.SYSTEM_NOTIFICATION
                        priority = SSEPriority.NORMAL

                    # Filter based on priority threshold
                    if priority.value < priority_threshold.value:
                        continue

                    yield SSEEvent(
                        event_type=event_type,
                        data={
                            "type": "notification",
                            **notification
                        },
                        priority=priority,
                        user_id=user_id
                    )

            except Exception as e:
                logger.error(f"Notification stream error: {e}")
                yield SSEEvent(
                    event_type=SSEEventType.ERROR,
                    data={
                        "type": "stream_error",
                        "error": str(e),
                        "message": "Notification stream encountered an error"
                    },
                    priority=SSEPriority.CRITICAL,
                    user_id=user_id
                )

        return SSEResponse.create_event_stream(
            notification_event_generator(),
            default_retry=5000,
            ping_interval=60,
            include_metrics=False
        )

    @staticmethod
    def create_multi_stream(
        generators: Dict[str, AsyncGenerator[Dict[str, Any], None]],
        stream_config: Optional[Dict[str, Any]] = None
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create a combined stream from multiple generators"""
        async def multi_stream_generator():
            try:
                # Send initial multi-stream event
                yield SSEEvent(
                    event_type=SSEEventType.CONNECTION_STATUS,
                    data={
                        "status": "connected",
                        "message": "Multi-stream connection established",
                        "active_streams": list(generators.keys())
                    },
                    priority=SSEPriority.NORMAL
                )

                # Create tasks for each generator
                streams = {}
                for stream_name, generator in generators.items():
                    streams[stream_name] = asyncio.create_task(
                        SSEResponse._process_single_stream(stream_name, generator)
                    )

                # Wait for any task to complete (which indicates an error)
                done, pending = await asyncio.wait(
                    streams.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()

            except Exception as e:
                logger.error(f"Multi-stream error: {e}")
                yield SSEEvent(
                    event_type=SSEEventType.ERROR,
                    data={
                        "type": "multi_stream_error",
                        "error": str(e),
                        "message": "Multi-stream encountered an error"
                    },
                    priority=SSEPriority.CRITICAL
                )

        return SSEResponse.create_event_stream(
            multi_stream_generator(),
            default_retry=3000,
            ping_interval=15,
            include_metrics=True
        )

    @staticmethod
    async def _process_single_stream(
        stream_name: str,
        generator: AsyncGenerator[Dict[str, Any], None]
    ):
        """Process a single stream and yield events"""
        try:
            async for data in generator:
                yield SSEEvent(
                    event_type=SSEEventType.USER_ACTIVITY,  # Generic event type
                    data={
                        "stream_name": stream_name,
                        **data
                    }
                )
        except Exception as e:
            logger.error(f"Stream {stream_name} error: {e}")
            yield SSEEvent(
                event_type=SSEEventType.ERROR,
                data={
                    "stream_name": stream_name,
                    "error": str(e)
                },
                priority=SSEPriority.HIGH
            )


class EventStreamResponse(SSEResponse):
    """Specialized SSE response for general event streaming"""

    def __init__(self,
                 event_filters: Optional[Dict[str, Any]] = None,
                 buffer_size: int = 100,
                 compression: bool = False):
        self.event_filters = event_filters or {}
        self.buffer_size = buffer_size
        self.compression = compression

    def create_filtered_stream(
        self,
        generator: AsyncGenerator[SSEEvent, None]
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create a stream with event filtering"""
        async def filtered_generator():
            async for event in generator:
                if self._should_filter_event(event):
                    continue
                yield event

        return SSEResponse.create_event_stream(
            filtered_generator(),
            include_metrics=True
        )

    def _should_filter_event(self, event: SSEEvent) -> bool:
        """Check if event should be filtered out"""
        # Priority filter
        if "priority" in self.event_filters:
            min_priority = self.event_filters["priority"]
            if isinstance(min_priority, str):
                min_priority = SSEPriority(min_priority)
            if event.priority.value < min_priority.value:
                return True

        # User filter
        if "user_id" in self.event_filters and self.event_filters["user_id"] != event.user_id:
            return True

        # Agent filter
        if "agent_id" in self.event_filters and self.event_filters["agent_id"] != event.agent_id:
            return True

        # Event type filter
        if "event_types" in self.event_filters:
            allowed_types = self.event_filters["event_types"]
            if event.event_type.value not in allowed_types:
                return True

        return False


class AgentEventStream(SSEResponse):
    """Specialized SSE response for agent-specific events"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def create_agent_stream(
        self,
        status_generator: AsyncGenerator[Dict[str, Any], None],
        include_thinking: bool = True,
        include_errors: bool = True
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create agent-specific stream with enhanced filtering"""
        async def agent_enhanced_generator():
            async for status in status_generator:
                # Skip thinking events if not requested
                if not include_thinking and status.get("status") == "thinking":
                    continue

                # Skip errors if not requested
                if not include_errors and status.get("status") == "error":
                    continue

                yield SSEEvent(
                    event_type=self._map_status_to_event_type(status),
                    data=status,
                    agent_id=self.agent_id,
                    priority=self._determine_priority(status)
                )

        return self.create_agent_status_stream(
            self.agent_id,
            agent_enhanced_generator()
        )

    def _map_status_to_event_type(self, status: Dict[str, Any]) -> SSEEventType:
        """Map agent status to appropriate event type"""
        status_value = status.get("status", "")
        if status_value == "thinking":
            return SSEEventType.AGENT_THINKING
        elif status_value in ["response", "completed", "success"]:
            return SSEEventType.AGENT_RESPONSE
        elif status_value == "error":
            return SSEEventType.ERROR
        else:
            return SSEEventType.AGENT_STATUS_UPDATE

    def _determine_priority(self, status: Dict[str, Any]) -> SSEPriority:
        """Determine event priority based on status"""
        status_value = status.get("status", "")
        if status_value in ["error", "critical", "failed"]:
            return SSEPriority.CRITICAL
        elif status_value in ["thinking", "processing", "warning"]:
            return SSEPriority.HIGH
        else:
            return SSEPriority.NORMAL


class TaskEventStream(SSEResponse):
    """Specialized SSE response for task-specific events"""

    def __init__(self, task_id: str, agent_id: Optional[str] = None):
        self.task_id = task_id
        self.agent_id = agent_id

    def create_task_stream(
        self,
        progress_generator: AsyncGenerator[Dict[str, Any], None],
        include_subtasks: bool = True,
        progress_threshold: float = 0.01
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create task-specific stream with enhanced features"""
        async def task_enhanced_generator():
            last_progress = 0.0

            async for progress in progress_generator:
                current_progress = progress.get("progress", 0.0)

                # Filter out minor progress updates if below threshold
                if (current_progress - last_progress) < progress_threshold and not progress.get("status"):
                    continue

                yield SSEEvent(
                    event_type=self._map_progress_to_event_type(progress),
                    data=progress,
                    task_id=self.task_id,
                    agent_id=self.agent_id,
                    priority=self._determine_task_priority(progress)
                )

                last_progress = current_progress

        return self.create_task_progress_stream(
            self.task_id,
            task_enhanced_generator(),
            self.agent_id
        )

    def _map_progress_to_event_type(self, progress: Dict[str, Any]) -> SSEEventType:
        """Map progress update to appropriate event type"""
        status = progress.get("status", "")
        if status == "completed":
            return SSEEventType.TASK_COMPLETED
        elif status == "failed":
            return SSEEventType.TASK_FAILED
        elif status == "cancelled":
            return SSEEventType.TASK_CANCELLED
        else:
            return SSEEventType.TASK_PROGRESS

    def _determine_task_priority(self, progress: Dict[str, Any]) -> SSEPriority:
        """Determine event priority based on progress"""
        status = progress.get("status", "")
        if status in ["failed", "error", "cancelled"]:
            return SSEPriority.CRITICAL
        elif status == "completed":
            return SSEPriority.HIGH
        elif progress.get("progress", 0) >= 0.8:
            return SSEPriority.HIGH
        else:
            return SSEPriority.NORMAL


class SystemEventStream(SSEResponse):
    """Specialized SSE response for system-level events"""

    def create_system_stream(
        self,
        notification_generator: AsyncGenerator[Dict[str, Any], None],
        include_health_checks: bool = True,
        health_check_interval: int = 60
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create system-specific stream with health monitoring"""
        async def system_enhanced_generator():
            last_health_check = time.time()

            async for notification in notification_generator:
                current_time = time.time()

                # Add periodic health checks if enabled
                if (include_health_checks and
                    (current_time - last_health_check) >= health_check_interval):
                    yield SSEEvent(
                        event_type=SSEEventType.HEALTH_CHECK,
                        data={
                            "status": "healthy",
                            "timestamp": datetime.utcnow().isoformat(),
                            "uptime": current_time
                        },
                        priority=SSEPriority.LOW
                    )
                    last_health_check = current_time

                yield SSEEvent(
                    event_type=self._map_notification_to_event_type(notification),
                    data=notification,
                    priority=self._determine_system_priority(notification)
                )

        return self.create_system_notification_stream(
            system_enhanced_generator()
        )

    def _map_notification_to_event_type(self, notification: Dict[str, Any]) -> SSEEventType:
        """Map notification to appropriate event type"""
        level = notification.get("level", "info")
        if level in ["critical", "emergency"]:
            return SSEEventType.SYSTEM_ALERT
        elif notification.get("type") == "batch_operation":
            return SSEEventType.BATCH_OPERATION
        elif notification.get("type") == "workflow_update":
            return SSEEventType.WORKFLOW_UPDATE
        else:
            return SSEEventType.SYSTEM_NOTIFICATION

    def _determine_system_priority(self, notification: Dict[str, Any]) -> SSEPriority:
        """Determine event priority based on notification"""
        level = notification.get("level", "info")
        if level in ["critical", "emergency"]:
            return SSEPriority.CRITICAL
        elif level in ["error", "warning"]:
            return SSEPriority.HIGH
        else:
            return SSEPriority.NORMAL


class MetricsStream(SSEResponse):
    """Specialized SSE response for real-time metrics"""

    def create_metrics_stream(
        self,
        metrics_generator: AsyncGenerator[Dict[str, Any], None],
        update_interval: int = 5,
        include_trends: bool = True
    ) -> Union[EventSourceResponse, StreamingResponse]:
        """Create metrics-specific stream with trend analysis"""
        async def metrics_enhanced_generator():
            metrics_history = []

            async for metrics in metrics_generator:
                current_time = time.time()

                # Add timestamp to metrics
                metrics["timestamp"] = current_time

                # Calculate trends if enabled and we have history
                if include_trends and len(metrics_history) > 0:
                    previous = metrics_history[-1]
                    metrics["trends"] = self._calculate_trends(previous, metrics)

                metrics_history.append(metrics)

                # Keep only last 100 data points for trend calculation
                if len(metrics_history) > 100:
                    metrics_history.pop(0)

                yield SSEEvent(
                    event_type=SSEEventType.METRICS_UPDATE,
                    data=metrics,
                    priority=SSEPriority.LOW
                )

        return SSEResponse.create_event_stream(
            metrics_enhanced_generator(),
            ping_interval=update_interval,
            include_metrics=False
        )

    def _calculate_trends(self, previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trends between metric updates"""
        trends = {}

        # Calculate trend for numeric metrics
        numeric_keys = ["cpu_usage", "memory_usage", "active_connections", "events_per_second"]
        for key in numeric_keys:
            if key in previous and key in current:
                prev_val = float(previous[key])
                curr_val = float(current[key])

                if prev_val > 0:
                    change_pct = ((curr_val - prev_val) / prev_val) * 100
                    trends[key] = {
                        "change_pct": round(change_pct, 2),
                        "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "stable"
                    }

        return trends


class StreamingUtils:
    """Utility functions for creating streaming data generators"""

    @staticmethod
    async def create_periodic_status_generator(
        status_func: callable,
        interval: float = 1.0,
        max_duration: Optional[float] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Create a generator that calls status_func periodically

        Args:
            status_func: Function that returns status dict
            interval: Interval between calls in seconds
            max_duration: Maximum duration in seconds (None for unlimited)
        """
        start_time = datetime.utcnow()

        try:
            while True:
                # Check duration limit
                if max_duration:
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed >= max_duration:
                        break

                # Get status
                try:
                    status = await status_func() if asyncio.iscoroutinefunction(status_func) else status_func()
                    yield status
                except Exception as e:
                    yield {"error": str(e), "type": "status_error"}

                # Wait for next interval
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            # Client disconnected
            yield {"status": "disconnected", "type": "client_disconnect"}

    @staticmethod
    async def create_conditional_generator(
        condition_func: callable,
        data_func: callable,
        check_interval: float = 0.5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Create generator that yields data when condition is met

        Args:
            condition_func: Function that returns True when data should be sent
            data_func: Function that returns data to send
            check_interval: Interval between condition checks
        """
        try:
            while True:
                try:
                    # Check condition
                    should_update = await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func()

                    if should_update:
                        # Get and yield data
                        data = await data_func() if asyncio.iscoroutinefunction(data_func) else data_func()
                        yield data

                except Exception as e:
                    yield {"error": str(e), "type": "generator_error"}

                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            # Client disconnected
            yield {"status": "disconnected", "type": "client_disconnect"}


class LongPollingResponse:
    """Long polling response utilities for efficient HTTP updates"""

    @staticmethod
    async def create_long_polling_response(
        data_generator: callable,
        timeout: float = 30.0,
        check_interval: float = 0.5
    ) -> Dict[str, Any]:
        """
        Create a long polling response that waits for data or timeout

        Args:
            data_generator: Function that generates data or returns None if no update
            timeout: Maximum time to wait in seconds
            check_interval: Interval between checks in seconds

        Returns:
            Dict containing data or timeout indication
        """
        start_time = datetime.utcnow()

        while True:
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed >= timeout:
                return {
                    "status": "timeout",
                    "message": "No updates within timeout period",
                    "elapsed": elapsed
                }

            # Check for data
            try:
                data = await data_generator() if asyncio.iscoroutinefunction(data_generator) else data_generator()
                if data is not None:
                    return {
                        "status": "success",
                        "data": data,
                        "elapsed": elapsed
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "elapsed": elapsed
                }

            # Wait before next check
            await asyncio.sleep(check_interval)


# Export all SSE classes and utilities
__all__ = [
    # Core SSE classes
    "SSEResponse",
    "StreamingUtils",
    "LongPollingResponse",

    # Enhanced SSE response classes
    "EventStreamResponse",
    "AgentEventStream",
    "TaskEventStream",
    "SystemEventStream",
    "MetricsStream",

    # SSE data structures
    "SSEEvent",
    "SSEPriority",
    "SSEEventType"
]