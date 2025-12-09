"""
Comprehensive structured logging system with correlation IDs and distributed tracing
"""

import uuid
import time
import json
import asyncio
from contextvars import ContextVar
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Context variables for request tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class LogLevel(Enum):
    """Log levels with severity mapping"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceComponent(Enum):
    """Service components for categorization"""
    AGENT = "agent"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    WEBHOOK = "webhook"
    SCHEDULER = "scheduler"
    MONITORING = "monitoring"


@dataclass
class LogContext:
    """Structured log context with correlation information"""
    correlation_id: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    service_name: str = "autoadmin-backend"
    version: str = "1.0.0"
    environment: str = "development"
    component: Optional[ServiceComponent] = None
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    duration_ms: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """
    Structured logger with correlation IDs and distributed tracing
    """

    def __init__(self, name: str, service_name: str = "autoadmin-backend"):
        self.name = name
        self.service_name = service_name
        self.environment = "development"  # Should come from env

    def _create_context(self, component: Optional[ServiceComponent] = None, **kwargs) -> LogContext:
        """Create log context with correlation IDs from context variables"""
        return LogContext(
            correlation_id=correlation_id.get() or str(uuid.uuid4()),
            trace_id=trace_id.get(),
            span_id=span_id.get(),
            user_id=user_id.get(),
            request_id=request_id.get(),
            service_name=self.service_name,
            environment=self.environment,
            component=component,
            extra=kwargs if kwargs else None
        )

    def _log(self, level: LogLevel, message: str, context: LogContext, **kwargs):
        """Internal logging method with structured output"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "logger": self.name,
            "message": message,
            "service": context.service_name,
            "environment": context.environment,
            "correlation_id": context.correlation_id,
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "parent_span_id": context.parent_span_id,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "session_id": context.session_id,
            "version": context.version,
            "component": context.component.value if context.component else None,
            "agent_id": context.agent_id,
            "task_id": context.task_id,
            "duration_ms": context.duration_ms,
        }

        # Add extra context
        if context.extra:
            log_entry.update(context.extra)

        # Add kwargs
        if kwargs:
            log_entry.update(kwargs)

        # Output as JSON
        print(json.dumps(log_entry, default=str))

    def debug(self, message: str, component: Optional[ServiceComponent] = None, **kwargs):
        """Log debug message"""
        context = self._create_context(component=component, **kwargs)
        self._log(LogLevel.DEBUG, message, context, **kwargs)

    def info(self, message: str, component: Optional[ServiceComponent] = None, **kwargs):
        """Log info message"""
        context = self._create_context(component=component, **kwargs)
        self._log(LogLevel.INFO, message, context, **kwargs)

    def warning(self, message: str, component: Optional[ServiceComponent] = None, **kwargs):
        """Log warning message"""
        context = self._create_context(component=component, **kwargs)
        self._log(LogLevel.WARNING, message, context, **kwargs)

    def error(self, message: str, component: Optional[ServiceComponent] = None, error: Optional[Exception] = None, **kwargs):
        """Log error message"""
        context = self._create_context(component=component, **kwargs)
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": error.__traceback__.to_dict() if hasattr(error, '__traceback__') and error.__traceback__ else None
            })
        self._log(LogLevel.ERROR, message, context, **kwargs)

    def critical(self, message: str, component: Optional[ServiceComponent] = None, error: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        context = self._create_context(component=component, **kwargs)
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": error.__traceback__.to_dict() if hasattr(error, '__traceback__') and error.__traceback__ else None
            })
        self._log(LogLevel.CRITICAL, message, context, **kwargs)


class ContextualLogger:
    """
    Contextual logger that manages trace spans
    """

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.spans = []

    def create_span(self, operation_name: str, component: ServiceComponent, **kwargs):
        """Create a new span for tracing"""
        span_id = str(uuid.uuid4())
        parent_span_id = span_id.get()

        span_context = LogContext(
            correlation_id=correlation_id.get() or str(uuid.uuid4()),
            trace_id=trace_id.get() or str(uuid.uuid4()),
            span_id=span_id,
            parent_span_id=parent_span_id,
            component=component,
            extra={"operation_name": operation_name, **kwargs}
        )

        # Set current span
        span_id.set(span_id)

        # Record span
        span_info = {
            "span_id": span_id,
            "operation_name": operation_name,
            "component": component,
            "start_time": time.time(),
            "context": span_context
        }
        self.spans.append(span_info)

        self.logger.info(f"Starting span: {operation_name}", component=component, **kwargs)
        return span_id

    def finish_span(self, span_id: str, success: bool = True, error: Optional[Exception] = None, **kwargs):
        """Finish a span with duration and result"""
        span_info = next((s for s in self.spans if s["span_id"] == span_id), None)
        if span_info:
            duration_ms = (time.time() - span_info["start_time"]) * 1000

            log_context = span_info["context"]
            log_context.duration_ms = duration_ms

            if success:
                self.logger.info(
                    f"Completed span: {span_info['operation_name']}",
                    component=span_info["component"],
                    duration_ms=duration_ms,
                    span_id=span_id,
                    **kwargs
                )
            else:
                self.logger.error(
                    f"Failed span: {span_info['operation_name']}",
                    component=span_info["component"],
                    error=error,
                    duration_ms=duration_ms,
                    span_id=span_id,
                    **kwargs
                )

            # Remove from active spans
            self.spans.remove(span_info)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


def get_contextual_logger(name: str) -> ContextualLogger:
    """Get a contextual logger instance"""
    return ContextualLogger(get_logger(name))


def set_correlation_id(cid: str):
    """Set correlation ID in current context"""
    correlation_id.set(cid)


def set_trace_id(tid: str):
    """Set trace ID in current context"""
    trace_id.set(tid)


def set_user_id(uid: str):
    """Set user ID in current context"""
    user_id.set(uid)


def set_request_id(rid: str):
    """Set request ID in current context"""
    request_id.set(rid)


class LogMiddleware:
    """
    Middleware for automatic correlation ID and logging
    """

    def __init__(self, service_name: str = "autoadmin-backend"):
        self.service_name = service_name
        self.logger = get_logger("middleware")

    async def log_request(self, request, call_next):
        """Log HTTP request with correlation ID"""
        # Generate or extract correlation ID
        cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Set in context
        set_correlation_id(cid)
        set_request_id(rid)

        # Log request
        self.logger.info(
            f"HTTP {request.method} {request.url.path}",
            component=ServiceComponent.API,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Add correlation ID to response headers
            response.headers["x-correlation-id"] = cid
            response.headers["x-request-id"] = rid

            # Log response
            self.logger.info(
                f"HTTP {response.status_code} {request.method} {request.url.path}",
                component=ServiceComponent.API,
                status_code=response.status_code,
                duration_ms=duration_ms,
                method=request.method,
                path=request.url.path,
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            self.logger.error(
                f"HTTP 500 {request.method} {request.url.path}",
                component=ServiceComponent.API,
                status_code=500,
                duration_ms=duration_ms,
                method=request.method,
                path=request.url.path,
                error=e,
            )
            raise


# Global logger instance for backward compatibility
default_logger = get_logger("autoadmin")