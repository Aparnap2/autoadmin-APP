"""
Async Agent Base - Enhanced base agent with robust async lifecycle management
Handles async operations, task cancellation, and resource cleanup properly
"""

import asyncio
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import weakref

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


class ServiceState(str, Enum):
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


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
    metadata: Dict[str, Any] = field(default_factory=dict)
    cancellation_requested: bool = False


@dataclass
class TaskResult:
    taskId: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = field(default_factory=dict)
    nextActions: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    cancellation_reason: Optional[str] = None


@dataclass
class AgentCapabilities:
    agentId: str
    agentType: AgentType
    capabilities: List[str]
    maxConcurrentTasks: int
    currentLoad: int = 0
    averageProcessingTime: int = 60000  # milliseconds
    successRate: float = 0.9
    resourceLimits: Dict[str, int] = field(default_factory=dict)
    currentResourceUsage: Dict[str, int] = field(default_factory=dict)
    supportedTaskTypes: List[TaskType] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)
    performance: Dict[str, float] = field(default_factory=dict)


class AsyncCommunicationProtocol:
    """Enhanced communication protocol with proper async handling"""

    def __init__(self):
        self.firebase_service = get_firebase_service()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._message_semaphore = asyncio.Semaphore(10)  # Limit concurrent message operations

    async def send_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
        target: str,
        source: str,
        priority: str = "medium",
        correlation_id: Optional[str] = None,
        timeout: float = 30.0
    ) -> str:
        """Send message with timeout and proper error handling"""
        try:
            async with asyncio.timeout(timeout):
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

                # Use semaphore to limit concurrent Firebase operations
                async with self._message_semaphore:
                    await self.firebase_service.create_webhook_event(message_data)

                self.logger.info(f"Sent message {message['id']} to {target}")
                return message["id"]

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout sending message to {target}")
            raise
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            raise

    async def send_task_result(self, result: TaskResult, source_agent: str, timeout: float = 30.0) -> str:
        """Send task result with proper error handling"""
        return await self.send_message(
            "task_response",
            {
                "taskId": result.taskId,
                "result": result.__dict__,
                "timestamp": datetime.now().isoformat(),
                "source": source_agent
            },
            "orchestrator",
            source_agent,
            priority="high",
            correlation_id=result.taskId,
            timeout=timeout
        )

    async def send_status_update(
        self,
        task_id: str,
        status: TaskStatus,
        message: str,
        source_agent: str,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0
    ) -> str:
        """Send status update with timeout"""
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
            correlation_id=task_id,
            timeout=timeout
        )

    async def send_progress_update(
        self,
        task_id: str,
        current_step: str,
        total_steps: int,
        completed_steps: int,
        percentage: float,
        source_agent: str,
        current_activity: str,
        timeout: float = 15.0
    ) -> str:
        """Send progress update with timeout"""
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
            correlation_id=task_id,
            timeout=timeout
        )

    async def get_pending_tasks(self, agent_type: AgentType, limit: int = 10) -> List[TaskDelegation]:
        """Get pending tasks with error handling"""
        try:
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


