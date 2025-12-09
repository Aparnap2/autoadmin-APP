"""
Async Context Manager for AutoAdmin Backend
Provides robust async lifecycle management, exception handling, and graceful shutdown
"""

import asyncio
import signal
import logging
import weakref
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import traceback
from contextlib import asynccontextmanager


class ServiceState(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceMetrics:
    """Metrics for monitoring service health"""
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    exceptions: List[Dict[str, Any]] = field(default_factory=list)
    last_heartbeat: Optional[datetime] = None


class AsyncServiceManager:
    """
    Manages async services with proper lifecycle, exception handling, and graceful shutdown
    """

    def __init__(self, shutdown_timeout: float = 30.0):
        self.shutdown_timeout = shutdown_timeout
        self.services: Dict[str, 'ManagedService'] = {}
        self.background_tasks: Set[asyncio.Task] = set()
        self.state = ServiceState.INITIALIZING
        self.metrics = ServiceMetrics()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Signal handling for graceful shutdown
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        self._exception_handlers: List[Callable] = []

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()
        if exc_type:
            self.logger.error(f"Exception in context: {exc_type.__name__}: {exc_val}")
            self.logger.error(traceback.format_exc())

    def register_service(self, name: str, service: Any,
                         initialize_func: Optional[Callable] = None,
                         start_func: Optional[Callable] = None,
                         stop_func: Optional[Callable] = None):
        """Register a service with lifecycle management"""
        managed_service = ManagedService(
            name=name,
            service=service,
            initialize_func=initialize_func,
            start_func=start_func,
            stop_func=stop_func,
            manager=self
        )
        self.services[name] = managed_service
        self.logger.info(f"Registered service: {name}")

    def add_exception_handler(self, handler: Callable):
        """Add custom exception handler"""
        self._exception_handlers.append(handler)

    async def initialize(self):
        """Initialize all registered services"""
        self.logger.info("Initializing AsyncServiceManager...")
        self.metrics.start_time = datetime.now()

        try:
            # Setup signal handlers
            self._setup_signal_handlers()

            # Initialize all services
            for name, service in self.services.items():
                self.logger.info(f"Initializing service: {name}")
                await service.initialize()

            self.state = ServiceState.RUNNING
            self.logger.info("AsyncServiceManager initialized successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to initialize AsyncServiceManager: {e}")
            self.logger.error(traceback.format_exc())
            await self._handle_exception(e, "initialization")
            raise

    async def start(self):
        """Start all registered services"""
        if self.state != ServiceState.RUNNING:
            raise RuntimeError("Manager must be initialized before starting")

        self.logger.info("Starting all services...")

        try:
            # Start all services
            start_tasks = []
            for name, service in self.services.items():
                self.logger.info(f"Starting service: {name}")
                start_tasks.append(service.start())

            # Wait for all services to start
            await asyncio.gather(*start_tasks, return_exceptions=True)

            # Start monitoring task
            monitor_task = asyncio.create_task(self._monitoring_loop())
            self.background_tasks.add(monitor_task)

            self.logger.info("All services started successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to start services: {e}")
            await self._handle_exception(e, "startup")
            raise

    async def shutdown(self):
        """Gracefully shutdown all services"""
        if self.state == ServiceState.STOPPED:
            return

        self.logger.info("Shutting down AsyncServiceManager...")
        self.state = ServiceState.STOPPING
        self.metrics.stop_time = datetime.now()

        # Signal shutdown to all loops
        self._shutdown_requested = True
        self._shutdown_event.set()

        try:
            # Create shutdown timeout
            shutdown_tasks = []

            # Stop all services
            for name, service in self.services.items():
                self.logger.info(f"Stopping service: {name}")
                shutdown_tasks.append(service.stop())

            # Wait for graceful shutdown with timeout
            if shutdown_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*shutdown_tasks, return_exceptions=True),
                        timeout=self.shutdown_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Shutdown timeout exceeded, forcing cancellation")

            # Cancel background tasks
            await self._cancel_background_tasks()

            self.state = ServiceState.STOPPED
            self.logger.info("AsyncServiceManager shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.logger.error(traceback.format_exc())

    async def create_background_task(self, coro, name: Optional[str] = None):
        """Create a background task with proper cleanup"""
        task = asyncio.create_task(coro, name=name)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            # Handle SIGINT and SIGTERM
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
        except NotImplementedError:
            # Windows doesn't support signal handlers in the same way
            self.logger.warning("Signal handlers not supported on this platform")

    def _signal_handler(self):
        """Handle shutdown signals"""
        if not self._shutdown_requested:
            self.logger.info("Received shutdown signal")
            asyncio.create_task(self.shutdown())

    async def _handle_exception(self, exception: Exception, context: str):
        """Handle exceptions with custom handlers"""
        exception_info = {
            "exception": str(exception),
            "type": type(exception).__name__,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        }

        self.metrics.exceptions.append(exception_info)

        # Call custom exception handlers
        for handler in self._exception_handlers:
            try:
                await handler(exception, context, exception_info)
            except Exception as handler_error:
                self.logger.error(f"Exception handler failed: {handler_error}")

    async def _cancel_background_tasks(self):
        """Cancel all background tasks"""
        if not self.background_tasks:
            return

        self.logger.info(f"Cancelling {len(self.background_tasks)} background tasks...")

        # Cancel all tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Background tasks didn't complete within timeout")

        self.background_tasks.clear()

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.state == ServiceState.RUNNING and not self._shutdown_requested:
            try:
                # Update heartbeat
                self.metrics.last_heartbeat = datetime.now()

                # Check service health
                unhealthy_services = []
                for name, service in self.services.items():
                    if service.state == ServiceState.ERROR:
                        unhealthy_services.append(name)

                if unhealthy_services:
                    self.logger.warning(f"Unhealthy services: {unhealthy_services}")

                # Log metrics
                self.logger.debug(
                    f"Metrics - Tasks: {self.metrics.total_tasks}, "
                    f"Completed: {self.metrics.completed_tasks}, "
                    f"Failed: {self.metrics.failed_tasks}, "
                    f"Exceptions: {len(self.metrics.exceptions)}"
                )

                # Wait before next check
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=60.0)
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue monitoring

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await self._handle_exception(e, "monitoring")
                await asyncio.sleep(10)  # Brief pause before retry

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all services"""
        return {
            "manager_state": self.state.value,
            "services": {
                name: {
                    "state": service.state.value,
                    "metrics": {
                        "total_tasks": service.metrics.total_tasks,
                        "completed_tasks": service.metrics.completed_tasks,
                        "failed_tasks": service.metrics.failed_tasks,
                        "exceptions": len(service.metrics.exceptions)
                    }
                }
                for name, service in self.services.items()
            },
            "background_tasks": len(self.background_tasks),
            "shutdown_requested": self._shutdown_requested,
            "metrics": {
                "start_time": self.metrics.start_time.isoformat() if self.metrics.start_time else None,
                "stop_time": self.metrics.stop_time.isoformat() if self.metrics.stop_time else None,
                "total_tasks": self.metrics.total_tasks,
                "completed_tasks": self.metrics.completed_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "total_exceptions": len(self.metrics.exceptions),
                "last_heartbeat": self.metrics.last_heartbeat.isoformat() if self.metrics.last_heartbeat else None
            }
        }


class ManagedService:
    """Represents a managed service with lifecycle hooks"""

    def __init__(self, name: str, service: Any,
                 initialize_func: Optional[Callable] = None,
                 start_func: Optional[Callable] = None,
                 stop_func: Optional[Callable] = None,
                 manager: Optional[AsyncServiceManager] = None):
        self.name = name
        self.service = service
        self.initialize_func = initialize_func
        self.start_func = start_func
        self.stop_func = stop_func
        self.manager = manager
        self.state = ServiceState.INITIALIZING
        self.metrics = ServiceMetrics()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    async def initialize(self):
        """Initialize the service"""
        try:
            self.state = ServiceState.INITIALIZING

            if self.initialize_func:
                await self.initialize_func(self.service)
            elif hasattr(self.service, 'initialize'):
                await self.service.initialize()

            self.state = ServiceState.RUNNING
            self.logger.info(f"Service {self.name} initialized successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to initialize service {self.name}: {e}")
            if self.manager:
                await self.manager._handle_exception(e, f"service_initialization_{self.name}")
            raise

    async def start(self):
        """Start the service"""
        try:
            if self.start_func:
                await self.start_func(self.service)
            elif hasattr(self.service, 'start'):
                await self.service.start()

            self.logger.info(f"Service {self.name} started successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to start service {self.name}: {e}")
            if self.manager:
                await self.manager._handle_exception(e, f"service_start_{self.name}")
            raise

    async def stop(self):
        """Stop the service"""
        try:
            self.state = ServiceState.STOPPING

            if self.stop_func:
                await self.stop_func(self.service)
            elif hasattr(self.service, 'stop'):
                await self.service.stop()

            self.state = ServiceState.STOPPED
            self.logger.info(f"Service {self.name} stopped successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to stop service {self.name}: {e}")
            if self.manager:
                await self.manager._handle_exception(e, f"service_stop_{self.name}")


# Context manager for easy usage
@asynccontextmanager
async def async_service_manager(shutdown_timeout: float = 30.0):
    """Context manager for AsyncServiceManager"""
    manager = AsyncServiceManager(shutdown_timeout)
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()