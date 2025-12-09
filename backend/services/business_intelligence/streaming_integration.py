"""
Business Intelligence Streaming Integration
Comprehensive integration between business intelligence modules and HTTP streaming system
using Server-Sent Events for real-time updates and notifications.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import HTTPException
from fastapi.responses import StreamingResponse


class StreamingEventType(str, Enum):
    """Types of streaming events"""
    MORNING_BRIEFING_UPDATE = "morning_briefing_update"
    KPI_UPDATE = "kpi_update"
    REVENUE_UPDATE = "revenue_update"
    TASK_DELEGATION_UPDATE = "task_delegation_update"
    COMPETITIVE_UPDATE = "competitive_update"
    CRM_UPDATE = "crm_update"
    STRATEGIC_PLAN_UPDATE = "strategic_plan_update"
    ALERT_UPDATE = "alert_update"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class StreamingEvent:
    """Represents a streaming event"""
    event_type: StreamingEventType
    data: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_sse_format(self) -> str:
        """Convert event to Server-Sent Events format"""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)

        event_data = {
            "type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata or {}
        }

        sse_lines = [
            f"event: {self.event_type.value}",
            f"data: {json.dumps(event_data)}",
            "",  # Empty line to mark end of event
        ]
        return "\n".join(sse_lines)


class StreamingConnectionManager:
    """Manages active streaming connections"""

    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.event_subscribers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)

    def register_connection(
        self,
        connection_id: str,
        user_id: str,
        session_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a new streaming connection"""
        self.active_connections[connection_id] = {
            "user_id": user_id,
            "session_type": session_type,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "metadata": metadata or {}
        }

        self.logger.info(
            f"Registered streaming connection: {connection_id}",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "session_type": session_type,
                "active_connections": len(self.active_connections)
            }
        )

    def unregister_connection(self, connection_id: str) -> None:
        """Unregister a streaming connection"""
        if connection_id in self.active_connections:
            connection_info = self.active_connections[connection_id]
            del self.active_connections[connection_id]

            self.logger.info(
                f"Unregistered streaming connection: {connection_id}",
                extra={
                    "connection_id": connection_id,
                    "user_id": connection_info.get("user_id"),
                    "session_type": connection_info.get("session_type"),
                    "active_connections": len(self.active_connections)
                }
            )

    def update_connection_activity(self, connection_id: str) -> None:
        """Update last activity timestamp for a connection"""
        if connection_id in self.active_connections:
            self.active_connections[connection_id]["last_activity"] = datetime.now(timezone.utc)

    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a specific user"""
        return [
            conn_id for conn_id, conn_info in self.active_connections.items()
            if conn_info.get("user_id") == user_id
        ]

    def subscribe_to_events(
        self,
        event_type: StreamingEventType,
        callback: Callable[[StreamingEvent], None]
    ) -> str:
        """Subscribe to specific event types"""
        subscription_id = str(uuid.uuid4())
        if event_type.value not in self.event_subscribers:
            self.event_subscribers[event_type.value] = []

        self.event_subscribers[event_type.value].append({
            "id": subscription_id,
            "callback": callback
        })

        return subscription_id

    def unsubscribe_from_events(self, event_type: StreamingEventType, subscription_id: str) -> None:
        """Unsubscribe from event notifications"""
        if event_type.value in self.event_subscribers:
            self.event_subscribers[event_type.value] = [
                sub for sub in self.event_subscribers[event_type.value]
                if sub["id"] != subscription_id
            ]

    async def publish_event(self, event: StreamingEvent) -> None:
        """Publish an event to all relevant subscribers"""
        try:
            # Update timestamp
            event.timestamp = datetime.now(timezone.utc)

            # Notify subscribers
            if event.event_type.value in self.event_subscribers:
                for subscription in self.event_subscribers[event.event_type.value]:
                    try:
                        await subscription["callback"](event)
                    except Exception as e:
                        self.logger.error(f"Error in event subscriber callback: {e}")

            self.logger.debug(
                f"Published event: {event.event_type.value}",
                extra={
                    "event_type": event.event_type.value,
                    "user_id": event.user_id,
                    "session_id": event.session_id
                }
            )

        except Exception as e:
            self.logger.error(f"Error publishing event: {e}")

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        now = datetime.now(timezone.utc)
        active_count = 0

        for conn_info in self.active_connections.values():
            # Consider connections active if they had activity in the last 5 minutes
            if (now - conn_info["last_activity"]).seconds < 300:
                active_count += 1

        return {
            "total_connections": len(self.active_connections),
            "active_connections": active_count,
            "connections_by_type": {
                session_type: len([
                    conn for conn in self.active_connections.values()
                    if conn.get("session_type") == session_type
                ])
                for session_type in set(
                    conn.get("session_type") for conn in self.active_connections.values()
                )
            },
            "event_subscribers": {
                event_type: len(subscribers) for event_type, subscribers in self.event_subscribers.items()
            }
        }


class BIDataStreamManager:
    """Main manager for business intelligence data streaming"""

    def __init__(self):
        self.connection_manager = StreamingConnectionManager()
        self.logger = logging.getLogger(__name__)

        # Initialize BI engines (these would be injected or imported)
        self.morning_briefing_engine = None
        self.revenue_intelligence_engine = None
        self.kpi_engine = None
        self.task_delegator = None
        self.alert_system = None

        # Background tasks
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}

    def set_engines(self, **engines) -> None:
        """Set BI engines for streaming operations"""
        for name, engine in engines.items():
            setattr(self, name, engine)

    async def create_morning_briefing_stream(
        self,
        user_id: str,
        refresh_interval: int = 30
    ) -> AsyncGenerator[str, None]:
        """Create a morning briefing streaming response"""
        connection_id = f"briefing_{user_id}_{uuid.uuid4().hex[:8]}"
        self.connection_manager.register_connection(
            connection_id, user_id, "morning_briefing"
        )

        try:
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._send_heartbeat(connection_id, refresh_interval)
            )
            self.heartbeat_tasks[connection_id] = heartbeat_task

            while True:
                try:
                    # Update connection activity
                    self.connection_manager.update_connection_activity(connection_id)

                    # Generate fresh briefing
                    if self.morning_briefing_engine:
                        briefing = await self.morning_briefing_engine.generate_morning_briefing(
                            user_id=user_id,
                            date_range=None,
                            include_forecasts=True
                        )

                        # Create streaming event
                        event = StreamingEvent(
                            event_type=StreamingEventType.MORNING_BRIEFING_UPDATE,
                            data={
                                "briefing_id": briefing.id,
                                "date": briefing.date.isoformat() if hasattr(briefing.date, 'isoformat') else str(briefing.date),
                                "executive_summary": getattr(briefing, 'executive_summary', {}),
                                "key_metrics_count": len(getattr(briefing, 'key_metrics', [])),
                                "alerts_count": len(getattr(briefing, 'alerts', [])),
                                "opportunities_count": len(getattr(briefing, 'growth_opportunities', [])),
                                "strategic_priorities": getattr(briefing, 'strategic_priorities', [])
                            },
                            user_id=user_id,
                            session_id=connection_id
                        )

                        yield event.to_sse_format()

                        # Publish to internal subscribers
                        await self.connection_manager.publish_event(event)

                    # Wait before next update
                    await asyncio.sleep(refresh_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in morning briefing stream: {e}")

                    # Send error event
                    error_event = StreamingEvent(
                        event_type=StreamingEventType.ERROR,
                        data={"error": str(e), "context": "morning_briefing_stream"},
                        user_id=user_id,
                        session_id=connection_id
                    )
                    yield error_event.to_sse_format()

        finally:
            # Cleanup
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]

            self.connection_manager.unregister_connection(connection_id)

    async def create_kpi_dashboard_stream(
        self,
        dashboard_id: str,
        user_id: str,
        refresh_interval: int = 60
    ) -> AsyncGenerator[str, None]:
        """Create a KPI dashboard streaming response"""
        connection_id = f"kpi_{user_id}_{dashboard_id}_{uuid.uuid4().hex[:8]}"
        self.connection_manager.register_connection(
            connection_id, user_id, "kpi_dashboard",
            {"dashboard_id": dashboard_id}
        )

        try:
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._send_heartbeat(connection_id, refresh_interval)
            )
            self.heartbeat_tasks[connection_id] = heartbeat_task

            while True:
                try:
                    # Update connection activity
                    self.connection_manager.update_connection_activity(connection_id)

                    # Get dashboard data
                    if self.kpi_engine:
                        dashboard = await self.kpi_engine.get_kpi_dashboard(
                            user_id=user_id,
                            dashboard_id=dashboard_id,
                            real_time=True
                        )

                        # Create streaming event
                        event = StreamingEvent(
                            event_type=StreamingEventType.KPI_UPDATE,
                            data={
                                "dashboard_id": dashboard_id,
                                "summary": dashboard.get("summary", {}),
                                "kpi_values": dashboard.get("kpi_values", []),
                                "last_updated": dashboard.get("last_updated"),
                                "trend_data": dashboard.get("trend_data", {}),
                                "alert_count": len(dashboard.get("active_alerts", []))
                            },
                            user_id=user_id,
                            session_id=connection_id,
                            metadata={"dashboard_id": dashboard_id}
                        )

                        yield event.to_sse_format()

                        # Publish to internal subscribers
                        await self.connection_manager.publish_event(event)

                    # Wait before next update
                    await asyncio.sleep(refresh_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in KPI dashboard stream: {e}")

                    # Send error event
                    error_event = StreamingEvent(
                        event_type=StreamingEventType.ERROR,
                        data={"error": str(e), "context": "kpi_dashboard_stream"},
                        user_id=user_id,
                        session_id=connection_id
                    )
                    yield error_event.to_sse_format()

        finally:
            # Cleanup
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]

            self.connection_manager.unregister_connection(connection_id)

    async def create_alerts_stream(
        self,
        user_id: str,
        refresh_interval: int = 15
    ) -> AsyncGenerator[str, None]:
        """Create an alerts streaming response"""
        connection_id = f"alerts_{user_id}_{uuid.uuid4().hex[:8]}"
        self.connection_manager.register_connection(
            connection_id, user_id, "alerts"
        )

        try:
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._send_heartbeat(connection_id, refresh_interval)
            )
            self.heartbeat_tasks[connection_id] = heartbeat_task

            while True:
                try:
                    # Update connection activity
                    self.connection_manager.update_connection_activity(connection_id)

                    # Get alerts data
                    if self.alert_system:
                        alerts_data = await self.alert_system.get_active_alerts(
                            user_id=user_id
                        )

                        # Create streaming event
                        event = StreamingEvent(
                            event_type=StreamingEventType.ALERT_UPDATE,
                            data={
                                "active_alerts": alerts_data.get("active_alerts", []),
                                "alert_count": len(alerts_data.get("active_alerts", [])),
                                "severity_distribution": alerts_data.get("severity_distribution", {}),
                                "recent_escalations": alerts_data.get("recent_escalations", [])
                            },
                            user_id=user_id,
                            session_id=connection_id
                        )

                        yield event.to_sse_format()

                        # Publish to internal subscribers
                        await self.connection_manager.publish_event(event)

                    # Wait before next update
                    await asyncio.sleep(refresh_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in alerts stream: {e}")

                    # Send error event
                    error_event = StreamingEvent(
                        event_type=StreamingEventType.ERROR,
                        data={"error": str(e), "context": "alerts_stream"},
                        user_id=user_id,
                        session_id=connection_id
                    )
                    yield error_event.to_sse_format()

        finally:
            # Cleanup
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]

            self.connection_manager.unregister_connection(connection_id)

    async def create_executive_dashboard_stream(
        self,
        user_id: str,
        refresh_interval: int = 30
    ) -> AsyncGenerator[str, None]:
        """Create a comprehensive executive dashboard streaming response"""
        connection_id = f"executive_{user_id}_{uuid.uuid4().hex[:8]}"
        self.connection_manager.register_connection(
            connection_id, user_id, "executive_dashboard"
        )

        try:
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._send_heartbeat(connection_id, refresh_interval)
            )
            self.heartbeat_tasks[connection_id] = heartbeat_task

            while True:
                try:
                    # Update connection activity
                    self.connection_manager.update_connection_activity(connection_id)

                    # Collect data from all BI modules
                    dashboard_data = {}

                    if self.morning_briefing_engine:
                        try:
                            briefing = await self.morning_briefing_engine.get_latest_briefing(user_id)
                            dashboard_data["morning_briefing"] = {
                                "id": briefing.id,
                                "date": briefing.date.isoformat() if hasattr(briefing.date, 'isoformat') else str(briefing.date),
                                "health_score": getattr(briefing, 'health_score', 0)
                            }
                        except Exception as e:
                            self.logger.warning(f"Error getting morning briefing: {e}")

                    if self.revenue_intelligence_engine:
                        try:
                            revenue_data = await self.revenue_intelligence_engine.get_current_metrics(user_id)
                            dashboard_data["revenue_metrics"] = {
                                "current_mrr": getattr(revenue_data, 'current_mrr', 0),
                                "growth_rate": getattr(revenue_data, 'growth_rate', 0),
                                "health_status": getattr(revenue_data, 'health_status', 'unknown')
                            }
                        except Exception as e:
                            self.logger.warning(f"Error getting revenue metrics: {e}")

                    if self.kpi_engine:
                        try:
                            kpi_summary = await self.kpi_engine.get_kpi_summary(user_id)
                            dashboard_data["kpi_summary"] = {
                                "overall_health": getattr(kpi_summary, 'overall_health', 0),
                                "critical_count": getattr(kpi_summary, 'critical_count', 0),
                                "healthy_count": getattr(kpi_summary, 'healthy_count', 0)
                            }
                        except Exception as e:
                            self.logger.warning(f"Error getting KPI summary: {e}")

                    if self.alert_system:
                        try:
                            alerts = await self.alert_system.get_alert_summary(user_id)
                            dashboard_data["alerts"] = {
                                "active_count": getattr(alerts, 'active_count', 0),
                                "critical_count": getattr(alerts, 'critical_count', 0),
                                "resolution_rate": getattr(alerts, 'resolution_rate', 0)
                            }
                        except Exception as e:
                            self.logger.warning(f"Error getting alerts summary: {e}")

                    # Create comprehensive streaming event
                    event = StreamingEvent(
                        event_type=StreamingEventType.SYSTEM_STATUS,
                        data={
                            "dashboard_data": dashboard_data,
                            "last_updated": datetime.now(timezone.utc).isoformat(),
                            "data_sources": list(dashboard_data.keys())
                        },
                        user_id=user_id,
                        session_id=connection_id
                    )

                    yield event.to_sse_format()

                    # Publish to internal subscribers
                    await self.connection_manager.publish_event(event)

                    # Wait before next update
                    await asyncio.sleep(refresh_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in executive dashboard stream: {e}")

                    # Send error event
                    error_event = StreamingEvent(
                        event_type=StreamingEventType.ERROR,
                        data={"error": str(e), "context": "executive_dashboard_stream"},
                        user_id=user_id,
                        session_id=connection_id
                    )
                    yield error_event.to_sse_format()

        finally:
            # Cleanup
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]

            self.connection_manager.unregister_connection(connection_id)

    async def _send_heartbeat(self, connection_id: str, interval: int) -> None:
        """Send periodic heartbeat events for connection monitoring"""
        while True:
            try:
                await asyncio.sleep(interval * 2)  # Send heartbeat less frequently than data updates

                heartbeat_event = StreamingEvent(
                    event_type=StreamingEventType.HEARTBEAT,
                    data={
                        "connection_id": connection_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    session_id=connection_id
                )

                # Publish heartbeat internally (not sent to client)
                await self.connection_manager.publish_event(heartbeat_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error sending heartbeat: {e}")
                break

    async def cleanup_stale_connections(self) -> None:
        """Clean up connections that have been inactive for too long"""
        now = datetime.now(timezone.utc)
        stale_connections = []

        for connection_id, conn_info in self.connection_manager.active_connections.items():
            # Remove connections inactive for more than 10 minutes
            if (now - conn_info["last_activity"]).seconds > 600:
                stale_connections.append(connection_id)

        for connection_id in stale_connections:
            self.logger.info(f"Cleaning up stale connection: {connection_id}")

            # Cancel heartbeat task if exists
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]

            self.connection_manager.unregister_connection(connection_id)

    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get comprehensive streaming statistics"""
        return {
            "connections": self.connection_manager.get_connection_stats(),
            "heartbeat_tasks": len(self.heartbeat_tasks),
            "engines_status": {
                "morning_briefing": self.morning_briefing_engine is not None,
                "revenue_intelligence": self.revenue_intelligence_engine is not None,
                "kpi_engine": self.kpi_engine is not None,
                "task_delegator": self.task_delegator is not None,
                "alert_system": self.alert_system is not None
            }
        }


# Global streaming manager instance
streaming_manager = BIDataStreamManager()


# Utility functions for FastAPI integration
def create_streaming_response(
    stream_generator: AsyncGenerator[str, None],
    stream_type: str
) -> StreamingResponse:
    """Create a properly configured streaming response"""
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Stream-Type": stream_type,
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# Background task for periodic cleanup
async def start_streaming_cleanup_task():
    """Start background task for cleaning up stale connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            await streaming_manager.cleanup_stale_connections()
        except Exception as e:
            logging.error(f"Error in streaming cleanup task: {e}")


# Export main components
__all__ = [
    "StreamingEventType",
    "StreamingEvent",
    "StreamingConnectionManager",
    "BIDataStreamManager",
    "streaming_manager",
    "create_streaming_response",
    "start_streaming_cleanup_task"
]