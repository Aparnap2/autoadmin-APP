"""
Long Polling Service for AutoAdmin Backend
Provides real-time updates without WebSockets using HTTP long polling
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PollingEvent:
    """Long polling event structure"""
    def __init__(
        self,
        event_id: str,
        event_type: str,
        data: Dict[str, Any],
        timestamp: datetime,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp
        self.user_id = user_id
        self.session_id = session_id
        self.agent_id = agent_id
        self.task_id = task_id
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=1))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "expires_at": self.expires_at.isoformat()
        }

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def matches_filters(self, filters: Dict[str, Any]) -> bool:
        """Check if event matches the given filters"""
        # Filter by event type
        if "event_types" in filters and self.event_type not in filters["event_types"]:
            return False

        # Filter by user ID
        if "user_id" in filters and self.user_id and self.user_id != filters["user_id"]:
            return False

        # Filter by session ID
        if "session_id" in filters and self.session_id and self.session_id != filters["session_id"]:
            return False

        # Filter by agent ID
        if "agent_id" in filters and self.agent_id and self.agent_id != filters["agent_id"]:
            return False

        # Filter by task ID
        if "task_id" in filters and self.task_id and self.task_id != filters["task_id"]:
            return False

        # Filter by time range
        if "since" in filters and self.timestamp < filters["since"]:
            return False

        return True


@dataclass
class PollingSession:
    """Long polling session"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    filters: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    event_ids_sent: List[str] = field(default_factory=list)


