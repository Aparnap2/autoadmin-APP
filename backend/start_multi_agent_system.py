#!/usr/bin/env python3
"""
Multi-Agent Orchestration System Startup Script
Deploys and starts the robust multi-agent system with load balancing, failover, and health monitoring
"""

import os
import sys
import asyncio
import logging
import yaml
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import signal

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.swarm.orchestrator import AgentOrchestrator
from agents.swarm.load_balancer import get_load_balancer
from agents.swarm.failover_manager import get_failover_manager
from agents.swarm.health_monitor import get_health_monitor
from database.manager import get_database_manager
from fastapi import FastAPI
import uvicorn

# Configure logging
def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration"""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper())

    # Create formatters
    if log_config.get("format") == "json":
        import json
        import pythonjsonlogger

        formatter = pythonjsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console handler
    if log_config.get("console", {}).get("enabled", True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        if log_config.get("console", {}).get("colored", True):
            try:
                import colorlog
                formatter = colorlog.ColoredFormatter(
                    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(formatter)
            except ImportError:
                pass
        root_logger.addHandler(console_handler)

    # File handler
    if log_config.get("file", {}).get("enabled", False):
        log_dir = Path(log_config.get("file", {}).get("path", "/var/log/autoadmin"))
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "multi_agent_system.log",
            maxBytes=log_config.get("file", {}).get("max_size_mb", 100) * 1024 * 1024,
            backupCount=log_config.get("file", {}).get("backup_count", 10)
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.info("Logging configured")


def load_config(config_file: Optional[str] = None, environment: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file and environment variables"""
    config = {}

    # Load from YAML file
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        print(f"Loaded configuration from {config_file}")

    # Load environment-specific configuration
    if environment and "environments" in config and environment in config["environments"]:
        env_config = config["environments"][environment]
        # Deep merge environment config
        for key, value in env_config.items():
            if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                config[key].update(value)
            else:
                config[key] = value
        print(f"Applied {environment} environment configuration")

    # Substitute environment variables
    config = substitute_env_vars(config)

    return config


