"""
Firebase Recovery Service
Handles automatic recovery from Firebase authentication failures
Provides circuit breaker pattern and health monitoring
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker state"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovery is possible

@dataclass
class RecoveryMetrics:
    """Recovery service metrics"""
    total_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    last_recovery_time: Optional[datetime] = None
    consecutive_failures: int = 0
    average_recovery_time: float = 0.0

class FirebaseRecoveryService:
    """
    Automatic recovery service for Firebase authentication failures
    Implements circuit breaker pattern with exponential backoff
    """

    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 300.0,
        backoff_multiplier: float = 2.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier

        # Circuit breaker settings
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_count = 0
        self.circuit_last_failure_time = None

        # Recovery metrics
        self.metrics = RecoveryMetrics()

        # Recovery callbacks
        self.recovery_callbacks: List[Callable] = []

        # Recovery state
        self.is_recovering = False
        self.last_recovery_attempt = None
        self.recovery_lock = asyncio.Lock()

    def add_recovery_callback(self, callback: Callable):
        """Add a callback to be called on successful recovery"""
        self.recovery_callbacks.append(callback)

    async def attempt_recovery(
        self,
        recovery_func: Callable,
        operation_name: str = "firebase_operation"
    ) -> tuple[bool, Any]:
        """
        Attempt to execute an operation with automatic recovery

        Returns:
            tuple: (success, result_or_error)
        """
        async with self.recovery_lock:
            if self.is_recovering:
                logger.info(f"Recovery already in progress, skipping {operation_name}")
                return False, "Recovery already in progress"

            # Check circuit breaker
            if not self._can_attempt_operation():
                logger.warning(f"Circuit breaker OPEN, skipping {operation_name}")
                return False, "Circuit breaker is open"

            self.is_recovering = True
            self.metrics.total_attempts += 1

        try:
            # Attempt operation with retries
            success, result = await self._execute_with_retries(recovery_func, operation_name)

            if success:
                await self._handle_recovery_success(operation_name)
                return True, result
            else:
                await self._handle_recovery_failure(operation_name, result)
                return False, result

        finally:
            async with self.recovery_lock:
                self.is_recovering = False
                self.last_recovery_attempt = datetime.utcnow()

    def _can_attempt_operation(self) -> bool:
        """Check if operation can be attempted based on circuit breaker state"""
        if self.circuit_state == CircuitState.CLOSED:
            return True

        if self.circuit_state == CircuitState.OPEN:
            # Check if timeout has passed to try half-open state
            if (datetime.utcnow() - self.circuit_last_failure_time).seconds > self.circuit_breaker_timeout:
                self.circuit_state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker moving to HALF_OPEN state")
                return True
            return False

        if self.circuit_state == CircuitState.HALF_OPEN:
            return True

        return False

    async def _execute_with_retries(self, func: Callable, operation_name: str) -> tuple[bool, Any]:
        """Execute function with retry logic and exponential backoff"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying {operation_name} in {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)

                # Execute the operation
                result = await func()
                logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")
                return True, result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"{operation_name} failed on attempt {attempt + 1}: {last_error}")

                # Update circuit breaker on failure
                if self.circuit_state == CircuitState.HALF_OPEN:
                    self._update_circuit_breaker_on_failure()

        return False, last_error

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.initial_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)

    async def _handle_recovery_success(self, operation_name: str):
        """Handle successful recovery"""
        async with self.recovery_lock:
            self.metrics.successful_recoveries += 1
            self.metrics.last_recovery_time = datetime.utcnow()
            self.metrics.consecutive_failures = 0

            # Reset circuit breaker
            self.circuit_state = CircuitState.CLOSED
            self.circuit_failure_count = 0

        logger.info(f"✅ Firebase recovery successful for {operation_name}")

        # Call recovery callbacks
        for callback in self.recovery_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(operation_name)
                else:
                    callback(operation_name)
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")

    async def _handle_recovery_failure(self, operation_name: str, error: str):
        """Handle recovery failure"""
        async with self.recovery_lock:
            self.metrics.failed_recoveries += 1
            self.metrics.consecutive_failures += 1

            # Update circuit breaker
            self._update_circuit_breaker_on_failure()

        logger.error(f"❌ Firebase recovery failed for {operation_name}: {error}")

    def _update_circuit_breaker_on_failure(self):
        """Update circuit breaker state on failure"""
        self.circuit_failure_count += 1
        self.circuit_last_failure_time = datetime.utcnow()

        if self.circuit_failure_count >= self.circuit_breaker_threshold:
            self.circuit_state = CircuitState.OPEN
            logger.warning(f"⚠️  Circuit breaker OPENED after {self.circuit_failure_count} failures")

    async def force_recovery_attempt(self, recovery_func: Callable) -> bool:
        """Force a recovery attempt regardless of circuit breaker state"""
        logger.info("Forcing Firebase recovery attempt")

        # Temporarily close circuit breaker
        original_state = self.circuit_state
        self.circuit_state = CircuitState.CLOSED

        try:
            success, result = await self.attempt_recovery(recovery_func, "forced_recovery")
            return success
        finally:
            # Restore original circuit state if recovery failed
            if not success:
                self.circuit_state = original_state

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        return {
            "circuit_breaker": {
                "state": self.circuit_state.value,
                "failure_count": self.circuit_failure_count,
                "threshold": self.circuit_breaker_threshold,
                "timeout": self.circuit_breaker_timeout,
                "last_failure_time": self.circuit_last_failure_time.isoformat() if self.circuit_last_failure_time else None
            },
            "metrics": {
                "total_attempts": self.metrics.total_attempts,
                "successful_recoveries": self.metrics.successful_recoveries,
                "failed_recoveries": self.metrics.failed_recoveries,
                "consecutive_failures": self.metrics.consecutive_failures,
                "success_rate": (
                    self.metrics.successful_recoveries / self.metrics.total_attempts
                    if self.metrics.total_attempts > 0 else 0
                ),
                "last_recovery_time": (
                    self.metrics.last_recovery_time.isoformat()
                    if self.metrics.last_recovery_time else None
                )
            },
            "recovery_status": {
                "is_recovering": self.is_recovering,
                "last_recovery_attempt": (
                    self.last_recovery_attempt.isoformat()
                    if self.last_recovery_attempt else None
                ),
                "can_attempt_operation": self._can_attempt_operation()
            },
            "configuration": {
                "max_retries": self.max_retries,
                "initial_delay": self.initial_delay,
                "max_delay": self.max_delay,
                "backoff_multiplier": self.backoff_multiplier
            }
        }

    def reset_circuit_breaker(self):
        """Reset circuit breaker to closed state"""
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_count = 0
        self.circuit_last_failure_time = None
        logger.info("🔄 Circuit breaker reset to CLOSED state")

    def reset_metrics(self):
        """Reset all recovery metrics"""
        self.metrics = RecoveryMetrics()
        logger.info("📊 Recovery metrics reset")