class AsyncAgentBase(ABC):
    """Enhanced base agent with robust async lifecycle management"""

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        openai_api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        shutdown_timeout: float = 30.0,
        task_timeout: float = 300.0  # 5 minutes default task timeout
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.shutdown_timeout = shutdown_timeout
        self.task_timeout = task_timeout

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=openai_api_key
        )

        # Initialize communication with Firebase
        self.communication = AsyncCommunicationProtocol()

        # Agent state management
        self.state = ServiceState.INITIALIZING
        self.capabilities = AgentCapabilities(
            agentId=agent_id,
            agentType=agent_type,
            capabilities=self.get_agent_capabilities(),
            maxConcurrentTasks=5,
            supportedTaskTypes=self.get_supported_task_types(),
            specialties=self.get_agent_specialties(),
            resourceLimits={"compute": 100, "memory": 100, "network": 100, "storage": 100},
            currentResourceUsage={"compute": 0, "memory": 0, "network": 0, "storage": 0},
            performance={"throughput": 10, "latency": 60000, "errorRate": 0.1}
        )

        # Task management
        self.current_tasks: Dict[str, asyncio.Task] = {}
        self.task_metadata: Dict[str, TaskDelegation] = {}
        self._task_semaphore = asyncio.Semaphore(self.capabilities.maxConcurrentTasks)
        self._shutdown_event = asyncio.Event()

        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()

        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")

        # Health metrics
        self.start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.total_tasks_processed: int = 0
        self.successful_tasks: int = 0
        self.failed_tasks: int = 0

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
    async def process_task_core(self, task: TaskDelegation) -> TaskResult:
        """Core task processing logic (must be implemented by subclasses)"""
        pass

    async def initialize(self):
        """Initialize the agent"""
        try:
            self.state = ServiceState.INITIALIZING
            self.logger.info(f"Initializing agent {self.agent_id}")

            # Update agent capabilities
            await self.update_capabilities()

            # Set start time
            self.start_time = datetime.now()
            self.last_heartbeat = datetime.now()

            self.state = ServiceState.IDLE
            self.logger.info(f"Agent {self.agent_id} initialized successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def start(self):
        """Start the agent and begin processing tasks"""
        if self.state != ServiceState.IDLE:
            raise RuntimeError(f"Agent {self.agent_id} must be initialized before starting")

        try:
            self.logger.info(f"Starting agent {self.agent_id}")

            # Start background tasks
            task_processor = asyncio.create_task(
                self.task_processing_loop(),
                name=f"{self.agent_id}_task_processor"
            )
            self.background_tasks.add(task_processor)

            health_checker = asyncio.create_task(
                self.health_check_loop(),
                name=f"{self.agent_id}_health_checker"
            )
            self.background_tasks.add(health_checker)

            self.logger.info(f"Agent {self.agent_id} started successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Failed to start agent {self.agent_id}: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def stop(self):
        """Stop the agent gracefully"""
        if self.state == ServiceState.STOPPED:
            return

        try:
            self.state = ServiceState.STOPPING
            self.logger.info(f"Stopping agent {self.agent_id}")

            # Signal shutdown
            self._shutdown_event.set()

            # Cancel all running tasks
            await self.cancel_all_tasks("Agent shutting down")

            # Wait for background tasks to complete
            if self.background_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.background_tasks, return_exceptions=True),
                        timeout=self.shutdown_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Background tasks didn't complete within shutdown timeout")

                    # Force cancel remaining tasks
                    for task in self.background_tasks:
                        if not task.done():
                            task.cancel()

                    try:
                        await asyncio.gather(*self.background_tasks, return_exceptions=True)
                    except Exception as e:
                        self.logger.error(f"Error cancelling background tasks: {e}")

                self.background_tasks.clear()

            # Final capabilities update
            await self.update_capabilities()

            self.state = ServiceState.STOPPED
            self.logger.info(f"Agent {self.agent_id} stopped successfully")

        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Error stopping agent {self.agent_id}: {e}")
            self.logger.error(traceback.format_exc())

    async def process_task(self, task: TaskDelegation) -> TaskResult:
        """Process a task with robust error handling and cancellation support"""
        start_time = datetime.now()

        try:
            # Check if task was already cancelled
            if task.cancellation_requested:
                return TaskResult(
                    taskId=task.id,
                    success=False,
                    error="Task was cancelled before processing",
                    cancellation_reason="Pre-cancelled"
                )

            # Send initial progress
            await self.communication.send_status_update(
                task.id,
                TaskStatus.PROCESSING,
                f"Task assigned to {self.agent_id}",
                self.agent_id
            )

            # Process the task with timeout
            try:
                async with asyncio.timeout(self.task_timeout):
                    result = await self.process_task_core(task)
            except asyncio.TimeoutError:
                error_msg = f"Task processing timed out after {self.task_timeout} seconds"
                self.logger.error(f"Task {task.id} timed out")
                result = TaskResult(
                    taskId=task.id,
                    success=False,
                    error=error_msg
                )

            # Add processing metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            result.metrics.update({
                "duration": processing_time,
                "agentId": self.agent_id,
                "agentType": self.agent_type.value,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            })

            # Update metrics
            self.total_tasks_processed += 1
            if result.success:
                self.successful_tasks += 1
            else:
                self.failed_tasks += 1

            # Send result
            await self.communication.send_task_result(result, self.agent_id)

            # Update task status
            final_status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            await self.communication.send_status_update(
                task.id,
                final_status,
                "Task completed" if result.success else f"Task failed: {result.error}",
                self.agent_id,
                metadata={"result": result.__dict__}
            )

            self.logger.info(f"Completed task {task.id}: {result.success}")
            return result

        except asyncio.CancelledError:
            self.logger.info(f"Task {task.id} was cancelled")
            return TaskResult(
                taskId=task.id,
                success=False,
                error="Task was cancelled",
                cancellation_reason="Processing cancelled"
            )

        except Exception as e:
            self.logger.error(f"Error processing task {task.id}: {e}")
            self.logger.error(traceback.format_exc())
            self.failed_tasks += 1

            error_result = TaskResult(
                taskId=task.id,
                success=False,
                error=str(e),
                metrics={"duration": (datetime.now() - start_time).total_seconds()}
            )

            await self.communication.send_task_result(error_result, self.agent_id)
            return error_result

    async def task_processing_loop(self):
        """Main loop for processing tasks"""
        self.logger.info("Starting task processing loop")

        while not self._shutdown_event.is_set():
            try:
                # Check if we can accept more tasks
                if len(self.current_tasks) < self.capabilities.maxConcurrentTasks:
                    # Get pending tasks
                    pending_tasks = await self.communication.get_pending_tasks(
                        self.agent_type,
                        limit=self.capabilities.maxConcurrentTasks - len(self.current_tasks)
                    )

                    for task in pending_tasks:
                        if self._shutdown_event.is_set():
                            break

                        # Check if we're already processing this task
                        if task.id not in self.current_tasks:
                            await self.start_task_processing(task)

                # Update state
                self.state = ServiceState.BUSY if self.current_tasks else ServiceState.IDLE

                # Update capabilities
                self.capabilities.currentLoad = len(self.current_tasks)
                await self.update_capabilities()

                # Wait before next check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=5.0
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue processing

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

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

            # Store task metadata
            self.task_metadata[task.id] = task

            # Create task with semaphore
            async with self._task_semaphore:
                if self._shutdown_event.is_set():
                    return

                task_coro = self.process_task(task)
                task_task = asyncio.create_task(
                    task_coro,
                    name=f"{self.agent_id}_task_{task.id[:8]}"
                )
                self.current_tasks[task.id] = task_task

                # Add cleanup callback
                task_task.add_done_callback(lambda t: self.current_tasks.pop(task.id, None))

            self.logger.info(f"Started processing task {task.id}")

        except Exception as e:
            self.logger.error(f"Error starting task processing: {e}")
            await self.fail_task(task.id, f"Failed to start processing: {e}")

    async def cancel_task(self, task_id: str, reason: str):
        """Cancel a specific task"""
        try:
            # Mark task as cancelled in metadata
            if task_id in self.task_metadata:
                self.task_metadata[task_id].cancellation_requested = True

            # Cancel the asyncio task
            if task_id in self.current_tasks:
                task = self.current_tasks[task_id]
                task.cancel()

                # Wait for cancellation to complete
                try:
                    await asyncio.wait_for(task, timeout=10.0)
                except asyncio.TimeoutError:
                    self.logger.warning(f"Task {task_id} didn't cancel cleanly")
                except asyncio.CancelledError:
                    pass  # Expected

                self.current_tasks.pop(task_id, None)

            # Send status update
            await self.communication.send_status_update(
                task_id,
                TaskStatus.CANCELLED,
                reason,
                self.agent_id
            )

            self.logger.info(f"Cancelled task {task_id}: {reason}")

        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {e}")

    async def cancel_all_tasks(self, reason: str):
        """Cancel all running tasks"""
        self.logger.info(f"Cancelling all tasks: {reason}")

        # Mark all tasks as cancelled
        for task_id in self.task_metadata:
            self.task_metadata[task_id].cancellation_requested = True

        # Cancel all asyncio tasks
        cancellation_tasks = []
        for task_id, task in list(self.current_tasks.items()):
            task.cancel()
            cancellation_tasks.append(self._wait_for_task_cancellation(task_id, task))

        # Wait for all cancellations
        if cancellation_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cancellation_tasks, return_exceptions=True),
                    timeout=self.shutdown_timeout
                )
            except asyncio.TimeoutError:
                self.logger.warning("Some tasks didn't cancel within timeout")

        self.current_tasks.clear()
        self.task_metadata.clear()

    async def _wait_for_task_cancellation(self, task_id: str, task: asyncio.Task):
        """Wait for a specific task to be cancelled"""
        try:
            await asyncio.wait_for(task, timeout=10.0)
        except asyncio.TimeoutError:
            self.logger.warning(f"Task {task_id} didn't cancel cleanly")
        except asyncio.CancelledError:
            pass  # Expected

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
            self.failed_tasks += 1

        except Exception as e:
            self.logger.error(f"Error failing task {task_id}: {e}")

    async def health_check_loop(self):
        """Periodic health check and capability updates"""
        while not self._shutdown_event.is_set():
            try:
                self.last_heartbeat = datetime.now()

                # Update capabilities
                await self.update_capabilities()

                # Send heartbeat
                await self.communication.send_message(
                    "heartbeat",
                    {
                        "timestamp": datetime.now().isoformat(),
                        "status": "healthy",
                        "state": self.state.value,
                        "currentLoad": self.capabilities.currentLoad,
                        "maxConcurrentTasks": self.capabilities.maxConcurrentTasks,
                        "successRate": self.capabilities.successRate,
                        "totalTasksProcessed": self.total_tasks_processed,
                        "successfulTasks": self.successful_tasks,
                        "failedTasks": self.failed_tasks
                    },
                    "all",
                    self.agent_id,
                    priority="low"
                )

                # Wait before next check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=60.0
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue health checking

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                await asyncio.sleep(10)

    async def update_capabilities(self):
        """Update agent capabilities in the system"""
        try:
            # Update success rate
            if self.total_tasks_processed > 0:
                self.capabilities.successRate = self.successful_tasks / self.total_tasks_processed

            # Store capabilities in Firebase
            capabilities_data = {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "state": self.state.value,
                "capabilities": json.dumps(self.capabilities.capabilities),
                "max_concurrent_tasks": self.capabilities.maxConcurrentTasks,
                "current_load": self.capabilities.currentLoad,
                "success_rate": self.capabilities.successRate,
                "supported_task_types": json.dumps([t.value for t in self.capabilities.supportedTaskTypes]),
                "specialties": json.dumps(self.capabilities.specialties),
                "total_tasks_processed": self.total_tasks_processed,
                "successful_tasks": self.successful_tasks,
                "failed_tasks": self.failed_tasks,
                "updated_at": datetime.now().isoformat()
            }

            # Store in Firebase using agent_files collection
            await get_firebase_service().store_agent_file(
                f"agent_capabilities/{self.agent_id}",
                json.dumps(capabilities_data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error updating capabilities: {e}")

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

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "state": self.state.value,
            "current_tasks": len(self.current_tasks),
            "load": self.capabilities.currentLoad,
            "max_load": self.capabilities.maxConcurrentTasks,
            "success_rate": self.capabilities.successRate,
            "total_tasks_processed": self.total_tasks_processed,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }