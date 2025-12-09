"""
Comprehensive metrics collection and monitoring system
"""

import time
import asyncio
import psutil
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
from contextlib import asynccontextmanager


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    METER = "meter"


class MetricUnit(Enum):
    """Units for metrics"""
    COUNT = "count"
    PERCENTAGE = "percentage"
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    BYTES = "bytes"
    REQUESTS_PER_SECOND = "requests_per_second"
    ERRORS_PER_SECOND = "errors_per_second"
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    timestamp: datetime
    value: float
    labels: Dict[str, str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MetricDefinition:
    """Metric definition with configuration"""
    name: str
    description: str
    metric_type: MetricType
    unit: MetricUnit
    labels: List[str]
    aggregation: str = "avg"  # avg, sum, min, max, p50, p95, p99


class Histogram:
    """Simple histogram implementation"""

    def __init__(self, buckets: List[float] = None):
        self.buckets = buckets or [1, 5, 10, 25, 50, 100, 250, 500, 1000, float('inf')]
        self.counts = defaultdict(int)
        self.sum = 0
        self.count = 0
        self.values = deque(maxlen=10000)  # Keep last 10k values for percentiles

    def observe(self, value: float):
        """Observe a value"""
        self.sum += value
        self.count += 1
        self.values.append(value)

        # Update bucket counts
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1

    def get_summary(self) -> Dict[str, float]:
        """Get histogram summary"""
        if not self.values:
            return {"count": 0, "sum": 0, "avg": 0}

        sorted_values = sorted(list(self.values))
        n = len(sorted_values)

        return {
            "count": self.count,
            "sum": self.sum,
            "avg": self.sum / self.count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": sorted_values[int(n * 0.5)],
            "p75": sorted_values[int(n * 0.75)],
            "p90": sorted_values[int(n * 0.9)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)],
            **{f"le_{bucket}": count for bucket, count in self.counts.items()}
        }


class Meter:
    """Meter for measuring rates"""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.events = deque()
        self.count = 0

    def mark(self, count: int = 1):
        """Mark an event"""
        timestamp = time.time()
        for _ in range(count):
            self.events.append(timestamp)
        self.count += count

    def get_rate(self) -> float:
        """Get events per second in the window"""
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old events
        while self.events and self.events[0] < cutoff:
            self.events.popleft()

        return len(self.events) / self.window_seconds