class FirebaseHealthMonitor:
    """Monitor Firebase health and trigger recovery when needed"""

    def __init__(
        self,
        firebase_service,
        recovery_service: FirebaseRecoveryService,
        check_interval: float = 60.0,
        unhealthy_threshold: int = 3
    ):
        self.firebase_service = firebase_service
        self.recovery_service = recovery_service
        self.check_interval = check_interval
        self.unhealthy_threshold = unhealthy_threshold

        self.monitoring_active = False
        self.unhealthy_count = 0
        self.last_health_check = None

    async def start_monitoring(self):
        """Start health monitoring loop"""
        if self.monitoring_active:
            logger.warning("Health monitoring already active")
            return

        self.monitoring_active = True
        logger.info("🔍 Firebase health monitoring started")

        while self.monitoring_active:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

    async def stop_monitoring(self):
        """Stop health monitoring loop"""
        self.monitoring_active = False
        logger.info("⏹️  Firebase health monitoring stopped")

    async def _perform_health_check(self):
        """Perform Firebase health check"""
        try:
            # Get health status from Firebase service
            health = await self.firebase_service.health_check()
            self.last_health_check = datetime.utcnow()

            if health.get("status") == "healthy":
                self.unhealthy_count = 0
                logger.debug("✅ Firebase health check passed")
            else:
                self.unhealthy_count += 1
                logger.warning(f"⚠️  Firebase health check failed ({self.unhealthy_count}/{self.unhealthy_threshold})")

                # Trigger recovery if threshold reached
                if self.unhealthy_count >= self.unhealthy_threshold:
                    logger.error(f"❌ Firebase unhealthy threshold reached, triggering recovery")
                    await self._trigger_recovery()

        except Exception as e:
            self.unhealthy_count += 1
            logger.error(f"❌ Firebase health check error: {e}")

            if self.unhealthy_count >= self.unhealthy_threshold:
                await self._trigger_recovery()

    async def _trigger_recovery(self):
        """Trigger Firebase recovery"""
        recovery_func = self.firebase_service.attempt_recovery
        success, result = await self.recovery_service.attempt_recovery(
            recovery_func,
            "health_monitor_recovery"
        )

        if success:
            self.unhealthy_count = 0
            logger.info("🎉 Firebase recovery triggered by health monitor successful")
        else:
            logger.error(f"💥 Firebase recovery triggered by health monitor failed: {result}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            "active": self.monitoring_active,
            "check_interval": self.check_interval,
            "unhealthy_count": self.unhealthy_count,
            "unhealthy_threshold": self.unhealthy_threshold,
            "last_health_check": (
                self.last_health_check.isoformat()
                if self.last_health_check else None
            )
        }