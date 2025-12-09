"""
Enhanced Base Agent - Improved foundation with proper LLM integration
Handles agentic responses with comprehensive logging and error handling
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config.llm_config import llm_config


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentResponse:
    """Standardized agent response structure"""
    agent_id: str
    agent_type: str
    success: bool
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    processing_time: float
    llm_calls: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class EnhancedBaseAgent(ABC):
    """Enhanced base agent with proper LLM integration and comprehensive logging"""

    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type

        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")
        self.logger.setLevel(logging.DEBUG)

        # Add detailed formatter if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # LLM configuration
        self.llm_config = llm_config.get_agent_config(agent_type)

        # Initialize LLM with proper error handling
        try:
            self.logger.info(f"Initializing LLM for {agent_id} with config: {self.llm_config}")
            self.llm = ChatOpenAI(**self.llm_config)
            self.logger.info(f"LLM initialized successfully for {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM for {agent_id}: {e}")
            raise

        # Output parser
        self.output_parser = StrOutputParser()

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "total_llm_calls": 0
        }

        self.logger.info(f"Enhanced base agent {agent_id} initialized")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        pass

    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Process a message and return an agentic response"""
        start_time = datetime.now()
        llm_calls = 0

        self.logger.info(f"[{self.agent_id}] Processing message: {message[:100]}...")
        self.logger.debug(f"[{self.agent_id}] Context: {context}")

        try:
            # Update metrics
            self.metrics["total_requests"] += 1

            # Create prompt messages
            messages = self._create_messages(message, context)

            # Generate response
            self.logger.debug(f"[{self.agent_id}] Invoking LLM...")
            llm_calls += 1
            response = await self.llm.ainvoke(messages)

            # Parse response
            content = response.content if hasattr(response, 'content') else str(response)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            # Update metrics
            self.metrics["successful_requests"] += 1
            self.metrics["total_llm_calls"] += llm_calls
            self._update_average_response_time(processing_time)

            # Create response object
            agent_response = AgentResponse(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                success=True,
                content=content,
                metadata={
                    "model": self.llm_config.get("model"),
                    "temperature": self.llm_config.get("temperature"),
                    "max_tokens": self.llm_config.get("max_tokens"),
                    "capabilities": self.get_capabilities(),
                    "context": context or {}
                },
                timestamp=datetime.now().isoformat(),
                processing_time=processing_time,
                llm_calls=llm_calls
            )

            self.logger.info(f"[{self.agent_id}] Response generated successfully in {processing_time:.2f}s")
            self.logger.debug(f"[{self.agent_id}] Response preview: {content[:200]}...")

            return agent_response

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Error processing message: {str(e)}"

            self.logger.error(f"[{self.agent_id}] {error_msg}", exc_info=True)

            # Update metrics
            self.metrics["failed_requests"] += 1

            # Return error response
            return AgentResponse(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                success=False,
                content=f"I apologize, but I encountered an error while processing your request: {error_msg}",
                metadata={
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "capabilities": self.get_capabilities()
                },
                timestamp=datetime.now().isoformat(),
                processing_time=processing_time,
                llm_calls=llm_calls,
                error=error_msg
            )

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task input (for compatibility with existing orchestrator)"""
        self.logger.info(f"[{self.agent_id}] Processing task with input: {task_input}")

        # Extract message and context from task input
        message = task_input.get("message", "")
        if not message and "messages" in task_input:
            # Handle LangChain message format
            messages = task_input["messages"]
            if messages and isinstance(messages[-1], HumanMessage):
                message = messages[-1].content

        context = {
            "ceo_guidance": task_input.get("ceo_guidance", {}),
            "task_analysis": task_input.get("task_analysis", {}),
            "selected_agents": task_input.get("selected_agents", []),
            "task_type": task_input.get("task_type", "general")
        }

        # Process the message
        response = await self.process_message(message, context)

        # Convert to expected format
        return {
            "agent": self.agent_id,
            "success": response.success,
            "response": response.content,
            "metadata": response.metadata,
            "timestamp": response.timestamp,
            "processing_time": response.processing_time,
            "llm_calls": response.llm_calls,
            "error": response.error
        }

    def _create_messages(self, message: str, context: Optional[Dict[str, Any]] = None) -> List[BaseMessage]:
        """Create message list for LLM"""
        messages = [SystemMessage(content=self.get_system_prompt())]

        # Add context if provided
        if context:
            context_str = self._format_context(context)
            if context_str:
                messages.append(HumanMessage(content=f"Context:\n{context_str}\n\nNow, please respond to the following:"))

        # Add main message
        messages.append(HumanMessage(content=message))

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the LLM"""
        formatted_parts = []

        if "ceo_guidance" in context and context["ceo_guidance"]:
            formatted_parts.append("CEO Guidance:")
            guidance = context["ceo_guidance"]
            if isinstance(guidance, dict):
                for key, value in guidance.items():
                    formatted_parts.append(f"  - {key}: {value}")
            else:
                formatted_parts.append(f"  {guidance}")

        if "task_analysis" in context and context["task_analysis"]:
            formatted_parts.append("Task Analysis:")
            analysis = context["task_analysis"]
            for key, value in analysis.items():
                formatted_parts.append(f"  - {key}: {value}")

        if "selected_agents" in context and context["selected_agents"]:
            formatted_parts.append(f"Selected Agents: {', '.join(context['selected_agents'])}")

        if "task_type" in context and context["task_type"]:
            formatted_parts.append(f"Task Type: {context['task_type']}")

        return "\n".join(formatted_parts)

    def _update_average_response_time(self, processing_time: float):
        """Update average response time metric"""
        if self.metrics["successful_requests"] > 0:
            weight = 0.9  # Exponential moving average
            self.metrics["average_response_time"] = (
                self.metrics["average_response_time"] * weight + processing_time * (1 - weight)
            )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for the agent"""
        try:
            # Quick LLM test
            test_message = "Respond with 'OK' if you're working properly."
            test_response = await self.process_message(test_message)

            health_status = {
                "status": "healthy" if test_response.success and "OK" in test_response.content else "unhealthy",
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "capabilities": self.get_capabilities(),
                "metrics": self.metrics,
                "llm_config": {
                    "model": self.llm_config.get("model"),
                    "base_url": self.llm_config.get("openai_api_base"),
                    "temperature": self.llm_config.get("temperature"),
                    "max_tokens": self.llm_config.get("max_tokens")
                },
                "timestamp": datetime.now().isoformat()
            }

            if not test_response.success:
                health_status["error"] = test_response.error

            return health_status

        except Exception as e:
            self.logger.error(f"[{self.agent_id}] Health check failed: {e}")
            return {
                "status": "unhealthy",
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "metrics": self.metrics.copy(),
            "success_rate": (
                self.metrics["successful_requests"] / max(1, self.metrics["total_requests"]) * 100
            )
        }