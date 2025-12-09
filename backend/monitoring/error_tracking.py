"""
Comprehensive error tracking and debugging system
"""

import traceback
import sys
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json
import inspect

from .logger import get_logger, LogLevel, ServiceComponent, correlation_id, trace_id


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    AGENT_ERROR = "agent_error"
    TASK_EXECUTION = "task_execution"
    UNKNOWN = "unknown"


class ErrorStatus(Enum):
    """Error tracking status"""
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"


@dataclass
class ErrorFrame:
    """Stack frame information"""
    filename: str
    line_number: int
    function_name: str
    code_line: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    context_lines: Optional[List[str]] = None


@dataclass
class ErrorContext:
    """Error context information"""
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[ServiceComponent] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None


@dataclass
class ErrorOccurrence:
    """Individual error occurrence"""
    id: str
    error_id: str
    timestamp: datetime
    message: str
    exception_type: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    stack_trace: List[ErrorFrame]
    system_info: Dict[str, Any]
    environment: Dict[str, Any]
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class ErrorReport:
    """Aggregated error report"""
    error_id: str
    exception_type: str
    message_pattern: str
    severity: ErrorSeverity
    category: ErrorCategory
    first_seen: datetime
    last_seen: datetime
    occurrences: List[ErrorOccurrence]
    total_occurrences: int
    unique_users: int
    affected_components: List[str]
    status: ErrorStatus
    similar_errors: List[str] = None
    potential_causes: List[str] = None
    resolution_suggestions: List[str] = None


