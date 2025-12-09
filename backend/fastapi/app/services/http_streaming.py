"""
HTTP Streaming Service for AutoAdmin Backend
Replaces WebSocket functionality with Server-Sent Events (SSE) and HTTP streaming
Provides real-time communication using standard HTTP protocols
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    # Fallback if sse-starlette is not available
    EventSourceResponse = None

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for SSE streaming"""
    AGENT_STATUS_UPDATE = "agent_status_update"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SYSTEM_NOTIFICATION = "system_notification"
    CHAT_MESSAGE = "chat_message"
    HEALTH_CHECK = "health_check"
    ERROR = "error"


@dataclass
class StreamingEvent:
    """Streaming event data structure"""
    event_id: str
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None


@dataclass
class ClientConnection:
    """Client connection for SSE streaming"""
    client_id: str
    user_id: Optional[str]
    session_id: str
    connected_at: datetime
    last_ping: datetime
    event_types: List[EventType]
    filters: Dict[str, Any]
    is_active: bool = True


class HTTPStreamingService:
    """
    HTTP-based streaming service using Server-Sent Events
    Replaces WebSocket functionality with standard HTTP streaming
    """

    _instance = None
    _connections: Dict[str, ClientConnection] = {}
    _event_queue: asyncio.Queue = None
    _background_task = None
    _max_connections = 1000
    _connection_timeout = 300  # 5 minutes
    _ping_interval = 30  # 30 seconds
    _event_history_size = 100
    _event_history: List[StreamingEvent] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HTTPStreamingService, cls).__new__(cls)
            cls._instance._event_queue = asyncio.Queue(maxsize=10000)
            cls._instance._background_task = None
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._start_background_processor()

    def _start_background_processor(self):
        """Start the background event processor"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._process_events())

    async def _process_events(self):
        """Background task to process events from the queue"""
        while True:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._broadcast_event(event)
                self._add_to_history(event)

            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(0.1)

    def _add_to_history(self, event: StreamingEvent):
        """Add event to history for new connections"""
        self._event_history.append(event)
        if len(self._event_history) > self._event_history_size:
            self._event_history.pop(0)

    async def create_connection(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new streaming connection

        Args:
            user_id: User identifier
            session_id: Session identifier
            event_types: List of event types to subscribe to
            filters: Event filters

        Returns:
            str: Connection ID
        """
        client_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        event_types = event_types or list(EventType)
        filters = filters or {}

        # Check connection limit
        if len(self._connections) >= self._max_connections:
            raise HTTPException(
                status_code=503,
                detail="Maximum number of connections reached"
            )

        connection = ClientConnection(
            client_id=client_id,
            user_id=user_id,
            session_id=session_id,
            connected_at=datetime.utcnow(),
            last_ping=datetime.utcnow(),
            event_types=event_types,
            filters=filters,
            is_active=True
        )

        self._connections[client_id] = connection

        logger.info(
            f"Created streaming connection",
            client_id=client_id,
            user_id=user_id,
            total_connections=len(self._connections)
        )

        return client_id

    async def remove_connection(self, client_id: str):
        """Remove a streaming connection"""
        if client_id in self._connections:
            connection = self._connections[client_id]
            connection.is_active = False
            del self._connections[client_id]

            logger.info(
                f"Removed streaming connection",
                client_id=client_id,
                total_connections=len(self._connections)
            )

    async def send_event(self, event: StreamingEvent):
        """
        Send an event to the streaming service

        Args:
            event: Event to send
        """
        try:
            await self._event_queue.put(event)
        except asyncio.QueueFull:
            logger.warning("Event queue is full, dropping event")
            # Handle queue full - could implement priority or overflow handling

    async def _broadcast_event(self, event: StreamingEvent):
        """Broadcast event to all matching connections"""
        disconnected_clients = []

        for client_id, connection in self._connections.items():
            if not connection.is_active:
                continue

            try:
                # Check if connection should receive this event
                if not self._should_receive_event(connection, event):
                    continue

                # Send event to this connection's queue
                # This would be implemented by the specific streaming endpoint
                # that manages per-client event queues

            except Exception as e:
                logger.error(f"Error sending event to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.remove_connection(client_id)

    def _should_receive_event(self, connection: ClientConnection, event: StreamingEvent) -> bool:
        """Check if connection should receive the event"""
        # Check event type subscription
        if event.event_type not in connection.event_types:
            return False

        # Check user-specific filtering
        if connection.user_id and event.user_id and connection.user_id != event.user_id:
            return False

        # Check agent-specific filtering
        if connection.filters.get("agent_id") and event.agent_id:
            if connection.filters["agent_id"] != event.agent_id:
                return False

        # Check task-specific filtering
        if connection.filters.get("task_id") and event.task_id:
            if connection.filters["task_id"] != event.task_id:
                return False

        return True

    async def create_streaming_response(
        self,
        client_id: str,
        with_history: bool = True,
        history_count: int = 50
    ) -> StreamingResponse:
        """
        Create a streaming response for Server-Sent Events

        Args:
            client_id: Client connection ID
            with_history: Whether to send historical events
            history_count: Number of historical events to send

        Returns:
            StreamingResponse: FastAPI streaming response
        """
        if client_id not in self._connections:
            raise HTTPException(status_code=404, detail="Connection not found")

        async def event_generator():
            """Generate events for SSE streaming"""
            connection = self._connections[client_id]

            try:
                # Send historical events if requested
                if with_history and self._event_history:
                    for event in self._event_history[-history_count:]:
                        if self._should_receive_event(connection, event):
                            yield self._format_sse_event(event)
                            await asyncio.sleep(0.01)  # Small delay between events

                # Send connection established event
                welcome_event = StreamingEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.SYSTEM_NOTIFICATION,
                    data={
                        "message": "Streaming connection established",
                        "client_id": client_id
                    },
                    timestamp=datetime.utcnow(),
                    user_id=connection.user_id,
                    session_id=connection.session_id
                )
                yield self._format_sse_event(welcome_event)

                # Main streaming loop
                last_ping = time.time()

                while connection.is_active:
                    try:
                        # Get events for this specific connection
                        # In a real implementation, you'd have per-client queues
                        # For now, we'll use a simplified approach

                        # Send ping periodically
                        current_time = time.time()
                        if current_time - last_ping >= self._ping_interval:
                            ping_event = StreamingEvent(
                                event_id=str(uuid.uuid4()),
                                event_type=EventType.HEALTH_CHECK,
                                data={"ping": True, "timestamp": current_time},
                                timestamp=datetime.utcnow(),
                                session_id=connection.session_id
                            )
                            yield self._format_sse_event(ping_event)
                            last_ping = current_time
                            connection.last_ping = datetime.utcnow()

                        # Check for new events (simplified approach)
                        # In production, you'd maintain per-client event queues
                        await asyncio.sleep(1)  # Prevent tight loop

                        # Check if connection timed out
                        if (datetime.utcnow() - connection.last_ping).seconds > self._connection_timeout:
                            logger.info(f"Connection {client_id} timed out")
                            break

                    except Exception as e:
                        logger.error(f"Error in streaming loop for {client_id}: {e}")
                        break

            finally:
                # Clean up connection
                await self.remove_connection(client_id)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )

    def _format_sse_event(self, event: StreamingEvent) -> str:
        """Format event as SSE string"""
        event_data = {
            "id": event.event_id,
            "type": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "session_id": event.session_id,
            "agent_id": event.agent_id,
            "task_id": event.task_id
        }

        # Format as SSE
        lines = [
            f"id: {event.event_id}",
            f"event: {event.event_type.value}",
            f"data: {json.dumps(event_data)}",
            "",  # Empty line to end the event
            "\n"  # Extra newline
        ]

        return "\n".join(lines)

    # Convenience methods for creating specific event types
    async def send_agent_status_update(
        self,
        agent_id: str,
        status: str,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Send agent status update event"""
        event = StreamingEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.AGENT_STATUS_UPDATE,
            data={
                "agent_id": agent_id,
                "status": status,
                **(additional_data or {})
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            agent_id=agent_id
        )
        await self.send_event(event)

    async def send_task_progress(
        self,
        task_id: str,
        progress: float,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None
    ):
        """Send task progress event"""
        event = StreamingEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_PROGRESS,
            data={
                "task_id": task_id,
                "progress": progress,
                "message": message
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id
        )
        await self.send_event(event)

    async def send_task_completed(
        self,
        task_id: str,
        result: Dict[str, Any],
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Send task completed event"""
        event = StreamingEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_COMPLETED,
            data={
                "task_id": task_id,
                "result": result
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id
        )
        await self.send_event(event)

    async def send_chat_message(
        self,
        message: str,
        agent_id: str,
        user_id: str,
        session_id: str,
        message_type: str = "response"
    ):
        """Send chat message event"""
        event = StreamingEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.CHAT_MESSAGE,
            data={
                "message": message,
                "type": message_type,
                "agent_id": agent_id
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id
        )
        await self.send_event(event)

    async def send_system_notification(
        self,
        message: str,
        level: str = "info",
        user_id: Optional[str] = None
    ):
        """Send system notification event"""
        event = StreamingEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SYSTEM_NOTIFICATION,
            data={
                "message": message,
                "level": level
            },
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        await self.send_event(event)

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        active_connections = len([c for c in self._connections.values() if c.is_active])

        return {
            "active_connections": active_connections,
            "total_connections": len(self._connections),
            "max_connections": self._max_connections,
            "event_queue_size": self._event_queue.qsize(),
            "event_history_size": len(self._event_history),
            "connection_timeout": self._connection_timeout,
            "ping_interval": self._ping_interval
        }

    async def cleanup_inactive_connections(self):
        """Clean up inactive connections"""
        current_time = datetime.utcnow()
        inactive_clients = []

        for client_id, connection in self._connections.items():
            if not connection.is_active:
                inactive_clients.append(client_id)
                continue

            # Check for timeout
            time_diff = (current_time - connection.last_ping).seconds
            if time_diff > self._connection_timeout:
                logger.info(f"Connection {client_id} inactive for {time_diff} seconds")
                inactive_clients.append(client_id)

        # Remove inactive connections
        for client_id in inactive_clients:
            await self.remove_connection(client_id)


# Create singleton instance
streaming_service = HTTPStreamingService()


def get_streaming_service() -> HTTPStreamingService:
    """Get the streaming service singleton"""
    return streaming_service


# Export for use in routers
__all__ = [
    'HTTPStreamingService',
    'get_streaming_service',
    'EventType',
    'StreamingEvent',
    'ClientConnection'
]