class MetricsCollector:
    """
    Comprehensive metrics collection system
    """

    def __init__(self, service_name: str = "autoadmin-backend"):
        self.service_name = service_name
        self.metrics: Dict[str, Any] = {}
        self.definitions: Dict[str, MetricDefinition] = {}
        self.collector_thread = None
        self.running = False
        self.collection_interval = 15  # seconds
        self.retention_hours = 24

        # Time series storage (in production, use Prometheus or similar)
        self.time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        # System metrics
        self.system_metrics_enabled = True
        self.process = psutil.Process()

    def register_metric(self, definition: MetricDefinition):
        """Register a new metric definition"""
        self.definitions[definition.name] = definition

        if definition.metric_type == MetricType.COUNTER:
            self.metrics[definition.name] = 0.0
        elif definition.metric_type == MetricType.GAUGE:
            self.metrics[definition.name] = 0.0
        elif definition.metric_type == MetricType.HISTOGRAM:
            self.metrics[definition.name] = Histogram()
        elif definition.metric_type == MetricType.TIMER:
            self.metrics[definition.name] = Histogram()
        elif definition.metric_type == MetricType.METER:
            self.metrics[definition.name] = Meter()

    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        if name not in self.metrics:
            # Auto-register as counter if not exists
            self.register_metric(MetricDefinition(
                name=name,
                description=f"Auto-registered counter: {name}",
                metric_type=MetricType.COUNTER,
                unit=MetricUnit.COUNT,
                labels=list(labels.keys()) if labels else []
            ))

        metric = self.metrics[name]
        if isinstance(metric, (float, int)):
            self.metrics[name] += value
        elif hasattr(metric, 'mark'):  # Meter
            metric.mark(int(value))

        # Record time series
        self._record_time_series(name, value, labels)

    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        if name not in self.metrics:
            self.register_metric(MetricDefinition(
                name=name,
                description=f"Auto-registered gauge: {name}",
                metric_type=MetricType.GAUGE,
                unit=MetricUnit.COUNT,
                labels=list(labels.keys()) if labels else []
            ))

        self.metrics[name] = value
        self._record_time_series(name, value, labels)

    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        if name not in self.metrics:
            self.register_metric(MetricDefinition(
                name=name,
                description=f"Auto-registered histogram: {name}",
                metric_type=MetricType.HISTOGRAM,
                unit=MetricUnit.MILLISECONDS,
                labels=list(labels.keys()) if labels else []
            ))

        metric = self.metrics[name]
        if hasattr(metric, 'observe'):  # Histogram or Timer
            metric.observe(value)

        self._record_time_series(name, value, labels)

    def timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None):
        """Record a timer value"""
        self.histogram(name, duration_ms, labels)

    def meter(self, name: str, count: int = 1, labels: Dict[str, str] = None):
        """Mark a meter event"""
        if name not in self.metrics:
            self.register_metric(MetricDefinition(
                name=name,
                description=f"Auto-registered meter: {name}",
                metric_type=MetricType.METER,
                unit=MetricUnit.REQUESTS_PER_SECOND,
                labels=list(labels.keys()) if labels else []
            ))

        metric = self.metrics[name]
        if hasattr(metric, 'mark'):  # Meter
            metric.mark(count)

        self._record_time_series(name, count, labels)

    def _record_time_series(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a time series data point"""
        timestamp = datetime.utcnow()
        metric_value = MetricValue(
            timestamp=timestamp,
            value=value,
            labels=labels or {}
        )

        # Store in time series
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self.time_series[key].append(metric_value)

    @asynccontextmanager
    async def timer_context(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.timer(name, duration_ms, labels)

    def collect_system_metrics(self):
        """Collect system-level metrics"""
        if not self.system_metrics_enabled:
            return

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.gauge("system_cpu_percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.gauge("system_memory_percent", memory.percent)
            self.gauge("system_memory_bytes_used", memory.used)
            self.gauge("system_memory_bytes_total", memory.total)

            # Process-specific metrics
            process_cpu = self.process.cpu_percent()
            process_memory = self.process.memory_info()
            self.gauge("process_cpu_percent", process_cpu)
            self.gauge("process_memory_bytes", process_memory.rss)

            # Disk metrics
            disk = psutil.disk_usage('/')
            self.gauge("system_disk_percent", (disk.used / disk.total) * 100)
            self.gauge("system_disk_bytes_used", disk.used)
            self.gauge("system_disk_bytes_total", disk.total)

            # Network metrics
            network = psutil.net_io_counters()
            self.gauge("system_network_bytes_sent", network.bytes_sent)
            self.gauge("system_network_bytes_recv", network.bytes_recv)

        except Exception as e:
            # Log error but don't raise to avoid breaking metrics collection
            print(f"Error collecting system metrics: {e}")

    def collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            # Agent metrics
            active_agents = len([a for a in self.metrics.get('agents', {}).values() if a.get('status') == 'active'])
            total_agents = len(self.metrics.get('agents', {}))

            self.gauge("agents_active_count", active_agents)
            self.gauge("agents_total_count", total_agents)

            # Task metrics
            tasks_pending = self.metrics.get('tasks_pending', 0)
            tasks_running = self.metrics.get('tasks_running', 0)
            tasks_completed = self.metrics.get('tasks_completed_total', 0)
            tasks_failed = self.metrics.get('tasks_failed_total', 0)

            self.gauge("tasks_pending_count", tasks_pending)
            self.gauge("tasks_running_count", tasks_running)
            self.gauge("tasks_completed_total", tasks_completed)
            self.gauge("tasks_failed_total", tasks_failed)

            # Request metrics
            requests_total = self.metrics.get('http_requests_total', 0)
            requests_success = self.metrics.get('http_requests_success_total', 0)
            requests_error = self.metrics.get('http_requests_error_total', 0)

            self.gauge("http_requests_total", requests_total)
            self.gauge("http_requests_success_total", requests_success)
            self.gauge("http_requests_error_total", requests_error)

            # Calculate error rate
            if requests_total > 0:
                error_rate = (requests_error / requests_total) * 100
                self.gauge("http_requests_error_rate_percent", error_rate)

        except Exception as e:
            print(f"Error collecting application metrics: {e}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics"""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "metrics": {}
        }

        for name, metric in self.metrics.items():
            definition = self.definitions.get(name)
            if not definition:
                continue

            if isinstance(metric, (float, int)):
                summary["metrics"][name] = {
                    "type": definition.metric_type.value,
                    "value": metric,
                    "unit": definition.unit.value
                }
            elif hasattr(metric, 'get_summary'):  # Histogram
                summary["metrics"][name] = {
                    "type": definition.metric_type.value,
                    "summary": metric.get_summary(),
                    "unit": definition.unit.value
                }
            elif hasattr(metric, 'get_rate'):  # Meter
                summary["metrics"][name] = {
                    "type": definition.metric_type.value,
                    "count": metric.count,
                    "rate": metric.get_rate(),
                    "unit": definition.unit.value
                }

        return summary

    def get_metrics_for_export(self) -> Dict[str, Any]:
        """Get metrics in export format (e.g., for Prometheus)"""
        metrics_for_export = {}

        for name, metric in self.metrics.items():
            definition = self.definitions.get(name)
            if not definition:
                continue

            if isinstance(metric, (float, int)):
                metrics_for_export[name] = metric
            elif hasattr(metric, 'get_summary'):  # Histogram
                summary = metric.get_summary()
                for key, value in summary.items():
                    if key not in ["count", "sum"]:
                        metrics_for_export[f"{name}_{key}"] = value
                metrics_for_export[f"{name}_count"] = summary["count"]
                metrics_for_export[f"{name}_sum"] = summary["sum"]
            elif hasattr(metric, 'get_rate'):  # Meter
                metrics_for_export[f"{name}_total"] = metric.count
                metrics_for_export[f"{name}_rate"] = metric.get_rate()

        return metrics_for_export

    def start_collection(self):
        """Start background metrics collection"""
        if self.running:
            return

        self.running = True
        self.collector_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collector_thread.start()

    def stop_collection(self):
        """Stop background metrics collection"""
        self.running = False
        if self.collector_thread:
            self.collector_thread.join()

    def _collection_loop(self):
        """Background collection loop"""
        while self.running:
            try:
                self.collect_system_metrics()
                self.collect_application_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Error in metrics collection loop: {e}")
                time.sleep(self.collection_interval)


