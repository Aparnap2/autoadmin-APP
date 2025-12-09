"""
Health Monitor for Multi-Agent System
Provides comprehensive health monitoring, metrics collection, and anomaly detection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import statistics
import uuid

from ...database.manager import get_database_manager
from .load_balancer import get_load_balancer, AgentStatus

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNHEALTHY = "unhealthy"


class MetricType(Enum):
    """Types of metrics to monitor"""

    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    CIRCUIT_BREAKER_STATE = "circuit_breaker_state"
    HEARTBEAT_INTERVAL = "heartbeat_interval"


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Health metric data point"""

    metric_type: MetricType
    agent_id: str
    value: float
    timestamp: datetime
    unit: str = ""
    threshold: Optional[float] = None
    is_anomaly: bool = False


@dataclass
class HealthAlert:
    """Health alert"""

    alert_id: str
    agent_id: str
    severity: AlertSeverity
    message: str
    metric_type: MetricType
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Health check result for an agent"""

    agent_id: str
    agent_type: str
    status: HealthStatus
    score: float  # 0-100
    metrics: Dict[MetricType, float] = field(default_factory=dict)
    alerts: List[HealthAlert] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class AnomalyDetector:
    """Detects anomalies in agent metrics"""

    def __init__(self, window_size: int = 20, threshold_multiplier: float = 2.0):
        self.window_size = window_size
        self.threshold_multiplier = threshold_multiplier
        self.metric_history: Dict[str, List[float]] = {}

    def detect_anomaly(self, agent_id: str, metric_type: str, value: float) -> bool:
        """Detect if a value is anomalous"""
        try:
            key = f"{agent_id}_{metric_type}"

            # Initialize history if needed
            if key not in self.metric_history:
                self.metric_history[key] = []

            # Add new value
            self.metric_history[key].append(value)

            # Keep only recent values
            if len(self.metric_history[key]) > self.window_size:
                self.metric_history[key] = self.metric_history[key][-self.window_size :]

            # Need at least some history for anomaly detection
            if len(self.metric_history[key]) < 5:
                return False

            # Calculate statistics
            recent_values = self.metric_history[key][:-1]  # Exclude current value
            mean = statistics.mean(recent_values)
            stdev = statistics.stdev(recent_values) if len(recent_values) > 1 else 0

            # Check if current value is anomalous
            if stdev == 0:
                return False

            z_score = abs(value - mean) / stdev
            return z_score > self.threshold_multiplier

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return False


class HealthMonitor:
    """Comprehensive health monitoring system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Monitoring configuration
        self.check_interval = config.get("check_interval", 30)
        self.metrics_retention_hours = config.get("metrics_retention_hours", 24)
        self.alert_thresholds = config.get("alert_thresholds", {})

        # Health data storage
        self.health_metrics: List[HealthMetric] = []
        self.health_alerts: Dict[str, HealthAlert] = {}
        self.agent_health_status: Dict[str, HealthCheckResult] = {}

        # Anomaly detection
        self.anomaly_detector = AnomalyDetector(
            window_size=config.get("anomaly_window_size", 20),
            threshold_multiplier=config.get("anomaly_threshold", 2.0),
        )

        # Database manager
        self.db_manager = None

        # Load balancer reference
        self.load_balancer = None

        # Monitoring state
        self.is_running = False
        self.monitoring_tasks: List[asyncio.Task] = []

        # Default thresholds
        self.default_thresholds = {
            MetricType.RESPONSE_TIME: {
                "warning": 5000,
                "critical": 10000,
            },  # milliseconds
            MetricType.SUCCESS_RATE: {"warning": 0.9, "critical": 0.8},  # percentage
            MetricType.ERROR_RATE: {"warning": 0.1, "critical": 0.2},  # percentage
            MetricType.THROUGHPUT: {
                "warning": 0.5,
                "critical": 0.1,
            },  # tasks per minute
            MetricType.HEARTBEAT_INTERVAL: {"warning": 60, "critical": 120},  # seconds
        }

        # Merge with custom thresholds
        self.thresholds = {**self.default_thresholds, **self.alert_thresholds}

        self.logger.info("Health Monitor initialized")

    async def initialize(self):
        """Initialize health monitor"""
        try:
            self.db_manager = await get_database_manager()
            self.load_balancer = await get_load_balancer()

            # Load historical data
            await self._load_historical_data()

            self.logger.info("Health monitor initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize health monitor: {e}")
            return False

    async def start_monitoring(self):
        """Start health monitoring"""
        try:
            if self.is_running:
                self.logger.warning("Health monitoring already running")
                return

            self.is_running = True

            # Start monitoring tasks
            self.monitoring_tasks = [
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._metrics_collection_loop()),
                asyncio.create_task(self._alert_processing_loop()),
                asyncio.create_task(self._data_cleanup_loop()),
            ]

            self.logger.info("Health monitoring started")

        except Exception as e:
            self.logger.error(f"Failed to start health monitoring: {e}")
            self.is_running = False

    async def stop_monitoring(self):
        """Stop health monitoring"""
        try:
            self.is_running = False

            # Cancel monitoring tasks
            for task in self.monitoring_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)

            self.logger.info("Health monitoring stopped")

        except Exception as e:
            self.logger.error(f"Failed to stop health monitoring: {e}")

    async def check_agent_health(self, agent_id: str) -> HealthCheckResult:
        """Perform comprehensive health check for an agent"""
        try:
            start_time = datetime.now()

            # Get agent metrics from load balancer
            agent_status = await self.load_balancer.get_agent_status(agent_id)
            if not agent_status:
                return HealthCheckResult(
                    agent_id=agent_id,
                    agent_type="unknown",
                    status=HealthStatus.UNHEALTHY,
                    score=0,
                    details={"error": "Agent not found in load balancer"},
                )

            # Collect health metrics
            metrics = await self._collect_agent_metrics(agent_id, agent_status)

            # Calculate health score
            score, status = await self._calculate_health_score(agent_id, metrics)

            # Check for alerts
            alerts = await self._check_metric_alerts(agent_id, metrics)

            # Detect anomalies
            await self._detect_metric_anomalies(agent_id, metrics)

            result = HealthCheckResult(
                agent_id=agent_id,
                agent_type=agent_status.get("agent_type", "unknown"),
                status=status,
                score=score,
                metrics=metrics,
                alerts=alerts,
                timestamp=datetime.now(),
                details={
                    "circuit_breaker_state": agent_status.get("circuit_breaker_state"),
                    "consecutive_failures": agent_status.get("consecutive_failures", 0),
                    "check_duration": (datetime.now() - start_time).total_seconds(),
                },
            )

            # Store health status
            self.agent_health_status[agent_id] = result

            # Store in database
            await self._store_health_result(result)

            return result

        except Exception as e:
            self.logger.error(f"Failed to check agent health {agent_id}: {e}")
            return HealthCheckResult(
                agent_id=agent_id,
                agent_type="unknown",
                status=HealthStatus.UNHEALTHY,
                score=0,
                details={"error": str(e)},
            )

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        try:
            # Get load balancer stats
            load_balancer_stats = await self.load_balancer.get_load_balancer_stats()

            # Health summary
            health_summary = {
                "total_agents": len(self.agent_health_status),
                "healthy_agents": len(
                    [
                        r
                        for r in self.agent_health_status.values()
                        if r.status == HealthStatus.HEALTHY
                    ]
                ),
                "degraded_agents": len(
                    [
                        r
                        for r in self.agent_health_status.values()
                        if r.status == HealthStatus.DEGRADED
                    ]
                ),
                "unhealthy_agents": len(
                    [
                        r
                        for r in self.agent_health_status.values()
                        if r.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]
                    ]
                ),
                "average_health_score": 0.0,
                "active_alerts": len(
                    [a for a in self.health_alerts.values() if not a.resolved]
                ),
                "critical_alerts": len(
                    [
                        a
                        for a in self.health_alerts.values()
                        if a.severity == AlertSeverity.CRITICAL and not a.resolved
                    ]
                ),
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate average health score
            if self.agent_health_status:
                health_summary["average_health_score"] = statistics.mean(
                    [r.score for r in self.agent_health_status.values()]
                )

            # Agent-specific health
            health_summary["agents"] = {}
            for agent_id, result in self.agent_health_status.items():
                health_summary["agents"][agent_id] = {
                    "status": result.status.value,
                    "score": result.score,
                    "alerts": len(result.alerts),
                    "last_check": result.timestamp.isoformat(),
                }

            # System metrics
            health_summary["system_metrics"] = load_balancer_stats

            return health_summary

        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def create_health_alert(
        self,
        agent_id: str,
        metric_type: MetricType,
        severity: AlertSeverity,
        message: str,
        value: float,
        threshold: float,
    ) -> str:
        """Create a health alert"""
        try:
            alert_id = str(uuid.uuid4())

            alert = HealthAlert(
                alert_id=alert_id,
                agent_id=agent_id,
                severity=severity,
                message=message,
                metric_type=metric_type,
                value=value,
                threshold=threshold,
                timestamp=datetime.now(),
            )

            self.health_alerts[alert_id] = alert

            # Store alert in database
            await self._store_health_alert(alert)

            # Log alert
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL,
            }.get(severity, logging.WARNING)

            self.logger.log(
                log_level, f"Health alert [{severity.value}] {agent_id}: {message}"
            )

            return alert_id

        except Exception as e:
            self.logger.error(f"Failed to create health alert: {e}")
            return ""

    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge a health alert"""
        try:
            if alert_id not in self.health_alerts:
                self.logger.warning(f"Alert not found: {alert_id}")
                return False

            alert = self.health_alerts[alert_id]
            alert.acknowledged = True
            alert.metadata["acknowledged_by"] = user_id
            alert.metadata["acknowledged_at"] = datetime.now().isoformat()

            # Update in database
            await self._store_health_alert(alert)

            self.logger.info(f"Alert acknowledged: {alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False

    async def resolve_alert(self, alert_id: str, resolution: str) -> bool:
        """Resolve a health alert"""
        try:
            if alert_id not in self.health_alerts:
                self.logger.warning(f"Alert not found: {alert_id}")
                return False

            alert = self.health_alerts[alert_id]
            alert.resolved = True
            alert.metadata["resolution"] = resolution
            alert.metadata["resolved_at"] = datetime.now().isoformat()

            # Update in database
            await self._store_health_alert(alert)

            self.logger.info(f"Alert resolved: {alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False

    async def _health_check_loop(self):
        """Main health check loop"""
        while self.is_running:
            try:
                # Get all agents from load balancer
                stats = await self.load_balancer.get_load_balancer_stats()
                agents = stats.get("agents", {})

                # Check health for each agent
                for agent_id in agents.keys():
                    try:
                        await self.check_agent_health(agent_id)
                    except Exception as e:
                        self.logger.error(f"Health check failed for {agent_id}: {e}")

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)

    async def _metrics_collection_loop(self):
        """Collect metrics from all agents"""
        while self.is_running:
            try:
                # Collect metrics from load balancer
                stats = await self.load_balancer.get_load_balancer_stats()

                # Store metrics for each agent
                for agent_id, agent_info in stats.get("agents", {}).items():
                    await self._collect_and_store_metrics(agent_id, agent_info)

                await asyncio.sleep(60)  # Collect metrics every minute

            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)

    async def _alert_processing_loop(self):
        """Process and evaluate alerts"""
        while self.is_running:
            try:
                # Check for escalation conditions
                await self._check_alert_escalations()

                # Send notifications for critical alerts
                await self._send_alert_notifications()

                await asyncio.sleep(30)  # Process alerts every 30 seconds

            except Exception as e:
                self.logger.error(f"Alert processing error: {e}")
                await asyncio.sleep(60)

    async def _data_cleanup_loop(self):
        """Clean up old data"""
        while self.is_running:
            try:
                cutoff_time = datetime.now() - timedelta(
                    hours=self.metrics_retention_hours
                )

                # Clean up old metrics
                self.health_metrics = [
                    metric
                    for metric in self.health_metrics
                    if metric.timestamp > cutoff_time
                ]

                # Clean up resolved alerts (older than 7 days)
                alert_cutoff = datetime.now() - timedelta(days=7)
                self.health_alerts = {
                    alert_id: alert
                    for alert_id, alert in self.health_alerts.items()
                    if not alert.resolved or alert.timestamp > alert_cutoff
                }

                await asyncio.sleep(3600)  # Clean up every hour

            except Exception as e:
                self.logger.error(f"Data cleanup error: {e}")
                await asyncio.sleep(3600)

    async def _collect_agent_metrics(
        self, agent_id: str, agent_status: Dict[str, Any]
    ) -> Dict[MetricType, float]:
        """Collect metrics for a specific agent"""
        try:
            metrics = {}

            # Response time
            if "response_time" in agent_status:
                metrics[MetricType.RESPONSE_TIME] = float(agent_status["response_time"])

            # Success rate
            if "success_rate" in agent_status:
                metrics[MetricType.SUCCESS_RATE] = float(agent_status["success_rate"])

            # Error rate (calculated from success rate)
            if MetricType.SUCCESS_RATE in metrics:
                metrics[MetricType.ERROR_RATE] = 1.0 - metrics[MetricType.SUCCESS_RATE]

            # Throughput (estimated from load and tasks processed)
            load = agent_status.get("load", 0)
            metrics[MetricType.THROUGHPUT] = float(load)  # Simplified throughput

            # Resource usage (estimated from load and capacity)
            capacity = agent_status.get("capacity", 5)
            if capacity > 0:
                metrics[MetricType.RESOURCE_USAGE] = (
                    load / capacity
                ) * 100  # Percentage

            # Heartbeat interval
            if "last_heartbeat" in agent_status:
                last_heartbeat = datetime.fromisoformat(agent_status["last_heartbeat"])
                metrics[MetricType.HEARTBEAT_INTERVAL] = (
                    datetime.now() - last_heartbeat
                ).total_seconds()

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to collect metrics for {agent_id}: {e}")
            return {}

    async def _calculate_health_score(
        self, agent_id: str, metrics: Dict[MetricType, float]
    ) -> Tuple[float, HealthStatus]:
        """Calculate health score and status"""
        try:
            if not metrics:
                return 0.0, HealthStatus.UNHEALTHY

            scores = []

            for metric_type, value in metrics.items():
                if metric_type == MetricType.RESPONSE_TIME:
                    # Lower response time is better
                    threshold = self.thresholds.get(metric_type, {})
                    if value <= threshold.get("warning", 5000):
                        scores.append(100)
                    elif value <= threshold.get("critical", 10000):
                        scores.append(70)
                    else:
                        scores.append(30)

                elif metric_type == MetricType.SUCCESS_RATE:
                    # Higher success rate is better
                    if value >= 0.95:
                        scores.append(100)
                    elif value >= 0.9:
                        scores.append(80)
                    elif value >= 0.8:
                        scores.append(60)
                    else:
                        scores.append(20)

                elif metric_type == MetricType.ERROR_RATE:
                    # Lower error rate is better
                    if value <= 0.05:
                        scores.append(100)
                    elif value <= 0.1:
                        scores.append(80)
                    elif value <= 0.2:
                        scores.append(60)
                    else:
                        scores.append(20)

                elif metric_type == MetricType.RESOURCE_USAGE:
                    # Moderate resource usage is best
                    if value <= 50:
                        scores.append(100)
                    elif value <= 80:
                        scores.append(80)
                    elif value <= 95:
                        scores.append(60)
                    else:
                        scores.append(30)

                elif metric_type == MetricType.HEARTBEAT_INTERVAL:
                    # Lower heartbeat interval is better
                    threshold = self.thresholds.get(metric_type, {})
                    if value <= threshold.get("warning", 60):
                        scores.append(100)
                    elif value <= threshold.get("critical", 120):
                        scores.append(70)
                    else:
                        scores.append(20)

                else:
                    # Default score for unknown metrics
                    scores.append(70)

            # Calculate overall score
            overall_score = statistics.mean(scores) if scores else 0

            # Determine health status
            if overall_score >= 90:
                status = HealthStatus.HEALTHY
            elif overall_score >= 70:
                status = HealthStatus.WARNING
            elif overall_score >= 50:
                status = HealthStatus.DEGRADED
            elif overall_score >= 30:
                status = HealthStatus.CRITICAL
            else:
                status = HealthStatus.UNHEALTHY

            return overall_score, status

        except Exception as e:
            self.logger.error(f"Failed to calculate health score for {agent_id}: {e}")
            return 0.0, HealthStatus.UNHEALTHY

    async def _check_metric_alerts(
        self, agent_id: str, metrics: Dict[MetricType, float]
    ) -> List[HealthAlert]:
        """Check metrics against thresholds and create alerts"""
        try:
            alerts = []

            for metric_type, value in metrics.items():
                thresholds = self.thresholds.get(metric_type, {})
                warning_threshold = thresholds.get("warning")
                critical_threshold = thresholds.get("critical")

                if critical_threshold is not None and value >= critical_threshold:
                    alert_id = await self.create_health_alert(
                        agent_id,
                        metric_type,
                        AlertSeverity.CRITICAL,
                        f"Critical {metric_type.value}: {value:.2f} (threshold: {critical_threshold})",
                        value,
                        critical_threshold,
                    )
                    if alert_id:
                        # Get the alert from storage
                        alert = self.health_alerts.get(alert_id)
                        if alert:
                            alerts.append(alert)

                elif warning_threshold is not None and value >= warning_threshold:
                    alert_id = await self.create_health_alert(
                        agent_id,
                        metric_type,
                        AlertSeverity.WARNING,
                        f"Warning {metric_type.value}: {value:.2f} (threshold: {warning_threshold})",
                        value,
                        warning_threshold,
                    )
                    if alert_id:
                        alert = self.health_alerts.get(alert_id)
                        if alert:
                            alerts.append(alert)

            return alerts

        except Exception as e:
            self.logger.error(f"Failed to check metric alerts for {agent_id}: {e}")
            return []

    async def _detect_metric_anomalies(
        self, agent_id: str, metrics: Dict[MetricType, float]
    ):
        """Detect anomalies in metrics"""
        try:
            for metric_type, value in metrics.items():
                is_anomaly = self.anomaly_detector.detect_anomaly(
                    agent_id, metric_type.value, value
                )

                if is_anomaly:
                    await self.create_health_alert(
                        agent_id,
                        metric_type,
                        AlertSeverity.WARNING,
                        f"Anomaly detected in {metric_type.value}: {value:.2f}",
                        value,
                        0,  # No threshold for anomaly detection
                    )

        except Exception as e:
            self.logger.error(f"Failed to detect anomalies for {agent_id}: {e}")

    async def _collect_and_store_metrics(
        self, agent_id: str, agent_info: Dict[str, Any]
    ):
        """Collect and store metrics for an agent"""
        try:
            # Create metric data points
            timestamp = datetime.now()

            metrics_to_store = [
                HealthMetric(
                    metric_type=MetricType.RESPONSE_TIME,
                    agent_id=agent_id,
                    value=float(agent_info.get("response_time", 0)),
                    timestamp=timestamp,
                    unit="ms",
                ),
                HealthMetric(
                    metric_type=MetricType.SUCCESS_RATE,
                    agent_id=agent_id,
                    value=float(agent_info.get("success_rate", 0)),
                    timestamp=timestamp,
                    unit="ratio",
                ),
                HealthMetric(
                    metric_type=MetricType.THROUGHPUT,
                    agent_id=agent_id,
                    value=float(agent_info.get("load", 0)),
                    timestamp=timestamp,
                    unit="tasks/min",
                ),
            ]

            # Store metrics
            for metric in metrics_to_store:
                self.health_metrics.append(metric)

        except Exception as e:
            self.logger.error(
                f"Failed to collect and store metrics for {agent_id}: {e}"
            )

    async def _check_alert_escalations(self):
        """Check for alert escalation conditions"""
        try:
            current_time = datetime.now()

            for alert in self.health_alerts.values():
                if alert.resolved or alert.acknowledged:
                    continue

                # Check for escalation based on age
                age_minutes = (current_time - alert.timestamp).total_seconds() / 60

                if alert.severity == AlertSeverity.WARNING and age_minutes > 30:
                    # Escalate warning to error after 30 minutes
                    alert.severity = AlertSeverity.ERROR
                    alert.message = f"[ESCALATED] {alert.message}"
                    await self._store_health_alert(alert)

                elif alert.severity == AlertSeverity.ERROR and age_minutes > 60:
                    # Escalate error to critical after 60 minutes
                    alert.severity = AlertSeverity.CRITICAL
                    alert.message = f"[ESCALATED] {alert.message}"
                    await self._store_health_alert(alert)

        except Exception as e:
            self.logger.error(f"Failed to check alert escalations: {e}")

    async def _send_alert_notifications(self):
        """Send notifications for critical alerts"""
        try:
            critical_alerts = [
                alert
                for alert in self.health_alerts.values()
                if alert.severity == AlertSeverity.CRITICAL and not alert.resolved
            ]

            for alert in critical_alerts:
                # Check if notification already sent recently
                last_notification = alert.metadata.get("last_notification")
                if last_notification:
                    last_notification_time = datetime.fromisoformat(last_notification)
                    if (
                        datetime.now() - last_notification_time
                    ).total_seconds() < 300:  # 5 minutes
                        continue

                # Send notification (implementation depends on notification system)
                await self._send_notification(alert)

                # Update notification timestamp
                alert.metadata["last_notification"] = datetime.now().isoformat()
                await self._store_health_alert(alert)

        except Exception as e:
            self.logger.error(f"Failed to send alert notifications: {e}")

    async def _send_notification(self, alert: HealthAlert):
        """Send notification for an alert"""
        try:
            # Implementation would send email, Slack, etc.
            self.logger.critical(f"CRITICAL ALERT: {alert.agent_id} - {alert.message}")

        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    async def _load_historical_data(self):
        """Load historical health data from database"""
        try:
            if not self.db_manager:
                return

            # Implementation would load historical metrics and alerts
            pass

        except Exception as e:
            self.logger.error(f"Failed to load historical data: {e}")

    async def _store_health_result(self, result: HealthCheckResult):
        """Store health check result in database"""
        try:
            if not self.db_manager:
                return

            result_data = {
                "agent_id": result.agent_id,
                "agent_type": result.agent_type,
                "status": result.status.value,
                "score": result.score,
                "metrics": {
                    m_type.value: value for m_type, value in result.metrics.items()
                },
                "details": result.details,
                "timestamp": result.timestamp.isoformat(),
            }

            # Store in database
            await self.db_manager.record_agent_metric(
                result.agent_id, "health_score", result.score, "score"
            )

            await self.db_manager.store_agent_memory("health_check", result_data)

        except Exception as e:
            self.logger.error(f"Failed to store health result: {e}")

    async def _store_health_alert(self, alert: HealthAlert):
        """Store health alert in database"""
        try:
            if not self.db_manager:
                return

            alert_data = {
                "alert_id": alert.alert_id,
                "agent_id": alert.agent_id,
                "severity": alert.severity.value,
                "message": alert.message,
                "metric_type": alert.metric_type.value,
                "value": alert.value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "metadata": alert.metadata,
            }

            # Store in database
            await self.db_manager.create_agent_task(
                {
                    **alert_data,
                    "task_type": "health_alert",
                    "task_status": "active" if not alert.resolved else "resolved",
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to store health alert: {e}")


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


async def get_health_monitor(config: Optional[Dict[str, Any]] = None) -> HealthMonitor:
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        default_config = {
            "check_interval": 30,
            "metrics_retention_hours": 24,
            "alert_thresholds": {
                "response_time": {"warning": 5000, "critical": 10000},
                "success_rate": {"warning": 0.9, "critical": 0.8},
                "error_rate": {"warning": 0.1, "critical": 0.2},
                "heartbeat_interval": {"warning": 60, "critical": 120},
            },
            "anomaly_window_size": 20,
            "anomaly_threshold": 2.0,
        }
        _health_monitor = HealthMonitor(config or default_config)
        await _health_monitor.initialize()
        await _health_monitor.start_monitoring()
    return _health_monitor
