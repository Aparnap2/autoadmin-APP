"""
Comprehensive monitoring and observability system for AutoAdmin
"""

from .logger import (
    StructuredLogger,
    ContextualLogger,
    LogLevel,
    ServiceComponent,
    get_logger,
    get_contextual_logger,
    set_correlation_id,
    set_trace_id,
    set_user_id,
    set_request_id,
    LogMiddleware
)

from .metrics import (
    MetricsCollector,
    MetricType,
    MetricUnit,
    MetricDefinition,
    Histogram,
    Meter,
    metrics_collector,
    register_default_metrics
)

from .health import (
    HealthChecker,
    HealthStatus,
    HealthStatusReport,
    SystemHealthReport,
    HealthCheck,
    health_checker,
    check_database_health,
    check_redis_health,
    check_qdrant_health,
    check_external_api_health,
    check_system_resources,
    check_filesystem_health
)

from .alerting import (
    AlertManager,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
    alert_manager,
    register_default_alert_rules,
    register_default_notification_channels
)

from .error_tracking import (
    ErrorTracker,
    ErrorOccurrence,
    ErrorReport,
    ErrorSeverity,
    ErrorCategory,
    ErrorStatus,
    ErrorContext,
    error_tracker,
    ErrorClassifier
)

from .endpoints import router as monitoring_router, monitoring_middleware
from .dashboard import (
    MonitoringDashboards,
    DashboardRenderer,
    create_all_dashboards
)

# Convenience imports
__all__ = [
    # Logging
    "StructuredLogger",
    "ContextualLogger",
    "LogLevel",
    "ServiceComponent",
    "get_logger",
    "get_contextual_logger",
    "set_correlation_id",
    "set_trace_id",
    "set_user_id",
    "set_request_id",
    "LogMiddleware",

    # Metrics
    "MetricsCollector",
    "MetricType",
    "MetricUnit",
    "MetricDefinition",
    "Histogram",
    "Meter",
    "metrics_collector",
    "register_default_metrics",

    # Health checks
    "HealthChecker",
    "HealthStatus",
    "HealthStatusReport",
    "SystemHealthReport",
    "HealthCheck",
    "health_checker",
    "check_database_health",
    "check_redis_health",
    "check_qdrant_health",
    "check_external_api_health",
    "check_system_resources",
    "check_filesystem_health",

    # Alerting
    "AlertManager",
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertStatus",
    "NotificationChannel",
    "alert_manager",
    "register_default_alert_rules",
    "register_default_notification_channels",

    # Error tracking
    "ErrorTracker",
    "ErrorOccurrence",
    "ErrorReport",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorStatus",
    "ErrorContext",
    "error_tracker",
    "ErrorClassifier",

    # Endpoints and middleware
    "monitoring_router",
    "monitoring_middleware",

    # Dashboards
    "MonitoringDashboards",
    "DashboardRenderer",
    "create_all_dashboards"
]