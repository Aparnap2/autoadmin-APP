"""
Main entry point for AutoAdmin Deep Agents system.

This module provides the primary interface for running the hierarchical
agent system in GitHub Actions or other execution environments.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the agents directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from deep_agents.base import AgentOrchestrator, AgentType, Task, TaskStatus
from deep_agents.ceo_agent import CEOAgent
from deep_agents.strategy_agent import StrategyAgent
from deep_agents.devops_agent import DevOpsAgent
from memory.graph_memory import GraphMemory, GraphMemoryTools
from memory.virtual_filesystem import VirtualFileSystem, VirtualFileSystemTools
from tools.tavily_tools import TavilySearchTools
from tools.github_tools import GitHubTools


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoAdminAgents:
    """
    Main AutoAdmin Agents system coordinator.

    Integrates all agent types, tools, and memory systems into a cohesive
    platform that can run autonomously in GitHub Actions or other environments.
    """

    def __init__(self):
        """Initialize the AutoAdmin Agents system."""
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.graph_memory: Optional[GraphMemory] = None
        self.virtual_fs: Optional[VirtualFileSystem] = None
        self.tavily_tools: Optional[TavilySearchTools] = None
        self.github_tools: Optional[GitHubTools] = None

        # Load configuration
        self.config = self._load_configuration()

    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "supabase_url": os.getenv("SUPABASE_URL"),
            "supabase_key": os.getenv("SUPABASE_KEY"),
            "github_token": os.getenv("GITHUB_TOKEN"),
            "tavily_api_key": os.getenv("TAVILY_API_KEY"),
            "default_repo": os.getenv("GITHUB_REPO", "autoadmin-app"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "session_id": os.getenv("SESSION_ID", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        }

        # Validate required configuration
        required_keys = ["openai_api_key", "supabase_url", "supabase_key"]
        missing_keys = [key for key in required_keys if not config[key]]

        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")

        logger.info(f"Configuration loaded for session: {config['session_id']}")
        return config

    async def initialize(self) -> None:
        """Initialize all system components."""
        try:
            logger.info("Initializing AutoAdmin Agents system...")

            # Initialize memory systems
            await self._initialize_memory_systems()

            # Initialize tools
            await self._initialize_tools()

            # Initialize agents
            await self._initialize_agents()

            # Build and compile agent graph
            await self._build_agent_graph()

            logger.info("AutoAdmin Agents system initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing system: {str(e)}")
            raise

    async def _initialize_memory_systems(self) -> None:
        """Initialize graph memory and virtual file system."""
        logger.info("Initializing memory systems...")

        # Initialize graph memory
        self.graph_memory = GraphMemory(
            supabase_url=self.config["supabase_url"],
            supabase_key=self.config["supabase_key"],
            openai_api_key=self.config["openai_api_key"]
        )

        # Initialize virtual file system
        self.virtual_fs = VirtualFileSystem(
            supabase_url=self.config["supabase_url"],
            supabase_key=self.config["supabase_key"]
        )

        logger.info("Memory systems initialized")

    async def _initialize_tools(self) -> None:
        """Initialize agent tools."""
        logger.info("Initializing tools...")

        # Initialize Tavily search tools if API key is provided
        if self.config.get("tavily_api_key"):
            self.tavily_tools = TavilySearchTools(api_key=self.config["tavily_api_key"])
            logger.info("Tavily search tools initialized")
        else:
            logger.warning("Tavily API key not provided - search features limited")

        # Initialize GitHub tools if token is provided
        if self.config.get("github_token"):
            self.github_tools = GitHubTools(token=self.config["github_token"])
            logger.info("GitHub tools initialized")
        else:
            logger.warning("GitHub token not provided - GitHub features limited")

    async def _initialize_agents(self) -> None:
        """Initialize all agent types."""
        logger.info("Initializing agents...")

        # Create tool collections for each agent
        all_tools = []

        # Add memory tools
        if self.graph_memory:
            memory_tools = GraphMemoryTools(self.graph_memory)
            all_tools.extend([
                memory_tools.store_memory,
                memory_tools.recall_memory,
                memory_tools.connect_memories
            ])

        # Add file system tools
        if self.virtual_fs:
            fs_tools = VirtualFileSystemTools(self.virtual_fs)
            all_tools.extend([
                fs_tools.save_document,
                fs_tools.load_document,
                fs_tools.list_workspace,
                fs_tools.workspace_stats
            ])

        # Create CEO agent
        ceo_agent = CEOAgent(tools=all_tools)

        # Create Strategy agent with search tools
        strategy_tools = all_tools.copy()
        if self.tavily_tools:
            strategy_tools.extend([
                self.tavily_tools.search_market_trends,
                self.tavily_tools.search_competitors,
                self.tavily_tools.search_technology_trends,
                self.tavily_tools.search_content_ideas,
                self.tavily_tools.comprehensive_research
            ])

        strategy_agent = StrategyAgent(
            tavily_tools=self.tavily_tools,
            tools=strategy_tools
        )

        # Create DevOps agent with GitHub tools
        devops_tools = all_tools.copy()
        if self.github_tools:
            devops_tools.extend([
                self.github_tools.get_repository_info,
                self.github_tools.create_branch,
                self.github_tools.create_file,
                self.github_tools.create_pull_request,
                self.github_tools.get_pull_requests,
                self.github_tools.create_issue,
                self.github_tools.analyze_code_structure
            ])

        devops_agent = DevOpsAgent(
            github_tools=self.github_tools,
            tools=devops_tools
        )

        # Initialize orchestrator
        self.orchestrator = AgentOrchestrator(
            supabase_url=self.config["supabase_url"],
            supabase_key=self.config["supabase_key"],
            openai_api_key=self.config["openai_api_key"],
            github_token=self.config.get("github_token"),
            tavily_api_key=self.config.get("tavily_api_key")
        )

        # Register agents
        self.orchestrator.register_agent(ceo_agent)
        self.orchestrator.register_agent(strategy_agent)
        self.orchestrator.register_agent(devops_agent)

        logger.info("All agents initialized and registered")

    async def _build_agent_graph(self) -> None:
        """Build and compile the agent execution graph."""
        logger.info("Building agent execution graph...")
        await self.orchestrator.compile_graph()
        logger.info("Agent execution graph built and compiled")

    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a message through the agent system.

        Args:
            message: Input message to process
            context: Optional context information

        Returns:
            Response from the agent system
        """
        if not self.orchestrator:
            raise RuntimeError("System not initialized. Call initialize() first.")

        logger.info(f"Processing message: {message[:100]}...")

        try:
            result = await self.orchestrator.process_message(
                message=message,
                session_id=self.config["session_id"]
            )

            logger.info("Message processed successfully")
            return result

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": f"Error processing message: {str(e)}",
                "session_id": self.config["session_id"],
                "error": True
            }

    async def run_proactive_analysis(self) -> Dict[str, Any]:
        """
        Run proactive analysis and generate insights.

        Returns:
            Analysis results and recommendations
        """
        if not self.orchestrator:
            raise RuntimeError("System not initialized. Call initialize() first.")

        logger.info("Running proactive analysis...")

        # Trigger proactive analysis with a special message
        message = "Run your daily proactive analysis and generate strategic insights"
        result = await self.process_message(message)

        logger.info("Proactive analysis completed")
        return result

    async def create_task(
        self,
        task_type: AgentType,
        description: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a task for a specific agent.

        Args:
            task_type: Type of agent to assign task to
            description: Task description
            parameters: Additional task parameters

        Returns:
            Task result
        """
        task_message = f"""
Please execute the following {task_type.value} task:

Description: {description}

Parameters: {json.dumps(parameters or {}, indent=2)}

Please analyze the requirements and execute the task using your specialized capabilities.
"""

        result = await self.process_message(task_message)
        return result.get("response", "No response generated")

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent system.

        Returns:
            System status information
        """
        if not self.orchestrator:
            return {"status": "not_initialized"}

        status = await self.orchestrator.get_agent_status()

        # Add memory system status
        if self.graph_memory:
            # This would normally query the actual memory systems
            status["memory_systems"] = {
                "graph_memory": "connected",
                "virtual_filesystem": "connected"
            }

        # Add tools status
        status["tools"] = {
            "tavily_search": "available" if self.tavily_tools else "unavailable",
            "github_integration": "available" if self.github_tools else "unavailable"
        }

        return {
            "system_id": self.config["session_id"],
            "initialized": True,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }

    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        logger.info("Cleaning up AutoAdmin Agents system...")

        # Clear file system cache
        if self.virtual_fs:
            self.virtual_fs.clear_cache()

        # Close any open connections
        # (This would be implemented based on specific requirements)

        logger.info("System cleanup completed")


async def main():
    """Main function for running the agent system."""
    import argparse

    parser = argparse.ArgumentParser(description="AutoAdmin Deep Agents System")
    parser.add_argument("--mode", choices=["interactive", "proactive", "task"], default="proactive",
                       help="Execution mode")
    parser.add_argument("--message", type=str, help="Message to process (for interactive mode)")
    parser.add_argument("--task-type", choices=["ceo", "strategy", "devops"], help="Task type")
    parser.add_argument("--task-description", type=str, help="Task description")
    parser.add_argument("--output", type=str, help="Output file for results")

    args = parser.parse_args()

    # Initialize the system
    agents = AutoAdminAgents()
    await agents.initialize()

    try:
        if args.mode == "interactive":
            if not args.message:
                print("Error: --message is required for interactive mode")
                return

            result = await agents.process_message(args.message)
            print(json.dumps(result, indent=2))

        elif args.mode == "proactive":
            print("Running proactive analysis...")
            result = await agents.run_proactive_analysis()
            print(json.dumps(result, indent=2))

        elif args.mode == "task":
            if not args.task_type or not args.task_description:
                print("Error: --task-type and --task-description are required for task mode")
                return

            task_type = AgentType(args.task_type)
            result = await agents.create_task(task_type, args.task_description)
            print(result)

        # Save results to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to: {args.output}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

    finally:
        await agents.cleanup()

    return 0


if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)