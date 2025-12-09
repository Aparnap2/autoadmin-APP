"""
Monitoring and health check endpoints for FastAPI integration
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
import asyncio

from .logger import get_logger, set_correlation_id, set_request_id, LogLevel, ServiceComponent
from .metrics import metrics_collector
from .health import health_checker, HealthStatus
from .alerting import alert_manager, AlertSeverity

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = get_logger("monitoring_endpoints")


@router.get("/health", summary="Basic Health Check")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "autoadmin-backend",
        "version": "1.0.0"
    }


@router.get("/health/ready", summary="Readiness Probe")
async def readiness_probe():
    """Readiness probe - checks if service is ready to handle requests"""
    try:
        # Check critical components
        critical_checks = ["system_resources", "filesystem"]

        for check_name in critical_checks:
            if check_name in health_checker.health_checks:
                result = await health_checker.check_component_health(check_name)
                if result.status == HealthStatus.UNHEALTHY:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "status": "not_ready",
                            "timestamp": datetime.utcnow().isoformat(),
                            "reason": f"Component {check_name} is unhealthy: {result.message}"
                        }
                    )

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks_passed": len(critical_checks)
        }

    except Exception as e:
        logger.error("Readiness probe failed", component=ServiceComponent.MONITORING, error=e)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f"Readiness check failed: {str(e)}"
            }
        )


@router.get("/health/live", summary="Liveness Probe")
async def liveness_probe():
    """Liveness probe - checks if service is alive"""
    try:
        # Basic liveness check
        uptime_seconds = datetime.utcnow().timestamp() - health_checker.start_time

        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds
        }

    except Exception as e:
        logger.error("Liveness probe failed", component=ServiceComponent.MONITORING, error=e)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_alive",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f"Liveness check failed: {str(e)}"
            }
        )


@router.get("/health/detailed", summary="Detailed Health Check")
async def detailed_health_check():
    """Comprehensive health check of all components"""
    try:
        system_health = await health_checker.get_system_health()

        return {
            "status": system_health.status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "uptime_seconds": system_health.uptime_seconds,
            "summary": system_health.summary,
            "components": {
                name: {
                    "status": report.status.value,
                    "message": report.message,
                    "response_time_ms": report.response_time_ms,
                    "consecutive_failures": report.consecutive_failures,
                    "details": report.details
                }
                for name, report in system_health.components.items()
            },
            "recommendations": system_health.recommendations
        }

    except Exception as e:
        logger.error("Detailed health check failed", component=ServiceComponent.MONITORING, error=e)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.get("/health/components/{component_name}", summary="Component Health Check")
async def component_health_check(component_name: str):
    """Check health of a specific component"""
    try:
        result = await health_checker.check_component_health(component_name)

        return {
            "component": result.component,
            "component_type": result.component_type,
            "status": result.status.value,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
            "response_time_ms": result.response_time_ms,
            "consecutive_failures": result.consecutive_failures,
            "uptime_percentage": result.uptime_percentage,
            "details": result.details
        }

    except Exception as e:
        logger.error(f"Component health check failed for {component_name}",
                    component=ServiceComponent.MONITORING, error=e)
        return JSONResponse(
            status_code=500,
            content={
                "component": component_name,
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.get("/metrics", summary="System Metrics")
async def get_metrics(
    format: str = Query(default="json", description="Output format: json, prometheus"),
    component: Optional[str] = Query(default=None, description="Filter by component")
):
    """Get current system metrics"""
    try:
        if format == "prometheus":
            metrics_data = metrics_collector.get_metrics_for_export()

            # Format as Prometheus text format
            prometheus_lines = []
            for metric_name, value in metrics_data.items():
                prometheus_lines.append(f"{metric_name} {value}")

            prometheus_text = "\n".join(prometheus_lines)
            return Response(
                content=prometheus_text,
                media_type="text/plain"
            )
        else:
            metrics_summary = metrics_collector.get_metrics_summary()

            if component:
                # Filter metrics by component
                filtered_metrics = {}
                for key, value in metrics_summary.get("metrics", {}).items():
                    if component in key.lower() or (isinstance(value, dict) and
                        any(component in str(v).lower() for v in value.values())):
                        filtered_metrics[key] = value
                metrics_summary["metrics"] = filtered_metrics

            return metrics_summary

    except Exception as e:
        logger.error("Failed to get metrics", component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/history", summary="Metrics History")
async def get_metrics_history(
    metric_name: str = Query(..., description="Metric name"),
    hours: int = Query(default=24, description="History in hours"),
    labels: Optional[str] = Query(default=None, description="Labels as JSON string")
):
    """Get historical metrics data"""
    try:
        import json

        label_dict = json.loads(labels) if labels else {}

        # This would typically query a time series database
        # For now, return recent values from the time_series storage
        key = f"{metric_name}:{json.dumps(label_dict, sort_keys=True)}"
        time_series = metrics_collector.time_series.get(key, [])

        # Filter by time window
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_values = [
            {
                "timestamp": value.timestamp.isoformat(),
                "value": value.value,
                "labels": value.labels
            }
            for value in time_series
            if value.timestamp >= cutoff_time
        ]

        return {
            "metric_name": metric_name,
            "labels": label_dict,
            "hours": hours,
            "data_points": len(recent_values),
            "values": recent_values
        }

    except Exception as e:
        logger.error(f"Failed to get metrics history for {metric_name}",
                    component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics history")


@router.get("/alerts", summary="Active Alerts")
async def get_alerts(
    severity: Optional[AlertSeverity] = Query(default=None, description="Filter by severity"),
    status: Optional[str] = Query(default="active", description="Filter by status: active, history")
):
    """Get alerts"""
    try:
        if status == "active":
            alerts = alert_manager.get_active_alerts(severity)
        else:
            alerts = alert_manager.get_alert_history(24)  # Last 24 hours
            if severity:
                alerts = [a for a in alerts if a.severity == severity]

        return {
            "status": status,
            "severity_filter": severity.value if severity else None,
            "count": len(alerts),
            "alerts": [
                {
                    "id": alert.id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "component": alert.component,
                    "metric_value": alert.metric_value,
                    "threshold_value": alert.threshold_value,
                    "timestamp": alert.timestamp.isoformat(),
                    "first_seen": alert.first_seen.isoformat() if alert.first_seen else None,
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                    "labels": alert.labels,
                    "annotations": alert.annotations,
                    "consecutive_failures": getattr(alert, 'consecutive_failures', 0)
                }
                for alert in alerts
            ]
        }

    except Exception as e:
        logger.error("Failed to get alerts", component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/alerts/statistics", summary="Alert Statistics")
async def get_alert_statistics():
    """Get alert statistics"""
    try:
        return alert_manager.get_alert_statistics()

    except Exception as e:
        logger.error("Failed to get alert statistics", component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to retrieve alert statistics")


@router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge Alert")
async def acknowledge_alert(alert_id: str, user: str = Query(..., description="User acknowledging the alert")):
    """Acknowledge an alert"""
    try:
        # Find the alert
        alert = None
        for active_alert in alert_manager.active_alerts.values():
            if active_alert.id == alert_id:
                alert = active_alert
                break

        if not alert:
            # Also check history
            for hist_alert in alert_manager.alert_history:
                if hist_alert.id == alert_id and hist_alert.status.value == "active":
                    alert = hist_alert
                    break

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Update alert status
        alert.status = alert_manager.AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user

        logger.info(
            f"Alert {alert_id} acknowledged by {user}",
            component=ServiceComponent.MONITORING,
            alert_id=alert_id,
            user=user
        )

        return {
            "alert_id": alert_id,
            "status": "acknowledged",
            "acknowledged_by": user,
            "acknowledged_at": alert.acknowledged_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}",
                    component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/logs", summary="System Logs")
async def get_logs(
    level: Optional[LogLevel] = Query(default=None, description="Filter by log level"),
    component: Optional[ServiceComponent] = Query(default=None, description="Filter by component"),
    hours: int = Query(default=1, description="Log history in hours"),
    limit: int = Query(default=100, description="Maximum number of log entries")
):
    """Get system logs (placeholder - would typically query log storage)"""
    try:
        # This is a placeholder - in a real implementation, this would query
        # a log storage system like Elasticsearch, Loki, or similar

        return {
            "message": "Log retrieval not implemented - integrate with log storage system",
            "parameters": {
                "level": level.value if level else None,
                "component": component.value if component else None,
                "hours": hours,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error("Failed to get logs", component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/status", summary="System Status Overview")
async def get_system_status():
    """Get comprehensive system status overview"""
    try:
        # Get system health
        system_health = await health_checker.get_system_health()

        # Get metrics summary
        metrics_summary = metrics_collector.get_metrics_summary()

        # Get alert statistics
        alert_stats = alert_manager.get_alert_statistics()

        # Get uptime
        uptime_seconds = datetime.utcnow().timestamp() - health_checker.start_time

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "autoadmin-backend",
            "version": "1.0.0",
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": str(timedelta(seconds=int(uptime_seconds))),
            "health": {
                "status": system_health.status.value,
                "components_healthy": system_health.summary["healthy_components"],
                "components_total": system_health.summary["total_components"],
                "critical_failures": system_health.summary["critical_failures"]
            },
            "metrics": {
                "total_metrics": len(metrics_summary.get("metrics", {})),
                "key_metrics": {
                    "cpu_percent": metrics_summary.get("metrics", {}).get("system_cpu_percent", {}).get("value", 0),
                    "memory_percent": metrics_summary.get("metrics", {}).get("system_memory_percent", {}).get("value", 0),
                    "agents_active": metrics_summary.get("metrics", {}).get("agents_active_count", {}).get("value", 0),
                    "http_requests_total": metrics_summary.get("metrics", {}).get("http_requests_total", {}).get("value", 0),
                    "error_rate": metrics_summary.get("metrics", {}).get("http_requests_error_rate_percent", {}).get("value", 0)
                }
            },
            "alerts": {
                "active_alerts": alert_stats["active_alerts"],
                "total_alerts": alert_stats["total_alerts"],
                "severity_breakdown": alert_stats["severity_breakdown"]
            }
        }

    except Exception as e:
        logger.error("Failed to get system status", component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")


@router.post("/test-alert", summary="Test Alert System")
async def test_alert_system(
    severity: AlertSeverity = Query(default=AlertSeverity.INFO, description="Test alert severity"),
    message: str = Query(default="Test alert", description="Test alert message")
):
    """Send a test alert to verify notification channels"""
    try:
        # Create a test alert
        test_alert_id = f"test_alert_{int(datetime.utcnow().timestamp())}"

        from .alerting import Alert, AlertStatus
        test_alert = Alert(
            id=test_alert_id,
            rule_name="test_alert",
            severity=severity,
            status=AlertStatus.ACTIVE,
            message=message,
            timestamp=datetime.utcnow(),
            labels={"test": "true", "component": "monitoring"},
            annotations={"test_alert": "true"},
            metric_value=0.0,
            threshold_value=0.0,
            component="monitoring"
        )

        # Send notifications
        await alert_manager._send_notifications(test_alert)

        logger.info(
            f"Test alert sent: {message}",
            component=ServiceComponent.MONITORING,
            alert_id=test_alert_id,
            severity=severity.value
        )

        return {
            "test_alert_id": test_alert_id,
            "severity": severity.value,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "sent"
        }

    except Exception as e:
        logger.error("Failed to send test alert", component=ServiceComponent.MONITORING, error=e)
        raise HTTPException(status_code=500, detail="Failed to send test alert")


# Middleware for automatic monitoring
async def monitoring_middleware(request: Request, call_next):
    """Middleware to automatically track requests and metrics"""
    # Generate correlation ID and request ID
    cid = request.headers.get("x-correlation-id") or f"req_{int(datetime.utcnow().timestamp())}"
    rid = request.headers.get("x-request-id") or f"req_{int(datetime.utcnow().timestamp() * 1000)}"

    # Set in context
    set_correlation_id(cid)
    set_request_id(rid)

    # Record request start
    start_time = datetime.utcnow()

    # Log request
    logger.info(
        f"HTTP {request.method} {request.url.path}",
        component=ServiceComponent.API,
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # Increment request counter
    metrics_collector.increment(
        "http_requests_total",
        labels={
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": "pending"  # Will be updated after response
        }
    )

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update metrics with actual status code
        status_code = str(response.status_code)
        metrics_collector.increment(
            "http_requests_total",
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": status_code
            }
        )

        # Record response time
        metrics_collector.timer(
            "http_request_duration_ms",
            duration_ms,
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": status_code
            }
        )

        # Track errors
        if response.status_code >= 400:
            metrics_collector.increment(
                "http_requests_error_total",
                labels={
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": status_code
                }
            )

        # Add correlation headers to response
        response.headers["x-correlation-id"] = cid
        response.headers["x-request-id"] = rid

        # Log response
        logger.info(
            f"HTTP {response.status_code} {request.method} {request.url.path}",
            component=ServiceComponent.API,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        return response

    except Exception as e:
        # Calculate duration for failed request
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update error metrics
        metrics_collector.increment(
            "http_requests_total",
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": "500"
            }
        )

        metrics_collector.increment(
            "http_requests_error_total",
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": "500"
            }
        )

        metrics_collector.timer(
            "http_request_duration_ms",
            duration_ms,
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": "500"
            }
        )

        # Log error
        logger.error(
            f"HTTP 500 {request.method} {request.url.path}",
            component=ServiceComponent.API,
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration_ms,
            error=e
        )

        raise