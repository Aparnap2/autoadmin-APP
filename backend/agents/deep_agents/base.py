"""
Base classes and utilities for AutoAdmin deep agents.

This module provides the foundation for building hierarchical agents
using LangGraph, including shared state management and agent interfaces.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, TypedDict, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Enumeration of agent types in the hierarchy."""
    CEO = "ceo"
    STRATEGY = "strategy"  # CMO/CFO combined
    DEVOPS = "devops"  # CTO


class TaskStatus(Enum):
    """Enumeration of task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class Task:
    """Represents a task assigned to an agent."""
    id: str
    type: AgentType
    description: str
    parameters: Dict[str, Any]
    status: TaskStatus
    assigned_by: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'id': self.id,
            'type': self.type.value,
            'description': self.description,
            'parameters': self.parameters,
            'status': self.status.value,
            'assigned_by': self.assigned_by,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at
        }


class AgentState(TypedDict):
    """Shared state for all agents in the system."""
    # Core conversation state
    messages: List[BaseMessage]

    # Agent orchestration state
    current_agent: str
    agent_task_queue: List[Task]

    # Business context
    business_context: Dict[str, Any]
    current_trends: List[str]
    finance_alerts: List[str]
    marketing_queue: List[Dict[str, Any]]

    # DevOps context
    repo_context: Dict[str, Any]
    open_prs: List[Dict[str, Any]]
    pending_issues: List[Dict[str, Any]]

    # Memory and persistence
    session_id: str
    last_updated: str


class BaseAgent(ABC):
    """
    Abstract base class for all AutoAdmin agents.

    Provides common functionality and interface for agent implementations.
    """

    def __init__(
        self,
        agent_type: AgentType,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Any]] = None
    ):
        """
        Initialize the base agent.

        Args:
            agent_type: Type of the agent
            model_name: Name of the LLM model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tools: List of tools available to the agent
        """
        self.agent_type = agent_type
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tools = tools or []

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Agent configuration
        self.name = self._get_agent_name()
        self.description = self._get_agent_description()
        self.capabilities = self._get_capabilities()

    @abstractmethod
    def _get_agent_name(self) -> str:
        """Get the agent's display name."""
        pass

    @abstractmethod
    def _get_agent_description(self) -> str:
        """Get the agent's description."""
        pass

    @abstractmethod
    def _get_capabilities(self) -> List[str]:
        """Get the list of agent capabilities."""
        pass

    @abstractmethod
    async def process_task(self, task: Task, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Process a task assigned to this agent.

        Args:
            task: Task to process
            state: Current agent state

        Returns:
            Command indicating next action or agent
        """
        pass

    def create_system_prompt(self, state: AgentState) -> str:
        """
        Create a system prompt for the agent based on current state.

        Args:
            state: Current agent state

        Returns:
            System prompt string
        """
        base_prompt = f"""
You are {self.name}, a specialized AutoAdmin agent.

Your role: {self.description}
Your capabilities: {', '.join(self.capabilities)}

Current business context:
{json.dumps(state.get('business_context', {}), indent=2)}

Current trends:
{', '.join(state.get('current_trends', []))}

Available tools: {len(self.tools)} tools

Instructions:
1. Analyze the current task and business context
2. Use your tools and capabilities to address the task
3. Make decisions based on the available information
4. Return a clear action or delegate to another agent
5. Always be specific and actionable in your responses

You should only use tools when necessary and provide clear reasoning for your actions.
"""
        return base_prompt

    async def think_and_act(self, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Core thinking and action method for the agent.

        Args:
            state: Current agent state

        Returns:
            Command indicating next action or agent to delegate to
        """
        # Get current task if any
        current_task = None
        task_queue = state.get('agent_task_queue', [])
        if task_queue:
            current_task = task_queue[0]  # Get the first pending task

        if current_task and current_task.type == self.agent_type:
            # Process the assigned task
            return await self.process_task(current_task, state)
        else:
            # No specific task, perform routine activities
            return await self.perform_routine_activities(state)

    @abstractmethod
    async def perform_routine_activities(self, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Perform routine activities when no specific task is assigned.

        Args:
            state: Current agent state

        Returns:
            Command indicating next action or agent
        """
        pass


class AgentOrchestrator:
    """
    Orchestrator for managing the hierarchical agent system.

    Coordinates between different agents, manages task distribution,
    and maintains the overall state of the system.
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_api_key: str,
        github_token: Optional[str] = None,
        tavily_api_key: Optional[str] = None
    ):
        """
        Initialize the agent orchestrator.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
            openai_api_key: OpenAI API key
            github_token: GitHub access token (optional)
            tavily_api_key: Tavily search API key (optional)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.openai_api_key = openai_api_key
        self.github_token = github_token
        self.tavily_api_key = tavily_api_key

        # Initialize agents
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.

        Args:
            agent: Agent to register
        """
        self.agents[agent.agent_type] = agent
        logger.info(f"Registered agent: {agent.name}")

    async def build_graph(self) -> StateGraph:
        """
        Build the agent execution graph.

        Returns:
            Configured StateGraph for agent execution
        """
        if not self.agents:
            raise ValueError("No agents registered. Cannot build graph.")

        # Create the state graph
        graph = StateGraph(AgentState)

        # Add agent nodes
        for agent_type, agent in self.agents.items():
            graph.add_node(agent_type.value, agent.think_and_act)

        # Create supervisor node (CEO agent if available, else first agent)
        if AgentType.CEO in self.agents:
            supervisor = self.agents[AgentType.CEO]
        else:
            supervisor = list(self.agents.values())[0]

        graph.add_node("supervisor", supervisor.think_and_act)

        # Define the flow
        graph.add_edge(START, "supervisor")

        # Add conditional edges from supervisor to other agents
        agent_names = [agent_type.value for agent_type in self.agents.keys() if agent_type != AgentType.CEO]
        if agent_names:
            graph.add_conditional_edges(
                "supervisor",
                self._route_to_agent,
                agent_names + [END]
            )

        # Add edges back to supervisor from other agents
        for agent_type in self.agents.keys():
            if agent_type != AgentType.CEO:
                graph.add_edge(agent_type.value, "supervisor")

        return graph

    async def compile_graph(self) -> None:
        """Compile the agent execution graph."""
        self.graph = await self.build_graph()
        self.compiled_graph = self.graph.compile()
        logger.info("Agent execution graph compiled successfully")

    async def process_message(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Process a message through the agent system.

        Args:
            message: Input message
            session_id: Session identifier

        Returns:
            Response from the agent system
        """
        if not self.compiled_graph:
            await self.compile_graph()

        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "current_agent": "supervisor",
            "agent_task_queue": [],
            "business_context": {},
            "current_trends": [],
            "finance_alerts": [],
            "marketing_queue": [],
            "repo_context": {},
            "open_prs": [],
            "pending_issues": [],
            "session_id": session_id,
            "last_updated": ""
        }

        try:
            # Run the graph
            result = await self.compiled_graph.ainvoke(initial_state)

            # Extract the response
            if result.get("messages"):
                last_message = result["messages"][-1]
                if isinstance(last_message, AIMessage):
                    response = last_message.content
                else:
                    response = "No AI response generated"
            else:
                response = "No response generated"

            return {
                "response": response,
                "state": result,
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": f"Error processing message: {str(e)}",
                "state": initial_state,
                "session_id": session_id
            }

    def _route_to_agent(self, state: AgentState) -> str:
        """
        Route to the appropriate agent based on state.

        Args:
            state: Current agent state

        Returns:
            Name of the agent to route to
        """
        # Check if there's a specific task in the queue
        task_queue = state.get('agent_task_queue', [])
        if task_queue:
            current_task = task_queue[0]
            return current_task.type.value

        # Default routing based on message content
        messages = state.get('messages', [])
        if messages:
            last_message = messages[-1]
            content = last_message.content.lower()

            if any(word in content for word in ['code', 'github', 'pr', 'deploy', 'build']):
                return AgentType.DEVOPS.value
            elif any(word in content for word in ['research', 'market', 'trend', 'analyze', 'finance']):
                return AgentType.STRATEGY.value

        # Default to CEO or first available agent
        if AgentType.CEO in self.agents:
            return AgentType.CEO.value
        else:
            return list(self.agents.keys())[0].value

    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the status of all registered agents.

        Returns:
            Dictionary with agent status information
        """
        status = {}
        for agent_type, agent in self.agents.items():
            status[agent_type.value] = {
                "name": agent.name,
                "type": agent.agent_type.value,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "tools_count": len(agent.tools),
                "model": agent.model_name
            }

        return {
            "agents": status,
            "total_agents": len(self.agents),
            "graph_compiled": self.compiled_graph is not None
        }