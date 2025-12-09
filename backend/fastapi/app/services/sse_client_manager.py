"""
SSE Client Manager for AutoAdmin Backend
Manages SSE client connections, authentication, and connection lifecycle
Provides comprehensive client tracking with health monitoring and graceful disconnection
"""

import asyncio
import time
import uuid
import json
import weakref
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse
from app.responses.sse import SSEEvent, SSEPriority, SSEEventType

logger = logging.getLogger(__name__)


class ClientStatus(Enum):
    """Client connection status"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"


class ClientType(Enum):
    """Types of SSE clients"""
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass
class ClientConnection:
    """SSE client connection information"""
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_type: ClientType = ClientType.WEB
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: ClientStatus = ClientStatus.CONNECTING
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    subscription_ids: List[str] = field(default_factory=list)
    event_filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_authenticated: bool = False
    connection_limit: Optional[int] = None
    ping_interval: int = 30
    timeout_seconds: int = 300
    max_events_per_minute: Optional[int] = None

    def update_activity(self):
        """Update client last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def update_ping(self):
        """Update client last ping timestamp"""
        self.last_ping = datetime.utcnow()

    def is_timeout(self) -> bool:
        """Check if client connection has timed out"""
        return (datetime.utcnow() - self.last_activity).seconds > self.timeout_seconds

    def is_stale(self) -> bool:
        """Check if client connection is stale (no recent pings)"""
        return (datetime.utcnow() - self.last_ping).seconds > (self.ping_interval * 3)

    def to_dict(self) -> Dict[str, Any]:
        """Convert client connection to dictionary"""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "connection_id": self.connection_id,
            "client_type": self.client_type.value,
            "ip_address": self.ip_address,
            "status": self.status.value,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "subscription_count": len(self.subscription_ids),
            "is_authenticated": self.is_authenticated,
            "ping_interval": self.ping_interval,
            "timeout_seconds": self.timeout_seconds
        }


@dataclass
class ClientMetrics:
    """Client connection metrics"""
    client_id: str
    events_sent: int = 0
    events_received: int = 0
    bytes_sent: int = 0
    connection_duration: float = 0.0
    reconnections: int = 0
    errors: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

    def reset_metrics(self):
        """Reset metrics counters"""
        self.events_sent = 0
        self.events_received = 0
        self.bytes_sent = 0
        self.errors = 0
        self.last_reset = datetime.utcnow()


