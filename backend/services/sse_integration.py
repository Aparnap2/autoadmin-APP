"""
SSE Integration Service for AutoAdmin Backend
Integrates Server-Sent Events with existing services including agent orchestrator and HTTP polling
Provides seamless real-time communication with existing architecture
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging

from fastapi.app import FastAPI

# Import existing services
try:
    from app.services.http_streaming import get_streaming_service, StreamingEvent, EventType
    from app.services.long_polling import get_long_polling_service
    from app.services.sse_event_manager import get_sse_event_manager, SSEEvent, SSEEventType, SSEPriority
    from app.services.sse_client_manager import get_sse_client_manager
except ImportError:
    # Handle import errors for standalone usage
    logging.warning("Some services not available for SSE integration")
    get_streaming_service = None
    get_long_polling_service = None

logger = logging.getLogger(__name__)


class SSEIntegrationService:
    """
    Service for integrating SSE with existing AutoAdmin services
    Bridges legacy HTTP streaming/polling with new SSE infrastructure
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SSEIntegrationService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._event_manager = get_sse_event_manager() if get_sse_event_manager else None
            self._client_manager = get_sse_client_manager() if get_sse_client_manager else None
            self._streaming_service = get_streaming_service() if get_streaming_service else None
            self._polling_service = get_long_polling_service() if get_long_polling_service else None
            self._integration_stats = {
                'legacy_events_converted': 0,
                'sse_events_broadcast': 0,
                'polling_events_bridged': 0,
                'integrations_active': 0,
                'start_time': datetime.utcnow()
            }
            self._legacy_listeners = []
            self._bridging_tasks = []

    async def initialize_integration(self, app: FastAPI):
        """
        Initialize SSE integration with FastAPI application

        Args:
            app: FastAPI application instance
        """
        try:
            # Set up event bridging from legacy services
            if self._streaming_service and self._event_manager:
                await self._setup_streaming_bridge()

            if self._polling_service and self._event_manager:
                await self._setup_polling_bridge()

            # Set up application lifecycle hooks
            app.add_event_handler("shutdown", self._shutdown_integration)

            self._integration_stats['integrations_active'] = len(self._bridging_tasks)

            logger.info("SSE Integration initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SSE integration: {e}")

    async def _setup_streaming_bridge(self):
        """Set up event bridging from HTTP streaming service to SSE"""
        try:
            # Create a bridge task that monitors legacy streaming events
            bridge_task = asyncio.create_task(self._streaming_bridge_worker())
            self._bridging_tasks.append(bridge_task)
            logger.info("HTTP streaming to SSE bridge established")
        except Exception as e:
            logger.error(f"Failed to setup streaming bridge: {e}")

    async def _setup_polling_bridge(self):
        """Set up event bridging from HTTP polling service to SSE"""
        try:
            # Create a bridge task that monitors polling events
            bridge_task = asyncio.create_task(self._polling_bridge_worker())
            self._bridging_tasks.append(bridge_task)
            logger.info("HTTP polling to SSE bridge established")
        except Exception as e:
            logger.error(f"Failed to setup polling bridge: {e}")

    async def _streaming_bridge_worker(self):
        """Bridge events from HTTP streaming service to SSE"""
        while True:
            try:
                await asyncio.sleep(0.1)  # Small delay to prevent tight loop

                # Check for new streaming events
                # This would need to be implemented based on the actual streaming service API
                if self._streaming_service and hasattr(self._streaming_service, '_event_history'):
                    # Get recent events from streaming service
                    recent_events = self._streaming_service._event_history[-10:]  # Last 10 events

                    for event in recent_events:
                        if isinstance(event, StreamingEvent):
                            await self._convert_legacy_event(event)

            except Exception as e:
                logger.error(f"Streaming bridge worker error: {e}")
                await asyncio.sleep(1)

    async def _polling_bridge_worker(self):
        """Bridge events from HTTP polling service to SSE"""
        while True:
            try:
                await asyncio.sleep(1)  # Check every second

                # Check for new polling events
                if self._polling_service and hasattr(self._polling_service, '_events'):
                    # Get recent events from polling service
                    recent_events = list(self._polling_service._events)[-10:]  # Last 10 events

                    for event in recent_events:
                        await self._convert_polling_event(event)

            except Exception as e:
                logger.error(f"Polling bridge worker error: {e}")
                await asyncio.sleep(1)

    async def _convert_legacy_event(self, event: StreamingEvent):
        """Convert legacy streaming event to SSE event"""
        try:
            if not self._event_manager:
                return

            # Map legacy event type to SSE event type
            sse_event_type = self._map_legacy_event_type(event.event_type)
            sse_priority = self._determine_event_priority(event)

            # Create SSE event
            sse_event = SSEEvent(
                event_type=sse_event_type,
                data=event.data,
                priority=sse_priority,
                user_id=event.user_id,
                session_id=event.session_id,
                agent_id=event.agent_id,
                task_id=event.task_id,
                timestamp=event.timestamp
            )

            # Broadcast to SSE subscribers
            await self._event_manager.broadcast_event(sse_event)

            self._integration_stats['legacy_events_converted'] += 1
            self._integration_stats['sse_events_broadcast'] += 1

        except Exception as e:
            logger.error(f"Failed to convert legacy event: {e}")

    async def _convert_polling_event(self, event: Dict[str, Any]):
        """Convert polling event to SSE event"""
        try:
            if not self._event_manager:
                return

            # Extract event information from polling event
            event_type = event.get('event_type', 'system_notification')
            event_data = event.get('data', {})
            user_id = event.get('user_id')
            session_id = event.get('session_id')
            agent_id = event.get('agent_id')
            task_id = event.get('task_id')

            # Map polling event type to SSE event type
            sse_event_type = self._map_polling_event_type(event_type)
            sse_priority = self._determine_polling_event_priority(event)

            # Create SSE event
            sse_event = SSEEvent(
                event_type=sse_event_type,
                data=event_data,
                priority=sse_priority,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id
            )

            # Broadcast to SSE subscribers
            await self._event_manager.broadcast_event(sse_event)

            self._integration_stats['polling_events_bridged'] += 1
            self._integration_stats['sse_events_broadcast'] += 1

        except Exception as e:
            logger.error(f"Failed to convert polling event: {e}")

    def _map_legacy_event_type(self, legacy_type: EventType) -> SSEEventType:
        """Map legacy streaming event type to SSE event type"""
        mapping = {
            EventType.AGENT_STATUS_UPDATE: SSEEventType.AGENT_STATUS_UPDATE,
            EventType.TASK_PROGRESS: SSEEventType.TASK_PROGRESS,
            EventType.TASK_COMPLETED: SSEEventType.TASK_COMPLETED,
            EventType.TASK_FAILED: SSEEventType.TASK_FAILED,
            EventType.SYSTEM_NOTIFICATION: SSEEventType.SYSTEM_NOTIFICATION,
            EventType.CHAT_MESSAGE: SSEEventType.CHAT_MESSAGE,
            EventType.HEALTH_CHECK: SSEEventType.HEALTH_CHECK,
            EventType.ERROR: SSEEventType.ERROR
        }
        return mapping.get(legacy_type, SSEEventType.SYSTEM_NOTIFICATION)

    def _map_polling_event_type(self, polling_type: str) -> SSEEventType:
        """Map polling event type to SSE event type"""
        mapping = {
            'agent_status': SSEEventType.AGENT_STATUS_UPDATE,
            'task_progress': SSEEventType.TASK_PROGRESS,
            'task_completed': SSEEventType.TASK_COMPLETED,
            'task_failed': SSEEventType.TASK_FAILED,
            'notification': SSEEventType.SYSTEM_NOTIFICATION,
            'system_alert': SSEEventType.SYSTEM_ALERT,
            'chat_message': SSEEventType.CHAT_MESSAGE,
            'health_check': SSEEventType.HEALTH_CHECK,
            'error': SSEEventType.ERROR
        }
        return mapping.get(polling_type, SSEEventType.SYSTEM_NOTIFICATION)

    def _determine_event_priority(self, event: StreamingEvent) -> SSEPriority:
        """Determine SSE priority from legacy event"""
        if event.event_type == EventType.ERROR:
            return SSEPriority.CRITICAL
        elif event.event_type in [EventType.TASK_FAILED, EventType.AGENT_STATUS_UPDATE]:
            return SSEPriority.HIGH
        elif event.event_type == EventType.HEALTH_CHECK:
            return SSEPriority.LOW
        else:
            return SSEPriority.NORMAL

    def _determine_polling_event_priority(self, event: Dict[str, Any]) -> SSEPriority:
        """Determine SSE priority from polling event"""
        event_type = event.get('event_type', '')
        level = event.get('level', '')

        if event_type == 'error' or level in ['critical', 'error']:
            return SSEPriority.CRITICAL
        elif event_type in ['task_failed', 'agent_status'] or level == 'warning':
            return SSEPriority.HIGH
        elif event_type == 'health_check' or level == 'info':
            return SSEPriority.LOW
        else:
            return SSEPriority.NORMAL

    async def send_agent_status_to_legacy(
        self,
        agent_id: str,
        status: str,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Send agent status to legacy services and SSE"""
        try:
            # Send to legacy streaming service
            if self._streaming_service:
                await self._streaming_service.send_agent_status_update(
                    agent_id=agent_id,
                    status=status,
                    user_id=user_id,
                    additional_data=additional_data
                )

            # Send to SSE system
            if self._event_manager:
                sse_event = SSEEvent(
                    event_type=SSEEventType.AGENT_STATUS_UPDATE,
                    data={
                        "agent_id": agent_id,
                        "status": status,
                        **(additional_data or {})
                    },
                    priority=SSEPriority.NORMAL,
                    user_id=user_id,
                    agent_id=agent_id
                )
                await self._event_manager.broadcast_event(sse_event)

            # Send to polling service
            if self._polling_service:
                self._polling_service.add_agent_status_event(
                    agent_id=agent_id,
                    status=status,
                    user_id=user_id,
                    additional_data=additional_data
                )

            logger.info(f"Agent status update sent to all services: {agent_id} - {status}")

        except Exception as e:
            logger.error(f"Failed to send agent status to legacy services: {e}")

    async def send_task_progress_to_legacy(
        self,
        task_id: str,
        progress: float,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message: Optional[str] = None
    ):
        """Send task progress to legacy services and SSE"""
        try:
            # Send to legacy streaming service
            if self._streaming_service:
                await self._streaming_service.send_task_progress(
                    task_id=task_id,
                    progress=progress,
                    agent_id=agent_id,
                    user_id=user_id,
                    message=message
                )

            # Send to SSE system
            if self._event_manager:
                sse_event = SSEEvent(
                    event_type=SSEEventType.TASK_PROGRESS,
                    data={
                        "task_id": task_id,
                        "progress": progress,
                        "message": message
                    },
                    priority=SSEPriority.NORMAL,
                    user_id=user_id,
                    agent_id=agent_id,
                    task_id=task_id
                )
                await self._event_manager.broadcast_event(sse_event)

            # Send to polling service
            if self._polling_service:
                self._polling_service.add_task_progress_event(
                    task_id=task_id,
                    progress=progress,
                    agent_id=agent_id,
                    user_id=user_id,
                    message=message
                )

            logger.info(f"Task progress update sent to all services: {task_id} - {progress}")

        except Exception as e:
            logger.error(f"Failed to send task progress to legacy services: {e}")

    async def send_system_notification_to_legacy(
        self,
        message: str,
        level: str = "info",
        user_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Send system notification to legacy services and SSE"""
        try:
            # Send to legacy streaming service
            if self._streaming_service:
                await self._streaming_service.send_system_notification(
                    message=message,
                    level=level,
                    user_id=user_id
                )

            # Send to SSE system
            if self._event_manager:
                event_type = SSEEventType.SYSTEM_ALERT if level in ['critical', 'error'] else SSEEventType.SYSTEM_NOTIFICATION
                priority = SSEPriority.CRITICAL if level == 'critical' else SSEPriority.HIGH if level == 'error' else SSEPriority.NORMAL

                sse_event = SSEEvent(
                    event_type=event_type,
                    data={
                        "message": message,
                        "level": level,
                        **(data or {})
                    },
                    priority=priority,
                    user_id=user_id
                )
                await self._event_manager.broadcast_event(sse_event)

            # Send to polling service
            if self._polling_service:
                self._polling_service.add_notification_event(
                    message=message,
                    level=level,
                    user_id=user_id,
                    data=data
                )

            logger.info(f"System notification sent to all services: {message} ({level})")

        except Exception as e:
            logger.error(f"Failed to send system notification to legacy services: {e}")

    async def add_legacy_listener(self, listener_func: Callable):
        """Add a listener for legacy events"""
        self._legacy_listeners.append(listener_func)

    async def remove_legacy_listener(self, listener_func: Callable):
        """Remove a legacy event listener"""
        if listener_func in self._legacy_listeners:
            self._legacy_listeners.remove(listener_func)

    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            "stats": self._integration_stats.copy(),
            "active_bridges": len(self._bridging_tasks),
            "legacy_listeners": len(self._legacy_listeners),
            "services_available": {
                "sse_event_manager": self._event_manager is not None,
                "sse_client_manager": self._client_manager is not None,
                "http_streaming": self._streaming_service is not None,
                "http_polling": self._polling_service is not None
            },
            "uptime_seconds": (datetime.utcnow() - self._integration_stats['start_time']).total_seconds()
        }

    async def _shutdown_integration(self):
        """Shutdown integration services"""
        # Cancel bridge tasks
        for task in self._bridging_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._bridging_tasks.clear()
        self._legacy_listeners.clear()

        logger.info("SSE Integration shutdown complete")


