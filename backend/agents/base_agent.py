"""
Base Agent - Foundation for all Python deep agents
Handles communication, task processing, and coordination with frontend
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import asyncio
import logging
import json
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import uuid
import os

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import requests
from services.firebase_service import get_firebase_service, Task, GraphNode, GraphEdge


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    MARKET_RESEARCH = "market_research"
    FINANCIAL_ANALYSIS = "financial_analysis"
    CODE_ANALYSIS = "code_analysis"
    UI_UX_REVIEW = "ui_ux_review"
    STRATEGIC_PLANNING = "strategic_planning"
    TECHNICAL_DECISION = "technical_decision"
    DATA_PROCESSING = "data_processing"
    COMPUTATION_HEAVY = "computation_heavy"


class AgentType(str, Enum):
    MARKETING = "marketing"
    FINANCE = "finance"
    DEVOPS = "devops"
    STRATEGY = "strategy"


@dataclass
class TaskDelegation:
    id: str
    type: str  # 'light_task', 'heavy_task', 'hybrid_task'
    category: TaskType
    priority: str  # 'low', 'medium', 'high', 'urgent'
    title: str
    description: str
    parameters: Dict[str, Any]
    expectedDuration: int  # seconds
    complexity: int  # 1-10
    resourceRequirements: Dict[str, str]
    assignedTo: str
    status: TaskStatus
    createdAt: datetime
    updatedAt: datetime
    scheduledAt: Optional[datetime] = None
    deadline: Optional[datetime] = None
    retryCount: int = 0
    maxRetries: int = 3
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskResult:
    taskId: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    nextActions: Optional[List[Dict[str, Any]]] = None


@dataclass
class AgentCapabilities:
    agentId: str
    agentType: AgentType
    capabilities: List[str]
    maxConcurrentTasks: int
    currentLoad: int
    averageProcessingTime: int  # milliseconds
    successRate: float  # 0-1
    resourceLimits: Dict[str, int]
    currentResourceUsage: Dict[str, int]
    supportedTaskTypes: List[TaskType]
    specialties: List[str]
    performance: Dict[str, float]


class CommunicationProtocol:
    """Handles bidirectional communication with frontend agents using Firebase"""

    def __init__(self):
        self.firebase_service = get_firebase_service()
        self.logger = logging.getLogger(__name__)

    async def send_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
        target: str,
        source: str,
        priority: str = "medium",
        correlation_id: Optional[str] = None
    ) -> str:
        """Send message to frontend agents"""
        try:
            message = {
                "id": f"msg_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
                "type": message_type,
                "source": source,
                "target": target,
                "payload": payload,
                "timestamp": datetime.now().isoformat(),
                "priority": priority,
                "requiresAck": False,
                "correlationId": correlation_id
            }

            # Store message in Firebase for frontend to pick up
            message_data = {
                "user_id": payload.get("userId", "system"),
                "agent_id": source,
                "content": json.dumps(message),
                "type": "agent",
                "metadata": {
                    "type": "message_stored",
                    "messageId": message["id"],
                    "messageType": message_type,
                    "source": source,
                    "target": target,
                    "priority": priority
                }
            }

            # Store in Firebase messages collection
            await self.firebase_service.create_webhook_event(message_data)

            self.logger.info(f"Sent message {message['id']} to {target}")
            return message["id"]

        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            raise

    async def send_task_result(self, result: TaskResult, source_agent: str) -> str:
        """Send task result back to frontend"""
        return await self.send_message(
            "task_response",
            {
                "taskId": result.taskId,
                "result": asdict(result),
                "timestamp": datetime.now().isoformat(),
                "source": source_agent
            },
            "orchestrator",
            source_agent,
            priority="high",
            correlation_id=result.taskId
        )

    async def send_status_update(
        self,
        task_id: str,
        status: TaskStatus,
        message: str,
        source_agent: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send status update for a task"""
        return await self.send_message(
            "status_update",
            {
                "taskId": task_id,
                "status": status.value,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            },
            "orchestrator",
            source_agent,
            priority="medium",
            correlation_id=task_id
        )

    async def send_progress_update(
        self,
        task_id: str,
        current_step: str,
        total_steps: int,
        completed_steps: int,
        percentage: float,
        source_agent: str,
        current_activity: str
    ) -> str:
        """Send progress update for a task"""
        return await self.send_message(
            "progress_update",
            {
                "taskId": task_id,
                "progress": {
                    "taskId": task_id,
                    "currentStep": current_step,
                    "totalSteps": total_steps,
                    "completedSteps": completed_steps,
                    "percentage": percentage,
                    "estimatedTimeRemaining": None,
                    "currentActivity": current_activity,
                    "lastUpdate": datetime.now().isoformat()
                }
            },
            "orchestrator",
            source_agent,
            priority="low",
            correlation_id=task_id
        )

    async def get_pending_tasks(self, agent_type: AgentType, limit: int = 10) -> List[TaskDelegation]:
        """Get pending tasks assigned to this agent type"""
        try:
            # Get tasks from Firebase
            firebase_tasks = await self.firebase_service.get_tasks_by_agent_type(agent_type.value)

            tasks = []
            for firebase_task in firebase_tasks:
                if firebase_task.status == 'pending':
                    task = TaskDelegation(
                        id=firebase_task.id,
                        type=firebase_task.parameters.get('type', 'heavy_task') if firebase_task.parameters else 'heavy_task',
                        category=TaskType(firebase_task.agent_type),
                        priority=firebase_task.priority,
                        title=firebase_task.input_prompt[:100] + '...' if len(firebase_task.input_prompt) > 100 else firebase_task.input_prompt,
                        description=firebase_task.input_prompt,
                        parameters=firebase_task.parameters or {},
                        expectedDuration=firebase_task.parameters.get('expected_duration', 300) if firebase_task.parameters else 300,
                        complexity=firebase_task.parameters.get('complexity', 5) if firebase_task.parameters else 5,
                        resourceRequirements=firebase_task.parameters.get('resource_requirements', {}) if firebase_task.parameters else {},
                        assignedTo=agent_type.value,
                        status=TaskStatus(firebase_task.status),
                        createdAt=firebase_task.created_at,
                        updatedAt=firebase_task.updated_at or datetime.now(),
                        metadata=firebase_task.parameters.get('metadata', {}) if firebase_task.parameters else {}
                    )
                    tasks.append(task)
                    if len(tasks) >= limit:
                        break

            return tasks

        except Exception as e:
            self.logger.error(f"Error getting pending tasks: {e}")
            return []


