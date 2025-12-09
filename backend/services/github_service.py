"""
Enhanced GitHub Service with Circuit Breaker, Retry Logic, and Token Management
Handles GitHub API integration with robust error handling and recovery mechanisms
"""

import os
import logging
import json
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import requests
from github import Github, GithubException, RateLimitExceededException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from functools import wraps
import threading
from backend.fastapi.app.core.config import get_settings

try:
    settings = get_settings()
except ImportError:
    # Fallback to environment variables if config import fails
    class DummySettings:
        def __init__(self):
            self.github_token = os.getenv("GITHUB_TOKEN", "")
            self.github_repo = os.getenv("GITHUB_REPO", "")

    settings = DummySettings()

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type = Exception
    success_threshold: int = 3  # Successes needed to close circuit


class CircuitBreaker:
    """
    Circuit breaker implementation for GitHub API calls
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.success_count = 0
        self._lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker"""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not await self._can_execute():
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.config.expected_exception as e:
                self._on_failure()
                raise e

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self._can_execute_sync():
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.config.expected_exception as e:
                self._on_failure()
                raise e

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    async def _can_execute(self) -> bool:
        """Check if request can be executed"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
                return False
            else:  # HALF_OPEN
                return True

    def _can_execute_sync(self) -> bool:
        """Sync version of _can_execute"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
                return False
            else:  # HALF_OPEN
                return True

    def _on_success(self):
        """Handle successful execution"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def _on_failure(self):
        """Handle failed execution"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker OPENED after {self.failure_count} failures"
                    )
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker re-OPENED during half-open state")

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
            }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""

    pass


@dataclass
class GitHubTokenConfig:
    """GitHub token configuration"""

    token: str
    expires_at: Optional[datetime] = None
    is_valid: bool = True
    last_used: Optional[datetime] = None
    usage_count: int = 0


