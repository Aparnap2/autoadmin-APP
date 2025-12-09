"""
Agent Orchestrator - Central coordinator for the AutoAdmin agent swarm
Manages task delegation, inter-agent communication, and workflow orchestration
Enhanced with load balancing, failover, and comprehensive health monitoring
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from uuid import uuid4

from langgraph.graph import StateGraph, END
from typing import Any as CompiledGraph  # Temporary fix
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from .ceo_agent import CEOAgent
from .strategy_agent import StrategyAgent
from .devops_agent import DevOpsAgent
from .load_balancer import get_load_balancer, AgentStatus
from .failover_manager import get_failover_manager
from .health_monitor import get_health_monitor, HealthStatus

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(Enum):
    """Task status tracking"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task representation for agent swarm"""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    parent_task: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "dependencies": self.dependencies,
            "subtasks": self.subtasks,
            "parent_task": self.parent_task,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class SwarmState:
    """State object for LangGraph workflow"""
    messages: List[BaseMessage] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    active_tasks: Dict[str, Task] = field(default_factory=dict)
    completed_tasks: Dict[str, Task] = field(default_factory=dict)
    current_task: Optional[Task] = None
    agent_responses: Dict[str, Any] = field(default_factory=dict)
    workflow_status: str = "idle"
    error: Optional[str] = None