# Global metrics collector instance
metrics_collector = MetricsCollector()

# Predefined metrics definitions
def register_default_metrics():
    """Register default metrics for AutoAdmin"""

    # HTTP metrics
    metrics_collector.register_metric(MetricDefinition(
        name="http_requests_total",
        description="Total HTTP requests",
        metric_type=MetricType.COUNTER,
        unit=MetricUnit.COUNT,
        labels=["method", "status", "endpoint"]
    ))

    metrics_collector.register_metric(MetricDefinition(
        name="http_request_duration_ms",
        description="HTTP request duration in milliseconds",
        metric_type=MetricType.HISTOGRAM,
        unit=MetricUnit.MILLISECONDS,
        labels=["method", "status", "endpoint"]
    ))

    # Agent metrics
    metrics_collector.register_metric(MetricDefinition(
        name="agents_active_count",
        description="Number of active agents",
        metric_type=MetricType.GAUGE,
        unit=MetricUnit.COUNT,
        labels=[]
    ))

    metrics_collector.register_metric(MetricDefinition(
        name="agent_task_duration_ms",
        description="Agent task execution duration",
        metric_type=MetricType.HISTOGRAM,
        unit=MetricUnit.MILLISECONDS,
        labels=["agent_type", "task_type"]
    ))

    # Task metrics
    metrics_collector.register_metric(MetricDefinition(
        name="tasks_completed_total",
        description="Total completed tasks",
        metric_type=MetricType.COUNTER,
        unit=MetricUnit.COUNT,
        labels=["agent_type", "task_type"]
    ))

    metrics_collector.register_metric(MetricDefinition(
        name="tasks_failed_total",
        description="Total failed tasks",
        metric_type=MetricType.COUNTER,
        unit=MetricUnit.COUNT,
        labels=["agent_type", "task_type", "error_type"]
    ))

    # Database metrics
    metrics_collector.register_metric(MetricDefinition(
        name="database_connections_active",
        description="Active database connections",
        metric_type=MetricType.GAUGE,
        unit=MetricUnit.COUNT,
        labels=["database"]
    ))

    metrics_collector.register_metric(MetricDefinition(
        name="database_query_duration_ms",
        description="Database query duration",
        metric_type=MetricType.HISTOGRAM,
        unit=MetricUnit.MILLISECONDS,
        labels=["database", "operation"]
    ))

    # Cache metrics
    metrics_collector.register_metric(MetricDefinition(
        name="cache_hit_rate",
        description="Cache hit rate",
        metric_type=MetricType.GAUGE,
        unit=MetricUnit.PERCENTAGE,
        labels=["cache_type"]
    ))

    # External API metrics
    metrics_collector.register_metric(MetricDefinition(
        name="external_api_requests_total",
        description="External API requests",
        metric_type=MetricType.COUNTER,
        unit=MetricUnit.COUNT,
        labels=["service", "endpoint", "status"]
    ))

    metrics_collector.register_metric(MetricDefinition(
        name="external_api_request_duration_ms",
        description="External API request duration",
        metric_type=MetricType.HISTOGRAM,
        unit=MetricUnit.MILLISECONDS,
        labels=["service", "endpoint"]
    ))


# Initialize default metrics
register_default_metrics()