class GitHubTokenManager:
    """
    Manages GitHub tokens with validation and refresh capabilities
    """

    def __init__(self):
        self.tokens: Dict[str, GitHubTokenConfig] = {}
        self.active_token_key: Optional[str] = None
        self._lock = threading.Lock()

    def add_token(self, key: str, token: str, expires_at: Optional[datetime] = None):
        """Add a token to the manager"""
        with self._lock:
            self.tokens[key] = GitHubTokenConfig(
                token=token, expires_at=expires_at, is_valid=True
            )
            if not self.active_token_key:
                self.active_token_key = key
            logger.info(f"Added GitHub token with key: {key}")

    def get_active_token(self) -> Optional[str]:
        """Get the currently active token"""
        with self._lock:
            if not self.active_token_key:
                return None

            token_config = self.tokens.get(self.active_token_key)
            if not token_config or not token_config.is_valid:
                return None

            # Check if token is expired
            if token_config.expires_at and datetime.now() >= token_config.expires_at:
                token_config.is_valid = False
                logger.warning(f"Token {self.active_token_key} has expired")
                return None

            token_config.last_used = datetime.now()
            token_config.usage_count += 1
            return token_config.token

    def mark_token_invalid(self, key: str):
        """Mark a token as invalid"""
        with self._lock:
            if key in self.tokens:
                self.tokens[key].is_valid = False
                logger.warning(f"Marked token {key} as invalid")

                # Switch to another valid token if available
                if self.active_token_key == key:
                    self.active_token_key = None
                    for token_key, token_config in self.tokens.items():
                        if token_config.is_valid:
                            self.active_token_key = token_key
                            logger.info(f"Switched to token: {token_key}")
                            break

    def validate_token(self, token: str) -> bool:
        """Validate a GitHub token"""
        try:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = requests.get(
                "https://api.github.com/user", headers=headers, timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get token manager status"""
        with self._lock:
            return {
                "active_token": self.active_token_key,
                "total_tokens": len(self.tokens),
                "valid_tokens": sum(1 for t in self.tokens.values() if t.is_valid),
                "tokens": {
                    key: {
                        "is_valid": token.is_valid,
                        "expires_at": token.expires_at.isoformat()
                        if token.expires_at
                        else None,
                        "last_used": token.last_used.isoformat()
                        if token.last_used
                        else None,
                        "usage_count": token.usage_count,
                    }
                    for key, token in self.tokens.items()
                },
            }


@dataclass
class GitHubConnectionStatus:
    """GitHub connection status information"""

    is_connected: bool = False
    last_check: Optional[datetime] = None
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None


class GitHubService:
    """
    Enhanced GitHub service with circuit breaker, retry logic, and token management
    """

    def __init__(self):
        self.token_manager = GitHubTokenManager()
        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=GithubException,
            )
        )
        self.connection_status = GitHubConnectionStatus()
        self._rate_limit_cache = {}
        self._initialize_tokens()

    def _initialize_tokens(self):
        """Initialize tokens from environment variables"""
        # Primary token from settings
        if hasattr(settings, "GITHUB_TOKEN") and settings.GITHUB_TOKEN:
            self.token_manager.add_token("primary", settings.GITHUB_TOKEN)

        # Additional tokens from environment
        for i in range(1, 6):  # Check for up to 5 additional tokens
            token_env = f"GITHUB_TOKEN_{i}"
            token = os.getenv(token_env)
            if token:
                self.token_manager.add_token(f"token_{i}", token)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, GithubException)),
    )
    async def test_connection(self) -> GitHubConnectionStatus:
        """Test GitHub connection and update status"""
        token = self.token_manager.get_active_token()
        if not token:
            self.connection_status = GitHubConnectionStatus(
                is_connected=False,
                last_check=datetime.now(),
                error_message="No valid GitHub token available",
            )
            return self.connection_status

        try:
            start_time = time.time()
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }

            response = requests.get(
                "https://api.github.com/user", headers=headers, timeout=10
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                self.connection_status = GitHubConnectionStatus(
                    is_connected=True,
                    last_check=datetime.now(),
                    response_time=response_time,
                    rate_limit_remaining=int(
                        response.headers.get("X-RateLimit-Remaining", 0)
                    ),
                    rate_limit_reset=datetime.fromtimestamp(
                        int(response.headers.get("X-RateLimit-Reset", 0))
                    )
                    if response.headers.get("X-RateLimit-Reset")
                    else None,
                )
                logger.info("GitHub connection test successful")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                if response.status_code == 401:
                    # Mark token as invalid for 401 errors
                    active_key = self.token_manager.active_token_key
                    if active_key:
                        self.token_manager.mark_token_invalid(active_key)

                self.connection_status = GitHubConnectionStatus(
                    is_connected=False,
                    last_check=datetime.now(),
                    error_message=error_msg,
                )
                logger.error(f"GitHub connection test failed: {error_msg}")

        except Exception as e:
            self.connection_status = GitHubConnectionStatus(
                is_connected=False, last_check=datetime.now(), error_message=str(e)
            )
            logger.error(f"GitHub connection test error: {e}")

        return self.connection_status

    @CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=60, expected_exception=GithubException
        )
    )
    async def get_github_client(self) -> Optional[Github]:
        """Get authenticated GitHub client with retry logic"""
        token = self.token_manager.get_active_token()
        if not token:
            logger.error("No valid GitHub token available")
            return None

        try:
            client = Github(token, per_page=100)
            # Test the connection
            user = client.get_user()
            user.login  # This will raise an exception if token is invalid
            return client
        except GithubException as e:
            if e.status == 401:
                # Mark token as invalid
                active_key = self.token_manager.active_token_key
                if active_key:
                    self.token_manager.mark_token_invalid(active_key)
                logger.error("GitHub token is invalid or expired")
            raise e
        except Exception as e:
            logger.error(f"Error creating GitHub client: {e}")
            raise e

    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute a GitHub operation with retry logic and circuit breaker"""
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                # Check if we have a valid token
                token = self.token_manager.get_active_token()
                if not token:
                    raise Exception("No valid GitHub token available")

                # Execute the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)

                return result

            except GithubException as e:
                # Handle specific GitHub errors
                if e.status == 401:
                    # Token is invalid, mark it and try with another token
                    active_key = self.token_manager.active_token_key
                    if active_key:
                        self.token_manager.mark_token_invalid(active_key)

                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"Retrying GitHub operation in {delay}s after 401 error"
                        )
                        await asyncio.sleep(delay)
                        continue

                elif e.status == 403:
                    # Rate limit or permission error
                    if "rate limit" in str(e).lower():
                        reset_time = int(
                            e.headers.get("X-RateLimit-Reset", time.time() + 60)
                        )
                        wait_time = max(reset_time - time.time(), 1)

                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Rate limit hit, waiting {wait_time}s before retry"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                # For other errors, use exponential backoff
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Retrying GitHub operation in {delay}s after error: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise e

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Retrying GitHub operation in {delay}s after unexpected error: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise e

        raise Exception("All retry attempts exhausted")

    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        return {
            "connection": {
                "is_connected": self.connection_status.is_connected,
                "last_check": self.connection_status.last_check.isoformat()
                if self.connection_status.last_check
                else None,
                "response_time": self.connection_status.response_time,
                "error_message": self.connection_status.error_message,
                "rate_limit_remaining": self.connection_status.rate_limit_remaining,
                "rate_limit_reset": self.connection_status.rate_limit_reset.isoformat()
                if self.connection_status.rate_limit_reset
                else None,
            },
            "circuit_breaker": self.circuit_breaker.get_state(),
            "tokens": self.token_manager.get_status(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        status = await self.test_connection()
        service_status = self.get_service_status()

        # Determine overall health
        is_healthy = (
            status.is_connected
            and service_status["circuit_breaker"]["state"] == CircuitState.CLOSED.value
            and service_status["tokens"]["valid_tokens"] > 0
        )

        return {
            "healthy": is_healthy,
            "timestamp": datetime.now().isoformat(),
            "service": service_status,
        }


# Global instance
github_service = GitHubService()
