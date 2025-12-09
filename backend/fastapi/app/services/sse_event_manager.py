"""
SSE Event Manager for AutoAdmin Backend
Handles event broadcasting, filtering, and priority management for Server-Sent Events
Provides comprehensive event distribution system with intelligent routing
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import logging
import json
import weakref

from app.responses.sse import SSEEvent, SSEPriority, SSEEventType

logger = logging.getLogger(__name__)


class EventFilterType(Enum):
    """Types of event filters"""
    USER_ID = "user_id"
    SESSION_ID = "session_id"
    AGENT_ID = "agent_id"
    TASK_ID = "task_id"
    EVENT_TYPE = "event_type"
    PRIORITY = "priority"
    CUSTOM = "custom"


@dataclass
class EventFilter:
    """Event filter configuration"""
    filter_type: EventFilterType
    value: Union[str, List[str], Callable]
    include: bool = True  # True for whitelist, False for blacklist
    custom_func: Optional[Callable[[SSEEvent], bool]] = None


@dataclass
class EventSubscription:
    """Event subscription configuration"""
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    filters: List[EventFilter] = field(default_factory=list)
    event_types: Set[SSEEventType] = field(default_factory=set)
    priority_threshold: SSEPriority = SSEPriority.LOW
    max_events_per_minute: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def should_receive_event(self, event: SSEEvent) -> bool:
        """Check if subscription should receive the event"""
        if not self.is_active:
            return False

        # Check priority threshold
        if event.priority.value < self.priority_threshold.value:
            return False

        # Check event types
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check all filters
        for filter_config in self.filters:
            if not self._passes_filter(filter_config, event):
                return False

        return True

    def _passes_filter(self, filter_config: EventFilter, event: SSEEvent) -> bool:
        """Check if event passes a specific filter"""
        try:
            if filter_config.filter_type == EventFilterType.USER_ID:
                event_value = event.user_id
            elif filter_config.filter_type == EventFilterType.SESSION_ID:
                event_value = event.session_id
            elif filter_config.filter_type == EventFilterType.AGENT_ID:
                event_value = event.agent_id
            elif filter_config.filter_type == EventFilterType.TASK_ID:
                event_value = event.task_id
            elif filter_config.filter_type == EventFilterType.EVENT_TYPE:
                event_value = event.event_type.value if event.event_type else None
            elif filter_config.filter_type == EventFilterType.PRIORITY:
                event_value = event.priority.value if event.priority else None
            elif filter_config.filter_type == EventFilterType.CUSTOM:
                if filter_config.custom_func:
                    return filter_config.custom_func(event)
                return True
            else:
                return True

            # Check if filter value matches
            if isinstance(filter_config.value, list):
                matches = event_value in filter_config.value
            elif callable(filter_config.value):
                matches = filter_config.value(event_value)
            else:
                matches = event_value == filter_config.value

            return matches if filter_config.include else not matches

        except Exception as e:
            logger.warning(f"Filter error: {e}")
            return True  # Default to allowing events on filter error


@dataclass
class EventBuffer:
    """Event buffer for client subscriptions"""
    buffer_id: str
    subscription_id: str
    max_size: int = 1000
    max_age_minutes: int = 30
    events: deque = field(default_factory=lambda: deque(maxlen=1000))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_event(self, event: SSEEvent):
        """Add event to buffer"""
        self.events.append(event)
        self._cleanup_expired()

    def get_events(self, last_event_id: Optional[str] = None) -> List[SSEEvent]:
        """Get events from buffer, optionally since last event ID"""
        self._cleanup_expired()

        if not last_event_id:
            return list(self.events)

        # Find events after the specified ID
        events_since = []
        found_last = False

        for event in self.events:
            if found_last:
                events_since.append(event)
            elif event.event_id == last_event_id:
                found_last = True

        return events_since

    def _cleanup_expired(self):
        """Remove expired events from buffer"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.max_age_minutes)

        # Remove old events
        while self.events and self.events[0].timestamp < cutoff_time:
            self.events.popleft()


