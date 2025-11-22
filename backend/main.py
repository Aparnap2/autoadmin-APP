"""
AutoAdmin Backend - Main entry point for Python deep agents
Handles task processing, communication with frontend, and agent coordination
"""

import asyncio
import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, Any, List

from dotenv import load_dotenv

# Import our agents
from agents.marketing_agent import MarketingAgent
from agents.base_agent import AgentType, TaskStatus
from communication.github_integration import GitHubActionsIntegration
from communication.webhook_handler import WebhookHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('autoadmin_backend.log')
    ]
)

logger = logging.getLogger(__name__)


class AutoAdminBackend:
    """Main backend application for AutoAdmin"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Validate required environment variables
        self.validate_environment()

        # Initialize agents
        self.agents: Dict[str, Any] = {}
        self.github_integration = None
        self.webhook_handler = None

    def validate_environment(self):
        """Validate required environment variables"""
        required_vars = [
            'OPENAI_API_KEY',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'TAVILY_API_KEY'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.info("Please set these variables in your .env file")
            sys.exit(1)

        # Optional variables
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')

        if self.github_token and self.github_repo:
            logger.info("GitHub integration enabled")
        else:
            logger.info("GitHub integration disabled (missing GITHUB_TOKEN or GITHUB_REPO)")

    async def initialize(self):
        """Initialize all backend services"""
        try:
            logger.info("Initializing AutoAdmin Backend...")

            # Initialize agents
            await self.initialize_agents()

            # Initialize GitHub Actions integration if configured
            if self.github_token and self.github_repo:
                self.github_integration = GitHubActionsIntegration(
                    token=self.github_token,
                    repo=self.github_repo,
                    supabase_url=os.getenv('SUPABASE_URL'),
                    supabase_key=os.getenv('SUPABASE_KEY')
                )
                await self.github_integration.initialize()

            # Initialize webhook handler
            self.webhook_handler = WebhookHandler(
                supabase_url=os.getenv('SUPABASE_URL'),
                supabase_key=os.getenv('SUPABASE_KEY'),
                agents=self.agents
            )
            await self.webhook_handler.initialize()

            logger.info("AutoAdmin Backend initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize backend: {e}")
            raise

    async def initialize_agents(self):
        """Initialize all agent types"""
        try:
            # Initialize Marketing Agent
            marketing_agent = MarketingAgent(
                supabase_url=os.getenv('SUPABASE_URL'),
                supabase_key=os.getenv('SUPABASE_KEY'),
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                tavily_api_key=os.getenv('TAVILY_API_KEY')
            )
            self.agents['marketing'] = marketing_agent

            # Additional agents would be initialized here:
            # - Finance Agent
            # - DevOps Agent
            # - Strategy Agent

            logger.info(f"Initialized {len(self.agents)} agents")

        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    async def start(self):
        """Start all backend services"""
        try:
            logger.info("Starting AutoAdmin Backend services...")

            # Start all agents
            agent_tasks = []
            for agent_name, agent in self.agents.items():
                logger.info(f"Starting {agent_name} agent...")
                task = asyncio.create_task(agent.start())
                agent_tasks.append(task)

            # Start GitHub integration if available
            if self.github_integration:
                logger.info("Starting GitHub Actions integration...")
                github_task = asyncio.create_task(self.github_integration.start())
                agent_tasks.append(github_task)

            # Start webhook handler
            logger.info("Starting webhook handler...")
            webhook_task = asyncio.create_task(self.webhook_handler.start())
            agent_tasks.append(webhook_task)

            # Start status monitoring
            monitor_task = asyncio.create_task(self.status_monitoring_loop())
            agent_tasks.append(monitor_task)

            logger.info("All backend services started successfully")

            # Wait for all tasks (they run indefinitely)
            await asyncio.gather(*agent_tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error starting backend services: {e}")
            raise

    async def stop(self):
        """Stop all backend services"""
        try:
            logger.info("Stopping AutoAdmin Backend services...")

            # Stop all agents
            for agent_name, agent in self.agents.items():
                logger.info(f"Stopping {agent_name} agent...")
                await agent.stop()

            # Stop GitHub integration
            if self.github_integration:
                await self.github_integration.stop()

            # Stop webhook handler
            if self.webhook_handler:
                await self.webhook_handler.stop()

            logger.info("All backend services stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping backend services: {e}")

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
    """Main entry point"""
    backend = AutoAdminBackend()

    try:
        # Initialize backend
        await backend.initialize()

        # Start backend services
        await backend.start()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Backend error: {e}")
    finally:
        # Clean shutdown
        await backend.stop()
        logger.info("AutoAdmin Backend shutdown complete")


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