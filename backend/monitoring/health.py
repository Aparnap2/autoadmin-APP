"""
Comprehensive health check system for all system components
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import asyncpg
import redis.asyncio as redis
from qdrant_client import QdrantClient
import psutil


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult(Enum):
    """Health check result types"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class HealthCheck:
    """Individual health check configuration"""
    name: str
    description: str
    component_type: str
    check_function: Callable
    timeout: float = 10.0
    interval: float = 30.0
    critical: bool = False
    parameters: Dict[str, Any] = None


@dataclass
class HealthStatusReport:
    """Health status report for a component"""
    component: str
    component_type: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = None
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    uptime_percentage: float = 100.0


@dataclass
class SystemHealthReport:
    """Overall system health report"""
    status: HealthStatus
    timestamp: datetime
    uptime_seconds: float
    components: Dict[str, HealthStatusReport]
    summary: Dict[str, Any]
    recommendations: List[str]


class HealthChecker:
    """
    Comprehensive health checking system
    """

    def __init__(self, service_name: str = "autoadmin-backend"):
        self.service_name = service_name
        self.health_checks: Dict[str, HealthCheck] = {}
        self.component_status: Dict[str, HealthStatusReport] = {}
        self.check_history: Dict[str, List[HealthStatusReport]] = {}
        self.running = False
        self.check_task = None
        self.start_time = time.time()

        # Health check thresholds
        self.degraded_threshold = 0.8  # 80% of components healthy
        self.unhealthy_threshold = 0.5  # 50% of components healthy

    def register_health_check(self, health_check: HealthCheck):
        """Register a new health check"""
        self.health_checks[health_check.name] = health_check
        self.check_history[health_check.name] = []

    def remove_health_check(self, name: str):
        """Remove a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
        if name in self.component_status:
            del self.component_status[name]
        if name in self.check_history:
            del self.check_history[name]

    async def check_component_health(self, name: str) -> HealthStatusReport:
        """Check health of a specific component"""
        if name not in self.health_checks:
            return HealthStatusReport(
                component=name,
                component_type="unknown",
                status=HealthStatus.UNKNOWN,
                message="Health check not found",
                timestamp=datetime.utcnow(),
                response_time_ms=0
            )

        health_check = self.health_checks[name]
        start_time = time.time()

        try:
            # Run health check with timeout
            result = await asyncio.wait_for(
                health_check.check_function(**(health_check.parameters or {})),
                timeout=health_check.timeout
            )

            response_time_ms = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "unknown"))
                message = result.get("message", "")
                details = result.get("details", {})
            else:
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "Check passed" if result else "Check failed"
                details = {"result": result}

            # Determine consecutive failures
            previous_status = self.component_status.get(name)
            consecutive_failures = 0
            if previous_status and status == HealthStatus.UNHEALTHY:
                consecutive_failures = previous_status.consecutive_failures + 1
            elif status != HealthStatus.UNHEALTHY:
                consecutive_failures = 0

            health_report = HealthStatusReport(
                component=name,
                component_type=health_check.component_type,
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time_ms,
                details=details,
                consecutive_failures=consecutive_failures
            )

            # Update component status
            self.component_status[name] = health_report

            # Add to history
            self.check_history[name].append(health_report)

            # Keep only last 100 checks
            if len(self.check_history[name]) > 100:
                self.check_history[name].pop(0)

            return health_report

        except asyncio.TimeoutError:
            response_time_ms = health_check.timeout * 1000
            return HealthStatusReport(
                component=name,
                component_type=health_check.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {health_check.timeout}s",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time_ms,
                consecutive_failures=self.component_status.get(name, HealthStatusReport(
                    component=name, component_type=health_check.component_type,
                    status=HealthStatus.UNHEALTHY, message="", timestamp=datetime.utcnow(),
                    response_time_ms=0
                )).consecutive_failures + 1
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthStatusReport(
                component=name,
                component_type=health_check.component_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time_ms,
                details={"error": str(e), "error_type": type(e).__name__},
                consecutive_failures=self.component_status.get(name, HealthStatusReport(
                    component=name, component_type=health_check.component_type,
                    status=HealthStatus.UNHEALTHY, message="", timestamp=datetime.utcnow(),
                    response_time_ms=0
                )).consecutive_failures + 1
            )

    async def check_all_components(self) -> Dict[str, HealthStatusReport]:
        """Check health of all registered components"""
        tasks = []
        for name in self.health_checks.keys():
            tasks.append(self.check_component_health(name))

        # Run all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results back to component names
        component_reports = {}
        for i, name in enumerate(self.health_checks.keys()):
            result = results[i]
            if isinstance(result, Exception):
                component_reports[name] = HealthStatusReport(
                    component=name,
                    component_type=self.health_checks[name].component_type,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check error: {str(result)}",
                    timestamp=datetime.utcnow(),
                    response_time_ms=0
                )
            else:
                component_reports[name] = result

        return component_reports

    def calculate_overall_health(self, component_reports: Dict[str, HealthStatusReport]) -> HealthStatus:
        """Calculate overall system health"""
        if not component_reports:
            return HealthStatus.UNKNOWN

        total_components = len(component_reports)
        critical_components = [r for r in component_reports.values() if r.status == HealthStatus.UNHEALTHY and self.health_checks[r.component].critical]
        healthy_components = len([r for r in component_reports.values() if r.status == HealthStatus.HEALTHY])
        degraded_components = len([r for r in component_reports.values() if r.status == HealthStatus.DEGRADED])

        # If any critical component is unhealthy, system is unhealthy
        if critical_components:
            return HealthStatus.UNHEALTHY

        # Calculate health percentage
        health_percentage = (healthy_components + degraded_components * 0.5) / total_components

        if health_percentage >= 1.0:
            return HealthStatus.HEALTHY
        elif health_percentage >= self.degraded_threshold:
            return HealthStatus.DEGRADED
        elif health_percentage >= self.unhealthy_threshold:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def generate_recommendations(self, component_reports: Dict[str, HealthStatusReport]) -> List[str]:
        """Generate recommendations based on health status"""
        recommendations = []

        for name, report in component_reports.items():
            if report.status == HealthStatus.UNHEALTHY:
                if report.consecutive_failures >= 3:
                    recommendations.append(f"URGENT: {name} has failed {report.consecutive_failures} consecutive health checks")
                else:
                    recommendations.append(f"Monitor {name}: {report.message}")

            elif report.status == HealthStatus.DEGRADED:
                recommendations.append(f"Performance concern for {name}: {report.message}")

            elif report.response_time_ms > 5000:  # > 5 seconds
                recommendations.append(f"Performance issue for {name}: Response time {report.response_time_ms:.0f}ms")

        if not recommendations:
            recommendations.append("All components are healthy")

        return recommendations

    async def get_system_health(self) -> SystemHealthReport:
        """Get comprehensive system health report"""
        component_reports = await self.check_all_components()
        overall_status = self.calculate_overall_health(component_reports)
        uptime_seconds = time.time() - self.start_time

        # Generate summary
        summary = {
            "total_components": len(component_reports),
            "healthy_components": len([r for r in component_reports.values() if r.status == HealthStatus.HEALTHY]),
            "degraded_components": len([r for r in component_reports.values() if r.status == HealthStatus.DEGRADED]),
            "unhealthy_components": len([r for r in component_reports.values() if r.status == HealthStatus.UNHEALTHY]),
            "unknown_components": len([r for r in component_reports.values() if r.status == HealthStatus.UNKNOWN]),
            "critical_failures": len([r for r in component_reports.values()
                                   if r.status == HealthStatus.UNHEALTHY and self.health_checks[r.component].critical]),
            "average_response_time_ms": sum(r.response_time_ms for r in component_reports.values()) / len(component_reports) if component_reports else 0
        }

        recommendations = self.generate_recommendations(component_reports)

        return SystemHealthReport(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime_seconds,
            components=component_reports,
            summary=summary,
            recommendations=recommendations
        )

    def get_component_uptime(self, name: str, hours: int = 24) -> float:
        """Calculate uptime percentage for a component over specified hours"""
        if name not in self.check_history:
            return 0.0

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_checks = [check for check in self.check_history[name] if check.timestamp >= cutoff_time]

        if not recent_checks:
            return 0.0

        healthy_checks = len([check for check in recent_checks if check.status == HealthStatus.HEALTHY])
        return (healthy_checks / len(recent_checks)) * 100

    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.running:
            return

        self.running = True
        self.check_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self.running = False
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                await self.check_all_components()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(30)


# Predefined health check functions
async def check_database_health(connection_string: str, query: str = "SELECT 1") -> Dict[str, Any]:
    """Check database connectivity and basic functionality"""
    try:
        # Parse connection string (implementation depends on database type)
        conn = await asyncpg.connect(connection_string)

        start_time = time.time()
        result = await conn.fetchval(query)
        response_time_ms = (time.time() - start_time) * 1000

        await conn.close()

        return {
            "status": "healthy" if result else "unhealthy",
            "message": "Database connection successful",
            "details": {
                "query_result": result,
                "response_time_ms": response_time_ms
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "details": {"error": str(e)}
        }


async def check_redis_health(host: str = "localhost", port: int = 6379, password: str = None, db: int = 0) -> Dict[str, Any]:
    """Check Redis connectivity"""
    try:
        redis_client = redis.Redis(host=host, port=port, password=password, db=db)

        start_time = time.time()
        result = await redis_client.ping()
        response_time_ms = (time.time() - start_time) * 1000

        await redis_client.close()

        return {
            "status": "healthy" if result else "unhealthy",
            "message": "Redis connection successful",
            "details": {
                "ping_result": result,
                "response_time_ms": response_time_ms
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
            "details": {"error": str(e)}
        }


async def check_qdrant_health(url: str, api_key: str = None) -> Dict[str, Any]:
    """Check Qdrant vector database connectivity"""
    try:
        client = QdrantClient(url=url, api_key=api_key)

        start_time = time.time()
        collections = client.get_collections()
        response_time_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "message": "Qdrant connection successful",
            "details": {
                "collection_count": len(collections.collections),
                "response_time_ms": response_time_ms
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {str(e)}",
            "details": {"error": str(e)}
        }


async def check_external_api_health(url: str, method: str = "GET", headers: Dict[str, str] = None, timeout: float = 5.0) -> Dict[str, Any]:
    """Check external API health"""
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()

            async with session.request(method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                response_time_ms = (time.time() - start_time) * 1000
                await response.text()  # Read response body

                return {
                    "status": "healthy" if 200 <= response.status < 400 else "degraded",
                    "message": f"API returned status {response.status}",
                    "details": {
                        "status_code": response.status,
                        "response_time_ms": response_time_ms,
                        "url": url
                    }
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"API health check failed: {str(e)}",
            "details": {"error": str(e), "url": url}
        }


async def check_system_resources() -> Dict[str, Any]:
    """Check system resource utilization"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage
        disk = psutil.disk_usage('/')

        # Network connections
        connections = len(psutil.net_connections())

        # Determine health status
        if cpu_percent > 90 or memory.percent > 90:
            status = "unhealthy"
        elif cpu_percent > 80 or memory.percent > 80:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "message": f"CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, Disk: {disk.percent:.1f}%",
            "details": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "network_connections": connections
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"System resource check failed: {str(e)}",
            "details": {"error": str(e)}
        }


async def check_filesystem_health(path: str = "/") -> Dict[str, Any]:
    """Check filesystem health and availability"""
    try:
        # Test write permissions
        test_file = f"{path}/.autoadmin_health_check"

        start_time = time.time()
        with open(test_file, 'w') as f:
            f.write("health_check")

        # Test read
        with open(test_file, 'r') as f:
            content = f.read()

        # Clean up
        import os
        os.remove(test_file)

        response_time_ms = (time.time() - start_time) * 1000

        # Check disk space
        disk_usage = psutil.disk_usage(path)

        return {
            "status": "healthy",
            "message": f"Filesystem access successful, {disk_usage.free / (1024**3):.1f}GB free",
            "details": {
                "path": path,
                "response_time_ms": response_time_ms,
                "disk_free_gb": disk_usage.free / (1024**3),
                "disk_total_gb": disk_usage.total / (1024**3),
                "disk_usage_percent": (disk_usage.used / disk_usage.total) * 100
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Filesystem health check failed: {str(e)}",
            "details": {"error": str(e), "path": path}
        }


# Global health checker instance
health_checker = HealthChecker()