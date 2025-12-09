"""
Comprehensive alerting system for critical system events and failures
"""

import asyncio
import json
import smtplib
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import os


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status levels"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    description: str
    condition: str  # Expression to evaluate
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 15
    threshold_count: int = 1
    evaluation_window_minutes: int = 5
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None
    notification_channels: List[str] = None


@dataclass
class Alert:
    """Individual alert instance"""
    id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    timestamp: datetime
    labels: Dict[str, str]
    annotations: Dict[str, str]
    metric_value: float
    threshold_value: float
    component: str
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    first_seen: Optional[datetime] = None


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    name: str
    type: str  # email, slack, webhook, pagerduty, etc.
    config: Dict[str, Any]
    enabled: bool = True
    severity_filter: List[AlertSeverity] = None


class AlertManager:
    """
    Comprehensive alert management system
    """

    def __init__(self, service_name: str = "autoadmin-backend"):
        self.service_name = service_name
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.running = False
        self.evaluation_task = None
        self.suppression_rules: Dict[str, Callable] = {}

        # Alert deduplication
        self.alert_cooldowns: Dict[str, datetime] = {}

        # Evaluation intervals
        self.evaluation_interval = 60  # seconds

    def register_alert_rule(self, rule: AlertRule):
        """Register a new alert rule"""
        self.alert_rules[rule.name] = rule

    def remove_alert_rule(self, name: str):
        """Remove an alert rule"""
        if name in self.alert_rules:
            del self.alert_rules[name]

    def register_notification_channel(self, channel: NotificationChannel):
        """Register a notification channel"""
        self.notification_channels[channel.name] = channel

    def register_suppression_rule(self, name: str, rule_func: Callable):
        """Register a suppression rule function"""
        self.suppression_rules[name] = rule_func

    async def evaluate_alert_rules(self, metrics: Dict[str, Any], health_status: Dict[str, Any]):
        """Evaluate all alert rules against current metrics and health status"""
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue

            # Check cooldown
            if rule_name in self.alert_cooldowns:
                if datetime.utcnow() < self.alert_cooldowns[rule_name]:
                    continue

            try:
                # Evaluate rule condition
                should_alert = await self._evaluate_rule_condition(rule, metrics, health_status)

                if should_alert:
                    await self._trigger_alert(rule, metrics)
                else:
                    await self._resolve_alert(rule_name)

            except Exception as e:
                print(f"Error evaluating alert rule {rule_name}: {e}")

    async def _evaluate_rule_condition(self, rule: AlertRule, metrics: Dict[str, Any], health_status: Dict[str, Any]) -> bool:
        """Evaluate a single alert rule condition"""
        # Create evaluation context
        context = {
            "metrics": metrics,
            "health": health_status,
            "time": datetime.utcnow(),
        }

        # Evaluate condition based on common patterns
        condition = rule.condition.lower()

        # System health alerts
        if "unhealthy" in condition and "components" in condition:
            unhealthy_count = len([c for c in health_status.get("components", {}).values() if c.status == "unhealthy"])
            if "unhealthy_components > 0" in condition:
                return unhealthy_count > 0
            elif "unhealthy_components >=" in condition:
                threshold = self._extract_number(condition.split(">=")[1])
                return unhealthy_count >= threshold

        # Error rate alerts
        if "error_rate" in condition:
            error_rate = metrics.get("http_requests_error_rate_percent", 0)
            if "error_rate >" in condition:
                threshold = self._extract_number(condition.split(">")[1])
                return error_rate > threshold

        # Response time alerts
        if "response_time" in condition or "duration" in condition:
            response_time = metrics.get("http_request_duration_ms_avg", 0)
            if "response_time >" in condition:
                threshold = self._extract_number(condition.split(">")[1])
                return response_time > threshold

        # CPU alerts
        if "cpu" in condition:
            cpu_percent = metrics.get("system_cpu_percent", 0)
            if "cpu >" in condition:
                threshold = self._extract_number(condition.split(">")[1])
                return cpu_percent > threshold

        # Memory alerts
        if "memory" in condition:
            memory_percent = metrics.get("system_memory_percent", 0)
            if "memory >" in condition:
                threshold = self._extract_number(condition.split(">")[1])
                return memory_percent > threshold

        # Database alerts
        if "database" in condition:
            if "connections" in condition:
                db_connections = metrics.get("database_connections_active", 0)
                if "connections >" in condition:
                    threshold = self._extract_number(condition.split(">")[1])
                    return db_connections > threshold

        # Agent-specific alerts
        if "agent" in condition:
            if "failed" in condition:
                failed_tasks = metrics.get("tasks_failed_total", 0)
                if "failed_tasks >" in condition:
                    threshold = self._extract_number(condition.split(">")[1])
                    return failed_tasks > threshold

        # Default: no alert
        return False

    def _extract_number(self, text: str) -> float:
        """Extract numeric value from text"""
        import re
        match = re.search(r'[\d.]+', text)
        return float(match.group()) if match else 0

    async def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger a new alert"""
        alert_id = f"{rule.name}_{int(datetime.utcnow().timestamp())}"

        # Get metric value for the alert
        metric_value = self._get_metric_value_for_rule(rule, metrics)
        threshold_value = self._get_threshold_value_for_rule(rule)

        # Check suppression rules
        if await self._is_suppressed(rule, metrics):
            return

        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=rule.description,
            timestamp=datetime.utcnow(),
            labels=rule.labels or {},
            annotations=rule.annotations or {},
            metric_value=metric_value,
            threshold_value=threshold_value,
            component=rule.labels.get("component", "system"),
            first_seen=datetime.utcnow()
        )

        # Store alert
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)

        # Keep only last 1000 alerts in history
        if len(self.alert_history) > 1000:
            self.alert_history.pop(0)

        # Set cooldown
        self.alert_cooldowns[rule.name] = datetime.utcnow() + timedelta(minutes=rule.cooldown_minutes)

        # Send notifications
        await self._send_notifications(alert)

        print(f"🚨 ALERT TRIGGERED: {rule.name} - {rule.description}")

    async def _resolve_alert(self, rule_name: str):
        """Resolve an active alert"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()

            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[rule_name]

            # Send resolution notification
            await self._send_resolution_notification(alert)

            print(f"✅ ALERT RESOLVED: {rule_name}")

    def _get_metric_value_for_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> float:
        """Get the current metric value for an alert rule"""
        condition = rule.condition.lower()

        if "error_rate" in condition:
            return metrics.get("http_requests_error_rate_percent", 0)
        elif "response_time" in condition:
            return metrics.get("http_request_duration_ms_avg", 0)
        elif "cpu" in condition:
            return metrics.get("system_cpu_percent", 0)
        elif "memory" in condition:
            return metrics.get("system_memory_percent", 0)
        elif "unhealthy" in condition:
            unhealthy_count = len([c for c in metrics.get("components", {}).values() if c.get("status") == "unhealthy"])
            return float(unhealthy_count)
        elif "failed_tasks" in condition:
            return metrics.get("tasks_failed_total", 0)
        else:
            return 0.0

    def _get_threshold_value_for_rule(self, rule: AlertRule) -> float:
        """Extract threshold value from alert rule condition"""
        condition = rule.condition
        if ">" in condition:
            return self._extract_number(condition.split(">")[1])
        elif "<" in condition:
            return self._extract_number(condition.split("<")[1])
        elif ">=" in condition:
            return self._extract_number(condition.split(">=")[1])
        elif "<=" in condition:
            return self._extract_number(condition.split("<=")[1])
        else:
            return 0.0

    async def _is_suppressed(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Check if an alert should be suppressed"""
        for name, suppression_func in self.suppression_rules.items():
            try:
                if await suppression_func(rule, metrics):
                    return True
            except Exception as e:
                print(f"Error evaluating suppression rule {name}: {e}")
        return False

    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        rule = self.alert_rules.get(alert.rule_name)
        if not rule:
            return

        for channel_name in rule.notification_channels or []:
            channel = self.notification_channels.get(channel_name)
            if not channel or not channel.enabled:
                continue

            # Check severity filter
            if channel.severity_filter and alert.severity not in channel.severity_filter:
                continue

            try:
                if channel.type == "email":
                    await self._send_email_notification(channel, alert)
                elif channel.type == "slack":
                    await self._send_slack_notification(channel, alert)
                elif channel.type == "webhook":
                    await self._send_webhook_notification(channel, alert)
                elif channel.type == "pagerduty":
                    await self._send_pagerduty_notification(channel, alert)
            except Exception as e:
                print(f"Error sending notification to {channel_name}: {e}")

    async def _send_resolution_notification(self, alert: Alert):
        """Send resolution notification"""
        for channel_name, channel in self.notification_channels.items():
            if not channel.enabled:
                continue

            try:
                if channel.type == "email":
                    await self._send_email_resolution(channel, alert)
                elif channel.type == "slack":
                    await self._send_slack_resolution(channel, alert)
            except Exception as e:
                print(f"Error sending resolution notification to {channel_name}: {e}")

    async def _send_email_notification(self, channel: NotificationChannel, alert: Alert):
        """Send email notification"""
        config = channel.config

        msg = MIMEMultipart()
        msg['From'] = config.get('from_email')
        msg['To'] = ', '.join(config.get('to_emails', []))
        msg['Subject'] = f"🚨 [{alert.severity.value.upper()}] AutoAdmin Alert: {alert.rule_name}"

        body = f"""
Alert Details:
- Rule: {alert.rule_name}
- Severity: {alert.severity.value.upper()}
- Message: {alert.message}
- Component: {alert.component}
- Metric Value: {alert.metric_value}
- Threshold: {alert.threshold_value}
- Timestamp: {alert.timestamp.isoformat()}

Labels:
{json.dumps(alert.labels, indent=2)}

Annotations:
{json.dumps(alert.annotations, indent=2)}
"""

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(config.get('smtp_host'), config.get('smtp_port', 587))
            server.starttls()
            server.login(config.get('smtp_username'), config.get('smtp_password'))
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Failed to send email notification: {e}")

    async def _send_email_resolution(self, channel: NotificationChannel, alert: Alert):
        """Send email resolution notification"""
        config = channel.config

        msg = MIMEMultipart()
        msg['From'] = config.get('from_email')
        msg['To'] = ', '.join(config.get('to_emails', []))
        msg['Subject'] = f"✅ RESOLVED: AutoAdmin Alert: {alert.rule_name}"

        body = f"""
Alert Resolved:
- Rule: {alert.rule_name}
- Message: {alert.message}
- Component: {alert.component}
- First Seen: {alert.first_seen.isoformat() if alert.first_seen else 'Unknown'}
- Resolved At: {alert.resolved_at.isoformat() if alert.resolved_at else 'Unknown'}
- Duration: {((alert.resolved_at or datetime.utcnow()) - (alert.first_seen or alert.timestamp)).total_seconds():.0f} seconds
"""

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(config.get('smtp_host'), config.get('smtp_port', 587))
            server.starttls()
            server.login(config.get('smtp_username'), config.get('smtp_password'))
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Failed to send email resolution: {e}")

    async def _send_slack_notification(self, channel: NotificationChannel, alert: Alert):
        """Send Slack notification"""
        config = channel.config
        webhook_url = config.get('webhook_url')

        color = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "danger",
            AlertSeverity.CRITICAL: "danger"
        }.get(alert.severity, "warning")

        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚨 {alert.severity.value.upper()} Alert: {alert.rule_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Component", "value": alert.component, "short": True},
                    {"title": "Metric Value", "value": str(alert.metric_value), "short": True},
                    {"title": "Threshold", "value": str(alert.threshold_value), "short": True},
                    {"title": "Timestamp", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                ],
                "footer": "AutoAdmin",
                "ts": int(alert.timestamp.timestamp())
            }]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to send Slack notification: {response.status}")

    async def _send_slack_resolution(self, channel: NotificationChannel, alert: Alert):
        """Send Slack resolution notification"""
        config = channel.config
        webhook_url = config.get('webhook_url')

        payload = {
            "attachments": [{
                "color": "good",
                "title": f"✅ RESOLVED: {alert.rule_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Component", "value": alert.component, "short": True},
                    {"title": "Duration", "value": f"{((alert.resolved_at or datetime.utcnow()) - (alert.first_seen or alert.timestamp)).total_seconds():.0f}s", "short": True},
                    {"title": "Resolved At", "value": (alert.resolved_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                ],
                "footer": "AutoAdmin",
                "ts": int((alert.resolved_at or datetime.utcnow()).timestamp())
            }]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to send Slack resolution: {response.status}")

    async def _send_webhook_notification(self, channel: NotificationChannel, alert: Alert):
        """Send webhook notification"""
        config = channel.config
        url = config.get('url')
        headers = config.get('headers', {})

        payload = {
            "alert_id": alert.id,
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "message": alert.message,
            "component": alert.component,
            "metric_value": alert.metric_value,
            "threshold_value": alert.threshold_value,
            "timestamp": alert.timestamp.isoformat(),
            "labels": alert.labels,
            "annotations": alert.annotations
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status not in [200, 201, 202]:
                    print(f"Failed to send webhook notification: {response.status}")

    async def _send_pagerduty_notification(self, channel: NotificationChannel, alert: Alert):
        """Send PagerDuty notification"""
        config = channel.config
        integration_key = config.get('integration_key')

        severity_map = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical"
        }

        payload = {
            "routing_key": integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"{alert.severity.value.upper()}: {alert.rule_name} - {alert.message}",
                "source": "autoadmin",
                "severity": severity_map.get(alert.severity, "error"),
                "component": alert.component,
                "custom_details": {
                    "alert_id": alert.id,
                    "rule_name": alert.rule_name,
                    "metric_value": alert.metric_value,
                    "threshold_value": alert.threshold_value,
                    "labels": alert.labels
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://events.pagerduty.com/v2/enqueue", json=payload) as response:
                if response.status != 202:
                    print(f"Failed to send PagerDuty notification: {response.status}")

    def get_active_alerts(self, severity: AlertSeverity = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        alerts = list(self.active_alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp >= cutoff_time]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)

        severity_counts = {
            severity.value: len([a for a in self.active_alerts.values() if a.severity == severity])
            for severity in AlertSeverity
        }

        recent_alerts = self.get_alert_history(24)
        recent_by_severity = {
            severity.value: len([a for a in recent_alerts if a.severity == severity])
            for severity in AlertSeverity
        }

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "severity_breakdown": severity_counts,
            "last_24_hours": {
                "total": len(recent_alerts),
                "by_severity": recent_by_severity
            }
        }

    async def start_monitoring(self):
        """Start continuous alert monitoring"""
        if self.running:
            return

        self.running = True
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())

    async def stop_monitoring(self):
        """Stop continuous alert monitoring"""
        self.running = False
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass

    async def _evaluation_loop(self):
        """Background alert evaluation loop"""
        while self.running:
            try:
                # This should be called with current metrics and health status
                # In practice, this would be integrated with the metrics and health systems
                await asyncio.sleep(self.evaluation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(self.evaluation_interval)


# Global alert manager instance
alert_manager = AlertManager()


def register_default_alert_rules():
    """Register default alert rules for AutoAdmin"""

    # System health alerts
    alert_manager.register_alert_rule(AlertRule(
        name="system_unhealthy_components",
        description="System has unhealthy components",
        condition="unhealthy_components > 0",
        severity=AlertSeverity.ERROR,
        cooldown_minutes=10,
        labels={"component": "system"},
        notification_channels=["email", "slack"]
    ))

    # Error rate alerts
    alert_manager.register_alert_rule(AlertRule(
        name="high_error_rate",
        description="HTTP error rate is too high",
        condition="error_rate > 5",
        severity=AlertSeverity.WARNING,
        cooldown_minutes=15,
        labels={"component": "api"},
        notification_channels=["email", "slack"]
    ))

    alert_manager.register_alert_rule(AlertRule(
        name="critical_error_rate",
        description="HTTP error rate is critical",
        condition="error_rate > 20",
        severity=AlertSeverity.CRITICAL,
        cooldown_minutes=5,
        labels={"component": "api"},
        notification_channels=["email", "slack", "pagerduty"]
    ))

    # Response time alerts
    alert_manager.register_alert_rule(AlertRule(
        name="slow_response_time",
        description="API response time is too slow",
        condition="response_time > 5000",
        severity=AlertSeverity.WARNING,
        cooldown_minutes=20,
        labels={"component": "api"},
        notification_channels=["email"]
    ))

    # System resource alerts
    alert_manager.register_alert_rule(AlertRule(
        name="high_cpu_usage",
        description="CPU usage is too high",
        condition="cpu > 80",
        severity=AlertSeverity.WARNING,
        cooldown_minutes=30,
        labels={"component": "system"},
        notification_channels=["email"]
    ))

    alert_manager.register_alert_rule(AlertRule(
        name="critical_cpu_usage",
        description="CPU usage is critical",
        condition="cpu > 95",
        severity=AlertSeverity.CRITICAL,
        cooldown_minutes=10,
        labels={"component": "system"},
        notification_channels=["email", "slack", "pagerduty"]
    ))

    alert_manager.register_alert_rule(AlertRule(
        name="high_memory_usage",
        description="Memory usage is too high",
        condition="memory > 85",
        severity=AlertSeverity.WARNING,
        cooldown_minutes=30,
        labels={"component": "system"},
        notification_channels=["email"]
    ))

    # Database alerts
    alert_manager.register_alert_rule(AlertRule(
        name="database_connection_issues",
        description="Too many database connections",
        condition="database_connections > 50",
        severity=AlertSeverity.WARNING,
        cooldown_minutes=15,
        labels={"component": "database"},
        notification_channels=["email", "slack"]
    ))

    # Agent alerts
    alert_manager.register_alert_rule(AlertRule(
        name="agent_task_failures",
        description="Too many agent task failures",
        condition="failed_tasks > 10",
        severity=AlertSeverity.ERROR,
        cooldown_minutes=20,
        labels={"component": "agents"},
        notification_channels=["email", "slack"]
    ))


def register_default_notification_channels():
    """Register default notification channels based on environment"""

    # Email channel (if configured)
    if os.getenv("ALERT_EMAIL_SMTP_HOST"):
        email_channel = NotificationChannel(
            name="email",
            type="email",
            config={
                "smtp_host": os.getenv("ALERT_EMAIL_SMTP_HOST"),
                "smtp_port": int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587")),
                "smtp_username": os.getenv("ALERT_EMAIL_USERNAME"),
                "smtp_password": os.getenv("ALERT_EMAIL_PASSWORD"),
                "from_email": os.getenv("ALERT_EMAIL_FROM"),
                "to_emails": os.getenv("ALERT_EMAIL_TO", "").split(",")
            },
            severity_filter=[AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        )
        alert_manager.register_notification_channel(email_channel)

    # Slack channel (if configured)
    if os.getenv("ALERT_SLACK_WEBHOOK_URL"):
        slack_channel = NotificationChannel(
            name="slack",
            type="slack",
            config={
                "webhook_url": os.getenv("ALERT_SLACK_WEBHOOK_URL")
            },
            severity_filter=[AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        )
        alert_manager.register_notification_channel(slack_channel)

    # PagerDuty channel (if configured)
    if os.getenv("ALERT_PAGERDUTY_INTEGRATION_KEY"):
        pagerduty_channel = NotificationChannel(
            name="pagerduty",
            type="pagerduty",
            config={
                "integration_key": os.getenv("ALERT_PAGERDUTY_INTEGRATION_KEY")
            },
            severity_filter=[AlertSeverity.CRITICAL]
        )
        alert_manager.register_notification_channel(pagerduty_channel)

    # Webhook channel (if configured)
    if os.getenv("ALERT_WEBHOOK_URL"):
        webhook_channel = NotificationChannel(
            name="webhook",
            type="webhook",
            config={
                "url": os.getenv("ALERT_WEBHOOK_URL"),
                "headers": {
                    "Authorization": f"Bearer {os.getenv('ALERT_WEBHOOK_TOKEN', '')}"
                }
            },
            severity_filter=[AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        )
        alert_manager.register_notification_channel(webhook_channel)


# Initialize default rules and channels
register_default_alert_rules()
register_default_notification_channels()