class LongPollingService:
    """
    HTTP Long Polling Service
    Provides real-time updates using standard HTTP requests
    """

    _instance = None
    _events: List[PollingEvent] = []
    _sessions: Dict[str, PollingSession] = {}
    _max_events = 10000
    _session_timeout = 1800  # 30 minutes
    _poll_timeout = 30  # 30 seconds
    _max_event_age = timedelta(hours=24)
    _cleanup_interval = 300  # 5 minutes
    _background_task: Optional[asyncio.Task] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LongPollingService, cls).__new__(cls)
            cls._instance._background_task = None
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start the background cleanup task"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        """Background task to clean up old events and sessions"""
        while True:
            try:
                await self.cleanup_expired_events()
                await self.cleanup_inactive_sessions()
                await asyncio.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)

    def create_session(
        self,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new polling session

        Args:
            user_id: User identifier
            filters: Event filters

        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())
        filters = filters or {}

        session = PollingSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            filters=filters
        )

        self._sessions[session_id] = session

        logger.info(
            f"Created polling session",
            session_id=session_id,
            user_id=user_id,
            total_sessions=len(self._sessions)
        )

        return session_id

    def remove_session(self, session_id: str):
        """Remove a polling session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(
                f"Removed polling session",
                session_id=session_id,
                total_sessions=len(self._sessions)
            )

    def add_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """
        Add a new event

        Args:
            event_type: Type of event
            data: Event data
            user_id: User ID (optional)
            session_id: Session ID (optional)
            agent_id: Agent ID (optional)
            task_id: Task ID (optional)
            expires_at: Event expiration time (optional)

        Returns:
            str: Event ID
        """
        event_id = str(uuid.uuid4())

        event = PollingEvent(
            event_id=event_id,
            event_type=event_type,
            data=data,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            task_id=task_id,
            expires_at=expires_at
        )

        self._events.append(event)

        # Keep only recent events
        if len(self._events) > self._max_events:
            self._events.pop(0)

        logger.debug(
            f"Added event",
            event_id=event_id,
            event_type=event_type,
            total_events=len(self._events)
        )

        return event_id

    async def poll_events(
        self,
        session_id: str,
        timeout: Optional[int] = None,
        max_events: int = 50
    ) -> Dict[str, Any]:
        """
        Poll for events using long polling

        Args:
            session_id: Session ID
            timeout: Poll timeout in seconds (default: 30)
            max_events: Maximum events to return

        Returns:
            Dict: Polling response
        """
        if session_id not in self._sessions:
            return {
                "success": False,
                "error": "Invalid session ID",
                "events": []
            }

        session = self._sessions[session_id]
        timeout = timeout or self._poll_timeout

        # Update session activity
        session.last_activity = datetime.utcnow()
        session.is_active = True

        # Get initial events
        initial_events = self._get_pending_events(session, max_events)

        # If we have events, return immediately
        if initial_events:
            return {
                "success": True,
                "events": [event.to_dict() for event in initial_events],
                "session_id": session_id,
                "immediate": True
            }

        # Otherwise, wait for new events (long polling)
        start_time = datetime.utcnow()
        timeout_delta = timedelta(seconds=timeout)

        while (datetime.utcnow() - start_time) < timeout_delta:
            # Check for new events
            new_events = self._get_pending_events(session, max_events)

            if new_events:
                return {
                    "success": True,
                    "events": [event.to_dict() for event in new_events],
                    "session_id": session_id,
                    "immediate": False,
                    "waited_seconds": (datetime.utcnow() - start_time).seconds
                }

            # Sleep briefly before checking again
            await asyncio.sleep(1)

        # Timeout reached, return empty response
        return {
            "success": True,
            "events": [],
            "session_id": session_id,
            "timeout": True,
            "waited_seconds": timeout
        }

    def _get_pending_events(self, session: PollingSession, max_events: int) -> List[PollingEvent]:
        """Get pending events for a session"""
        pending_events = []

        for event in self._events:
            # Skip if event was already sent to this session
            if event.event_id in session.event_ids_sent:
                continue

            # Skip if event is expired
            if event.is_expired():
                continue

            # Check if event matches session filters
            if not event.matches_filters(session.filters):
                continue

            pending_events.append(event)

            # Track that this event was sent to this session
            session.event_ids_sent.append(event.event_id)

            # Limit number of events
            if len(pending_events) >= max_events:
                break

        return pending_events

    async def cleanup_expired_events(self):
        """Remove expired events"""
        current_time = datetime.utcnow()
        events_before = len(self._events)

        # Remove expired events
        self._events = [
            event for event in self._events
            if not event.is_expired() and
            (current_time - event.timestamp) < self._max_event_age
        ]

        events_after = len(self._events)

        if events_before != events_after:
            logger.info(f"Cleaned up {events_before - events_after} expired events")

    async def cleanup_inactive_sessions(self):
        """Remove inactive sessions"""
        current_time = datetime.utcnow()
        timeout_delta = timedelta(seconds=self._session_timeout)
        sessions_before = len(self._sessions)

        inactive_sessions = []
        for session_id, session in self._sessions.items():
            if (current_time - session.last_activity) > timeout_delta:
                inactive_sessions.append(session_id)

        for session_id in inactive_sessions:
            self.remove_session(session_id)

        sessions_after = len(self._sessions)

        if sessions_before != sessions_after:
            logger.info(f"Cleaned up {sessions_before - sessions_after} inactive sessions")

    # Convenience methods for different event types
    def add_agent_status_event(
        self,
        agent_id: str,
        status: str,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add agent status update event"""
        data = {
            "agent_id": agent_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }

        if additional_data:
            data.update(additional_data)

        return self.add_event(
            event_type="agent_status_update",
            data=data,
            user_id=user_id,
            agent_id=agent_id
        )

    def add_task_progress_event(
        self,
        task_id: str,
        progress: float,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> str:
        """Add task progress event"""
        data = {
            "task_id": task_id,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }

        if message:
            data["message"] = message

        return self.add_event(
            event_type="task_progress",
            data=data,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id
        )

    def add_task_completed_event(
        self,
        task_id: str,
        result: Dict[str, Any],
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Add task completed event"""
        data = {
            "task_id": task_id,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        }

        return self.add_event(
            event_type="task_completed",
            data=data,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id
        )

    def add_notification_event(
        self,
        message: str,
        level: str = "info",
        user_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add notification event"""
        event_data = {
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat()
        }

        if data:
            event_data.update(data)

        return self.add_event(
            event_type="notification",
            data=event_data,
            user_id=user_id
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        active_sessions = len([
            s for s in self._sessions.values()
            if s.is_active and
            (datetime.utcnow() - s.last_activity).seconds < self._session_timeout
        ])

        return {
            "total_events": len(self._events),
            "total_sessions": len(self._sessions),
            "active_sessions": active_sessions,
            "max_events": self._max_events,
            "session_timeout": self._session_timeout,
            "poll_timeout": self._poll_timeout,
            "cleanup_interval": self._cleanup_interval
        }


# Create singleton instance
long_polling_service = LongPollingService()


def get_long_polling_service() -> LongPollingService:
    """Get long polling service singleton"""
    return long_polling_service


# Export for use in routers
__all__ = [
    'LongPollingService',
    'get_long_polling_service',
    'PollingEvent',
    'PollingSession'
]