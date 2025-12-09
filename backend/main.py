"""
AutoAdmin Backend - Main entry point for Python deep agents
Handles task processing, communication with frontend, and agent coordination
"""

import asyncio
import os
import sys
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our async context manager
from async_context_manager import AsyncServiceManager, ServiceState, async_service_manager

# Import monitoring system
from monitoring.integration import (
    initialize_monitoring,
    monitor_exceptions,
    monitor_performance,
    ServiceComponent
)
from monitoring.logger import get_logger, LogLevel, set_correlation_id
from monitoring.error_tracking import ErrorSeverity, ErrorCategory

# Import our agents
from agents.marketing_agent import MarketingAgent
from agents.base_agent import AgentType, TaskStatus
# from communication.github_integration import GitHubActionsIntegration
from communication.webhook_handler import WebhookHandler


# Configure basic logging (will be enhanced by monitoring system)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('autoadmin_backend.log')
    ]
)

# Initialize structured logger
logger = get_logger("autoadmin_backend")


class AutoAdminBackend:
    """Main backend application for AutoAdmin with robust async lifecycle management"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Validate required environment variables
        self.validate_environment()

        # Initialize async service manager
        self.service_manager = AsyncServiceManager(shutdown_timeout=30.0)

        # Initialize agents
        self.agents: Dict[str, Any] = {}
        self.github_integration = None
        self.webhook_handler = None

        # Setup exception handlers
        self._setup_exception_handlers()

    def validate_environment(self):
        """Validate required environment variables with Firebase validation"""
        required_vars = [
            'OPENAI_API_KEY'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.info("Please set these variables in your .env file")
            sys.exit(1)

        # Validate Firebase configuration
        self._validate_firebase_configuration()

        # Optional variables
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')

        if self.github_token and self.github_repo:
            logger.info("GitHub integration enabled")
        else:
            logger.info("GitHub integration disabled (missing GITHUB_TOKEN or GITHUB_REPO)")

    def _validate_firebase_configuration(self):
        """Validate Firebase configuration and provide guidance"""
        try:
            # Import here to avoid circular imports
            from utils.firebase_validator import FirebaseValidator

            validator = FirebaseValidator()
            result = validator.validate_all()

            if not result.is_valid:
                logger.warning("Firebase configuration validation failed:")

                for error in result.errors:
                    logger.error(f"  - {error}")

                for warning in result.warnings:
                    logger.warning(f"  - {warning}")

                logger.info("💡 Firebase setup recommendations:")
                for rec in result.recommendations:
                    logger.info(f"  - {rec}")

                # Log offline mode notification
                logger.warning("⚠️  Firebase will run in OFFLINE MODE due to configuration issues")
                logger.warning("    Data will be stored in memory only and lost on restart")

            else:
                logger.info("✅ Firebase configuration is valid")
                # Check for any warnings
                if result.warnings:
                    logger.info("Firebase configuration warnings:")
                    for warning in result.warnings:
                        logger.info(f"  - {warning}")

        except ImportError:
            logger.warning("Firebase validator not available, skipping validation")
        except Exception as e:
            logger.error(f"Firebase validation error: {e}")
            logger.warning("Continuing with Firebase validation skipped")

    def _setup_exception_handlers(self):
        """Setup custom exception handlers with monitoring integration"""
        async def global_exception_handler(exception, context, exception_info):
            # Use structured logging with monitoring
            logger.error(
                f"Global exception in {context}: {exception}",
                component=ServiceComponent.AGENT,
                context=context,
                exception_info=exception_info,
                error=exception
            )

            # Track error in monitoring system
            from monitoring.error_tracking import error_tracker, ErrorContext
            error_context = ErrorContext(
                component=ServiceComponent.AGENT,
                custom_data={
                    "context": context,
                    "exception_info": exception_info,
                    "service_manager": True
                }
            )
            await error_tracker.track_error(exception, context=error_context)

            # Send to external monitoring if configured
            if os.getenv('SENTRY_DSN'):
                try:
                    import sentry_sdk
                    sentry_sdk.capture_exception(exception)
                except ImportError:
                    pass

        self.service_manager.add_exception_handler(global_exception_handler)

    async def initialize(self):
        """Initialize all backend services using async service manager"""
        try:
            logger.info("Initializing AutoAdmin Backend with AsyncServiceManager...")

            # Initialize monitoring system first
            monitoring_config = {
                "environment": os.getenv("ENVIRONMENT", "development"),
                "database": {
                    "connection_string": os.getenv("DATABASE_URL")
                },
                "redis": {
                    "host": os.getenv("REDIS_HOST", "localhost"),
                    "port": int(os.getenv("REDIS_PORT", "6379")),
                    "password": os.getenv("REDIS_PASSWORD"),
                    "db": int(os.getenv("REDIS_DB", "0"))
                },
                "qdrant": {
                    "url": os.getenv("QDRANT_URL"),
                    "api_key": os.getenv("QDRANT_API_KEY")
                }
            }
            await initialize_monitoring(monitoring_config)

            # Initialize the service manager
            await self.service_manager.initialize()

            # Initialize agents
            await self.initialize_agents()

            # Register agents with service manager
            for name, agent in self.agents.items():
                self.service_manager.register_service(
                    name=f"agent_{name}",
                    service=agent,
                    initialize_func=lambda s: s.initialize() if hasattr(s, 'initialize') else None,
                    start_func=lambda s: s.start() if hasattr(s, 'start') else None,
                    stop_func=lambda s: s.stop() if hasattr(s, 'stop') else None
                )

            # Initialize GitHub Actions integration if configured
            # if self.github_token and self.github_repo:
            #     self.github_integration = GitHubActionsIntegration(
            #         token=self.github_token,
            #         repo=self.github_repo,
            #         supabase_url=os.getenv('SUPABASE_URL'),
            #         supabase_key=os.getenv('SUPABASE_KEY')
            #     )
            self.github_integration = None

            # Register GitHub integration with service manager if initialized
            if self.github_integration:
                self.service_manager.register_service(
                    name="github_integration",
                    service=self.github_integration,
                    initialize_func=lambda s: s.initialize() if hasattr(s, 'initialize') else None,
                    start_func=lambda s: s.start() if hasattr(s, 'start') else None,
                    stop_func=lambda s: s.stop() if hasattr(s, 'stop') else None
                )

            # Initialize webhook handler
            self.webhook_handler = WebhookHandler(
                supabase_url=os.getenv('SUPABASE_URL'),
                supabase_key=os.getenv('SUPABASE_KEY'),
                agents=self.agents
            )

            self.service_manager.register_service(
                name="webhook_handler",
                service=self.webhook_handler,
                initialize_func=lambda s: s.initialize() if hasattr(s, 'initialize') else None,
                start_func=lambda s: s.start() if hasattr(s, 'start') else None,
                stop_func=lambda s: s.stop() if hasattr(s, 'stop') else None
            )

            # Register status monitoring loop
            self.service_manager.register_service(
                name="status_monitor",
                service=self,
                start_func=lambda s: s.service_manager.create_background_task(
                    s.status_monitoring_loop(),
                    name="status_monitoring_loop"
                )
            )

            logger.info("AutoAdmin Backend initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize backend: {e}")
            logger.error(traceback.format_exc())
            raise

    @monitor_performance("initialize_agents", ServiceComponent.AGENT)
    @monitor_exceptions(ServiceComponent.AGENT)
    async def initialize_agents(self):
        """Initialize all agent types"""
        try:
            # Initialize Marketing Agent
            marketing_agent = MarketingAgent(
                openai_api_key=os.getenv('OPENAI_API_KEY')
            )
            self.agents['marketing'] = marketing_agent

            # Additional agents would be initialized here:
            # - Finance Agent
            # - DevOps Agent
            # - Strategy Agent

            logger.info(
                f"Initialized {len(self.agents)} agents",
                component=ServiceComponent.AGENT,
                agent_count=len(self.agents)
            )

            # Record agent initialization metrics
            from monitoring import metrics_collector
            metrics_collector.gauge("agents_initialized_count", len(self.agents))

        except Exception as e:
            logger.error(
                f"Failed to initialize agents: {e}",
                component=ServiceComponent.AGENT,
                error=e
            )
            raise

    async def start(self):
        """Start all backend services using service manager"""
        try:
            logger.info("Starting AutoAdmin Backend services...")

            # Start all services through service manager
            await self.service_manager.start()

            logger.info("All backend services started successfully")

            # Wait for shutdown signal (they run indefinitely)
            await self.service_manager._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Error starting backend services: {e}")
            logger.error(traceback.format_exc())
            raise

    async def stop(self):
        """Stop all backend services using service manager"""
        try:
            logger.info("Stopping AutoAdmin Backend services...")

            # Stop all services through service manager
            await self.service_manager.shutdown()

            logger.info("All backend services stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping backend services: {e}")
            logger.error(traceback.format_exc())

    
    async def status_monitoring_loop(self):
        """Monitor system status and health"""
        while True:
            try:
                # Collect status from all agents
                status_report = {
                    "timestamp": datetime.now().isoformat(),
                    "backend_version": "1.0.0",
                    "agents": {},
                    "github_integration": None,
                    "overall_health": "healthy"
                }

                # Get agent statuses
                for agent_name, agent in self.agents.items():
                    status_report["agents"][agent_name] = {
                        "agent_id": agent.agent_id,
                        "agent_type": agent.agent_type.value,
                        "current_load": agent.capabilities.currentLoad,
                        "max_concurrent_tasks": agent.capabilities.maxConcurrentTasks,
                        "success_rate": agent.capabilities.successRate,
                        "is_running": agent.is_running,
                        "capabilities": agent.capabilities.capabilities,
                        "supported_task_types": [t.value for t in agent.capabilities.supportedTaskTypes]
                    }

                # Get GitHub integration status
                if self.github_integration:
                    status_report["github_integration"] = {
                        "connected": self.github_integration.is_connected(),
                        "last_sync": self.github_integration.get_last_sync(),
                        "active_workflows": len(self.github_integration.get_active_workflows())
                    }

                # Log status summary
                total_load = sum(agent.capabilities.currentLoad for agent in self.agents.values())
                max_capacity = sum(agent.capabilities.maxConcurrentTasks for agent in self.agents.values())
                utilization = (total_load / max_capacity * 100) if max_capacity > 0 else 0

                logger.info(
                    f"Status Report - Agents: {len(self.agents)}, "
                    f"Load: {total_load}/{max_capacity} ({utilization:.1f}%), "
                    f"GitHub: {'Connected' if status_report['github_integration'] else 'Disconnected'}"
                )

                # Store status in Supabase for monitoring
                await self.store_status_report(status_report)

                # Wait before next status check
                await asyncio.sleep(60)  # Status check every minute

            except Exception as e:
                logger.error(f"Error in status monitoring: {e}")
                await asyncio.sleep(60)

    async def store_status_report(self, status_report: Dict[str, Any]):
        """Store status report in Supabase for monitoring"""
        try:
            # This would store the status report in Supabase
            # Implementation depends on the Supabase client setup
            logger.debug("Storing status report in Supabase")
        except Exception as e:
            logger.error(f"Error storing status report: {e}")

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all agents"""
        status = {}
        for agent_name, agent in self.agents.items():
            status[agent_name] = {
                "agent_id": agent.agent_id,
                "type": agent.agent_type.value,
                "running": agent.is_running,
                "current_tasks": len(agent.current_tasks),
                "load": agent.capabilities.currentLoad,
                "max_load": agent.capabilities.maxConcurrentTasks,
                "success_rate": agent.capabilities.successRate
            }
        return status

    async def handle_manual_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manually submitted task (for testing)"""
        try:
            from agents.base_agent import TaskDelegation, TaskType, TaskStatus
            import uuid

            # Create task from manual data
            task = TaskDelegation(
                id=task_data.get("id", f"manual_{uuid.uuid4().hex[:8]}"),
                type=task_data.get("type", "heavy_task"),
                category=TaskType(task_data.get("category", "market_research")),
                priority=task_data.get("priority", "medium"),
                title=task_data.get("title", "Manual Task"),
                description=task_data.get("description", ""),
                parameters=task_data.get("parameters", {}),
                expectedDuration=task_data.get("expectedDuration", 300),
                complexity=task_data.get("complexity", 5),
                resourceRequirements=task_data.get("resourceRequirements", {}),
                assignedTo=task_data.get("assignedTo", "marketing"),
                status=TaskStatus.PENDING,
                createdAt=datetime.now(),
                updatedAt=datetime.now(),
                metadata=task_data.get("metadata", {})
            )

            # Route to appropriate agent
            agent_type = task.assignedTo
            if agent_type not in self.agents:
                return {
                    "success": False,
                    "error": f"Agent type '{agent_type}' not available",
                    "available_agents": list(self.agents.keys())
                }

            agent = self.agents[agent_type]

            # Process the task
            result = await agent.process_task(task)

            return {
                "success": True,
                "task_id": task.id,
                "result": result.__dict__,
                "agent": agent_type
            }

        except Exception as e:
            logger.error(f"Error handling manual task: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def main():
    """Main entry point with robust async lifecycle management"""
    backend = AutoAdminBackend()

    try:
        # Initialize backend
        await backend.initialize()

        # Start backend services (this will run until shutdown)
        await backend.start()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Backend error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Clean shutdown - the service manager handles this gracefully
        logger.info("AutoAdmin Backend shutdown complete")


async def main_with_context_manager():
    """Alternative main using context manager for even better resource management"""
    async with async_service_manager(shutdown_timeout=30.0) as service_manager:
        backend = AutoAdminBackend()
        backend.service_manager = service_manager

        try:
            # Initialize backend
            await backend.initialize()

            # Start backend services
            await backend.start()

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Backend error: {e}")
            logger.error(traceback.format_exc())


if __name__ == "__main__":
    # For development, you can also run with specific commands:
    # python main.py --test-task '{"title": "Test Task", "description": "Test description"}'
    if len(sys.argv) > 1 and sys.argv[1] == "--test-task":
        # Test mode - process a single task
        import asyncio

        async def test_task():
            backend = AutoAdminBackend()
            await backend.initialize()

            if len(sys.argv) > 2:
                try:
                    task_data = json.loads(sys.argv[2])
                    result = await backend.handle_manual_task(task_data)
                    print("Test Result:", json.dumps(result, indent=2))
                except json.JSONDecodeError:
                    print("Invalid JSON task data")
            else:
                # Create a sample task
                sample_task = {
                    "title": "Sample Market Research",
                    "description": "Research the current state of AI-powered SaaS tools",
                    "category": "market_research",
                    "type": "heavy_task",
                    "priority": "medium"
                }
                result = await backend.handle_manual_task(sample_task)
                print("Sample Task Result:", json.dumps(result, indent=2))

        asyncio.run(test_task())
    else:
        # Normal operation
        asyncio.run(main())