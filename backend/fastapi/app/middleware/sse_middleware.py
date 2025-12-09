"""
Server-Sent Events (SSE) middleware for HTTP-only real-time communication
Handles SSE-specific headers and connection management
"""

import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SSEMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle Server-Sent Events specific headers and configuration
    Ensures proper SSE support for HTTP-only real-time communication
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add SSE-specific headers if needed

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response with appropriate SSE headers if applicable
        """
        # Check if this is likely an SSE request
        is_sse_request = (
            "text/event-stream" in request.headers.get("accept", "") or
            request.url.path.endswith("/stream") or
            "sse" in request.url.path
        )

        if is_sse_request:
            self.logger.info(
                "SSE request detected",
                extra={
                    "path": request.url.path,
                    "accept": request.headers.get("accept"),
                    "user_agent": request.headers.get("user-agent"),
                }
            )

            # Process the request
            response = await call_next(request)

            # Add SSE-specific headers to streaming responses
            if isinstance(response, StreamingResponse):
                response.headers.update({
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                    "X-Content-Type-Options": "nosniff",
                })

                self.logger.info(
                    "SSE response headers added",
                    extra={
                        "headers": dict(response.headers),
                        "path": request.url.path,
                    }
                )

            return response

        # For non-SSE requests, add helpful headers for HTTP polling
        response = await call_next(request)

        # Add polling-friendly headers to API responses
        if request.url.path.startswith("/api/v1/"):
            # Add headers that help with HTTP polling and caching
            if hasattr(response, 'headers'):
                response.headers.update({
                    "Access-Control-Allow-Headers": "Last-Event-ID, If-Modified-Since, If-None-Match",
                    "Access-Control-Expose-Headers": "ETag, Last-Modified, Cache-Control",
                })

        return response


class HTTPPollingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to optimize responses for HTTP polling scenarios
    Adds caching headers and ETags for efficient polling
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add polling-friendly headers and handle conditional requests

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response optimized for polling scenarios
        """
        # Check if this is a polling request
        is_polling_request = (
            request.url.path.endswith("/poll") or
            "last_seen" in request.query_params or
            "If-Modified-Since" in request.headers or
            "If-None-Match" in request.headers
        )

        # Check for long polling timeout parameter
        timeout = request.query_params.get("timeout", "0")
        is_long_polling = float(timeout) > 0

        if is_polling_request:
            self.logger.info(
                "Polling request detected",
                extra={
                    "path": request.url.path,
                    "is_long_polling": is_long_polling,
                    "timeout": timeout,
                    "query_params": dict(request.query_params),
                }
            )

        response = await call_next(request)

        # Add polling-optimized headers
        if is_polling_request and hasattr(response, 'headers'):
            response.headers.update({
                "Cache-Control": "no-cache, must-revalidate" if not is_long_polling else "no-cache",
                "Pragma": "no-cache",
                "Expires": "0",
            })

            # Add ETag for polling endpoints if not present
            if "ETag" not in response.headers:
                # Create simple ETag from response content
                try:
                    content = response.body if hasattr(response, 'body') else str(response)
                    etag = f'"{hash(content) % (2**32)}"'
                    response.headers["ETag"] = etag
                except Exception:
                    # Fallback ETag
                    response.headers["ETag"] = '"polling-response"'

            # Add Last-Modified if not present
            if "Last-Modified" not in response.headers:
                from datetime import datetime
                response.headers["Last-Modified"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

            self.logger.debug(
                "Polling response headers added",
                extra={
                    "headers": dict(response.headers),
                    "etag": response.headers.get("ETag"),
                }
            )

        return response


class ConnectionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track active SSE and polling connections
    Helps manage connection limits and monitoring
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger(__name__)
        self._active_connections = set()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Track connection lifecycle for monitoring and management

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response with connection tracking
        """
        connection_id = f"{request.client.host}:{request.url.path}:{id(request)}"

        # Track streaming connections
        is_streaming = (
            "text/event-stream" in request.headers.get("accept", "") or
            request.url.path.endswith("/stream")
        )

        if is_streaming:
            self._active_connections.add(connection_id)
            self.logger.info(
                "Streaming connection established",
                extra={
                    "connection_id": connection_id,
                    "path": request.url.path,
                    "active_connections": len(self._active_connections),
                }
            )

        try:
            response = await call_next(request)
            return response
        finally:
            # Clean up connection tracking
            if is_streaming and connection_id in self._active_connections:
                self._active_connections.remove(connection_id)
                self.logger.info(
                    "Streaming connection closed",
                    extra={
                        "connection_id": connection_id,
                        "active_connections": len(self._active_connections),
                    }
                )

    def get_active_connections_count(self) -> int:
        """Get current number of active streaming connections"""
        return len(self._active_connections)

    def get_connection_stats(self) -> dict:
        """Get connection statistics for monitoring"""
        return {
            "active_connections": len(self._active_connections),
            "max_connections": 1000,  # Configurable limit
            "connection_ids": list(self._active_connections),
        }


# Export middleware classes
__all__ = [
    "SSEMiddleware",
    "HTTPPollingMiddleware",
    "ConnectionTrackingMiddleware"
]