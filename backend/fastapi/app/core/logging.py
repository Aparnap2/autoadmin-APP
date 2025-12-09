"""
Structured logging configuration for AutoAdmin FastAPI Backend
Provides JSON-formatted logs with correlation IDs and performance metrics
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from .config import settings


def setup_logging():
    """Setup structured logging with JSON formatting for production"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Setup standard library logging
    setup_standard_logging()


def setup_standard_logging():
    """Setup standard library logging handlers and formatters"""

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
        root_logger.addHandler(file_handler)

    # Set specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DEBUG else logging.WARNING
    )


class StructuredLogger:
    """Enhanced structured logger with correlation tracking"""

    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self.correlation_id = None

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracking"""
        self.correlation_id = correlation_id

    def _get_context(self, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get context with correlation ID"""
        context = {}
        if self.correlation_id:
            context["correlation_id"] = self.correlation_id
        if extra:
            context.update(extra)
        return context

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **self._get_context(kwargs))

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **self._get_context(kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **self._get_context(kwargs))

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **self._get_context(kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **self._get_context(kwargs))

    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        kwargs.setdefault("exc_info", True)
        self.logger.error(message, **self._get_context(kwargs))

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        client_ip: str = None,
        user_agent: str = None,
        **kwargs
    ):
        """Log API request with performance metrics"""
        self.info(
            "API request completed",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            client_ip=client_ip,
            user_agent=user_agent,
            **kwargs
        )

    def log_agent_task(
        self,
        agent_id: str,
        task_id: str,
        action: str,
        status: str,
        duration: float = None,
        **kwargs
    ):
        """Log agent task execution"""
        context = {
            "agent_id": agent_id,
            "task_id": task_id,
            "action": action,
            "status": status,
        }

        if duration:
            context["duration_ms"] = round(duration * 1000, 2)

        context.update(kwargs)

        if status in ["failed", "error"]:
            self.error(f"Agent task {action} failed", **context)
        else:
            self.info(f"Agent task {action} {status}", **context)

    def log_ai_service_call(
        self,
        service: str,
        model: str,
        tokens_used: int = None,
        duration: float = None,
        **kwargs
    ):
        """Log AI service call with metrics"""
        context = {
            "service": service,
            "model": model,
            **kwargs
        }

        if tokens_used:
            context["tokens_used"] = tokens_used

        if duration:
            context["duration_ms"] = round(duration * 1000, 2)

        self.info("AI service call completed", **context)


def get_logger(name: str) -> StructuredLogger:
    """Get structured logger instance"""
    return StructuredLogger(name)


# Create default logger instance
logger = get_logger(__name__)