class SSEEventManager:
    """
    Comprehensive SSE Event Manager
    Handles event broadcasting, filtering, and client management
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SSEEventManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._subscriptions: Dict[str, EventSubscription] = {}
            self._client_subscriptions: Dict[str, List[str]] = defaultdict(list)
            self._event_buffers: Dict[str, EventBuffer] = {}
            self._event_queue: asyncio.Queue = None
            self._broadcast_task = None
            self._stats = {
                'events_broadcast': 0,
                'events_filtered': 0,
                'active_subscriptions': 0,
                'total_subscriptions': 0,
                'start_time': datetime.utcnow()
            }
            self._event_history: deque = deque(maxlen=10000)
            self._max_event_history = 10000
            self._start_background_processor()

    def _start_background_processor(self):
        """Start the background event processor"""
        if self._broadcast_task is None:
            self._event_queue = asyncio.Queue(maxsize=50000)
            self._broadcast_task = asyncio.create_task(self._process_events())

    async def _process_events(self):
        """Background task to process and broadcast events"""
        while True:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._broadcast_event(event)
                self._add_to_history(event)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event processor error: {e}")
                await asyncio.sleep(0.1)

    def _add_to_history(self, event: SSEEvent):
        """Add event to history for replay capabilities"""
        self._event_history.append(event)

    async def create_subscription(
        self,
        client_id: str,
        event_types: Optional[List[SSEEventType]] = None,
        filters: Optional[List[EventFilter]] = None,
        priority_threshold: SSEPriority = SSEPriority.LOW,
        max_events_per_minute: Optional[int] = None,
        buffer_size: int = 1000
    ) -> str:
        """
        Create a new event subscription

        Args:
            client_id: Client connection ID
            event_types: Event types to subscribe to
            filters: Event filters to apply
            priority_threshold: Minimum priority to receive
            max_events_per_minute: Rate limit for events
            buffer_size: Size of event buffer for this subscription

        Returns:
            str: Subscription ID
        """
        subscription = EventSubscription(
            client_id=client_id,
            filters=filters or [],
            event_types=set(event_types or []),
            priority_threshold=priority_threshold,
            max_events_per_minute=max_events_per_minute
        )

        self._subscriptions[subscription.subscription_id] = subscription
        self._client_subscriptions[client_id].append(subscription.subscription_id)

        # Create event buffer
        buffer = EventBuffer(
            buffer_id=str(uuid.uuid4()),
            subscription_id=subscription.subscription_id,
            max_size=buffer_size
        )
        self._event_buffers[subscription.subscription_id] = buffer

        # Update stats
        self._stats['active_subscriptions'] = len([s for s in self._subscriptions.values() if s.is_active])
        self._stats['total_subscriptions'] = len(self._subscriptions)

        logger.info(
            f"Created SSE subscription",
            subscription_id=subscription.subscription_id,
            client_id=client_id,
            event_types=[et.value for et in event_types] if event_types else None
        )

        return subscription.subscription_id

    async def remove_subscription(self, subscription_id: str) -> bool:
        """Remove an event subscription"""
        if subscription_id not in self._subscriptions:
            return False

        subscription = self._subscriptions[subscription_id]
        subscription.is_active = False

        # Remove from client subscriptions
        if subscription.client_id in self._client_subscriptions:
            self._client_subscriptions[subscription.client_id].remove(subscription_id)
            if not self._client_subscriptions[subscription.client_id]:
                del self._client_subscriptions[subscription.client_id]

        # Clean up buffers
        if subscription_id in self._event_buffers:
            del self._event_buffers[subscription_id]

        # Remove subscription
        del self._subscriptions[subscription_id]

        # Update stats
        self._stats['active_subscriptions'] = len([s for s in self._subscriptions.values() if s.is_active])

        logger.info(
            f"Removed SSE subscription",
            subscription_id=subscription_id,
            client_id=subscription.client_id
        )

        return True

    async def remove_client_subscriptions(self, client_id: str) -> int:
        """Remove all subscriptions for a client"""
        subscription_ids = self._client_subscriptions.get(client_id, []).copy()
        removed_count = 0

        for subscription_id in subscription_ids:
            if await self.remove_subscription(subscription_id):
                removed_count += 1

        return removed_count

    async def broadcast_event(self, event: SSEEvent) -> int:
        """
        Broadcast an event to all matching subscriptions

        Args:
            event: Event to broadcast

        Returns:
            int: Number of subscriptions that received the event
        """
        try:
            await self._event_queue.put(event)
            return 0  # Will be updated in _broadcast_event
        except asyncio.QueueFull:
            logger.warning("Event queue is full, dropping event")
            return 0

    async def _broadcast_event(self, event: SSEEvent) -> int:
        """Internal method to broadcast event to matching subscriptions"""
        recipients_count = 0
        filtered_count = 0

        # Find matching subscriptions
        matching_subscriptions = []
        for subscription in self._subscriptions.values():
            if not subscription.is_active:
                continue

            if subscription.should_receive_event(event):
                # Check rate limiting
                if subscription.max_events_per_minute:
                    events_per_minute = self._get_events_per_minute(subscription.subscription_id)
                    if events_per_minute >= subscription.max_events_per_minute:
                        filtered_count += 1
                        continue

                matching_subscriptions.append(subscription)
            else:
                filtered_count += 1

        # Send to matching subscriptions
        for subscription in matching_subscriptions:
            try:
                # Add to subscription's event buffer
                if subscription.subscription_id in self._event_buffers:
                    self._event_buffers[subscription.subscription_id].add_event(event)

                # Update subscription activity
                subscription.last_activity = datetime.utcnow()
                recipients_count += 1

            except Exception as e:
                logger.error(f"Error sending event to subscription {subscription.subscription_id}: {e}")

        # Update stats
        self._stats['events_broadcast'] += recipients_count
        self._stats['events_filtered'] += filtered_count

        if recipients_count > 0:
            logger.debug(
                f"Broadcast SSE event",
                event_type=event.event_type.value,
                event_id=event.event_id,
                recipients=recipients_count,
                filtered=filtered_count
            )

        return recipients_count

    def _get_events_per_minute(self, subscription_id: str) -> int:
        """Get number of events sent to subscription in the last minute"""
        if subscription_id not in self._event_buffers:
            return 0

        buffer = self._event_buffers[subscription_id]
        cutoff_time = datetime.utcnow() - timedelta(minutes=1)

        return sum(1 for event in buffer.events if event.timestamp >= cutoff_time)

    def get_subscription_events(
        self,
        subscription_id: str,
        last_event_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SSEEvent]:
        """Get events for a subscription since last event ID"""
        if subscription_id not in self._event_buffers:
            return []

        events = self._event_buffers[subscription_id].get_events(last_event_id)

        if limit:
            return events[-limit:] if limit < len(events) else events

        return events

    def create_event_generator(
        self,
        subscription_id: str,
        last_event_id: Optional[str] = None
    ) -> Any:
        """Create async generator for subscription events"""
        async def event_generator():
            try:
                # Send buffered events first
                buffered_events = self.get_subscription_events(subscription_id, last_event_id)
                for event in buffered_events:
                    yield event

                # Then listen for new events
                while True:
                    await asyncio.sleep(0.1)  # Small delay to prevent tight loop

                    # Get new events from buffer
                    new_events = self.get_subscription_events(subscription_id, last_event_id)
                    for event in new_events:
                        yield event
                        last_event_id = event.event_id

            except Exception as e:
                logger.error(f"Event generator error for {subscription_id}: {e}")

        return event_generator()

    async def create_agent_subscription(
        self,
        client_id: str,
        agent_id: str,
        include_status: bool = True,
        include_responses: bool = True,
        include_thinking: bool = True
    ) -> str:
        """Create subscription for agent-specific events"""
        event_types = set()
        filters = []

        if include_status:
            event_types.add(SSEEventType.AGENT_STATUS_UPDATE)

        if include_responses:
            event_types.add(SSEEventType.AGENT_RESPONSE)

        if include_thinking:
            event_types.add(SSEEventType.AGENT_THINKING)

        # Add agent filter
        filters.append(EventFilter(
            filter_type=EventFilterType.AGENT_ID,
            value=agent_id,
            include=True
        ))

        return await self.create_subscription(
            client_id=client_id,
            event_types=list(event_types),
            filters=filters
        )

    async def create_task_subscription(
        self,
        client_id: str,
        task_id: str,
        agent_id: Optional[str] = None,
        include_progress: bool = True,
        include_completion: bool = True,
        include_errors: bool = True
    ) -> str:
        """Create subscription for task-specific events"""
        event_types = set()
        filters = []

        if include_progress:
            event_types.add(SSEEventType.TASK_PROGRESS)

        if include_completion:
            event_types.update([SSEEventType.TASK_COMPLETED, SSEEventType.TASK_CANCELLED])

        if include_errors:
            event_types.add(SSEEventType.TASK_FAILED)

        # Add task filter
        filters.append(EventFilter(
            filter_type=EventFilterType.TASK_ID,
            value=task_id,
            include=True
        ))

        # Add agent filter if specified
        if agent_id:
            filters.append(EventFilter(
                filter_type=EventFilterType.AGENT_ID,
                value=agent_id,
                include=True
            ))

        return await self.create_subscription(
            client_id=client_id,
            event_types=list(event_types),
            filters=filters
        )

    async def create_system_subscription(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        include_notifications: bool = True,
        include_alerts: bool = True,
        priority_threshold: SSEPriority = SSEPriority.NORMAL
    ) -> str:
        """Create subscription for system-level events"""
        event_types = set()
        filters = []

        if include_notifications:
            event_types.add(SSEEventType.SYSTEM_NOTIFICATION)

        if include_alerts:
            event_types.add(SSEEventType.SYSTEM_ALERT)

        # Add user filter if specified
        if user_id:
            filters.append(EventFilter(
                filter_type=EventFilterType.USER_ID,
                value=user_id,
                include=True
            ))

        return await self.create_subscription(
            client_id=client_id,
            event_types=list(event_types),
            filters=filters,
            priority_threshold=priority_threshold
        )

    def get_subscription_stats(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a subscription"""
        if subscription_id not in self._subscriptions:
            return None

        subscription = self._subscriptions[subscription_id]
        buffer = self._event_buffers.get(subscription_id)

        return {
            "subscription_id": subscription_id,
            "client_id": subscription.client_id,
            "is_active": subscription.is_active,
            "created_at": subscription.created_at.isoformat(),
            "last_activity": subscription.last_activity.isoformat(),
            "event_types": [et.value for et in subscription.event_types],
            "priority_threshold": subscription.priority_threshold.value,
            "max_events_per_minute": subscription.max_events_per_minute,
            "buffer_size": len(buffer.events) if buffer else 0,
            "events_per_minute": self._get_events_per_minute(subscription_id)
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        active_subscriptions = len([s for s in self._subscriptions.values() if s.is_active])
        total_buffered_events = sum(len(buffer.events) for buffer in self._event_buffers.values())

        return {
            "stats": self._stats.copy(),
            "active_subscriptions": active_subscriptions,
            "total_subscriptions": len(self._subscriptions),
            "total_clients": len(self._client_subscriptions),
            "total_buffered_events": total_buffered_events,
            "event_history_size": len(self._event_history),
            "uptime_seconds": (datetime.utcnow() - self._stats['start_time']).total_seconds(),
            "queue_size": self._event_queue.qsize() if self._event_queue else 0
        }

    async def cleanup_expired_subscriptions(self, max_age_hours: int = 24) -> int:
        """Clean up expired subscriptions"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_subscriptions = []

        for subscription_id, subscription in self._subscriptions.items():
            if subscription.last_activity < cutoff_time and not subscription.is_active:
                expired_subscriptions.append(subscription_id)

        for subscription_id in expired_subscriptions:
            await self.remove_subscription(subscription_id)

        return len(expired_subscriptions)

    async def shutdown(self):
        """Shutdown the event manager"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        # Clear all subscriptions
        self._subscriptions.clear()
        self._client_subscriptions.clear()
        self._event_buffers.clear()
        self._event_history.clear()

        logger.info("SSE Event Manager shutdown complete")


# Create singleton instance
sse_event_manager = SSEEventManager()


def get_sse_event_manager() -> SSEEventManager:
    """Get the SSE event manager singleton"""
    return sse_event_manager


# Export classes and functions
__all__ = [
    "SSEEventManager",
    "get_sse_event_manager",
    "EventSubscription",
    "EventFilter",
    "EventBuffer",
    "EventFilterType"
]