class SSEClientManager:
    """
    Comprehensive SSE Client Manager
    Manages client connections, authentication, and lifecycle
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SSEClientManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._clients: Dict[str, ClientConnection] = {}
            self._client_metrics: Dict[str, ClientMetrics] = {}
            self._user_clients: Dict[str, List[str]] = defaultdict(list)
            self._session_clients: Dict[str, str] = {}  # session_id -> client_id
            self._ip_clients: Dict[str, List[str]] = defaultdict(list)
            self._client_cleanup_task = None
            self._connection_limits = {
                'default': 10,
                'authenticated': 50,
                'api': 100
            }
            self._global_limit = 1000
            self._stats = {
                'total_clients': 0,
                'active_clients': 0,
                'authenticated_clients': 0,
                'connections_created': 0,
                'connections_closed': 0,
                'timeout_disconnections': 0,
                'error_disconnections': 0,
                'start_time': datetime.utcnow()
            }
            self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start the client cleanup task"""
        if self._client_cleanup_task is None:
            self._client_cleanup_task = asyncio.create_task(self._cleanup_clients())

    async def _cleanup_clients(self):
        """Background task to clean up inactive clients"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._remove_stale_clients()
            except Exception as e:
                logger.error(f"Client cleanup error: {e}")
                await asyncio.sleep(5)

    async def create_client(
        self,
        request: Request,
        user_id: Optional[str] = None,
        client_type: ClientType = ClientType.WEB,
        event_filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClientConnection:
        """
        Create a new SSE client connection

        Args:
            request: FastAPI request object
            user_id: User identifier
            client_type: Type of client
            event_filters: Event filters for this client
            metadata: Additional client metadata

        Returns:
            ClientConnection: Created client connection
        """
        client = ClientConnection(
            user_id=user_id,
            client_type=client_type,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            event_filters=event_filters or {},
            metadata=metadata or {}
        )

        # Check connection limits
        if not await self._check_connection_limits(client):
            raise HTTPException(
                status_code=429,
                detail="Connection limit exceeded"
            )

        # Set authentication status
        client.is_authenticated = bool(user_id)
        client.status = ClientStatus.CONNECTED

        # Store client
        self._clients[client.client_id] = client
        self._client_metrics[client.client_id] = ClientMetrics(client_id=client.client_id)

        # Update indexes
        if user_id:
            self._user_clients[user_id].append(client.client_id)
        self._session_clients[client.session_id] = client.client_id
        if client.ip_address:
            self._ip_clients[client.ip_address].append(client.client_id)

        # Update stats
        self._stats['total_clients'] = len(self._clients)
        self._stats['active_clients'] = len([c for c in self._clients.values() if c.status == ClientStatus.CONNECTED])
        self._stats['authenticated_clients'] = len([c for c in self._clients.values() if c.is_authenticated])
        self._stats['connections_created'] += 1

        logger.info(
            f"Created SSE client",
            client_id=client.client_id,
            user_id=user_id,
            client_type=client_type.value,
            ip_address=client.ip_address
        )

        return client

    async def _check_connection_limits(self, client: ClientConnection) -> bool:
        """Check if client connection is allowed based on limits"""
        # Check global limit
        if len(self._clients) >= self._global_limit:
            logger.warning("Global connection limit reached")
            return False

        # Check per-user limit
        if client.user_id:
            user_limit = self._connection_limits['authenticated'] if client.is_authenticated else self._connection_limits['default']
            current_user_connections = len(self._user_clients.get(client.user_id, []))
            if current_user_connections >= user_limit:
                logger.warning(f"User {client.user_id} connection limit reached")
                return False

        # Check per-IP limit
        if client.ip_address:
            ip_limit = self._connection_limits.get(client.client_type.value, self._connection_limits['default'])
            current_ip_connections = len(self._ip_clients.get(client.ip_address, []))
            if current_ip_connections >= ip_limit:
                logger.warning(f"IP {client.ip_address} connection limit reached")
                return False

        return True

    def get_client(self, client_id: str) -> Optional[ClientConnection]:
        """Get client connection by ID"""
        return self._clients.get(client_id)

    def get_client_by_session(self, session_id: str) -> Optional[ClientConnection]:
        """Get client connection by session ID"""
        client_id = self._session_clients.get(session_id)
        if client_id:
            return self._clients.get(client_id)
        return None

    def get_user_clients(self, user_id: str) -> List[ClientConnection]:
        """Get all client connections for a user"""
        client_ids = self._user_clients.get(user_id, [])
        return [self._clients.get(cid) for cid in client_ids if cid in self._clients]

    async def update_client_status(self, client_id: str, status: ClientStatus) -> bool:
        """Update client connection status"""
        client = self._clients.get(client_id)
        if not client:
            return False

        client.status = status
        client.update_activity()

        # Update stats
        self._stats['active_clients'] = len([c for c in self._clients.values() if c.status == ClientStatus.CONNECTED])

        return True

    async def remove_client(self, client_id: str, reason: str = "manual") -> bool:
        """Remove a client connection"""
        client = self._clients.get(client_id)
        if not client:
            return False

        # Update status
        await self.update_client_status(client_id, ClientStatus.DISCONNECTED)

        # Remove from indexes
        if client.user_id and client_id in self._user_clients.get(client.user_id, []):
            self._user_clients[client.user_id].remove(client_id)
            if not self._user_clients[client.user_id]:
                del self._user_clients[client.user_id]

        if client.session_id in self._session_clients:
            del self._session_clients[client.session_id]

        if client.ip_address and client_id in self._ip_clients.get(client.ip_address, []):
            self._ip_clients[client.ip_address].remove(client_id)
            if not self._ip_clients[client.ip_address]:
                del self._ip_clients[client.ip_address]

        # Remove client and metrics
        del self._clients[client_id]
        if client_id in self._client_metrics:
            del self._client_metrics[client_id]

        # Update stats
        self._stats['total_clients'] = len(self._clients)
        self._stats['active_clients'] = len([c for c in self._clients.values() if c.status == ClientStatus.CONNECTED])
        self._stats['authenticated_clients'] = len([c for c in self._clients.values() if c.is_authenticated])
        self._stats['connections_closed'] += 1

        if reason == "timeout":
            self._stats['timeout_disconnections'] += 1
        elif reason == "error":
            self._stats['error_disconnections'] += 1

        logger.info(
            f"Removed SSE client",
            client_id=client_id,
            reason=reason,
            user_id=client.user_id
        )

        return True

    async def _remove_stale_clients(self):
        """Remove stale and timeout clients"""
        current_time = datetime.utcnow()
        stale_clients = []

        for client_id, client in self._clients.items():
            if client.is_timeout():
                stale_clients.append((client_id, "timeout"))
            elif client.is_stale() and client.status != ClientStatus.DISCONNECTED:
                stale_clients.append((client_id, "stale"))

        for client_id, reason in stale_clients:
            await self.remove_client(client_id, reason)

    def update_client_activity(self, client_id: str):
        """Update client activity timestamp"""
        client = self._clients.get(client_id)
        if client:
            client.update_activity()

    def update_client_ping(self, client_id: str):
        """Update client ping timestamp"""
        client = self._clients.get(client_id)
        if client:
            client.update_ping()

    def add_subscription(self, client_id: str, subscription_id: str):
        """Add subscription to client"""
        client = self._clients.get(client_id)
        if client and subscription_id not in client.subscription_ids:
            client.subscription_ids.append(subscription_id)

    def remove_subscription(self, client_id: str, subscription_id: str):
        """Remove subscription from client"""
        client = self._clients.get(client_id)
        if client and subscription_id in client.subscription_ids:
            client.subscription_ids.remove(subscription_id)

    def get_client_metrics(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a client"""
        metrics = self._client_metrics.get(client_id)
        if not metrics:
            return None

        client = self._clients.get(client_id)
        if client:
            metrics.connection_duration = (datetime.utcnow() - client.connected_at).total_seconds()

        return {
            "client_id": client_id,
            "events_sent": metrics.events_sent,
            "events_received": metrics.events_received,
            "bytes_sent": metrics.bytes_sent,
            "connection_duration": metrics.connection_duration,
            "reconnections": metrics.reconnections,
            "errors": metrics.errors,
            "last_reset": metrics.last_reset.isoformat()
        }

    def update_client_metrics(self, client_id: str, **updates):
        """Update client metrics"""
        metrics = self._client_metrics.get(client_id)
        if metrics:
            for key, value in updates.items():
                if hasattr(metrics, key):
                    setattr(metrics, key, value)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        client_type_counts = defaultdict(int)
        status_counts = defaultdict(int)

        for client in self._clients.values():
            client_type_counts[client.client_type.value] += 1
            status_counts[client.status.value] += 1

        return {
            "stats": self._stats.copy(),
            "total_clients": len(self._clients),
            "active_clients": len([c for c in self._clients.values() if c.status == ClientStatus.CONNECTED]),
            "authenticated_clients": len([c for c in self._clients.values() if c.is_authenticated]),
            "client_types": dict(client_type_counts),
            "client_statuses": dict(status_counts),
            "unique_users": len(self._user_clients),
            "unique_ips": len(self._ip_clients),
            "uptime_seconds": (datetime.utcnow() - self._stats['start_time']).total_seconds()
        }

    async def create_client_stream(
        self,
        client: ClientConnection,
        event_generator
    ) -> StreamingResponse:
        """
        Create streaming response for a client

        Args:
            client: Client connection
            event_generator: Async generator yielding events

        Returns:
            StreamingResponse: FastAPI streaming response
        """
        async def client_event_stream():
            try:
                # Send initial connection event
                connection_event = SSEEvent(
                    event_type=SSEEventType.CONNECTION_STATUS,
                    data={
                        "client_id": client.client_id,
                        "status": "connected",
                        "message": "SSE connection established",
                        "ping_interval": client.ping_interval
                    },
                    priority=SSEPriority.NORMAL,
                    user_id=client.user_id,
                    connection_id=client.connection_id
                )
                yield connection_event

                # Update client status
                await self.update_client_status(client.client_id, ClientStatus.CONNECTED)

                # Stream events
                async for event in event_generator:
                    # Update client activity
                    self.update_client_activity(client.client_id)

                    # Update metrics
                    self.update_client_metrics(
                        client.client_id,
                        events_sent=1,
                        bytes_sent=len(json.dumps(event.to_dict()))
                    )

                    yield event

            except Exception as e:
                logger.error(f"Client stream error for {client.client_id}: {e}")
                self.update_client_metrics(client.client_id, errors=1)

                # Send error event
                error_event = SSEEvent(
                    event_type=SSEEventType.ERROR,
                    data={
                        "client_id": client.client_id,
                        "error": str(e),
                        "message": "Client stream encountered an error"
                    },
                    priority=SSEPriority.CRITICAL,
                    user_id=client.user_id,
                    connection_id=client.connection_id
                )
                yield error_event

            finally:
                # Clean up client
                await self.remove_client(client.client_id, "stream_end")

        from app.responses.sse import SSEResponse
        return SSEResponse.create_event_stream(
            client_event_stream(),
            ping_interval=client.ping_interval,
            max_duration=client.timeout_seconds
        )

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address from request"""
        # Check for forwarded IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host

        return None

    async def shutdown(self):
        """Shutdown the client manager"""
        if self._client_cleanup_task:
            self._client_cleanup_task.cancel()
            try:
                await self._client_cleanup_task
            except asyncio.CancelledError:
                pass

        # Remove all clients
        client_ids = list(self._clients.keys())
        for client_id in client_ids:
            await self.remove_client(client_id, "shutdown")

        logger.info("SSE Client Manager shutdown complete")


# Create singleton instance
sse_client_manager = SSEClientManager()


def get_sse_client_manager() -> SSEClientManager:
    """Get the SSE client manager singleton"""
    return sse_client_manager


# Export classes and functions
__all__ = [
    "SSEClientManager",
    "get_sse_client_manager",
    "ClientConnection",
    "ClientMetrics",
    "ClientStatus",
    "ClientType"
]