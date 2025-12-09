"""
HTTP Polling Service for AutoAdmin Backend
Comprehensive fallback system for when Server-Sent Events (SSE) are not available
Provides reliable real-time functionality using regular HTTP polling
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import weakref
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class PollingInterval(Enum):
    """Configurable polling intervals in seconds"""
    VERY_FAST = 5    # 5 seconds - high priority tasks
    FAST = 15        # 15 seconds - active tasks
    NORMAL = 30      # 30 seconds - normal operation
    SLOW = 60       # 60 seconds - background monitoring
    VERY_SLOW = 300 # 5 minutes - minimal monitoring


class ConnectionStatus(Enum):
    """Connection status for HTTP polling clients"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"
    RECONNECTING = "reconnecting"


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5


class ErrorType(Enum):
    """Error classification types"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class PollingMetrics:
    """Performance metrics for HTTP polling"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    connection_drops: int = 0
    reconnections: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        return 100.0 - self.success_rate


@dataclass
class PollingEvent:
    """Event for HTTP polling system"""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    priority: EventPriority
    timestamp: datetime
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

    def is_expired(self) -> bool:
        """Check if event has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def can_retry(self) -> bool:
        """Check if event can be retried"""
        return self.retry_count < self.max_retries

    def matches_filters(self, filters: Dict[str, Any]) -> bool:
        """Check if event matches the given filters"""
        # Filter by event types
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

        # Filter by priority
        if "min_priority" in filters and self.priority.value < filters["min_priority"]:
            return False

        # Filter by time range
        if "since" in filters and self.timestamp < filters["since"]:
            return False

        if "until" in filters and self.timestamp > filters["until"]:
            return False

        return True


@dataclass
class PollingSession:
    """Session for HTTP polling client"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    interval: PollingInterval
    status: ConnectionStatus
    filters: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    delivered_events: Set[str] = field(default_factory=set)
    event_buffer: deque = field(default_factory=lambda: deque(maxlen=1000))
    metrics: PollingMetrics = field(default_factory=PollingMetrics)
    backoff_factor: float = 1.0
    max_backoff: float = 60.0
    error_count: int = 0
    consecutive_errors: int = 0

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def get_effective_interval(self) -> float:
        """Get effective polling interval with backoff"""
        base_interval = self.interval.value
        return min(base_interval * self.backoff_factor, self.max_backoff)

    def handle_success(self):
        """Handle successful request"""
        self.metrics.successful_requests += 1
        self.metrics.last_success_time = datetime.utcnow()
        self.consecutive_errors = 0
        self.backoff_factor = max(1.0, self.backoff_factor * 0.8)  # Reduce backoff
        self.status = ConnectionStatus.CONNECTED
        self.update_activity()

    def handle_error(self):
        """Handle failed request"""
        self.metrics.failed_requests += 1
        self.consecutive_errors += 1
        self.backoff_factor = min(self.backoff_factor * 1.5, self.max_backoff)  # Increase backoff

        if self.consecutive_errors >= 3:
            self.status = ConnectionStatus.ERROR
        elif self.consecutive_errors >= 1:
            self.status = ConnectionStatus.RECONNECTING

        self.update_activity()

    def handle_timeout(self):
        """Handle request timeout"""
        self.metrics.timeouts += 1
        self.backoff_factor = min(self.backoff_factor * 1.2, self.max_backoff)
        self.status = ConnectionStatus.TIMEOUT
        self.update_activity()