class BaseAgent(ABC):
    """Base class for all Python deep agents"""

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        openai_api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4000
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=openai_api_key
        )

        # Initialize communication with Firebase
        self.communication = CommunicationProtocol()

        # Agent capabilities
        self.capabilities = AgentCapabilities(
            agentId=agent_id,
            agentType=agent_type,
            capabilities=self.get_agent_capabilities(),
            maxConcurrentTasks=5,
            currentLoad=0,
            averageProcessingTime=60000,  # 1 minute default
            successRate=0.9,
            resourceLimits={"compute": 100, "memory": 100, "network": 100, "storage": 100},
            currentResourceUsage={"compute": 0, "memory": 0, "network": 0, "storage": 0},
            supportedTaskTypes=self.get_supported_task_types(),
            specialties=self.get_agent_specialties(),
            performance={"throughput": 10, "latency": 60000, "errorRate": 0.1}
        )

        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")

        # Task processing state
        self.current_tasks: Dict[str, TaskDelegation] = {}
        self.is_running = False

    @abstractmethod
    def get_agent_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        pass

    @abstractmethod
    def get_supported_task_types(self) -> List[TaskType]:
        """Return list of supported task types"""
        pass

    @abstractmethod
    def get_agent_specialties(self) -> List[str]:
        """Return list of agent specialties"""
        pass

    @abstractmethod
    async def process_task(self, task: TaskDelegation) -> TaskResult:
        """Process a task and return result"""
        pass

    async def start(self):
        """Start the agent and begin processing tasks"""
        self.is_running = True
        self.logger.info(f"Starting agent {self.agent_id}")

        # Update agent capabilities in the system
        await self.update_capabilities()

        # Start task processing loop
        asyncio.create_task(self.task_processing_loop())

        # Start health check loop
        asyncio.create_task(self.health_check_loop())

    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        self.logger.info(f"Stopping agent {self.agent_id}")

        # Complete current tasks gracefully
        for task_id, task in list(self.current_tasks.items()):
            await self.cancel_task(task_id, "Agent shutting down")

    async def task_processing_loop(self):
        """Main loop for processing tasks"""
        while self.is_running:
            try:
                # Check if we can accept more tasks
                if self.capabilities.currentLoad < self.capabilities.maxConcurrentTasks:
                    # Get pending tasks
                    pending_tasks = await self.communication.get_pending_tasks(
                        self.agent_type,
                        limit=self.capabilities.maxConcurrentTasks - self.capabilities.currentLoad
                    )

                    for task in pending_tasks:
                        if not self.is_running:
                            break

                        # Check if we're already processing this task
                        if task.id not in self.current_tasks:
                            await self.start_task_processing(task)

                # Wait before next check
                await asyncio.sleep(5)

            except Exception as e:
                self.logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(10)

    async def start_task_processing(self, task: TaskDelegation):
        """Start processing a specific task"""
        try:
            # Update task status
            await self.communication.send_status_update(
                task.id,
                TaskStatus.PROCESSING,
                f"Task assigned to {self.agent_id}",
                self.agent_id
            )

            # Update load
            self.capabilities.currentLoad += 1
            self.current_tasks[task.id] = task

            # Start task processing in background
            asyncio.create_task(self.process_task_async(task))

            self.logger.info(f"Started processing task {task.id}")

        except Exception as e:
            self.logger.error(f"Error starting task processing: {e}")
            await self.fail_task(task.id, f"Failed to start processing: {e}")

    async def process_task_async(self, task: TaskDelegation):
        """Process task asynchronously"""
        start_time = datetime.now()

        try:
            # Send initial progress
            await self.communication.send_progress_update(
                task.id,
                "Initializing",
                5, 1, 20,
                self.agent_id,
                "Setting up task processing"
            )

            # Process the task
            result = await self.process_task(task)

            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            result.metrics = result.metrics or {}
            result.metrics.update({
                "duration": processing_time,
                "agentId": self.agent_id,
                "agentType": self.agent_type.value,
                "success": result.success
            })

            # Send result
            await self.communication.send_task_result(result, self.agent_id)

            # Update task status
            final_status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            await self.communication.send_status_update(
                task.id,
                final_status,
                "Task completed" if result.success else f"Task failed: {result.error}",
                self.agent_id,
                metadata={"result": asdict(result)}
            )

            # Update agent metrics
            await self.update_performance_metrics(result.success, processing_time)

            self.logger.info(f"Completed task {task.id}: {result.success}")

        except Exception as e:
            self.logger.error(f"Error processing task {task.id}: {e}")
            await self.fail_task(task.id, f"Processing failed: {e}")

        finally:
            # Clean up
            self.current_tasks.pop(task.id, None)
            self.capabilities.currentLoad = max(0, self.capabilities.currentLoad - 1)

    async def fail_task(self, task_id: str, error_message: str):
        """Mark a task as failed"""
        try:
            await self.communication.send_status_update(
                task_id,
                TaskStatus.FAILED,
                error_message,
                self.agent_id
            )

            result = TaskResult(
                taskId=task_id,
                success=False,
                error=error_message,
                metrics={"failedAt": datetime.now().isoformat()}
            )

            await self.communication.send_task_result(result, self.agent_id)

            # Update metrics
            await self.update_performance_metrics(False, 0)

        except Exception as e:
            self.logger.error(f"Error failing task {task_id}: {e}")

    async def cancel_task(self, task_id: str, reason: str):
        """Cancel a task"""
        try:
            await self.communication.send_status_update(
                task_id,
                TaskStatus.CANCELLED,
                reason,
                self.agent_id
            )

            self.current_tasks.pop(task_id, None)
            self.capabilities.currentLoad = max(0, self.capabilities.currentLoad - 1)

        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {e}")

    async def update_capabilities(self):
        """Update agent capabilities in the system"""
        try:
            # Store capabilities in Firebase for routing decisions
            capabilities_data = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "capabilities": json.dumps(self.capabilities.capabilities),
                "max_concurrent_tasks": self.capabilities.maxConcurrentTasks,
                "current_load": self.capabilities.currentLoad,
                "success_rate": self.capabilities.successRate,
                "supported_task_types": json.dumps([t.value for t in self.capabilities.supportedTaskTypes]),
                "specialties": json.dumps(self.capabilities.specialties),
                "updated_at": datetime.now().isoformat()
            }

            # Store in Firebase using agent_files collection for now
            await get_firebase_service().store_agent_file(
                f"agent_capabilities/{self.agent_id}",
                json.dumps(capabilities_data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error updating capabilities: {e}")

    async def update_performance_metrics(self, success: bool, processing_time: float):
        """Update agent performance metrics"""
        try:
            # Update running averages
            if success:
                # Update success rate
                self.capabilities.successRate = (
                    self.capabilities.successRate * 0.9 + 0.1
                )
            else:
                self.capabilities.successRate = (
                    self.capabilities.successRate * 0.9
                )

            # Update average processing time
            if processing_time > 0:
                self.capabilities.averageProcessingTime = int(
                    self.capabilities.averageProcessingTime * 0.8 + processing_time * 1000 * 0.2
                )

            # Update capabilities periodically
            await self.update_capabilities()

        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")

    async def health_check_loop(self):
        """Periodic health check and capability updates"""
        while self.is_running:
            try:
                await self.update_capabilities()

                # Send heartbeat
                await self.communication.send_message(
                    "heartbeat",
                    {
                        "timestamp": datetime.now().isoformat(),
                        "status": "healthy",
                        "currentLoad": self.capabilities.currentLoad,
                        "maxConcurrentTasks": self.capabilities.maxConcurrentTasks,
                        "successRate": self.capabilities.successRate
                    },
                    "all",
                    self.agent_id,
                    priority="low"
                )

                await asyncio.sleep(60)  # Health check every minute

            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                await asyncio.sleep(60)

    def create_context_messages(self, task: TaskDelegation) -> List[BaseMessage]:
        """Create context messages for LLM processing"""
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=f"""
Task: {task.title}

Description: {task.description}

Parameters: {json.dumps(task.parameters, indent=2)}

Priority: {task.priority}
Complexity: {task.complexity}/10
Expected Duration: {task.expectedDuration} seconds

Please process this task and provide a comprehensive response.
            """.strip())
        ]

        return messages

    def get_system_prompt(self) -> str:
        """Get system prompt for this agent"""
        return f"""
You are a {self.agent_type.value} agent in the AutoAdmin system.

Your capabilities include: {', '.join(self.capabilities.capabilities)}
Your specialties include: {', '.join(self.capabilities.specialties)}

You should provide thorough, well-reasoned responses that demonstrate your expertise.
Always consider the business context and provide actionable insights.
When appropriate, suggest next steps or follow-up actions.

Current timestamp: {datetime.now().isoformat()}
        """.strip()