class ErrorClassifier:
    """Classify errors into categories and severity levels"""

    def __init__(self):
        self.classification_rules = self._build_classification_rules()

    def _build_classification_rules(self) -> Dict[str, Dict[str, Any]]:
        """Build error classification rules"""
        return {
            # Database errors
            "ConnectionError": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["connection", "database", "sql", "timeout"]
            },
            "OperationalError": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["sql", "database", "query"]
            },
            "IntegrityError": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["constraint", "foreign key", "unique"]
            },

            # Network errors
            "TimeoutError": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["timeout", "connection", "network"]
            },
            "ConnectionError": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["connection", "network", "unreachable"]
            },
            "HTTPError": {
                "category": ErrorCategory.EXTERNAL_API,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["http", "response", "status"]
            },

            # Authentication/Authorization
            "AuthenticationError": {
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["auth", "login", "credential", "token"]
            },
            "PermissionError": {
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["permission", "access", "unauthorized"]
            },

            # Validation errors
            "ValidationError": {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "keywords": ["validation", "invalid", "required"]
            },
            "ValueError": {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "keywords": ["value", "type", "conversion"]
            },

            # System errors
            "MemoryError": {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.CRITICAL,
                "keywords": ["memory", "allocation", "oom"]
            },
            "OSError": {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["system", "file", "permission", "disk"]
            },

            # Agent errors
            "AgentError": {
                "category": ErrorCategory.AGENT_ERROR,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["agent", "task", "execution", "processing"]
            },
            "TaskError": {
                "category": ErrorCategory.TASK_EXECUTION,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["task", "job", "worker", "queue"]
            }
        }

    def classify_error(self, exception: Exception, message: str) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify an exception"""
        exception_name = exception.__class__.__name__

        # Check exact matches first
        if exception_name in self.classification_rules:
            rule = self.classification_rules[exception_name]
            return rule["category"], rule["severity"]

        # Check keyword matches
        message_lower = message.lower()
        for exc_name, rule in self.classification_rules.items():
            if any(keyword in message_lower for keyword in rule["keywords"]):
                return rule["category"], rule["severity"]

        # Default classification
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


class ErrorTracker:
    """
    Comprehensive error tracking and debugging system
    """

    def __init__(self, service_name: str = "autoadmin-backend"):
        self.service_name = service_name
        self.classifier = ErrorClassifier()
        self.logger = get_logger("error_tracker")

        # Error storage
        self.error_reports: Dict[str, ErrorReport] = {}
        self.occurrences: List[ErrorOccurrence] = []
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)

        # Error grouping
        self.similarity_threshold = 0.8
        self.max_occurrences_per_report = 100

        # Context collectors
        self.context_collectors: List[Callable] = []

        # Error resolution tracking
        self.resolution_handlers: Dict[str, Callable] = {}

    def register_context_collector(self, collector: Callable):
        """Register a function to collect additional error context"""
        self.context_collectors.append(collector)

    def register_resolution_handler(self, error_pattern: str, handler: Callable):
        """Register a handler for resolving specific error patterns"""
        self.resolution_handlers[error_pattern] = handler

    async def track_error(
        self,
        exception: Exception,
        message: str = None,
        context: ErrorContext = None,
        severity: ErrorSeverity = None,
        category: ErrorCategory = None
    ) -> str:
        """Track an error occurrence"""
        try:
            # Generate error ID
            error_id = self._generate_error_id(exception, message)

            # Create occurrence
            occurrence = await self._create_error_occurrence(
                exception, message, context, severity, category, error_id
            )

            # Store occurrence
            self.occurrences.append(occurrence)

            # Keep only recent occurrences
            if len(self.occurrences) > 10000:
                self.occurrences = self.occurrences[-10000:]

            # Update or create error report
            await self._update_error_report(occurrence)

            # Log the error
            await self._log_tracked_error(occurrence)

            # Attempt auto-resolution if possible
            await self._attempt_auto_resolution(error_id)

            return error_id

        except Exception as e:
            # Don't let error tracking fail the application
            self.logger.error(
                "Failed to track error",
                component=ServiceComponent.MONITORING,
                error=e,
                original_exception=exception,
                original_message=message
            )
            return f"tracking_failed_{uuid.uuid4().hex[:8]}"

    def _generate_error_id(self, exception: Exception, message: str = None) -> str:
        """Generate error ID for grouping similar errors"""
        import hashlib

        # Create a normalized representation of the error
        error_repr = f"{exception.__class__.__name__}:{message or str(exception)}"

        # Extract stack trace info
        tb = exception.__traceback__
        if tb:
            # Get the most relevant frame (skip internal frames)
            while tb and any(skip in tb.tb_frame.f_code.co_filename for skip in ['site-packages', 'dist-packages']):
                tb = tb.tb_next

            if tb:
                error_repr += f":{tb.tb_frame.f_code.co_filename}:{tb.tb_frame.f_lineno}"

        # Generate hash
        error_hash = hashlib.md5(error_repr.encode()).hexdigest()[:16]

        return f"err_{error_hash}"

    async def _create_error_occurrence(
        self,
        exception: Exception,
        message: str = None,
        context: ErrorContext = None,
        severity: ErrorSeverity = None,
        category: ErrorCategory = None,
        error_id: str = None
    ) -> ErrorOccurrence:
        """Create an error occurrence from an exception"""

        # Generate occurrence ID
        occurrence_id = f"occ_{int(datetime.utcnow().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"

        # Classification
        error_message = message or str(exception)
        if not category or not severity:
            auto_category, auto_severity = self.classifier.classify_error(exception, error_message)
            category = category or auto_category
            severity = severity or auto_severity

        # Build context
        if not context:
            context = ErrorContext(
                correlation_id=correlation_id.get(),
                trace_id=trace_id.get(),
                user_id=getattr(context, 'user_id', None) if context else None
            )

        # Collect additional context
        additional_context = {}
        for collector in self.context_collectors:
            try:
                collected = await collector(exception, context) if asyncio.iscoroutinefunction(collector) else collector(exception, context)
                if collected:
                    additional_context.update(collected)
            except Exception as e:
                self.logger.warning(
                    "Context collector failed",
                    component=ServiceComponent.MONITORING,
                    error=e
                )

        # Update context with additional data
        if additional_context:
            if context.custom_data:
                context.custom_data.update(additional_context)
            else:
                context.custom_data = additional_context

        # Extract stack trace
        stack_trace = self._extract_stack_trace(exception)

        # Get system info
        system_info = self._collect_system_info()

        # Get environment info
        environment = self._collect_environment_info()

        return ErrorOccurrence(
            id=occurrence_id,
            error_id=error_id or self._generate_error_id(exception, message),
            timestamp=datetime.utcnow(),
            message=error_message,
            exception_type=exception.__class__.__name__,
            severity=severity,
            category=category,
            context=context,
            stack_trace=stack_trace,
            system_info=system_info,
            environment=environment
        )

    def _extract_stack_trace(self, exception: Exception) -> List[ErrorFrame]:
        """Extract and format stack trace"""
        frames = []
        tb = exception.__traceback__

        while tb:
            frame_info = {
                "filename": tb.tb_frame.f_code.co_filename,
                "line_number": tb.tb_lineno,
                "function_name": tb.tb_frame.f_code.co_name,
            }

            # Try to get source line
            try:
                with open(frame_info["filename"], 'r') as f:
                    lines = f.readlines()
                    frame_info["code_line"] = lines[frame_info["line_number"] - 1].strip()

                    # Get context lines
                    start = max(0, frame_info["line_number"] - 3)
                    end = min(len(lines), frame_info["line_number"] + 2)
                    frame_info["context_lines"] = [lines[i].rstrip() for i in range(start, end)]

            except (IOError, IndexError):
                frame_info["code_line"] = None
                frame_info["context_lines"] = None

            # Try to get local variables (only for debugging, be careful with sensitive data)
            try:
                frame_info["variables"] = {}
                for var_name, var_value in tb.tb_frame.f_locals.items():
                    # Skip potentially sensitive variables
                    if any(sensitive in var_name.lower() for sensitive in ['password', 'token', 'key', 'secret']):
                        continue

                    # Convert to string safely
                    try:
                        var_str = str(var_value)
                        if len(var_str) > 200:
                            var_str = var_str[:200] + "..."
                        frame_info["variables"][var_name] = var_str
                    except Exception:
                        frame_info["variables"][var_name] = "<无法表示>"

            except Exception:
                frame_info["variables"] = None

            frames.append(ErrorFrame(**frame_info))
            tb = tb.tb_next

        return frames

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        try:
            import psutil
            import platform

            return {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "disk_free_gb": psutil.disk_usage('/').free / (1024**3),
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
            }
        except Exception as e:
            return {"error": f"Failed to collect system info: {str(e)}"}

    def _collect_environment_info(self) -> Dict[str, Any]:
        """Collect environment information"""
        try:
            import os

            # Filter out potentially sensitive environment variables
            safe_env_vars = {}
            sensitive_keys = ['password', 'secret', 'key', 'token', 'credential']

            for key, value in os.environ.items():
                if not any(sensitive in key.lower() for sensitive in sensitive_keys):
                    safe_env_vars[key] = value

            return {
                "environment": os.getenv("ENVIRONMENT", "development"),
                "service_name": self.service_name,
                "pid": os.getpid(),
                "working_directory": os.getcwd(),
                "environment_variables": safe_env_vars
            }
        except Exception as e:
            return {"error": f"Failed to collect environment info: {str(e)}"}

    async def _update_error_report(self, occurrence: ErrorOccurrence):
        """Update or create error report"""
        error_id = occurrence.error_id

        if error_id not in self.error_reports:
            # Create new error report
            self.error_reports[error_id] = ErrorReport(
                error_id=error_id,
                exception_type=occurrence.exception_type,
                message_pattern=self._normalize_message(occurrence.message),
                severity=occurrence.severity,
                category=occurrence.category,
                first_seen=occurrence.timestamp,
                last_seen=occurrence.timestamp,
                occurrences=[occurrence],
                total_occurrences=1,
                unique_users=len([occ.context.user_id]) if occurrence.context and occurrence.context.user_id else 0,
                affected_components=[occ.context.component.value] if occurrence.context and occurrence.context.component else [],
                status=ErrorStatus.ACTIVE,
                similar_errors=self._find_similar_errors(occurrence),
                potential_causes=self._suggest_potential_causes(occurrence),
                resolution_suggestions=self._suggest_resolution(occurrence)
            )
        else:
            # Update existing report
            report = self.error_reports[error_id]
            report.last_seen = max(report.last_seen, occurrence.timestamp)
            report.occurrences.append(occurrence)
            report.total_occurrences += 1

            # Keep only recent occurrences
            if len(report.occurrences) > self.max_occurrences_per_report:
                report.occurrences = report.occurrences[-self.max_occurrences_per_report:]

            # Update unique users
            if occurrence.context and occurrence.context.user_id:
                all_users = [occ.context.user_id for occ in report.occurrences if occ.context and occ.context.user_id]
                report.unique_users = len(set(all_users))

            # Update affected components
            if occurrence.context and occurrence.context.component:
                components = [occ.context.component.value for occ in report.occurrences if occ.context and occ.context.component]
                report.affected_components = list(set(components))

            # Update severity if this occurrence is more severe
            if self._severity_order(occurrence.severity) > self._severity_order(report.severity):
                report.severity = occurrence.severity

    def _normalize_message(self, message: str) -> str:
        """Normalize error message for pattern matching"""
        import re

        # Remove specific values (numbers, UUIDs, timestamps)
        normalized = re.sub(r'\d+', '<NUMBER>', message)
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', normalized)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', normalized)

        # Remove file paths
        normalized = re.sub(r'/[^\s]+/[^\s]+/', '<PATH>/', normalized)

        return normalized

    def _find_similar_errors(self, occurrence: ErrorOccurrence) -> List[str]:
        """Find similar error patterns"""
        similar = []
        current_message = self._normalize_message(occurrence.message)

        for error_id, report in self.error_reports.items():
            if error_id == occurrence.error_id:
                continue

            # Simple similarity based on message pattern
            other_message = report.message_pattern
            similarity = self._calculate_similarity(current_message, other_message)

            if similarity > self.similarity_threshold:
                similar.append(error_id)

        return similar[:5]  # Return top 5 similar errors

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple heuristic"""
        from difflib import SequenceMatcher

        return SequenceMatcher(None, str1, str2).ratio()

    def _severity_order(self, severity: ErrorSeverity) -> int:
        """Get numeric order for severity comparison"""
        order = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        return order.get(severity, 2)

    def _suggest_potential_causes(self, occurrence: ErrorOccurrence) -> List[str]:
        """Suggest potential causes for the error"""
        causes = []

        category = occurrence.category
        exception_type = occurrence.exception_type

        if category == ErrorCategory.DATABASE:
            if "connection" in exception_type.lower():
                causes.append("Database connection pool exhausted")
                causes.append("Network connectivity issues to database")
                causes.append("Database server is down or overloaded")
            elif "constraint" in exception_type.lower():
                causes.append("Data validation failed")
                causes.append("Referential integrity violation")

        elif category == ErrorCategory.NETWORK:
            if "timeout" in exception_type.lower():
                causes.append("Network latency or slow response")
                causes.append("External service overloaded")
                causes.append("Firewall or network configuration issues")

        elif category == ErrorCategory.AUTHENTICATION:
            causes.append("Invalid or expired credentials")
            causes.append("Token validation failed")
            causes.append("User account locked or disabled")

        elif category == ErrorCategory.VALIDATION:
            causes.append("Invalid input data format")
            causes.append("Required fields missing")
            causes.append("Data type mismatch")

        elif category == ErrorCategory.AGENT_ERROR:
            causes.append("Agent configuration error")
            causes.append("Insufficient agent resources")
            causes.append("Task dependency failure")

        elif category == ErrorCategory.SYSTEM:
            if "memory" in exception_type.lower():
                causes.append("Memory leak or excessive memory usage")
                causes.append("Insufficient system memory")
            elif "disk" in exception_type.lower():
                causes.append("Insufficient disk space")
                causes.append("Disk I/O issues")

        if not causes:
            causes.append("Unknown cause - requires investigation")

        return causes

    def _suggest_resolution(self, occurrence: ErrorOccurrence) -> List[str]:
        """Suggest resolution steps for the error"""
        resolutions = []

        category = occurrence.category
        exception_type = occurrence.exception_type

        if category == ErrorCategory.DATABASE:
            if "connection" in exception_type.lower():
                resolutions.append("Check database server status")
                resolutions.append("Verify connection string and credentials")
                resolutions.append("Increase connection pool size")
                resolutions.append("Implement connection retry logic")

        elif category == ErrorCategory.NETWORK:
            if "timeout" in exception_type.lower():
                resolutions.append("Increase timeout values")
                resolutions.append("Implement circuit breaker pattern")
                resolutions.append("Add retry logic with exponential backoff")
                resolutions.append("Monitor external service health")

        elif category == ErrorCategory.AUTHENTICATION:
            resolutions.append("Verify authentication configuration")
            resolutions.append("Check token generation and validation")
            resolutions.append("Review user account status")

        elif category == ErrorCategory.VALIDATION:
            resolutions.append("Review input validation rules")
            resolutions.append("Check API documentation for required fields")
            resolutions.append("Add client-side validation")

        elif category == ErrorCategory.AGENT_ERROR:
            resolutions.append("Review agent configuration")
            resolutions.append("Check agent resource allocation")
            resolutions.append("Verify task dependencies")
            resolutions.append("Monitor agent health status")

        elif category == ErrorCategory.SYSTEM:
            if "memory" in exception_type.lower():
                resolutions.append("Monitor memory usage patterns")
                resolutions.append("Optimize memory-intensive operations")
                resolutions.append("Increase available memory")
                resolutions.append("Profile application for memory leaks")

        if not resolutions:
            resolutions.append("Review error logs and stack trace")
            resolutions.append("Check system resources and dependencies")
            resolutions.append("Contact development team for assistance")

        return resolutions

    async def _log_tracked_error(self, occurrence: ErrorOccurrence):
        """Log tracked error with structured information"""
        self.logger.error(
            f"Error tracked: {occurrence.exception_type} - {occurrence.message}",
            component=ServiceComponent.MONITORING,
            error_id=occurrence.error_id,
            occurrence_id=occurrence.id,
            severity=occurrence.severity.value,
            category=occurrence.category.value,
            correlation_id=occurrence.context.correlation_id if occurrence.context else None,
            user_id=occurrence.context.user_id if occurrence.context else None,
            endpoint=occurrence.context.endpoint if occurrence.context else None
        )

    async def _attempt_auto_resolution(self, error_id: str):
        """Attempt to automatically resolve known error patterns"""
        report = self.error_reports.get(error_id)
        if not report:
            return

        # Check for resolution handlers
        for pattern, handler in self.resolution_handlers.items():
            try:
                if pattern in report.exception_type.lower() or pattern in report.message_pattern.lower():
                    resolution_result = await handler(report) if asyncio.iscoroutinefunction(handler) else handler(report)

                    if resolution_result:
                        await self.resolve_error(error_id, f"Auto-resolved: {resolution_result}")
                        self.logger.info(
                            f"Auto-resolved error {error_id}",
                            component=ServiceComponent.MONITORING,
                            error_id=error_id,
                            resolution=resolution_result
                        )
                        break

            except Exception as e:
                self.logger.warning(
                    f"Auto-resolution handler failed for {error_id}",
                    component=ServiceComponent.MONITORING,
                    error_id=error_id,
                    handler=pattern,
                    error=e
                )

    async def resolve_error(self, error_id: str, resolution_notes: str = None):
        """Mark an error as resolved"""
        if error_id in self.error_reports:
            report = self.error_reports[error_id]
            report.status = ErrorStatus.RESOLVED
            report.resolved_at = datetime.utcnow()
            report.resolution_notes = resolution_notes

            self.logger.info(
                f"Error resolved: {error_id}",
                component=ServiceComponent.MONITORING,
                error_id=error_id,
                resolution_notes=resolution_notes
            )

    def get_error_report(self, error_id: str) -> Optional[ErrorReport]:
        """Get error report by ID"""
        return self.error_reports.get(error_id)

    def get_error_reports(
        self,
        severity: ErrorSeverity = None,
        category: ErrorCategory = None,
        status: ErrorStatus = None,
        hours: int = 24
    ) -> List[ErrorReport]:
        """Get error reports with optional filtering"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        filtered_reports = []
        for report in self.error_reports.values():
            # Time filter
            if report.last_seen < cutoff_time:
                continue

            # Severity filter
            if severity and report.severity != severity:
                continue

            # Category filter
            if category and report.category != category:
                continue

            # Status filter
            if status and report.status != status:
                continue

            filtered_reports.append(report)

        # Sort by last seen (most recent first)
        filtered_reports.sort(key=lambda r: r.last_seen, reverse=True)

        return filtered_reports

    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent reports
        recent_reports = [r for r in self.error_reports.values() if r.last_seen >= cutoff_time]

        # Count by severity
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = len([r for r in recent_reports if r.severity == severity])

        # Count by category
        category_counts = {}
        for category in ErrorCategory:
            category_counts[category.value] = len([r for r in recent_reports if r.category == category])

        # Count by status
        status_counts = {}
        for status in ErrorStatus:
            status_counts[status.value] = len([r for r in recent_reports if r.status == status])

        # Top errors by frequency
        top_errors = sorted(recent_reports, key=lambda r: r.total_occurrences, reverse=True)[:10]

        # Errors with highest impact (severity × frequency)
        high_impact_errors = sorted(
            recent_reports,
            key=lambda r: self._severity_order(r.severity) * r.total_occurrences,
            reverse=True
        )[:10]

        return {
            "time_range_hours": hours,
            "total_reports": len(recent_reports),
            "total_occurrences": sum(r.total_occurrences for r in recent_reports),
            "unique_users": sum(r.unique_users for r in recent_reports),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "status_breakdown": status_counts,
            "top_errors_by_frequency": [
                {
                    "error_id": r.error_id,
                    "exception_type": r.exception_type,
                    "message_pattern": r.message_pattern,
                    "occurrences": r.total_occurrences,
                    "severity": r.severity.value
                }
                for r in top_errors
            ],
            "high_impact_errors": [
                {
                    "error_id": r.error_id,
                    "exception_type": r.exception_type,
                    "message_pattern": r.message_pattern,
                    "occurrences": r.total_occurrences,
                    "severity": r.severity.value,
                    "impact_score": self._severity_order(r.severity) * r.total_occurrences
                }
                for r in high_impact_errors
            ]
        }

    def get_error_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get error occurrence timeline"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent occurrences
        recent_occurrences = [o for o in self.occurrences if o.timestamp >= cutoff_time]

        # Group by hour
        timeline = defaultdict(int)
        for occurrence in recent_occurrences:
            hour_key = occurrence.timestamp.replace(minute=0, second=0, microsecond=0)
            timeline[hour_key] += 1

        # Convert to list and sort
        timeline_data = [
            {
                "timestamp": hour.isoformat(),
                "count": count
            }
            for hour, count in sorted(timeline.items())
        ]

        return timeline_data


# Global error tracker instance
error_tracker = ErrorTracker()