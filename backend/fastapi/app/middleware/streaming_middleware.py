"""
Server-Sent Events Middleware for AutoAdmin Backend
Provides HTTP-based streaming capabilities to replace WebSocket functionality
"""

import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ConnectionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track and manage HTTP streaming connections
    Replaces WebSocket connection management
    """

    def __init__(self, app, max_connections: int = 1000):
        super().__init__(app)
        self.max_connections = max_connections
        self.active_connections: Dict[str, Dict] = {}
        self.connection_history: List[Dict] = []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track streaming connections"""

        # Check if this is a streaming request
        if request.url.path.endswith('/events/') or 'stream' in request.url.path:
            connection_id = self._generate_connection_id()

            # Check connection limit
            if len(self.active_connections) >= self.max_connections:
                raise HTTPException(
                    status_code=503,
                    detail="Maximum number of streaming connections reached"
                )

            # Track connection
            self.active_connections[connection_id] = {
                "id": connection_id,
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "started_at": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }

            try:
                response = await call_next(request)

                # Add connection headers
                response.headers["X-Connection-ID"] = connection_id
                response.headers["X-Connection-Count"] = str(len(self.active_connections))

                return response

            except Exception as e:
                # Clean up connection on error
                self._cleanup_connection(connection_id)
                raise

        # Non-streaming request
        response = await call_next(request)
        return response

    def _generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        return f"conn_{int(time.time() * 1000)}_{hash(datetime.utcnow())}"

    def _cleanup_connection(self, connection_id: str):
        """Clean up connection and move to history"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            connection["ended_at"] = datetime.utcnow()
            connection["duration"] = (connection["ended_at"] - connection["started_at"]).seconds

            # Move to history
            self.connection_history.append(connection)

            # Keep only recent history (last 1000 connections)
            if len(self.connection_history) > 1000:
                self.connection_history.pop(0)

            # Remove from active connections
            del self.active_connections[connection_id]

            logger.info(f"Cleaned up connection {connection_id}")

    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "max_connections": self.max_connections,
            "total_connections": len(self.connection_history),
            "connection_history_size": len(self.connection_history)
        }


class SSEMiddleware(BaseHTTPMiddleware):
    """
    Server-Sent Events middleware to handle SSE requests properly
    Replaces WebSocket middleware with HTTP-based streaming
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle SSE responses"""

        # Process request
        response = await call_next(request)

        # Enhance SSE responses with proper headers
        if (isinstance(response, StreamingResponse) and
            "text/event-stream" in str(response.media_type)):

            # Add proper SSE headers
            response.headers.update({
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "X-Content-Type-Options": "nosniff"
            })

            logger.info(f"SSE response prepared for {request.url.path}")

        return response


class HTTPPollingMiddleware(BaseHTTPMiddleware):
    """
    HTTP Long Polling middleware to handle long-running requests
    Provides WebSocket-like functionality through HTTP polling
    """

    def __init__(self, app, max_poll_time: int = 60):
        super().__init__(app)
        self.max_poll_time = max_poll_time
        self.active_polls: Dict[str, Dict] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle long polling"""

        # Check if this is a polling request
        if "/poll" in request.url.path:
            poll_id = self._generate_poll_id()

            # Track poll
            self.active_polls[poll_id] = {
                "id": poll_id,
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else None,
                "started_at": datetime.utcnow(),
                "timeout": self.max_poll_time
            }

            try:
                response = await call_next(request)

                # Add poll headers
                response.headers["X-Poll-ID"] = poll_id
                response.headers["X-Poll-Duration"] = str(
                    int((datetime.utcnow() - self.active_polls[poll_id]["started_at"]).total_seconds())
                )

                # Clean up poll
                self._cleanup_poll(poll_id)

                return response

            except Exception as e:
                self._cleanup_poll(poll_id)
                raise

        # Non-polling request
        return await call_next(request)

    def _generate_poll_id(self) -> str:
        """Generate unique poll ID"""
        return f"poll_{int(time.time() * 1000)}_{hash(datetime.utcnow())}"

    def _cleanup_poll(self, poll_id: str):
        """Clean up completed poll"""
        if poll_id in self.active_polls:
            poll = self.active_polls[poll_id]
            poll["completed_at"] = datetime.utcnow()
            poll["duration"] = (poll["completed_at"] - poll["started_at"]).total_seconds()

            logger.info(f"Completed poll {poll_id} in {poll['duration']:.2f}s")
            del self.active_polls[poll_id]

    def get_poll_stats(self) -> Dict:
        """Get polling statistics"""
        return {
            "active_polls": len(self.active_polls),
            "max_poll_time": self.max_poll_time,
            "active_poll_details": list(self.active_polls.values())
        }


class StreamingHealthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor health of streaming connections
    """

    def __init__(self, app, health_check_interval: int = 30):
        super().__init__(app)
        self.health_check_interval = health_check_interval
        self.health_stats = {
            "total_requests": 0,
            "streaming_requests": 0,
            "polling_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "last_health_check": None
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request health metrics"""

        start_time = time.time()
        self.health_stats["total_requests"] += 1

        # Categorize request type
        is_streaming = "stream" in request.url.path or "/events/" in request.url.path
        is_polling = "/poll" in request.url.path

        if is_streaming:
            self.health_stats["streaming_requests"] += 1
        elif is_polling:
            self.health_stats["polling_requests"] += 1

        try:
            response = await call_next(request)

            # Update response time
            response_time = time.time() - start_time
            self._update_average_response_time(response_time)

            # Add health headers
            response.headers["X-Response-Time"] = f"{response_time:.3f}"
            response.headers["X-Total-Requests"] = str(self.health_stats["total_requests"])
            response.headers["X-Streaming-Requests"] = str(self.health_stats["streaming_requests"])

            return response

        except Exception as e:
            self.health_stats["failed_requests"] += 1
            logger.error(f"Request failed: {e}")
            raise

    def _update_average_response_time(self, response_time: float):
        """Update average response time"""
        total_requests = self.health_stats["total_requests"]
        current_avg = self.health_stats["average_response_time"]

        # Calculate new average
        new_avg = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        self.health_stats["average_response_time"] = new_avg

    def get_health_stats(self) -> Dict:
        """Get health statistics"""
        return {
            **self.health_stats,
            "success_rate": 1.0 - (self.health_stats["failed_requests"] / max(1, self.health_stats["total_requests"])),
            "streaming_ratio": self.health_stats["streaming_requests"] / max(1, self.health_stats["total_requests"]),
            "polling_ratio": self.health_stats["polling_requests"] / max(1, self.health_stats["total_requests"])
        }


# Utility function to create and apply all streaming middleware
def apply_streaming_middleware(app, max_connections: int = 1000, max_poll_time: int = 60):
    """Apply all streaming-related middleware to FastAPI app"""

    # Add connection tracking
    connection_tracker = ConnectionTrackingMiddleware(app, max_connections)

    # Add SSE support
    sse_middleware = SSEMiddleware(connection_tracker)

    # Add polling support
    polling_middleware = HTTPPollingMiddleware(sse_middleware, max_poll_time)

    # Add health monitoring
    health_middleware = StreamingHealthMiddleware(polling_middleware)

    logger.info("Applied streaming middleware stack")

    return health_middleware


# Export middleware classes
__all__ = [
    'ConnectionTrackingMiddleware',
    'SSEMiddleware',
    'HTTPPollingMiddleware',
    'StreamingHealthMiddleware',
    'apply_streaming_middleware'
]