class AgentOrchestrator:
    """Central orchestrator for the AutoAdmin agent swarm"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize agents
        self.ceo = CEOAgent(config.get("ceo", {}))
        self.strategy = StrategyAgent(config.get("strategy", {}))
        self.devops = DevOpsAgent(config.get("devops", {}))

        self.agents = {
            "ceo": self.ceo,
            "strategy": self.strategy,
            "devops": self.devops,
        }

        # Task management
        self.tasks: Dict[str, Task] = {}
        self.active_workflows: Dict[str, CompiledGraph] = {}

        # Agent capabilities mapping
        self.agent_capabilities = {
            "ceo": ["strategic_planning", "decision_making", "coordination", "oversight"],
            "strategy": ["market_analysis", "financial_planning", "business_strategy", "competitive_analysis"],
            "devops": ["technical_implementation", "system_architecture", "deployment", "monitoring"],
        }

        # Enhanced orchestration components
        self.load_balancer = None
        self.failover_manager = None
        self.health_monitor = None

        # Orchestration metrics
        self.orchestrator_metrics = {
            "tasks_processed": 0,
            "tasks_successful": 0,
            "tasks_failed": 0,
            "average_processing_time": 0.0,
            "load_balancer_utilization": 0.0,
            "failover_events": 0,
            "health_checks_passed": 0,
            "health_checks_failed": 0
        }

        # Build the workflow graph
        self.workflow = self._build_workflow_graph()

        self.logger.info("Agent Orchestrator initialized with 3 agents")

    async def initialize(self):
        """Initialize orchestration components"""
        try:
            self.logger.info("Initializing orchestrator components...")

            # Initialize load balancer
            load_balancer_config = self.config.get("load_balancer", {})
            self.load_balancer = await get_load_balancer(load_balancer_config)

            # Initialize failover manager
            failover_config = self.config.get("failover", {})
            self.failover_manager = await get_failover_manager(failover_config)

            # Initialize health monitor
            health_config = self.config.get("health_monitor", {})
            self.health_monitor = await get_health_monitor(health_config)

            # Register agents with load balancer
            await self._register_agents_with_load_balancer()

            # Start orchestration monitoring
            asyncio.create_task(self._orchestration_monitoring_loop())

            self.logger.info("Orchestrator components initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator components: {e}")
            return False

    async def shutdown(self):
        """Shutdown orchestrator gracefully"""
        try:
            self.logger.info("Shutting down orchestrator...")

            # Stop health monitoring
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()

            self.logger.info("Orchestrator shutdown completed")

        except Exception as e:
            self.logger.error(f"Failed to shutdown orchestrator: {e}")

    async def process_task_with_failover(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task with comprehensive failover and load balancing"""
        try:
            task_id = task_input.get("id", str(uuid.uuid4()))
            self.orchestrator_metrics["tasks_processed"] += 1

            start_time = datetime.now()

            # Determine task requirements
            task_requirements = self._analyze_task_requirements(task_input)

            # Use load balancer to assign task to best agent
            assigned_agent_id = await self.load_balancer.assign_task({
                **task_input,
                "type": task_requirements.get("agent_type", "general"),
                "capabilities_required": task_requirements.get("capabilities", []),
                "priority": task_input.get("priority", "medium")
            })

            if not assigned_agent_id:
                # No available agents, trigger failover
                self.logger.warning(f"No available agents for task {task_id}, attempting failover")
                return await self._handle_task_failover(task_input, task_requirements)

            # Execute task with monitoring
            result = await self._execute_task_with_monitoring(
                assigned_agent_id, task_input, task_requirements
            )

            # Update orchestrator metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            await self._update_orchestrator_metrics(result, processing_time)

            return result

        except Exception as e:
            self.logger.error(f"Failed to process task with failover: {e}")
            await self._handle_orchestrator_error(e, task_input)
            return {
                "success": False,
                "error": str(e),
                "error_type": "orchestration_failure",
                "timestamp": datetime.now().isoformat(),
            }

    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        try:
            status = {
                "orchestrator": {
                    "status": "active",
                    "metrics": self.orchestrator_metrics,
                    "timestamp": datetime.now().isoformat(),
                },
                "load_balancer": await self.load_balancer.get_load_balancer_stats() if self.load_balancer else None,
                "failover": await self.failover_manager.get_failover_status() if self.failover_manager else None,
                "health": await self.health_monitor.get_system_health() if self.health_monitor else None,
                "agents": await self.get_enhanced_agent_status()
            }

            return status

        except Exception as e:
            self.logger.error(f"Failed to get orchestrator status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def trigger_manual_failover(self, agent_type: str, reason: str) -> bool:
        """Trigger manual failover for agent type"""
        try:
            self.logger.info(f"Manual failover triggered for {agent_type}: {reason}")

            if self.failover_manager:
                # Get agent IDs for this type
                agent_ids = [
                    agent_id for agent_id, agent in self.agents.items()
                    if agent_id.startswith(agent_type)
                ]

                for agent_id in agent_ids:
                    success = await self.failover_manager.trigger_manual_failover(agent_id, reason)
                    if not success:
                        self.logger.error(f"Manual failover failed for agent {agent_id}")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to trigger manual failover: {e}")
            return False

    async def _register_agents_with_load_balancer(self):
        """Register all agents with the load balancer"""
        try:
            agent_configs = {
                "ceo": {
                    "capabilities": ["strategic_planning", "decision_making", "coordination", "oversight"],
                    "max_concurrent_tasks": 3,
                    "weight": 1.0
                },
                "strategy": {
                    "capabilities": ["market_analysis", "financial_planning", "business_strategy"],
                    "max_concurrent_tasks": 5,
                    "weight": 0.9
                },
                "devops": {
                    "capabilities": ["technical_implementation", "system_architecture", "deployment"],
                    "max_concurrent_tasks": 5,
                    "weight": 0.9
                }
            }

            for agent_id, config in agent_configs.items():
                await self.load_balancer.register_agent(
                    agent_id,
                    agent_id,
                    config["capabilities"],
                    config["max_concurrent_tasks"],
                    config["weight"]
                )

            self.logger.info("Agents registered with load balancer")

        except Exception as e:
            self.logger.error(f"Failed to register agents with load balancer: {e}")

    async def _execute_task_with_monitoring(self, agent_id: str, task_input: Dict[str, Any],
                                           task_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task with comprehensive monitoring"""
        try:
            start_time = datetime.now()

            # Get appropriate agent instance
            agent_instance = self._get_agent_instance(agent_id)
            if not agent_instance:
                raise Exception(f"Agent instance not found: {agent_id}")

            # Execute task
            if agent_id.startswith("ceo"):
                result = await agent_instance.process_task({
                    "messages": [HumanMessage(content=task_input.get("message", ""))],
                    "selected_agents": task_requirements.get("selected_agents", ["ceo"]),
                    "task_analysis": task_requirements.get("task_analysis", {}),
                })
            else:
                result = await agent_instance.process_task({
                    "messages": [HumanMessage(content=task_input.get("message", ""))],
                    "ceo_guidance": task_requirements.get("ceo_guidance", {}),
                    "task_analysis": task_requirements.get("task_analysis", {}),
                })

            processing_time = (datetime.now() - start_time).total_seconds()

            # Update load balancer with task completion
            success = result.get("success", True)
            await self.load_balancer.complete_task(
                task_input.get("id", ""),
                success,
                processing_time * 1000  # Convert to milliseconds
            )

            # Update orchestrator metrics
            if success:
                self.orchestrator_metrics["tasks_successful"] += 1
            else:
                self.orchestrator_metrics["tasks_failed"] += 1
                # Handle task failure with failover
                await self._handle_task_failure(agent_id, task_input, result)

            return result

        except Exception as e:
            self.logger.error(f"Failed to execute task with monitoring: {e}")

            # Update load balancer with failure
            await self.load_balancer.complete_task(
                task_input.get("id", ""),
                False,
                0
            )

            # Attempt failover
            return await self._handle_task_failover(task_input, task_requirements)

    async def _handle_task_failover(self, task_input: Dict[str, Any], task_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task failover"""
        try:
            self.orchestrator_metrics["failover_events"] += 1

            # Check if failover manager has available standby agents
            agent_type = task_requirements.get("agent_type", "general")

            # For now, return a failover response
            # In production, this would activate standby agents and retry
            return {
                "success": False,
                "error": "Task execution failed, failover attempted but no standby available",
                "error_type": "failover_unavailable",
                "original_task": task_input,
                "failover_attempted": True,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to handle task failover: {e}")
            return {
                "success": False,
                "error": f"Failover failed: {str(e)}",
                "error_type": "failover_failure",
                "timestamp": datetime.now().isoformat(),
            }

    async def _handle_task_failure(self, agent_id: str, task_input: Dict[str, Any], result: Dict[str, Any]):
        """Handle task failure and trigger failover if needed"""
        try:
            self.logger.warning(f"Task failed on agent {agent_id}: {result.get('error', 'Unknown error')}")

            # Trigger failover for critical failures
            if result.get("success", False) is False and self.failover_manager:
                await self.failover_manager.handle_agent_failure(
                    agent_id,
                    "task_execution_failure",
                    result.get("error", "Task execution failed")
                )

        except Exception as e:
            self.logger.error(f"Failed to handle task failure: {e}")

    async def _handle_orchestrator_error(self, error: Exception, task_input: Dict[str, Any]):
        """Handle orchestrator-level errors"""
        try:
            self.logger.error(f"Orchestrator error: {error}")

            # Record error metrics
            if self.health_monitor:
                await self.health_monitor.create_health_alert(
                    "orchestrator",
                    "error_rate",
                    "error" if isinstance(error, Exception) else "critical",
                    f"Orchestrator error: {str(error)}",
                    1.0,
                    0.1
                )

        except Exception as e:
            self.logger.error(f"Failed to handle orchestrator error: {e}")

    def _analyze_task_requirements(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task requirements and determine optimal agent"""
        try:
            message = task_input.get("message", "").lower()

            requirements = {
                "agent_type": "general",
                "capabilities": [],
                "priority": task_input.get("priority", "medium")
            }

            # Determine agent type and capabilities based on content
            if any(word in message for word in ["analyze", "research", "market", "competition", "financial"]):
                requirements["agent_type"] = "strategy"
                requirements["capabilities"].extend(["market_analysis", "financial_planning"])

            if any(word in message for word in ["build", "deploy", "implement", "system", "technical"]):
                requirements["agent_type"] = "devops"
                requirements["capabilities"].extend(["technical_implementation", "system_architecture"])

            if any(word in message for word in ["decide", "plan", "coordinate", "oversee", "strategic"]):
                requirements["agent_type"] = "ceo"
                requirements["capabilities"].extend(["strategic_planning", "decision_making"])

            return requirements

        except Exception as e:
            self.logger.error(f"Failed to analyze task requirements: {e}")
            return {"agent_type": "general", "capabilities": []}

    def _get_agent_instance(self, agent_id: str):
        """Get agent instance by ID"""
        if agent_id.startswith("ceo"):
            return self.ceo
        elif agent_id.startswith("strategy"):
            return self.strategy
        elif agent_id.startswith("devops"):
            return self.devops
        return None

    async def _update_orchestrator_metrics(self, result: Dict[str, Any], processing_time: float):
        """Update orchestrator metrics"""
        try:
            # Update average processing time
            if self.orchestrator_metrics["tasks_processed"] > 0:
                current_avg = self.orchestrator_metrics["average_processing_time"]
                weight = 0.9  # Exponential moving average
                self.orchestrator_metrics["average_processing_time"] = (
                    current_avg * weight + processing_time * (1 - weight)
                )

            # Update load balancer utilization if available
            if self.load_balancer:
                stats = await self.load_balancer.get_load_balancer_stats()
                if "load_percentage" in stats:
                    self.orchestrator_metrics["load_balancer_utilization"] = stats["load_percentage"]

        except Exception as e:
            self.logger.error(f"Failed to update orchestrator metrics: {e}")

    async def _orchestration_monitoring_loop(self):
        """Main orchestration monitoring loop"""
        while True:
            try:
                # Perform periodic health checks
                if self.health_monitor:
                    system_health = await self.health_monitor.get_system_health()

                    # Update health check metrics
                    critical_count = system_health.get("critical_alerts", 0)
                    if critical_count > 0:
                        self.orchestrator_metrics["health_checks_failed"] += 1
                    else:
                        self.orchestrator_metrics["health_checks_passed"] += 1

                # Monitor load balancer health
                if self.load_balancer:
                    load_balancer_stats = await self.load_balancer.get_load_balancer_stats()
                    unhealthy_count = load_balancer_stats.get("unhealthy_agents", 0)

                    if unhealthy_count > 0:
                        self.logger.warning(f"Found {unhealthy_count} unhealthy agents")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Orchestration monitoring error: {e}")
                await asyncio.sleep(60)

    async def get_enhanced_agent_status(self) -> Dict[str, Any]:
        """Get enhanced status for all agents"""
        try:
            status = {}

            # Get status from original orchestrator
            original_status = await self.get_agent_status()

            # Enhance with load balancer data
            if self.load_balancer:
                load_balancer_stats = await self.load_balancer.get_load_balancer_stats()

                for agent_id, agent_info in original_status.get("agents", {}).items():
                    load_balancer_info = load_balancer_stats.get("agents", {}).get(agent_id, {})

                    status[agent_id] = {
                        **agent_info,
                        "load_balancer_info": load_balancer_info,
                        "health_status": await self.health_monitor.check_agent_health(agent_id) if self.health_monitor else None
                    }

            return status

        except Exception as e:
            self.logger.error(f"Failed to get enhanced agent status: {e}")
            return {"error": str(e)}

    def _build_workflow_graph(self) -> CompiledGraph:
        """Build the LangGraph workflow for agent coordination"""

        # Create the graph
        workflow = StateGraph(SwarmState)

        # Add nodes for each agent and orchestration steps
        workflow.add_node("task_analysis", self._analyze_task)
        workflow.add_node("agent_selection", self._select_agent)
        workflow.add_node("ceo_review", self._ceo_review)
        workflow.add_node("strategy_execution", self._execute_strategy)
        workflow.add_node("devops_execution", self._execute_devops)
        workflow.add_node("result_synthesis", self._synthesize_results)
        workflow.add_node("final_review", self._final_review)

        # Define the workflow edges
        workflow.set_entry_point("task_analysis")

        workflow.add_edge("task_analysis", "agent_selection")
        workflow.add_edge("agent_selection", "ceo_review")

        # Conditional routing based on task type
        workflow.add_conditional_edges(
            "ceo_review",
            self._route_to_execution_agent,
            {
                "strategy": "strategy_execution",
                "devops": "devops_execution",
                "ceo": "final_review"
            }
        )

        workflow.add_edge("strategy_execution", "result_synthesis")
        workflow.add_edge("devops_execution", "result_synthesis")
        workflow.add_edge("result_synthesis", "final_review")
        workflow.add_edge("final_review", END)

        # Compile the graph
        return workflow.compile()  # type: ignore

    async def _analyze_task(self, state: SwarmState) -> SwarmState:
        """Analyze incoming task and determine requirements"""
        if not state.messages:
            state.error = "No messages provided"
            return state

        latest_message = state.messages[-1]

        task_analysis = {
            "complexity": "medium",
            "required_capabilities": [],
            "estimated_duration": 30,
            "dependencies": [],
        }

        # Analyze task complexity and requirements
        if isinstance(latest_message, HumanMessage):
            content = latest_message.content.lower()

            # Determine required capabilities
            if any(word in content for word in ["analyze", "research", "market", "competition", "financial"]):
                task_analysis["required_capabilities"].append("strategy")

            if any(word in content for word in ["build", "deploy", "implement", "system", "technical"]):
                task_analysis["required_capabilities"].append("devops")

            if any(word in content for word in ["decide", "plan", "coordinate", "oversee"]):
                task_analysis["required_capabilities"].append("ceo")

            # Estimate complexity
            if any(word in content for word in ["urgent", "critical", "emergency"]):
                task_analysis["complexity"] = "high"
            elif any(word in content for word in ["simple", "quick", "easy"]):
                task_analysis["complexity"] = "low"

        # Store analysis in state
        state.agent_responses["task_analysis"] = task_analysis

        self.logger.info(f"Task analysis completed: {task_analysis}")
        return state

    async def _select_agent(self, state: SwarmState) -> SwarmState:
        """Select appropriate agent(s) for the task"""
        task_analysis = state.agent_responses.get("task_analysis", {})
        required_capabilities = task_analysis.get("required_capabilities", [])

        selected_agents = []

        # Primary agent selection based on capabilities
        for capability in required_capabilities:
            for agent_name, agent_capabilities in self.agent_capabilities.items():
                if capability in agent_capabilities and agent_name not in selected_agents:
                    selected_agents.append(agent_name)

        # Default to CEO if no specific capabilities required
        if not selected_agents:
            selected_agents = ["ceo"]

        state.agent_responses["selected_agents"] = selected_agents

        self.logger.info(f"Selected agents: {selected_agents}")
        return state

    async def _ceo_review(self, state: SwarmState) -> SwarmState:
        """CEO agent reviews and delegates the task"""
        selected_agents = state.agent_responses.get("selected_agents", ["ceo"])

        # CEO review and strategic oversight
        ceo_response = await self.ceo.process_task({
            "messages": state.messages,
            "selected_agents": selected_agents,
            "task_analysis": state.agent_responses.get("task_analysis", {}),
        })

        state.agent_responses["ceo_review"] = ceo_response

        # Determine next step based on CEO decision
        if len(selected_agents) == 1 and selected_agents[0] == "ceo":
            return {**state, "workflow_status": "ceo_direct"}
        elif "strategy" in selected_agents:
            return {**state, "workflow_status": "route_strategy"}
        elif "devops" in selected_agents:
            return {**state, "workflow_status": "route_devops"}
        else:
            return {**state, "workflow_status": "route_ceo"}

    def _route_to_execution_agent(self, state: SwarmState) -> str:
        """Route to the appropriate execution agent"""
        workflow_status = state.workflow_status

        if workflow_status == "route_strategy":
            return "strategy"
        elif workflow_status == "route_devops":
            return "devops"
        else:
            return "final_review"

    async def _execute_strategy(self, state: SwarmState) -> SwarmState:
        """Strategy agent executes the task"""
        strategy_response = await self.strategy.process_task({
            "messages": state.messages,
            "ceo_guidance": state.agent_responses.get("ceo_review", {}),
            "task_analysis": state.agent_responses.get("task_analysis", {}),
        })

        state.agent_responses["strategy_result"] = strategy_response
        return state

    async def _execute_devops(self, state: SwarmState) -> SwarmState:
        """DevOps agent executes the task"""
        devops_response = await self.devops.process_task({
            "messages": state.messages,
            "ceo_guidance": state.agent_responses.get("ceo_review", {}),
            "task_analysis": state.agent_responses.get("task_analysis", {}),
        })

        state.agent_responses["devops_result"] = devops_response
        return state

    async def _synthesize_results(self, state: SwarmState) -> SwarmState:
        """Synthesize results from execution agents"""
        results = {}

        # Collect results from execution agents
        if "strategy_result" in state.agent_responses:
            results["strategy"] = state.agent_responses["strategy_result"]

        if "devops_result" in state.agent_responses:
            results["devops"] = state.agent_responses["devops_result"]

        # Synthesize a comprehensive response
        synthesis = {
            "summary": "Task completed with agent collaboration",
            "results": results,
            "recommendations": [],
            "next_steps": [],
        }

        # Generate recommendations based on results
        for agent, result in results.items():
            if isinstance(result, dict) and "recommendations" in result:
                synthesis["recommendations"].extend(result["recommendations"])

            if isinstance(result, dict) and "next_steps" in result:
                synthesis["next_steps"].extend(result["next_steps"])

        state.agent_responses["synthesis"] = synthesis

        self.logger.info("Results synthesized successfully")
        return state

    async def _final_review(self, state: SwarmState) -> SwarmState:
        """CEO provides final review and approval"""
        synthesis = state.agent_responses.get("synthesis", {})

        final_response = await self.ceo.final_review({
            "synthesis": synthesis,
            "original_task": state.messages[-1].content if state.messages else "",
            "agent_contributions": {
                agent: state.agent_responses.get(f"{agent}_result")
                for agent in ["strategy", "devops"]
                if f"{agent}_result" in state.agent_responses
            }
        })

        state.agent_responses["final_result"] = final_response
        state.workflow_status = "completed"

        self.logger.info("Final review completed")
        return state

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task through the agent swarm"""
        try:
            # Create initial state
            initial_state = SwarmState(
                messages=[HumanMessage(content=task_input.get("message", ""))],
                workflow_status="started"
            )

            # Execute the workflow
            result = await self.workflow.ainvoke(initial_state)

            # Return the final result
            return {
                "success": True,
                "result": result.agent_responses.get("final_result", {}),
                "workflow_steps": {
                    "task_analysis": result.agent_responses.get("task_analysis"),
                    "selected_agents": result.agent_responses.get("selected_agents"),
                    "synthesis": result.agent_responses.get("synthesis"),
                },
                "status": result.workflow_status,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error processing task: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            }

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents in the swarm"""
        status = {}

        for agent_name, agent in self.agents.items():
            status[agent_name] = {
                "name": agent.name,
                "type": agent.__class__.__name__,
                "capabilities": self.agent_capabilities.get(agent_name, []),
                "status": "active",
            }

        return {
            "orchestrator": "active",
            "agents": status,
            "total_tasks": len(self.tasks),
            "active_workflows": len(self.active_workflows),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the orchestrator and all agents"""
        health = {
            "orchestrator": {"status": "healthy", "agents": len(self.agents)},
            "agents": {},
            "timestamp": datetime.now().isoformat(),
        }

        for agent_name, agent in self.agents.items():
            try:
                agent_health = await agent.health_check()
                health["agents"][agent_name] = agent_health
            except Exception as e:
                health["agents"][agent_name] = {"status": "unhealthy", "error": str(e)}

        return health