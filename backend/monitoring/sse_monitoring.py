"""
SSE Production Monitoring and Health Checks for AutoAdmin Backend
Comprehensive monitoring, alerting, and health check system for Server-Sent Events
Provides production-ready observability with metrics collection and alerting
"""

import asyncio
import time
import psutil
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics
import threading

# SSE imports
from app.services.sse_event_manager import get_sse_event_manager
from app.services.sse_client_manager import get_sse_client_manager
from app.services.sse_integration import get_sse_integration_service

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Alert:
    """Production alert structure"""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    component: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    affected_resources: List[str] = field(default_factory=list)

    def resolve(self):
        """Mark alert as resolved"""
        self.resolved = True
        self.resolved_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
            "affected_resources": self.affected_resources
        }


@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    check_func: Callable
    interval_seconds: int = 60
    timeout_seconds: int = 10
    critical: bool = False
    enabled: bool = True


@dataclass
class MetricsSnapshot:
    """Metrics snapshot for time-series data"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    active_connections: int = 0
    total_connections: int = 0
    events_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    error_rate: float = 0.0
    latency_ms: float = 0.0


class SSEMonitoringService:
    """
    Comprehensive monitoring service for SSE system
    Provides health checks, metrics collection, and alerting
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SSEMonitoringService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._alerts: Dict[str, Alert] = {}
            self._health_checks: Dict[str, HealthCheck] = {}
            self._metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 snapshots
            self._alert_callbacks: List[Callable[[Alert], None]] = []
            self._monitoring_task = None
            self._health_check_task = None
            self._alerting_enabled = True
            self._metrics_enabled = True
            self._start_time = datetime.utcnow()
            self._last_metrics = {}

            # Monitoring thresholds
            self._thresholds = {
                'max_connections': 1000,
                'max_memory_mb': 1024,
                'max_cpu_percent': 80,
                'max_error_rate': 0.05,  # 5%
                'max_latency_ms': 1000,
                'max_events_queue_size': 1000
            }

            self._setup_default_health_checks()
            self._start_monitoring()

    def _setup_default_health_checks(self):
        """Set up default health checks"""
        # Event manager health check
        self.add_health_check(
            HealthCheck(
                name="event_manager_health",
                check_func=self._check_event_manager_health,
                critical=True
            )
        )

        # Client manager health check
        self.add_health_check(
            HealthCheck(
                name="client_manager_health",
                check_func=self._check_client_manager_health,
                critical=True
            )
        )

        # Memory usage check
        self.add_health_check(
            HealthCheck(
                name="memory_usage",
                check_func=self._check_memory_usage,
                critical=False
            )
        )

        # CPU usage check
        self.add_health_check(
            HealthCheck(
                name="cpu_usage",
                check_func=self._check_cpu_usage,
                critical=False
            )
        )

        # Event processing rate check
        self.add_health_check(
            HealthCheck(
                name="event_processing_rate",
                check_func=self._check_event_processing_rate,
                critical=True
            )
        )

    def _start_monitoring(self):
        """Start background monitoring tasks"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _monitoring_loop(self):
        """Main monitoring loop for metrics collection"""
        while True:
            try:
                if self._metrics_enabled:
                    await self._collect_metrics()
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)

    async def _health_check_loop(self):
        """Health check execution loop"""
        while True:
            try:
                await self._run_health_checks()
                await asyncio.sleep(60)  # Run health checks every minute
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(10)

    async def _collect_metrics(self):
        """Collect system metrics"""
        try:
            # Get SSE service statistics
            event_manager = get_sse_event_manager()
            client_manager = get_sse_client_manager()
            integration_service = get_sse_integration_service()

            # Collect basic metrics
            event_stats = event_manager.get_system_stats() if event_manager else {}
            client_stats = client_manager.get_system_stats() if client_manager else {}
            integration_stats = integration_service.get_integration_stats() if integration_service else {}

            # Collect system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            # Create metrics snapshot
            snapshot = MetricsSnapshot(
                active_connections=client_stats.get('active_clients', 0),
                total_connections=client_stats.get('total_clients', 0),
                events_per_second=self._calculate_events_per_second(event_stats),
                memory_usage_mb=memory_info.used / 1024 / 1024,
                cpu_usage_percent=cpu_percent,
                error_rate=self._calculate_error_rate(event_stats),
                latency_ms=self._calculate_average_latency()
            )

            # Add to history
            self._metrics_history.append(snapshot)
            self._last_metrics = snapshot.to_dict()

            # Check thresholds and create alerts
            await self._check_metric_thresholds(snapshot)

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            self._create_alert(
                severity=AlertSeverity.HIGH,
                title="Metrics Collection Error",
                message=f"Failed to collect metrics: {str(e)}",
                component="monitoring",
                metadata={"error": str(e)}
            )

    async def _run_health_checks(self):
        """Run all configured health checks"""
        health_results = {}
        critical_failures = []

        for name, health_check in self._health_checks.items():
            if not health_check.enabled:
                continue

            try:
                # Run health check with timeout
                result = await asyncio.wait_for(
                    health_check.check_func(),
                    timeout=health_check.timeout_seconds
                )
                health_results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "details": result
                }

                if not result and health_check.critical:
                    critical_failures.append(name)

            except asyncio.TimeoutError:
                health_results[name] = {
                    "status": "timeout",
                    "details": f"Health check timed out after {health_check.timeout_seconds}s"
                }
                if health_check.critical:
                    critical_failures.append(name)

            except Exception as e:
                health_results[name] = {
                    "status": "error",
                    "details": str(e)
                }
                if health_check.critical:
                    critical_failures.append(name)

        # Create alerts for critical failures
        for failure in critical_failures:
            self._create_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Health Check Failed",
                message=f"Health check '{failure}' failed",
                component="health_check",
                affected_resources=[failure]
            )

        # Update overall system health
        await self._update_overall_health(health_results, critical_failures)

    async def _check_event_manager_health(self) -> bool:
        """Check event manager health"""
        event_manager = get_sse_event_manager()
        if not event_manager:
            return False

        stats = event_manager.get_system_stats()
        if not stats:
            return False

        # Check if event queue is not overloaded
        queue_size = stats.get('queue_size', 0)
        return queue_size < self._thresholds['max_events_queue_size']

    async def _check_client_manager_health(self) -> bool:
        """Check client manager health"""
        client_manager = get_sse_client_manager()
        if not client_manager:
            return False

        stats = client_manager.get_system_stats()
        if not stats:
            return False

        # Check connection counts
        active_clients = stats.get('active_clients', 0)
        return active_clients <= self._thresholds['max_connections']

    async def _check_memory_usage(self) -> bool:
        """Check memory usage"""
        memory_info = psutil.virtual_memory()
        memory_mb = memory_info.used / 1024 / 1024
        return memory_mb < self._thresholds['max_memory_mb']

    async def _check_cpu_usage(self) -> bool:
        """Check CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        return cpu_percent < self._thresholds['max_cpu_percent']

    async def _check_event_processing_rate(self) -> bool:
        """Check event processing rate"""
        event_manager = get_sse_event_manager()
        if not event_manager:
            return False

        stats = event_manager.get_system_stats()
        if not stats:
            return False

        # Calculate recent event processing rate
        events_broadcast = stats.get('stats', {}).get('events_broadcast', 0)
        uptime = stats.get('uptime_seconds', 1)
        events_per_second = events_broadcast / uptime if uptime > 0 else 0

        # Alert if processing rate is too low (indicates potential issues)
        return events_per_second > 0.1  # At least 0.1 events per second

    def _calculate_events_per_second(self, event_stats: Dict[str, Any]) -> float:
        """Calculate events per second rate"""
        if not event_stats:
            return 0.0

        uptime = event_stats.get('uptime_seconds', 1)
        events_broadcast = event_stats.get('stats', {}).get('events_broadcast', 0)

        return events_broadcast / uptime if uptime > 0 else 0.0

    def _calculate_error_rate(self, event_stats: Dict[str, Any]) -> float:
        """Calculate error rate"""
        if not event_stats:
            return 0.0

        stats = event_stats.get('stats', {})
        total_events = stats.get('events_broadcast', 0) + stats.get('events_filtered', 0)
        errors = stats.get('error_disconnections', 0)

        if total_events == 0:
            return 0.0

        return errors / total_events

    def _calculate_average_latency(self) -> float:
        """Calculate average event processing latency"""
        # This would be implemented based on actual latency measurements
        # For now, return a placeholder value
        return 50.0  # 50ms average latency

    async def _check_metric_thresholds(self, snapshot: MetricsSnapshot):
        """Check metrics against thresholds and create alerts"""
        # Check connection count
        if snapshot.active_connections > self._thresholds['max_connections']:
            self._create_alert(
                severity=AlertSeverity.HIGH,
                title="High Connection Count",
                message=f"Active connections: {snapshot.active_connections}",
                component="client_manager",
                metadata={"active_connections": snapshot.active_connections}
            )

        # Check memory usage
        if snapshot.memory_usage_mb > self._thresholds['max_memory_mb']:
            self._create_alert(
                severity=AlertSeverity.HIGH,
                title="High Memory Usage",
                message=f"Memory usage: {snapshot.memory_usage_mb:.1f} MB",
                component="system",
                metadata={"memory_usage_mb": snapshot.memory_usage_mb}
            )

        # Check CPU usage
        if snapshot.cpu_usage_percent > self._thresholds['max_cpu_percent']:
            self._create_alert(
                severity=AlertSeverity.HIGH,
                title="High CPU Usage",
                message=f"CPU usage: {snapshot.cpu_usage_percent:.1f}%",
                component="system",
                metadata={"cpu_usage_percent": snapshot.cpu_usage_percent}
            )

        # Check error rate
        if snapshot.error_rate > self._thresholds['max_error_rate']:
            self._create_alert(
                severity=AlertSeverity.MEDIUM,
                title="High Error Rate",
                message=f"Error rate: {snapshot.error_rate:.2%}",
                component="sse_system",
                metadata={"error_rate": snapshot.error_rate}
            )

    async def _update_overall_health(self, health_results: Dict[str, Any], critical_failures: List[str]):
        """Update overall system health status"""
        if critical_failures:
            overall_status = HealthStatus.UNHEALTHY
        elif any(result["status"] != "healthy" for result in health_results.values()):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Store overall health status
        self._last_health_status = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "health_checks": health_results,
            "critical_failures": critical_failures
        }

    def _create_alert(self, severity: AlertSeverity, title: str, message: str, component: str,
                     metadata: Optional[Dict[str, Any]] = None, affected_resources: Optional[List[str]] = None):
        """Create and process an alert"""
        if not self._alerting_enabled:
            return

        import uuid
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
            component=component,
            metadata=metadata or {},
            affected_resources=affected_resources or []
        )

        self._alerts[alert.alert_id] = alert

        # Call alert callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(f"Alert created: {severity.value} - {title} - {message}")

    def add_health_check(self, health_check: HealthCheck):
        """Add a custom health check"""
        self._health_checks[health_check.name] = health_check

    def remove_health_check(self, name: str):
        """Remove a health check"""
        if name in self._health_checks:
            del self._health_checks[name]

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add callback for alert notifications"""
        self._alert_callbacks.append(callback)

    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics history for the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        history = []
        for snapshot in self._metrics_history:
            if snapshot.timestamp >= cutoff_time:
                history.append(snapshot.to_dict())

        return history

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return self._last_metrics.copy() if self._last_metrics else {}

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return getattr(self, '_last_health_status', {
            "status": HealthStatus.UNKNOWN.value,
            "timestamp": datetime.utcnow().isoformat(),
            "health_checks": {},
            "critical_failures": []
        })

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get active (unresolved) alerts"""
        active_alerts = [
            alert for alert in self._alerts.values()
            if not alert.resolved
        ]

        if severity:
            active_alerts = [alert for alert in active_alerts if alert.severity == severity]

        return [alert.to_dict() for alert in active_alerts]

    def get_all_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get all alerts from the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_alerts = [
            alert for alert in self._alerts.values()
            if alert.timestamp >= cutoff_time
        ]

        return [alert.to_dict() for alert in recent_alerts]

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id not in self._alerts:
            return False

        alert = self._alerts[alert_id]
        alert.resolve()

        logger.info(f"Alert resolved: {alert_id} - {alert.title}")
        return True

    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview"""
        current_metrics = self.get_current_metrics()
        health_status = self.get_health_status()
        active_alerts = self.get_active_alerts()

        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "status": health_status["status"],
            "uptime_seconds": uptime_seconds,
            "metrics": current_metrics,
            "health": health_status,
            "alerts": {
                "active_count": len(active_alerts),
                "critical_count": len([a for a in active_alerts if a["severity"] == "critical"]),
                "high_count": len([a for a in active_alerts if a["severity"] == "high"]),
                "recent_alerts": active_alerts[:5]  # Last 5 alerts
            },
            "monitoring": {
                "enabled": self._metrics_enabled,
                "alerting_enabled": self._alerting_enabled,
                "health_checks_count": len(self._health_checks),
                "metrics_history_size": len(self._metrics_history)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def enable_monitoring(self):
        """Enable metrics collection"""
        self._metrics_enabled = True

    def disable_monitoring(self):
        """Disable metrics collection"""
        self._metrics_enabled = False

    def enable_alerting(self):
        """Enable alerting"""
        self._alerting_enabled = True

    def disable_alerting(self):
        """Disable alerting"""
        self._alerting_enabled = False

    async def shutdown(self):
        """Shutdown monitoring service"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("SSE Monitoring Service shutdown complete")


# Create singleton instance
sse_monitoring_service = SSEMonitoringService()


def get_sse_monitoring_service() -> SSEMonitoringService:
    """Get the SSE monitoring service singleton"""
    return sse_monitoring_service


# Export classes and functions
__all__ = [
    "SSEMonitoringService",
    "get_sse_monitoring_service",
    "Alert",
    "AlertSeverity",
    "HealthCheck",
    "HealthStatus",
    "MetricsSnapshot"
]