def substitute_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively substitute environment variables in configuration"""
    if isinstance(config, str):
        # Replace ${VAR_NAME} with environment variable
        import re
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, lambda m: os.getenv(m.group(1), ''), config)
    elif isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(item) for item in config]
    else:
        return config


class MultiAgentSystem:
    """Main multi-agent system class"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # System components
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.database_manager = None
        self.load_balancer = None
        self.failover_manager = None
        self.health_monitor = None

        # API server
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None

        # System state
        self.is_running = False
        self.startup_time = datetime.now()

        # Signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            self.logger.info("Initializing multi-agent system...")

            # Initialize database manager
            await self._initialize_database()

            # Initialize orchestrator with agents
            await self._initialize_orchestrator()

            # Initialize API server
            await self._initialize_api_server()

            self.logger.info("Multi-agent system initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize system: {e}")
            return False

    async def _initialize_database(self):
        """Initialize database connections"""
        try:
            self.logger.info("Initializing database connections...")

            database_config = self.config.get("database", {})
            self.database_manager = await get_database_manager(database_config)

            health = await self.database_manager.health_check()
            if health.get("overall_status") != "healthy":
                self.logger.warning(f"Database health is degraded: {health}")

            self.logger.info("Database connections established")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    async def _initialize_orchestrator(self):
        """Initialize orchestrator and agents"""
        try:
            self.logger.info("Initializing orchestrator and agents...")

            # Create orchestrator with agent configurations
            agent_config = {
                "ceo": self.config.get("agents", {}).get("ceo", {}),
                "strategy": self.config.get("agents", {}).get("strategy", {}),
                "devops": self.config.get("agents", {}).get("devops", {}),
                "load_balancer": self.config.get("load_balancer", {}),
                "failover": self.config.get("failover", {}),
                "health_monitor": self.config.get("health_monitor", {})
            }

            self.orchestrator = AgentOrchestrator(agent_config)

            # Initialize orchestrator (this also initializes load balancer, failover manager, health monitor)
            success = await self.orchestrator.initialize()

            if not success:
                raise Exception("Failed to initialize orchestrator")

            # Get references to components
            self.load_balancer = await get_load_balancer()
            self.failover_manager = await get_failover_manager()
            self.health_monitor = await get_health_monitor()

            self.logger.info("Orchestrator and agents initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            raise

    async def _initialize_api_server(self):
        """Initialize FastAPI server"""
        try:
            self.logger.info("Initializing API server...")

            # Create FastAPI app
            self.app = FastAPI(
                title="AutoAdmin Multi-Agent Orchestration API",
                description="Robust multi-agent system with load balancing, failover, and health monitoring",
                version="2.0.0",
                docs_url="/docs",
                redoc_url="/redoc"
            )

            # Include routers
            from fastapi.app.routers import multi_agent
            self.app.include_router(multi_agent.router)

            # Add middleware
            await self._add_middleware()

            self.logger.info("API server initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize API server: {e}")
            raise

    async def _add_middleware(self):
        """Add middleware to FastAPI app"""
        try:
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.middleware.gzip import GZipMiddleware

            # CORS middleware
            if self.config.get("api", {}).get("cors", {}).get("enabled", True):
                self.app.add_middleware(
                    CORSMiddleware,
                    allow_origins=self.config.get("api", {}).get("cors", {}).get("origins", ["*"]),
                    allow_credentials=True,
                    allow_methods=self.config.get("api", {}).get("cors", {}).get("methods", ["*"]),
                    allow_headers=self.config.get("api", {}).get("cors", {}).get("headers", ["*"])
                )

            # Gzip middleware
            self.app.add_middleware(GZipMiddleware)

            # Request logging middleware
            @self.app.middleware("http")
            async def log_requests(request, call_next):
                start_time = datetime.now()
                response = await call_next(request)
                duration = (datetime.now() - start_time).total_seconds()

                self.logger.info(
                    f"Request: {request.method} {request.url.path} - "
                    f"Status: {response.status_code} - "
                    f"Duration: {duration:.3f}s"
                )

                return response

        except Exception as e:
            self.logger.error(f"Failed to add middleware: {e}")

    async def start(self) -> bool:
        """Start the multi-agent system"""
        try:
            if self.is_running:
                self.logger.warning("System is already running")
                return True

            self.logger.info("Starting multi-agent system...")

            # Start API server
            await self._start_api_server()

            self.is_running = True
            self.startup_time = datetime.now()

            # Log system status
            await self._log_system_status()

            self.logger.info("Multi-agent system started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            return False

    async def _start_api_server(self):
        """Start API server"""
        try:
            api_config = self.config.get("api", {})

            # Create uvicorn config
            uvicorn_config = uvicorn.Config(
                self.app,
                host=api_config.get("host", "0.0.0.0"),
                port=api_config.get("port", 8000),
                workers=api_config.get("workers", 1),  # Set to 1 for now due to asyncio
                log_level="info",
                access_log=True,
                timeout_keep_alive=30
            )

            # Create server
            self.server = uvicorn.Server(uvicorn_config)

            # Start server in background task
            asyncio.create_task(self.server.serve())

            self.logger.info(f"API server started on {uvicorn_config.host}:{uvicorn_config.port}")

        except Exception as e:
            self.logger.error(f"Failed to start API server: {e}")
            raise

    async def _log_system_status(self):
        """Log comprehensive system status"""
        try:
            status = await self.orchestrator.get_orchestrator_status()

            self.logger.info("System Status Summary:")
            self.logger.info(f"  - Agents: {status.get('load_balancer', {}).get('total_agents', 0)} total")
            self.logger.info(f"  - Healthy Agents: {status.get('load_balancer', {}).get('healthy_agents', 0)}")
            self.logger.info(f"  - Active Tasks: {status.get('load_balancer', {}).get('active_tasks', 0)}")
            self.logger.info(f"  - System Health: {status.get('health', {}).get('average_health_score', 0):.1f}/100")

        except Exception as e:
            self.logger.error(f"Failed to log system status: {e}")

    async def shutdown(self) -> bool:
        """Shutdown the multi-agent system gracefully"""
        try:
            if not self.is_running:
                self.logger.warning("System is not running")
                return True

            self.logger.info("Shutting down multi-agent system...")

            # Stop API server
            if self.server:
                self.server.should_exit = True
                self.logger.info("API server shutdown initiated")

            # Shutdown orchestrator
            if self.orchestrator:
                await self.orchestrator.shutdown()
                self.logger.info("Orchestrator shutdown completed")

            # Close database connections
            if self.database_manager:
                await self.database_manager.close()
                self.logger.info("Database connections closed")

            self.is_running = False

            # Log shutdown duration
            shutdown_duration = (datetime.now() - self.startup_time).total_seconds()
            self.logger.info(f"Multi-agent system shutdown completed (duration: {shutdown_duration:.2f}s)")

            return True

        except Exception as e:
            self.logger.error(f"Failed to shutdown system: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            if not self.orchestrator:
                return {"status": "not_initialized"}

            status = await self.orchestrator.get_orchestrator_status()

            # Determine overall health
            overall_status = "healthy"
            health_score = 100.0

            # Check orchestrator status
            if status.get("orchestrator", {}).get("status") != "active":
                overall_status = "degraded"
                health_score -= 20

            # Check load balancer
            lb_stats = status.get("load_balancer", {})
            if lb_stats.get("unhealthy_agents", 0) > 0:
                overall_status = "degraded"
                health_score -= 10 * lb_stats.get("unhealthy_agents", 0)

            # Check failover
            failover_stats = status.get("failover", {})
            if failover_stats.get("statistics", {}).get("failed_failovers", 0) > 5:
                overall_status = "critical"
                health_score -= 30

            # Check health monitor
            health_stats = status.get("health", {})
            critical_alerts = health_stats.get("critical_alerts", 0)
            if critical_alerts > 0:
                overall_status = "critical" if critical_alerts > 3 else "degraded"
                health_score -= critical_alerts * 5

            return {
                "status": overall_status,
                "health_score": max(0, health_score),
                "components": status,
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds() if self.is_running else 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


async def main():
    """Main function to start the multi-agent system"""
    parser = argparse.ArgumentParser(description="AutoAdmin Multi-Agent Orchestration System")
    parser.add_argument("--config", type=str, help="Configuration file path")
    parser.add_argument("--environment", type=str, help="Environment (development, staging, production)")
    parser.add_argument("--port", type=int, help="API server port")
    parser.add_argument("--workers", type=int, help="Number of worker processes")
    parser.add_argument("--log-level", type=str, help="Log level")
    parser.add_argument("--health-check", action="store_true", help="Perform health check only")

    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config(args.config, args.environment)

        # Override config with command line arguments
        if args.port:
            config.setdefault("api", {})["port"] = args.port
        if args.workers:
            config.setdefault("api", {})["workers"] = args.workers
        if args.log_level:
            config.setdefault("logging", {})["level"] = args.log_level

        # Setup logging
        setup_logging(config)

        print("Starting AutoAdmin Multi-Agent Orchestration System...")
        print(f"Configuration loaded from: {args.config or 'default'}")
        print(f"Environment: {args.environment or 'default'}")
        print(f"Log level: {config.get('logging', {}).get('level', 'INFO')}")

        # Create and initialize system
        system = MultiAgentSystem(config)

        # Health check only
        if args.health_check:
            print("Performing health check...")
            await system.initialize()
            health = await system.health_check()
            print(f"Health Status: {health['status']}")
            print(f"Health Score: {health.get('health_score', 0):.1f}/100")
            if health.get('error'):
                print(f"Health Error: {health['error']}")
            return

        # Initialize system
        print("Initializing system...")
        if not await system.initialize():
            print("Failed to initialize system")
            sys.exit(1)

        # Start system
        print("Starting system...")
        if not await system.start():
            print("Failed to start system")
            sys.exit(1)

        print(f"Multi-agent system started successfully!")
        print(f"API server available at: http://{config.get('api', {}).get('host', 'localhost')}:{config.get('api', {}).get('port', 8000)}")
        print(f"API documentation available at: http://{config.get('api', {}).get('host', 'localhost')}:{config.get('api', {}).get('port', 8000)}/docs")
        print("\nPress Ctrl+C to shutdown gracefully...")

        # Keep running
        try:
            while system.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            print("Shutting down...")
            await system.shutdown()

    except KeyboardInterrupt:
        print("\nShutdown interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())