@dataclass
class EventBuffer:
    """Buffer for managing events during connection loss"""
    max_size: int = 10000
    max_age: timedelta = field(default_factory=lambda: timedelta(hours=24))
    events: Dict[str, PollingEvent] = field(default_factory=dict)
    priority_queues: Dict[EventPriority, deque] = field(default_factory=lambda: {
        priority: deque(maxlen=2000) for priority in EventPriority
    })

    def add_event(self, event: PollingEvent) -> bool:
        """Add event to buffer"""
        if len(self.events) >= self.max_size:
            # Remove oldest events by priority (low priority first)
            self._cleanup_old_events()

        self.events[event.event_id] = event
        self.priority_queues[event.priority].append(event.event_id)
        return True

    def get_events(self, session: PollingSession, limit: int = 100) -> List[PollingEvent]:
        """Get events for a session"""
        available_events = []

        # Get events by priority (highest first)
        for priority in sorted(EventPriority, key=lambda p: p.value, reverse=True):
            queue = self.priority_queues[priority]

            for event_id in list(queue):
                if event_id in session.delivered_events:
                    continue

                event = self.events.get(event_id)
                if not event or event.is_expired():
                    queue.remove(event_id)
                    continue

                if not event.matches_filters(session.filters):
                    continue

                available_events.append(event)
                session.delivered_events.add(event_id)

                if len(available_events) >= limit:
                    break

            if len(available_events) >= limit:
                break

        return available_events

    def _cleanup_old_events(self):
        """Remove old expired events"""
        current_time = datetime.utcnow()
        expired_events = []

        for event_id, event in self.events.items():
            if event.is_expired() or (current_time - event.timestamp) > self.max_age:
                expired_events.append(event_id)

        for event_id in expired_events:
            self.remove_event(event_id)

    def remove_event(self, event_id: str):
        """Remove event from buffer"""
        if event_id in self.events:
            event = self.events[event_id]
            # Remove from priority queue
            if event_id in self.priority_queues[event.priority]:
                self.priority_queues[event.priority].remove(event_id)
            del self.events[event_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        return {
            "total_events": len(self.events),
            "max_size": self.max_size,
            "priority_distribution": {
                priority.name: len(queue)
                for priority, queue in self.priority_queues.items()
            }
        }


class HTTPPollingService:
    """
    Comprehensive HTTP Polling Service
    Provides reliable real-time functionality when SSE is not available
    """

    _instance = None
    _sessions: Dict[str, PollingSession] = {}
    _event_buffer: EventBuffer = None
    _background_tasks: List[asyncio.Task] = []
    _shutdown_event: asyncio.Event = asyncio.Event()

    # Configuration
    _max_sessions: int = 1000
    _session_timeout: int = 1800  # 30 minutes
    _default_interval: PollingInterval = PollingInterval.NORMAL
    _cleanup_interval: int = 300  # 5 minutes
    _health_check_interval: int = 60  # 1 minute
    _metrics_interval: int = 300  # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HTTPPollingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._initialized = True
            self._event_buffer = EventBuffer()
            self._start_background_tasks()
            logger.info("HTTP Polling Service initialized")

    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        # Session cleanup task
        self._background_tasks.append(
            asyncio.create_task(self._session_cleanup_loop())
        )

        # Event buffer cleanup task
        self._background_tasks.append(
            asyncio.create_task(self._buffer_cleanup_loop())
        )

        # Health monitoring task
        self._background_tasks.append(
            asyncio.create_task(self._health_monitoring_loop())
        )

        # Metrics collection task
        self._background_tasks.append(
            asyncio.create_task(self._metrics_collection_loop())
        )

    async def _session_cleanup_loop(self):
        """Clean up inactive sessions"""
        while not self._shutdown_event.is_set():
            try:
                await self.cleanup_inactive_sessions()
                await asyncio.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _buffer_cleanup_loop(self):
        """Clean up expired events in buffer"""
        while not self._shutdown_event.is_set():
            try:
                self._event_buffer._cleanup_old_events()
                await asyncio.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in buffer cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _health_monitoring_loop(self):
        """Monitor service health and connection status"""
        while not self._shutdown_event.is_set():
            try:
                await self.monitor_connection_health()
                await asyncio.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _metrics_collection_loop(self):
        """Collect and report service metrics"""
        while not self._shutdown_event.is_set():
            try:
                await self.collect_and_report_metrics()
                await asyncio.sleep(self._metrics_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)

    def create_session(
        self,
        user_id: Optional[str] = None,
        interval: PollingInterval = None,
        filters: Optional[Dict[str, Any]] = None,
        max_buffer_size: int = 1000
    ) -> str:
        """
        Create a new polling session

        Args:
            user_id: User identifier for filtering
            interval: Polling interval (default: NORMAL)
            filters: Event filters
            max_buffer_size: Maximum buffer size for this session

        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())
        interval = interval or self._default_interval

        # Check session limit
        if len(self._sessions) >= self._max_sessions:
            raise Exception(f"Maximum number of sessions ({self._max_sessions}) reached")

        session = PollingSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            interval=interval,
            status=ConnectionStatus.CONNECTING,
            filters=filters or {}
        )

        # Set custom buffer size for session
        session.event_buffer = deque(maxlen=max_buffer_size)

        self._sessions[session_id] = session

        logger.info(
            f"Created polling session",
            session_id=session_id,
            user_id=user_id,
            interval=interval.name,
            total_sessions=len(self._sessions)
        )

        # Send welcome event
        self.add_event(
            event_type="session_created",
            data={
                "session_id": session_id,
                "interval": interval.name,
                "message": "Polling session established successfully"
            },
            priority=EventPriority.MEDIUM,
            user_id=user_id,
            session_id=session_id
        )

        return session_id

    def remove_session(self, session_id: str):
        """Remove a polling session"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.status = ConnectionStatus.DISCONNECTED
            session.is_active = False

            del self._sessions[session_id]

            logger.info(
                f"Removed polling session",
                session_id=session_id,
                user_id=session.user_id,
                total_sessions=len(self._sessions)
            )

    def add_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.MEDIUM,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        expires_in: Optional[int] = None,
        max_retries: int = 3
    ) -> str:
        """
        Add a new event to the polling system

        Args:
            event_type: Type of event
            data: Event data
            priority: Event priority
            user_id: User ID (optional)
            session_id: Session ID (optional)
            agent_id: Agent ID (optional)
            task_id: Task ID (optional)
            expires_in: Expiration time in seconds (optional)
            max_retries: Maximum retry attempts

        Returns:
            str: Event ID
        """
        event_id = str(uuid.uuid4())

        # Calculate expiration time
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        event = PollingEvent(
            event_id=event_id,
            event_type=event_type,
            data=data,
            priority=priority,
            timestamp=datetime.utcnow(),
            expires_at=expires_at,
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            task_id=task_id,
            max_retries=max_retries
        )

        # Add to event buffer
        self._event_buffer.add_event(event)

        logger.debug(
            f"Added polling event",
            event_id=event_id,
            event_type=event_type,
            priority=priority.name,
            user_id=user_id
        )

        return event_id

    async def poll_events(
        self,
        session_id: str,
        timeout: Optional[int] = None,
        max_events: int = 50,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Poll for events using long polling

        Args:
            session_id: Session ID
            timeout: Poll timeout in seconds (default: session interval)
            max_events: Maximum events to return
            include_metrics: Whether to include session metrics

        Returns:
            Dict: Polling response with events and metadata
        """
        if session_id not in self._sessions:
            return {
                "success": False,
                "error": "Invalid session ID",
                "events": []
            }

        session = self._sessions[session_id]
        timeout = timeout or session.get_effective_interval()

        # Update session metrics
        session.metrics.total_requests += 1
        session.metrics.last_request_time = datetime.utcnow()
        session.update_activity()

        try:
            # Get initial events
            events = self._event_buffer.get_events(session, max_events)

            if events:
                session.handle_success()
                response = {
                    "success": True,
                    "events": [event.to_dict() for event in events],
                    "session_id": session_id,
                    "immediate": True,
                    "event_count": len(events),
                    "status": session.status.value
                }

                if include_metrics:
                    response["metrics"] = asdict(session.metrics)

                return response

            # No events immediately available, enter long polling
            start_time = datetime.utcnow()
            timeout_delta = timedelta(seconds=timeout)

            while (datetime.utcnow() - start_time) < timeout_delta:
                await asyncio.sleep(1)  # Check every second

                # Look for new events
                new_events = self._event_buffer.get_events(session, max_events)
                if new_events:
                    waited_seconds = (datetime.utcnow() - start_time).total_seconds()
                    session.handle_success()

                    response = {
                        "success": True,
                        "events": [event.to_dict() for event in new_events],
                        "session_id": session_id,
                        "immediate": False,
                        "event_count": len(new_events),
                        "waited_seconds": waited_seconds,
                        "status": session.status.value
                    }

                    if include_metrics:
                        response["metrics"] = asdict(session.metrics)

                    return response

            # Timeout reached
            session.handle_timeout()
            return {
                "success": True,
                "events": [],
                "session_id": session_id,
                "timeout": True,
                "waited_seconds": timeout,
                "status": session.status.value,
                "metrics": asdict(session.metrics) if include_metrics else None
            }

        except asyncio.TimeoutError:
            session.handle_timeout()
            return {
                "success": True,
                "events": [],
                "session_id": session_id,
                "timeout": True,
                "waited_seconds": timeout,
                "status": session.status.value
            }
        except Exception as e:
            session.handle_error()
            logger.error(f"Error polling events for session {session_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "status": session.status.value
            }

    async def update_session(
        self,
        session_id: str,
        interval: Optional[PollingInterval] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update session configuration

        Args:
            session_id: Session ID
            interval: New polling interval
            filters: New event filters

        Returns:
            bool: Success status
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]

        if interval:
            session.interval = interval

        if filters:
            session.filters.update(filters)

        session.update_activity()

        logger.info(
            f"Updated polling session",
            session_id=session_id,
            new_interval=interval.name if interval else None,
            updated_filters=bool(filters)
        )

        return True

    async def cleanup_inactive_sessions(self):
        """Remove inactive sessions"""
        current_time = datetime.utcnow()
        timeout_delta = timedelta(seconds=self._session_timeout)
        inactive_sessions = []

        for session_id, session in self._sessions.items():
            if not session.is_active:
                inactive_sessions.append(session_id)
                continue

            # Check for timeout
            if (current_time - session.last_activity) > timeout_delta:
                logger.info(
                    f"Session {session_id} inactive for {(current_time - session.last_activity).seconds} seconds"
                )
                inactive_sessions.append(session_id)

        # Remove inactive sessions
        for session_id in inactive_sessions:
            self.remove_session(session_id)

        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")

    async def monitor_connection_health(self):
        """Monitor connection health and update status"""
        current_time = datetime.utcnow()
        health_report = {
            "timestamp": current_time.isoformat(),
            "total_sessions": len(self._sessions),
            "active_sessions": 0,
            "error_sessions": 0,
            "timeout_sessions": 0,
            "reconnecting_sessions": 0,
            "avg_success_rate": 0.0,
            "buffer_stats": self._event_buffer.get_stats()
        }

        success_rates = []

        for session in self._sessions.values():
            if not session.is_active:
                continue

            # Update connection status based on recent activity
            time_since_activity = (current_time - session.last_activity).seconds

            if time_since_activity > self._session_timeout:
                session.status = ConnectionStatus.DISCONNECTED
                session.is_active = False
            elif time_since_activity > session.get_effective_interval() * 3:
                if session.status == ConnectionStatus.CONNECTED:
                    session.status = ConnectionStatus.TIMEOUT
                    session.metrics.connection_drops += 1
            elif session.consecutive_errors > 0:
                session.status = ConnectionStatus.RECONNECTING
            elif session.consecutive_errors >= 3:
                session.status = ConnectionStatus.ERROR
            else:
                session.status = ConnectionStatus.CONNECTED
                health_report["active_sessions"] += 1

            # Collect success rates
            if session.metrics.total_requests > 0:
                success_rates.append(session.metrics.success_rate)

            # Count by status
            if session.status == ConnectionStatus.ERROR:
                health_report["error_sessions"] += 1
            elif session.status == ConnectionStatus.TIMEOUT:
                health_report["timeout_sessions"] += 1
            elif session.status == ConnectionStatus.RECONNECTING:
                health_report["reconnecting_sessions"] += 1

        # Calculate average success rate
        if success_rates:
            health_report["avg_success_rate"] = sum(success_rates) / len(success_rates)

        # Log health status
        logger.info(
            f"HTTP Polling Health Report - "
            f"Active: {health_report['active_sessions']}, "
            f"Errors: {health_report['error_sessions']}, "
            f"Timeouts: {health_report['timeout_sessions']}, "
            f"Avg Success Rate: {health_report['avg_success_rate']:.1f}%"
        )

        # Store health metrics for monitoring
        await self._store_health_metrics(health_report)

    async def _store_health_metrics(self, health_report: Dict[str, Any]):
        """Store health metrics for monitoring and alerting"""
        try:
            # This would integrate with your monitoring system
            # For now, just log the metrics
            logger.debug(f"Health metrics: {json.dumps(health_report, indent=2)}")
        except Exception as e:
            logger.error(f"Error storing health metrics: {e}")

    async def collect_and_report_metrics(self):
        """Collect comprehensive service metrics"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_metrics": self.get_service_metrics(),
            "performance_metrics": self.get_performance_metrics(),
            "error_metrics": self.get_error_metrics()
        }

        logger.info(
            f"HTTP Polling Metrics - "
            f"Sessions: {metrics['service_metrics']['total_sessions']}, "
            f"Events: {metrics['service_metrics']['buffered_events']}, "
            f"Success Rate: {metrics['performance_metrics']['overall_success_rate']:.1f}%"
        )

        # Send metrics to monitoring system
        await self._send_metrics_to_monitoring(metrics)

    async def _send_metrics_to_monitoring(self, metrics: Dict[str, Any]):
        """Send metrics to external monitoring system"""
        try:
            # This would integrate with your monitoring/telemetry system
            # For example: Prometheus, DataDog, etc.
            logger.debug(f"Sending metrics to monitoring: {json.dumps(metrics, indent=2)}")
        except Exception as e:
            logger.error(f"Error sending metrics to monitoring: {e}")

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get overall service metrics"""
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len([s for s in self._sessions.values() if s.is_active]),
            "buffered_events": len(self._event_buffer.events),
            "buffer_stats": self._event_buffer.get_stats(),
            "background_tasks": len(self._background_tasks),
            "max_sessions": self._max_sessions,
            "session_timeout": self._session_timeout
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total_requests = sum(s.metrics.total_requests for s in self._sessions.values())
        successful_requests = sum(s.metrics.successful_requests for s in self._sessions.values())
        failed_requests = sum(s.metrics.failed_requests for s in self._sessions.values())
        timeouts = sum(s.metrics.timeouts for s in self._sessions.values())

        overall_success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0.0

        avg_response_times = [
            s.metrics.avg_response_time for s in self._sessions.values()
            if s.metrics.avg_response_time > 0
        ]
        overall_avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0.0

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "timeouts": timeouts,
            "overall_success_rate": overall_success_rate,
            "overall_avg_response_time": overall_avg_response_time,
            "connection_drops": sum(s.metrics.connection_drops for s in self._sessions.values()),
            "reconnections": sum(s.metrics.reconnections for s in self._sessions.values())
        }

    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error classification metrics"""
        error_sessions = defaultdict(int)
        total_consecutive_errors = 0

        for session in self._sessions.values():
            error_sessions[session.status.value] += 1
            total_consecutive_errors += session.consecutive_errors

        return {
            "sessions_by_status": dict(error_sessions),
            "total_consecutive_errors": total_consecutive_errors,
            "error_rate": (error_sessions.get("error", 0) / len(self._sessions) * 100) if self._sessions else 0.0
        }

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a session"""
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "interval": session.interval.name,
            "effective_interval": session.get_effective_interval(),
            "status": session.status.value,
            "is_active": session.is_active,
            "delivered_events_count": len(session.delivered_events),
            "buffer_size": len(session.event_buffer),
            "backoff_factor": session.backoff_factor,
            "consecutive_errors": session.consecutive_errors,
            "metrics": asdict(session.metrics)
        }

    async def graceful_shutdown(self):
        """Gracefully shutdown the service"""
        logger.info("Starting graceful shutdown of HTTP Polling Service")

        # Signal background tasks to stop
        self._shutdown_event.set()

        # Wait for background tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Mark all sessions as disconnected
        for session in self._sessions.values():
            session.status = ConnectionStatus.DISCONNECTED
            session.is_active = False

        logger.info("HTTP Polling Service shutdown complete")

    # Convenience methods for common event types
    def add_agent_status_event(
        self,
        agent_id: str,
        status: str,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.MEDIUM
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
            priority=priority,
            user_id=user_id,
            agent_id=agent_id
        )

    def add_task_progress_event(
        self,
        task_id: str,
        progress: float,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None,
        priority: EventPriority = EventPriority.MEDIUM
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
            priority=priority,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id
        )

    def add_task_completed_event(
        self,
        task_id: str,
        result: Dict[str, Any],
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        priority: EventPriority = EventPriority.HIGH
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
            priority=priority,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id
        )

    def add_system_notification_event(
        self,
        message: str,
        level: str = "info",
        user_id: Optional[str] = None,
        priority: EventPriority = EventPriority.LOW
    ) -> str:
        """Add system notification event"""
        data = {
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat()
        }

        return self.add_event(
            event_type="system_notification",
            data=data,
            priority=priority,
            user_id=user_id
        )

    def add_error_event(
        self,
        error: str,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.HIGH
    ) -> str:
        """Add error event"""
        data = {
            "error": error,
            "error_type": error_type.value,
            "timestamp": datetime.utcnow().isoformat()
        }

        if context:
            data["context"] = context

        return self.add_event(
            event_type="error",
            data=data,
            priority=priority,
            user_id=user_id,
            session_id=session_id,
            expires_in=3600  # Error events expire in 1 hour
        )


# Create singleton instance
http_polling_service = HTTPPollingService()


def get_http_polling_service() -> HTTPPollingService:
    """Get the HTTP polling service singleton"""
    return http_polling_service


# Context manager for easy service management
@asynccontextmanager
async def http_polling_context():
    """Context manager for HTTP polling service"""
    service = get_http_polling_service()
    try:
        yield service
    finally:
        await service.graceful_shutdown()


# Export for use in routers and other modules
__all__ = [
    'HTTPPollingService',
    'get_http_polling_service',
    'http_polling_context',
    'PollingInterval',
    'ConnectionStatus',
    'EventPriority',
    'ErrorType',
    'PollingEvent',
    'PollingSession',
    'EventBuffer',
    'PollingMetrics'
]