# Create singleton instance
sse_integration_service = SSEIntegrationService()


def get_sse_integration_service() -> SSEIntegrationService:
    """Get the SSE integration service singleton"""
    return sse_integration_service


# Utility functions for existing services to send SSE events

async def broadcast_agent_update(agent_id: str, status: str, user_id: Optional[str] = None, **kwargs):
    """Utility function to broadcast agent updates via SSE"""
    integration_service = get_sse_integration_service()
    await integration_service.send_agent_status_to_legacy(
        agent_id=agent_id,
        status=status,
        user_id=user_id,
        additional_data=kwargs
    )


async def broadcast_task_progress(task_id: str, progress: float, agent_id: Optional[str] = None,
                                user_id: Optional[str] = None, message: Optional[str] = None):
    """Utility function to broadcast task progress via SSE"""
    integration_service = get_sse_integration_service()
    await integration_service.send_task_progress_to_legacy(
        task_id=task_id,
        progress=progress,
        agent_id=agent_id,
        user_id=user_id,
        message=message
    )


async def broadcast_system_notification(message: str, level: str = "info",
                                     user_id: Optional[str] = None, **kwargs):
    """Utility function to broadcast system notifications via SSE"""
    integration_service = get_sse_integration_service()
    await integration_service.send_system_notification_to_legacy(
        message=message,
        level=level,
        user_id=user_id,
        data=kwargs
    )


# Export classes and functions
__all__ = [
    "SSEIntegrationService",
    "get_sse_integration_service",
    "broadcast_agent_update",
    "broadcast_task_progress",
    "broadcast_system_notification"
]