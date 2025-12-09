"""
Rate limiting middleware for API endpoints
Implements token bucket algorithm with Redis backend
"""

import time
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm
    Stores rate limit state in Redis for distributed applications
    """

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_window = settings.RATE_LIMIT_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiting middleware"""

        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        rate_limit_result = await self._check_rate_limit(client_id)

        # Add rate limit headers to response
        response = await call_next(request)
        self._add_rate_limit_headers(response, rate_limit_result)

        # Check if request should be blocked
        if rate_limit_result["remaining"] <= 0:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                limit=self.requests_per_window,
                window=self.window_seconds
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {rate_limit_result['reset_time']} seconds.",
                    "limit": self.requests_per_window,
                    "window": self.window_seconds,
                    "retry_after": rate_limit_result["reset_time"]
                },
                headers={
                    "Retry-After": str(rate_limit_result["reset_time"]),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                    "X-RateLimit-Reset": str(rate_limit_result["reset_time"]),
                }
            )

        return response

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Try to get user ID from authentication (if available)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def _check_rate_limit(self, client_id: str) -> Dict[str, int]:
        """Check rate limit for client"""
        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        key = f"rate_limit:{client_id}"

        if self.redis_client:
            return await self._check_rate_limit_redis(key, current_time, window_start)
        else:
            return self._check_rate_limit_memory(key, current_time, window_start)

    async def _check_rate_limit_redis(
        self, key: str, current_time: int, window_start: int
    ) -> Dict[str, int]:
        """Check rate limit using Redis (for distributed applications)"""
        try:
            # Remove old entries outside the window
            await self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            request_count = await self.redis_client.zcard(key)

            # Add current request
            await self.redis_client.zadd(key, {str(current_time): current_time})

            # Set expiry on the key
            await self.redis_client.expire(key, self.window_seconds)

            # Calculate remaining requests
            remaining = max(0, self.requests_per_window - request_count - 1)

            # Calculate reset time
            oldest_request = await self.redis_client.zrange(key, 0, 0, withscores=True)
            reset_time = (
                int(oldest_request[0][1] + self.window_seconds - current_time)
                if oldest_request else self.window_seconds
            )

            return {
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": self.requests_per_window,
                "current": request_count + 1
            }

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fall back to allowing request if Redis fails
            return {
                "remaining": self.requests_per_window - 1,
                "reset_time": self.window_seconds,
                "limit": self.requests_per_window,
                "current": 1
            }

    def _check_rate_limit_memory(
        self, key: str, current_time: int, window_start: int
    ) -> Dict[str, int]:
        """Check rate limit using in-memory storage (for single instance)"""
        # This is a simple in-memory implementation
        # In production, use Redis for distributed rate limiting
        if not hasattr(self, "_memory_store"):
            self._memory_store = {}

        if key not in self._memory_store:
            self._memory_store[key] = []

        # Clean old requests outside the window
        self._memory_store[key] = [
            req_time for req_time in self._memory_store[key]
            if req_time > window_start
        ]

        # Count requests in current window
        request_count = len(self._memory_store[key])

        # Add current request
        self._memory_store[key].append(current_time)

        # Calculate remaining requests
        remaining = max(0, self.requests_per_window - request_count - 1)

        # Calculate reset time
        oldest_request = min(self._memory_store[key]) if self._memory_store[key] else current_time
        reset_time = max(0, oldest_request + self.window_seconds - current_time)

        return {
            "remaining": remaining,
            "reset_time": reset_time,
            "limit": self.requests_per_window,
            "current": request_count + 1
        }

    def _add_rate_limit_headers(self, response: Response, rate_limit_result: Dict[str, int]):
        """Add rate limit headers to response"""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_result["reset_time"])