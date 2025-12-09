"""
Integration layer for AutoAdmin monitoring system
"""

import asyncio
import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from . import (
    metrics_collector,
    health_checker,
    alert_manager,
    error_tracker,
    monitoring_router,
    monitoring_middleware
)
from .logger import get_logger, set_correlation_id, LogLevel, ServiceComponent
from .metrics import register_default_metrics
from .health import (
    check_database_health,
    check_redis_health,
    check_qdrant_health,
    check_external_api_health,
    check_system_resources,
    check_filesystem_health
)
from .alerting import register_default_alert_rules, register_default_notification_channels
from .error_tracking import ErrorContext


class AutoAdminMonitoring:
    """
    Main monitoring integration class for AutoAdmin
    """

    def __init__(self, service_name: str = "autoadmin-backend"):
        self.service_name = service_name
        self.logger = get_logger("autoadmin_monitoring")
        self.initialized = False
        self.running = False

    async def initialize(self, config: Dict[str, Any] = None):
        """Initialize all monitoring components"""
        if self.initialized:
            return

        try:
            self.logger.info(
                "Initializing AutoAdmin monitoring system",
                component=ServiceComponent.MONITORING
            )

            config = config or {}

            # Initialize metrics collection
            await self._initialize_metrics(config)

            # Initialize health checks
            await self._initialize_health_checks(config)

            # Initialize alerting
            await self._initialize_alerting(config)

            # Initialize error tracking
            await self._initialize_error_tracking(config)

            # Start monitoring background tasks
            await self.start_monitoring()

            self.initialized = True

            self.logger.info(
                "AutoAdmin monitoring system initialized successfully",
                component=ServiceComponent.MONITORING
            )

        except Exception as e:
            self.logger.error(
                "Failed to initialize monitoring system",
                component=ServiceComponent.MONITORING,
                error=e
            )
            raise

    async def _initialize_metrics(self, config: Dict[str, Any]):
        """Initialize metrics collection"""
        self.logger.info(
            "Initializing metrics collection",
            component=ServiceComponent.MONITORING
        )

        # Register default metrics
        register_default_metrics()

        # Configure metrics collection
        metrics_collector.service_name = self.service_name
        metrics_collector.environment = config.get("environment", "development")
        metrics_collector.collection_interval = config.get("metrics_collection_interval", 15)
        metrics_collector.retention_hours = config.get("metrics_retention_hours", 24)

        # Start metrics collection
        metrics_collector.start_collection()

    async def _initialize_health_checks(self, config: Dict[str, Any]):
        """Initialize health checks"""
        self.logger.info(
            "Initializing health checks",
            component=ServiceComponent.MONITORING
        )

        # Register system health checks
        health_checker.register_health_check(
            name="system_resources",
            description="System resource utilization check",
            component_type="system",
            check_function=check_system_resources,
            timeout=10.0,
            critical=True
        )

        health_checker.register_health_check(
            name="filesystem",
            description="Filesystem access and space check",
            component_type="system",
            check_function=lambda: check_filesystem_health(config.get("health_check_path", "/")),
            timeout=5.0,
            critical=True
        )

        # Database health checks
        db_config = config.get("database", {})
        if db_config.get("connection_string"):
            health_checker.register_health_check(
                name="database",
                description="Database connectivity and basic query check",
                component_type="database",
                check_function=lambda: check_database_health(db_config["connection_string"]),
                timeout=15.0,
                critical=True
            )

        # Redis health checks
        redis_config = config.get("redis", {})
        if redis_config.get("host"):
            health_checker.register_health_check(
                name="redis",
                description="Redis connectivity check",
                component_type="cache",
                check_function=lambda: check_redis_health(
                    redis_config.get("host", "localhost"),
                    redis_config.get("port", 6379),
                    redis_config.get("password"),
                    redis_config.get("db", 0)
                ),
                timeout=10.0,
                critical=False
            )

        # Qdrant health checks
        qdrant_config = config.get("qdrant", {})
        if qdrant_config.get("url"):
            health_checker.register_health_check(
                name="qdrant",
                description="Qdrant vector database check",
                component_type="database",
                check_function=lambda: check_qdrant_health(
                    qdrant_config.get("url"),
                    qdrant_config.get("api_key")
                ),
                timeout=10.0,
                critical=False
            )

        # External API health checks
        external_apis = config.get("external_apis", {})
        for api_name, api_config in external_apis.items():
            if api_config.get("health_check_url"):
                health_checker.register_health_check(
                    name=f"external_api_{api_name}",
                    description=f"External API health check: {api_name}",
                    component_type="external_api",
                    check_function=lambda: check_external_api_health(
                        api_config["health_check_url"],
                        api_config.get("method", "GET"),
                        api_config.get("headers", {}),
                        api_config.get("timeout", 5.0)
                    ),
                    timeout=10.0,
                    critical=False
                )

    async def _initialize_alerting(self, config: Dict[str, Any]):
        """Initialize alerting system"""
        self.logger.info(
            "Initializing alerting system",
            component=ServiceComponent.MONITORING
        )

        # Register default alert rules
        register_default_alert_rules()

        # Register default notification channels
        register_default_notification_channels()

        # Configure alerting
        alert_manager.service_name = self.service_name
        alert_manager.evaluation_interval = config.get("alert_evaluation_interval", 60)

        # Start alert monitoring
        await alert_manager.start_monitoring()

    async def _initialize_error_tracking(self, config: Dict[str, Any]):
        """Initialize error tracking"""
        self.logger.info(
            "Initializing error tracking",
            component=ServiceComponent.MONITORING
        )

        # Configure error tracker
        error_tracker.service_name = self.service_name

        # Register context collectors
        self._register_error_context_collectors()

        # Register resolution handlers
        self._register_error_resolution_handlers()

    def _register_error_context_collectors(self):
        """Register additional error context collectors"""
        def request_context_collector(exception: Exception, context: ErrorContext) -> Dict[str, Any]:
            """Collect request-specific context"""
            from .logger import request_id, trace_id

            return {
                "request_id": request_id.get(),
                "trace_id": trace_id.get(),
                "correlation_id": context.correlation_id if context else None
            }

        def system_context_collector(exception: Exception, context: ErrorContext) -> Dict[str, Any]:
            """Collect system-specific context"""
            try:
                import psutil

                process = psutil.Process()
                return {
                    "process_memory_mb": process.memory_info().rss / (1024**2),
                    "process_cpu_percent": process.cpu_percent(),
                    "open_files": len(process.open_files()),
                    "threads": process.num_threads()
                }
            except Exception:
                return {}

        error_tracker.register_context_collector(request_context_collector)
        error_tracker.register_context_collector(system_context_collector)

    def _register_error_resolution_handlers(self):
        """Register automatic error resolution handlers"""
        async def connection_error_handler(report) -> Optional[str]:
            """Handle database connection errors"""
            if "connection" in report.exception_type.lower():
                # Check if it's a transient error
                if report.total_occurrences < 5:
                    return "Transient connection error - will retry automatically"
                else:
                    return "Persistent connection error - requires investigation"
            return None

        async def timeout_error_handler(report) -> Optional[str]:
            """Handle timeout errors"""
            if "timeout" in report.exception_type.lower():
                if report.total_occurrences < 3:
                    return "Temporary timeout - will retry with backoff"
                else:
                    return "Repeated timeouts - check external service status"
            return None

        error_tracker.register_resolution_handler("connection", connection_error_handler)
        error_tracker.register_resolution_handler("timeout", timeout_error_handler)

    async def start_monitoring(self):
        """Start all monitoring background tasks"""
        if self.running:
            return

        self.logger.info(
            "Starting monitoring background tasks",
            component=ServiceComponent.MONITORING
        )

        # Start health monitoring
        await health_checker.start_monitoring()

        self.running = True

    async def stop_monitoring(self):
        """Stop all monitoring background tasks"""
        if not self.running:
            return

        self.logger.info(
            "Stopping monitoring background tasks",
            component=ServiceComponent.MONITORING
        )

        # Stop metrics collection
        metrics_collector.stop_collection()

        # Stop health monitoring
        await health_checker.stop_monitoring()

        # Stop alert monitoring
        await alert_manager.stop_monitoring()

        self.running = False

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary"""
        return {
            "service": self.service_name,
            "initialized": self.initialized,
            "running": self.running,
            "metrics": {
                "total_metrics": len(metrics_collector.metrics),
                "collection_running": metrics_collector.running,
                "collection_interval": metrics_collector.collection_interval
            },
            "health": {
                "total_checks": len(health_checker.health_checks),
                "monitoring_running": health_checker.running,
                "components_status": {
                    name: report.status.value
                    for name, report in health_checker.component_status.items()
                }
            },
            "alerting": {
                "total_rules": len(alert_manager.alert_rules),
                "active_alerts": len(alert_manager.active_alerts),
                "monitoring_running": alert_manager.running
            },
            "error_tracking": {
                "total_reports": len(error_tracker.error_reports),
                "total_occurrences": len(error_tracker.occurrences)
            }
        }

    @asynccontextmanager
    async def request_context(self, correlation_id: str = None, request_id: str = None):
        """Context manager for request-level monitoring"""
        from .logger import set_correlation_id, set_request_id

        # Set context
        if correlation_id:
            set_correlation_id(correlation_id)
        if request_id:
            set_request_id(request_id)

        try:
            yield
        except Exception as e:
            # Track the error
            context = ErrorContext(
                correlation_id=correlation_id,
                request_id=request_id
            )
            await error_tracker.track_error(e, context=context)
            raise

    def get_fastapi_middleware(self):
        """Get FastAPI middleware for request monitoring"""
        return monitoring_middleware

    def get_fastapi_router(self):
        """Get FastAPI router for monitoring endpoints"""
        return monitoring_router


# Global monitoring instance
monitoring = AutoAdminMonitoring()


async def initialize_monitoring(config: Dict[str, Any] = None):
    """Initialize global monitoring system"""
    await monitoring.initialize(config)


def get_monitoring_middleware():
    """Get monitoring middleware"""
    return monitoring.get_fastapi_middleware()


def get_monitoring_router():
    """Get monitoring router"""
    return monitoring.get_fastapi_router()


@asynccontextmanager
async def monitor_request(correlation_id: str = None, request_id: str = None):
    """Context manager for monitoring requests"""
    async with monitoring.request_context(correlation_id, request_id):
        yield


# Exception handler decorator
def monitor_exceptions(component: ServiceComponent = None):
    """Decorator to automatically monitor function exceptions"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    component=component,
                    custom_data={
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
                await error_tracker.track_error(e, context=context)
                raise

        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    component=component,
                    custom_data={
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
                # In sync context, we need to handle async error tracking
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, create a task
                        asyncio.create_task(error_tracker.track_error(e, context=context))
                    else:
                        # If we're in sync context, run the coroutine
                        asyncio.run(error_tracker.track_error(e, context=context))
                except Exception:
                    # If error tracking fails, don't let it break the application
                    pass
                raise

        import asyncio
        import inspect

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Performance monitoring decorator
def monitor_performance(
    operation_name: str,
    component: ServiceComponent = None,
    labels: Dict[str, str] = None
):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            metric_labels = labels or {}
            if component:
                metric_labels["component"] = component.value

            async with metrics_collector.timer_context(
                f"{operation_name}_duration_ms",
                metric_labels
            ):
                # Increment counter for operation start
                metrics_collector.increment(
                    f"{operation_name}_total",
                    1,
                    metric_labels
                )

                try:
                    result = await func(*args, **kwargs)

                    # Increment success counter
                    metrics_collector.increment(
                        f"{operation_name}_success_total",
                        1,
                        metric_labels
                    )

                    return result

                except Exception as e:
                    # Increment error counter
                    metrics_collector.increment(
                        f"{operation_name}_error_total",
                        1,
                        {**metric_labels, "error_type": type(e).__name__}
                    )
                    raise

        def sync_wrapper(*args, **kwargs):
            metric_labels = labels or {}
            if component:
                metric_labels["component"] = component.value

            import time

            start_time = time.time()

            # Increment counter for operation start
            metrics_collector.increment(
                f"{operation_name}_total",
                1,
                metric_labels
            )

            try:
                result = func(*args, **kwargs)

                # Record duration
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.timer(
                    f"{operation_name}_duration_ms",
                    duration_ms,
                    metric_labels
                )

                # Increment success counter
                metrics_collector.increment(
                    f"{operation_name}_success_total",
                    1,
                    metric_labels
                )

                return result

            except Exception as e:
                # Record duration even for errors
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.timer(
                    f"{operation_name}_duration_ms",
                    duration_ms,
                    {**metric_labels, "error_type": type(e).__name__}
                )

                # Increment error counter
                metrics_collector.increment(
                    f"{operation_name}_error_total",
                    1,
                    {**metric_labels, "error_type": type(e).__name__}
                )
                raise

        import asyncio
        import inspect

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator