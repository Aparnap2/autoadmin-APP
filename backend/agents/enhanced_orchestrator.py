"""
Enhanced Agent Orchestrator - Improved orchestrator with proper LLM integration
Manages task delegation, inter-agent communication, and workflow orchestration
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from uuid import uuid4

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from agents.enhanced_ceo_agent import EnhancedCEOAgent
from agents.enhanced_strategy_agent import EnhancedStrategyAgent
from agents.enhanced_devops_agent import EnhancedDevOpsAgent

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


class EnhancedAgentOrchestrator:
    """Enhanced orchestrator with proper LLM integration"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Setup detailed logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

        # Initialize enhanced agents
        try:
            self.logger.info("Initializing enhanced agents...")
            self.ceo = EnhancedCEOAgent(config.get("ceo", {}))
            self.strategy = EnhancedStrategyAgent(config.get("strategy", {}))
            self.devops = EnhancedDevOpsAgent(config.get("devops", {}))

            self.agents = {
                "ceo": self.ceo,
                "strategy": self.strategy,
                "devops": self.devops,
            }

            self.logger.info("Enhanced agents initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced agents: {e}")
            raise

        # Task management
        self.tasks: Dict[str, Task] = {}
        self.active_workflows: Dict[str, Any] = {}

        # Agent capabilities mapping
        self.agent_capabilities = {
            "ceo": [
                "strategic_planning", "decision_making", "coordination",
                "oversight", "business_analysis", "resource_allocation"
            ],
            "strategy": [
                "market_research", "financial_planning", "business_strategy",
                "competitive_analysis", "growth_planning", "risk_assessment"
            ],
            "devops": [
                "technical_implementation", "system_architecture", "deployment",
                "monitoring", "security", "infrastructure_design"
            ],
        }

        # Orchestrator metrics
        self.orchestrator_metrics = {
            "tasks_processed": 0,
            "tasks_successful": 0,
            "tasks_failed": 0,
            "average_processing_time": 0.0,
            "agent_utilization": {"ceo": 0, "strategy": 0, "devops": 0},
            "workflow_completions": 0
        }

        # Build the workflow graph
        try:
            self.workflow = self._build_workflow_graph()
            self.logger.info("LangGraph workflow built successfully")
        except Exception as e:
            self.logger.error(f"Failed to build workflow: {e}")
            self.workflow = None

        self.logger.info("Enhanced Agent Orchestrator initialized with 3 enhanced agents")

    async def process_task_with_failover(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task with enhanced error handling and fallbacks"""
        task_id = task_input.get("id", str(uuid.uuid4()))
        start_time = datetime.now()

        self.logger.info(f"[Orchestrator] Processing task {task_id}: {task_input.get('message', '')[:100]}...")
        self.logger.debug(f"[Orchestrator] Task input details: {task_input}")

        try:
            # Update metrics
            self.orchestrator_metrics["tasks_processed"] += 1

            # Use LangGraph workflow if available
            if self.workflow:
                self.logger.debug("[Orchestrator] Using LangGraph workflow")
                result = await self._process_with_langgraph(task_input)
            else:
                self.logger.warning("[Orchestrator] LangGraph not available, using direct agent routing")
                result = await self._process_direct_routing(task_input)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time

            # Update metrics
            if result.get("success", False):
                self.orchestrator_metrics["tasks_successful"] += 1
                self.logger.info(f"[Orchestrator] Task {task_id} completed successfully in {processing_time:.2f}s")
            else:
                self.orchestrator_metrics["tasks_failed"] += 1
                self.logger.error(f"[Orchestrator] Task {task_id} failed: {result.get('error', 'Unknown error')}")

            # Update average processing time
            weight = 0.9
            self.orchestrator_metrics["average_processing_time"] = (
                self.orchestrator_metrics["average_processing_time"] * weight +
                processing_time * (1 - weight)
            )

            return result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Orchestrator processing failed: {str(e)}"

            self.logger.error(f"[Orchestrator] {error_msg}", exc_info=True)

            # Update metrics
            self.orchestrator_metrics["tasks_failed"] += 1

            return {
                "success": False,
                "error": error_msg,
                "error_type": "orchestration_failure",
                "task_id": task_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
            }

    async def _process_with_langgraph(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process task using LangGraph workflow"""
        try:
            # Create initial state
            initial_state = SwarmState(
                messages=[HumanMessage(content=task_input.get("message", ""))],
                workflow_status="started"
            )

            # Execute the workflow
            self.logger.debug("[Orchestrator] Executing LangGraph workflow...")
            result = await self.workflow.ainvoke(initial_state)

            # Extract final result
            final_result = result.agent_responses.get("final_result", {})

            return {
                "success": True,
                "result": final_result,
                "summary": final_result.get("assessment", "Task completed successfully"),
                "workflow_steps": {
                    "task_analysis": result.agent_responses.get("task_analysis"),
                    "selected_agents": result.agent_responses.get("selected_agents"),
                    "synthesis": result.agent_responses.get("synthesis"),
                },
                "status": result.workflow_status,
                "agent_responses": result.agent_responses,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"[Orchestrator] LangGraph workflow failed: {e}")
            # Fallback to direct routing
            return await self._process_direct_routing(task_input)

    async def _process_direct_routing(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process task with direct agent routing (fallback)"""
        try:
            # Determine primary agent
            agent_id = self._route_to_agent(task_input.get("message", ""))
            self.logger.info(f"[Orchestrator] Routing to {agent_id} agent")

            # Get agent instance
            agent = self.agents.get(agent_id)
            if not agent:
                raise Exception(f"Agent {agent_id} not found")

            # Update agent utilization
            self.orchestrator_metrics["agent_utilization"][agent_id] += 1

            # Process task with agent
            agent_result = await agent.process_task(task_input)

            # Format response
            return {
                "success": agent_result.get("success", False),
                "result": {
                    "agent": agent_id,
                    "response": agent_result.get("response", ""),
                    "metadata": agent_result.get("metadata", {}),
                },
                "summary": agent_result.get("response", "")[:200] + "...",
                "routing": {
                    "primary_agent": agent_id,
                    "routing_method": "direct"
                },
                "agent_responses": {agent_id: agent_result},
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"[Orchestrator] Direct routing failed: {e}")
            return {
                "success": False,
                "error": f"Direct routing failed: {str(e)}",
                "routing": {
                    "primary_agent": None,
                    "routing_method": "direct",
                    "error": str(e)
                },
                "timestamp": datetime.now().isoformat(),
            }

    def _route_to_agent(self, message: str) -> str:
        """Route message to appropriate agent based on content"""
        message_lower = message.lower()

        # CEO routing keywords
        ceo_keywords = [
            "decide", "decision", "plan", "coordinate", "oversee",
            "strategic", "approve", "review", "lead", "manage"
        ]

        # Strategy routing keywords
        strategy_keywords = [
            "market", "analyze", "research", "financial", "budget",
            "competition", "growth", "strategy", "roi", "investment"
        ]

        # DevOps routing keywords
        devops_keywords = [
            "build", "deploy", "implement", "system", "technical",
            "architecture", "code", "infrastructure", "security", "monitor"
        ]

        # Count keyword matches
        ceo_score = sum(1 for kw in ceo_keywords if kw in message_lower)
        strategy_score = sum(1 for kw in strategy_keywords if kw in message_lower)
        devops_score = sum(1 for kw in devops_keywords if kw in message_lower)

        # Determine best match
        if ceo_score > strategy_score and ceo_score > devops_score:
            return "ceo"
        elif strategy_score > devops_score:
            return "strategy"
        elif devops_score > 0:
            return "devops"
        else:
            # Default to CEO for general queries
            return "ceo"

    def _build_workflow_graph(self) -> Any:
        """Build the LangGraph workflow for agent coordination"""
        try:
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
            return workflow.compile()

        except Exception as e:
            self.logger.error(f"[Orchestrator] Failed to build workflow: {e}")
            return None

    async def _analyze_task(self, state: SwarmState) -> SwarmState:
        """Analyze incoming task and determine requirements"""
        self.logger.debug("[Orchestrator] Analyzing task...")

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

        self.logger.info(f"[Orchestrator] Task analysis completed: {task_analysis}")
        return state

    async def _select_agent(self, state: SwarmState) -> SwarmState:
        """Select appropriate agent(s) for the task"""
        self.logger.debug("[Orchestrator] Selecting agents...")

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

        self.logger.info(f"[Orchestrator] Selected agents: {selected_agents}")
        return state

    async def _ceo_review(self, state: SwarmState) -> SwarmState:
        """CEO agent reviews and delegates the task"""
        self.logger.debug("[Orchestrator] CEO review...")

        selected_agents = state.agent_responses.get("selected_agents", ["ceo"])

        # CEO review and strategic oversight
        ceo_response = await self.ceo.process_task({
            "messages": state.messages,
            "selected_agents": selected_agents,
            "task_analysis": state.agent_responses.get("task_analysis", {}),
        })

        state.agent_responses["ceo_review"] = ceo_response

        # Determine next step based on CEO decision and selected agents
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
        self.logger.debug("[Orchestrator] Executing strategy task...")

        strategy_response = await self.strategy.process_task({
            "messages": state.messages,
            "ceo_guidance": state.agent_responses.get("ceo_review", {}),
            "task_analysis": state.agent_responses.get("task_analysis", {}),
        })

        state.agent_responses["strategy_result"] = strategy_response
        return state

    async def _execute_devops(self, state: SwarmState) -> SwarmState:
        """DevOps agent executes the task"""
        self.logger.debug("[Orchestrator] Executing DevOps task...")

        devops_response = await self.devops.process_task({
            "messages": state.messages,
            "ceo_guidance": state.agent_responses.get("ceo_review", {}),
            "task_analysis": state.agent_responses.get("task_analysis", {}),
        })

        state.agent_responses["devops_result"] = devops_response
        return state

    async def _synthesize_results(self, state: SwarmState) -> SwarmState:
        """Synthesize results from execution agents"""
        self.logger.debug("[Orchestrator] Synthesizing results...")

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

        # Extract recommendations from results
        for agent, result in results.items():
            if isinstance(result, dict) and "response" in result:
                response_text = result["response"]
                # Simple recommendation extraction
                if "recommend" in response_text.lower():
                    synthesis["recommendations"].append(f"{agent.title()}: See detailed response")

        state.agent_responses["synthesis"] = synthesis

        self.logger.info("[Orchestrator] Results synthesized successfully")
        return state

    async def _final_review(self, state: SwarmState) -> SwarmState:
        """CEO provides final review and approval"""
        self.logger.debug("[Orchestrator] Final review...")

        synthesis = state.agent_responses.get("synthesis", {})

        # Create final review input
        review_input = {
            "synthesis": synthesis,
            "original_task": state.messages[-1].content if state.messages else "",
            "agent_contributions": {
                agent: state.agent_responses.get(f"{agent}_result", {}).get("response", "")
                for agent in ["strategy", "devops"]
                if f"{agent}_result" in state.agent_responses
            }
        }

        # Get CEO final review
        if hasattr(self.ceo, 'final_review'):
            final_response = await self.ceo.final_review(review_input)
        else:
            # Fallback to regular processing
            final_response = await self.ceo.process_task({
                "message": f"Please provide final review for: {review_input}",
                "review_type": "final_approval"
            })

        state.agent_responses["final_result"] = final_response
        state.workflow_status = "completed"

        self.logger.info("[Orchestrator] Final review completed")
        return state

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents in the swarm"""
        self.logger.debug("[Orchestrator] Getting agent status...")

        status = {
            "orchestrator": {
                "status": "active",
                "workflow_available": self.workflow is not None,
                "metrics": self.orchestrator_metrics,
            },
            "agents": {}
        }

        # Get health status from each agent
        for agent_name, agent in self.agents.items():
            try:
                health = await agent.health_check()
                status["agents"][agent_name] = {
                    "name": agent_name.title() + " Agent",
                    "type": agent.__class__.__name__,
                    "capabilities": self.agent_capabilities.get(agent_name, []),
                    "status": health.get("status", "unknown"),
                    "metrics": agent.get_metrics(),
                    "health": health
                }
            except Exception as e:
                self.logger.error(f"[Orchestrator] Failed to get status for {agent_name}: {e}")
                status["agents"][agent_name] = {
                    "name": agent_name.title() + " Agent",
                    "status": "error",
                    "error": str(e)
                }

        return status

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the orchestrator and all agents"""
        self.logger.debug("[Orchestrator] Performing health check...")

        health = {
            "orchestrator": {
                "status": "healthy" if self.agents else "unhealthy",
                "agents": len(self.agents),
                "workflow_available": self.workflow is not None
            },
            "agents": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Check each agent
        for agent_name, agent in self.agents.items():
            try:
                agent_health = await agent.health_check()
                health["agents"][agent_name] = agent_health

                # Update orchestrator status if any agent is unhealthy
                if agent_health.get("status") != "healthy":
                    health["orchestrator"]["status"] = "degraded"

            except Exception as e:
                self.logger.error(f"[Orchestrator] Health check failed for {agent_name}: {e}")
                health["agents"][agent_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["orchestrator"]["status"] = "degraded"

        return health