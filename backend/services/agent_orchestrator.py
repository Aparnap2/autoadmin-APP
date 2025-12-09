"""
HTTP-based Agent Orchestrator for AutoAdmin Backend
Replaces WebSocket-based agent communication with HTTP streaming and polling
Provides real-time agent coordination using standard HTTP protocols
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

from fastapi.applications import FastAPI

# Import HTTP streaming services
from fastapi.app.services.http_streaming import get_streaming_service, EventType
from fastapi.app.services.long_polling import get_long_polling_service

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(Enum):
    """Message types for agent communication"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    COORDINATION = "coordination"
    COLLABORATION = "collaboration"


@dataclass
class AgentTask:
    """Task definition for agents"""
    task_id: str
    task_type: str
    priority: TaskPriority
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300  # 5 minutes default
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "data": self.data,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count
        }


@dataclass
class AgentMessage:
    """Message for agent communication"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str] = None
    task_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    requires_response: bool = False
    timeout: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "task_id": self.task_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "requires_response": self.message_id if self.requires_response else None,
            "timeout": self.timeout
        }


@dataclass
class AgentInfo:
    """Agent information"""
    agent_id: str
    agent_type: str
    name: str
    capabilities: List[str]
    status: AgentStatus
    last_heartbeat: datetime
    current_load: int = 0
    max_capacity: int = 10
    current_tasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "current_load": self.current_load,
            "max_capacity": self.max_capacity,
            "current_tasks": self.current_tasks,
            "metadata": self.metadata,
            "user_id": self.user_id,
            "session_id": self.session_id
        }


class HTTPAgentOrchestrator:
    """
    HTTP-based Agent Orchestrator
    Replaces WebSocket communication with HTTP streaming and long polling
    """

    _instance = None
    _agents: Dict[str, AgentInfo] = {}
    _tasks: Dict[str, AgentTask] = {}
    _message_handlers: Dict[str, Callable] = {}
    _task_handlers: Dict[str, Callable] = {}
    _heartbeat_interval = 30  # 30 seconds
    _task_timeout = 300  # 5 minutes
    _max_pending_tasks = 1000
    _background_tasks: List[asyncio.Task] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HTTPAgentOrchestrator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._initialized = True
            self._streaming_service = get_streaming_service()
            self._polling_service = get_long_polling_service()
            self._start_background_tasks()

    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        # Heartbeat monitoring
        self._background_tasks.append(
            asyncio.create_task(self._heartbeat_monitor())
        )

        # Task timeout monitoring
        self._background_tasks.append(
            asyncio.create_task(self._task_timeout_monitor())
        )

        # Cleanup old tasks
        self._background_tasks.append(
            asyncio.create_task(self._cleanup_monitor())
        )

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        name: str,
        capabilities: List[str],
        max_capacity: int = 10,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Register a new agent

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (marketing, sales, etc.)
            name: Human-readable name
            capabilities: List of agent capabilities
            max_capacity: Maximum concurrent tasks
            metadata: Additional agent metadata
            user_id: User ID for filtering
            session_id: Session ID for filtering

        Returns:
            bool: Success status
        """
        try:
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                name=name,
                capabilities=capabilities,
                status=AgentStatus.IDLE,
                last_heartbeat=datetime.utcnow(),
                max_capacity=max_capacity,
                metadata=metadata or {},
                user_id=user_id,
                session_id=session_id
            )

            self._agents[agent_id] = agent_info

            # Notify about agent registration
            await self._streaming_service.send_agent_status_update(
                agent_id=agent_id,
                status="registered",
                user_id=user_id,
                additional_data={
                    "agent_type": agent_type,
                    "name": name,
                    "capabilities": capabilities,
                    "max_capacity": max_capacity
                }
            )

            self._polling_service.add_agent_status_event(
                agent_id=agent_id,
                status="registered",
                user_id=user_id,
                additional_data=agent_info.to_dict()
            )

            logger.info(f"Agent {agent_id} ({agent_type}) registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str, user_id: Optional[str] = None) -> bool:
        """
        Unregister an agent

        Args:
            agent_id: Agent identifier
            user_id: User ID for filtering

        Returns:
            bool: Success status
        """
        try:
            if agent_id in self._agents:
                # Update status
                self._agents[agent_id].status = AgentStatus.OFFLINE

                # Complete or reassign current tasks
                await self._reassign_agent_tasks(agent_id)

                # Remove agent
                agent_info = self._agents.pop(agent_id)

                # Notify about agent unregistration
                await self._streaming_service.send_agent_status_update(
                    agent_id=agent_id,
                    status="unregistered",
                    user_id=user_id,
                    additional_data=agent_info.to_dict()
                )

                self._polling_service.add_agent_status_event(
                    agent_id=agent_id,
                    status="unregistered",
                    user_id=user_id,
                    additional_data=agent_info.to_dict()
                )

                logger.info(f"Agent {agent_id} unregistered successfully")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        current_load: Optional[int] = None,
        current_tasks: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update agent status

        Args:
            agent_id: Agent identifier
            status: New status
            current_load: Current task load
            current_tasks: List of current task IDs
            metadata: Additional metadata
            user_id: User ID for filtering

        Returns:
            bool: Success status
        """
        try:
            if agent_id in self._agents:
                agent_info = self._agents[agent_id]
                agent_info.status = status
                agent_info.last_heartbeat = datetime.utcnow()

                if current_load is not None:
                    agent_info.current_load = current_load
                if current_tasks is not None:
                    agent_info.current_tasks = current_tasks
                if metadata:
                    agent_info.metadata.update(metadata)

                # Broadcast status update
                await self._streaming_service.send_agent_status_update(
                    agent_id=agent_id,
                    status=status.value,
                    user_id=user_id,
                    additional_data={
                        "current_load": agent_info.current_load,
                        "current_tasks": agent_info.current_tasks,
                        "metadata": agent_info.metadata
                    }
                )

                self._polling_service.add_agent_status_event(
                    agent_id=agent_id,
                    status=status.value,
                    user_id=user_id,
                    additional_data={
                        "current_load": agent_info.current_load,
                        "current_tasks": agent_info.current_tasks,
                        "metadata": agent_info.metadata
                    }
                )

                return True

            return False

        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} status: {e}")
            return False

    async def create_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        assigned_to: Optional[str] = None,
        created_by: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        timeout: int = 300,
        user_id: Optional[str] = None
    ) -> str:
        """
        Create a new task

        Args:
            task_type: Type of task
            data: Task data
            priority: Task priority
            assigned_to: Specific agent to assign to
            created_by: Who created the task
            dependencies: Task dependencies
            timeout: Task timeout in seconds
            user_id: User ID for filtering

        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())

        task = AgentTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            assigned_to=assigned_to,
            created_by=created_by,
            data=data,
            dependencies=dependencies or [],
            timeout=timeout
        )

        self._tasks[task_id] = task

        # Try to assign task
        await self._assign_task(task_id, user_id=user_id)

        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id

    async def update_task_progress(
        self,
        task_id: str,
        progress: float,
        message: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update task progress

        Args:
            task_id: Task identifier
            progress: Progress percentage (0.0-1.0)
            message: Progress message
            agent_id: Agent updating the progress
            user_id: User ID for filtering

        Returns:
            bool: Success status
        """
        try:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.progress = progress

                if message:
                    task.data["progress_message"] = message

                # Broadcast progress update
                await self._streaming_service.send_task_progress(
                    task_id=task_id,
                    progress=progress,
                    agent_id=agent_id,
                    user_id=user_id,
                    message=message
                )

                self._polling_service.add_task_progress_event(
                    task_id=task_id,
                    progress=progress,
                    agent_id=agent_id,
                    user_id=user_id,
                    message=message
                )

                return True

            return False

        except Exception as e:
            logger.error(f"Failed to update task {task_id} progress: {e}")
            return False

    async def complete_task(
        self,
        task_id: str,
        result: Dict[str, Any],
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Complete a task

        Args:
            task_id: Task identifier
            result: Task result
            agent_id: Agent completing the task
            user_id: User ID for filtering

        Returns:
            bool: Success status
        """
        try:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.result = result

                # Update agent load
                if agent_id and agent_id in self._agents:
                    self._agents[agent_id].current_load -= 1
                    if task_id in self._agents[agent_id].current_tasks:
                        self._agents[agent_id].current_tasks.remove(task_id)

                # Broadcast task completion
                await self._streaming_service.send_task_completed(
                    task_id=task_id,
                    result=result,
                    agent_id=agent_id,
                    user_id=user_id
                )

                self._polling_service.add_task_completed_event(
                    task_id=task_id,
                    result=result,
                    agent_id=agent_id,
                    user_id=user_id
                )

                # Check for dependent tasks
                await self._check_dependent_tasks(task_id, user_id=user_id)

                logger.info(f"Task {task_id} completed successfully")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    async def fail_task(
        self,
        task_id: str,
        error: str,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Mark a task as failed

        Args:
            task_id: Task identifier
            error: Error message
            agent_id: Agent that failed the task
            user_id: User ID for filtering

        Returns:
            bool: Success status
        """
        try:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.error = error

                # Check if we should retry
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = "pending_retry"

                    # Schedule retry
                    asyncio.create_task(self._retry_task(task_id, delay=task.retry_count * 5, user_id=user_id))
                else:
                    task.status = "failed"
                    task.completed_at = datetime.utcnow()

                # Update agent load
                if agent_id and agent_id in self._agents:
                    self._agents[agent_id].current_load -= 1
                    if task_id in self._agents[agent_id].current_tasks:
                        self._agents[agent_id].current_tasks.remove(task_id)

                # Broadcast task failure
                await self._streaming_service.send_agent_status_update(
                    agent_id=agent_id or task.assigned_to,
                    status="task_failed",
                    user_id=user_id,
                    additional_data={
                        "task_id": task_id,
                        "error": error,
                        "retry_count": task.retry_count
                    }
                )

                self._polling_service.add_agent_status_event(
                    agent_id=agent_id or task.assigned_to,
                    status="task_failed",
                    user_id=user_id,
                    additional_data={
                        "task_id": task_id,
                        "error": error,
                        "retry_count": task.retry_count
                    }
                )

                logger.error(f"Task {task_id} failed: {error}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to fail task {task_id}: {e}")
            return False

    async def send_agent_message(
        self,
        message_type: MessageType,
        sender_id: str,
        recipient_id: Optional[str],
        data: Dict[str, Any],
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        requires_response: bool = False,
        user_id: Optional[str] = None
    ) -> str:
        """
        Send a message between agents

        Args:
            message_type: Type of message
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID (None for broadcast)
            data: Message data
            task_id: Related task ID
            correlation_id: Message correlation ID
            requires_response: Whether response is required
            user_id: User ID for filtering

        Returns:
            str: Message ID
        """
        message_id = str(uuid.uuid4())

        message = AgentMessage(
            message_id=message_id,
            message_type=message_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            task_id=task_id,
            data=data,
            correlation_id=correlation_id,
            requires_response=requires_response
        )

        # Send via streaming service
        event_data = message.to_dict()

        if recipient_id:
            # Send to specific agent
            event_data["target_agent"] = recipient_id
        else:
            # Broadcast to all agents
            event_data["broadcast"] = True

        await self._streaming_service.send_agent_status_update(
            agent_id=sender_id,
            status="message_sent",
            user_id=user_id,
            additional_data=event_data
        )

        # Also add to polling service
        self._polling_service.add_agent_status_event(
            agent_id=sender_id,
            status="message_sent",
            user_id=user_id,
            additional_data=event_data
        )

        return message_id

    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information"""
        return self._agents.get(agent_id)

    def get_task_info(self, task_id: str) -> Optional[AgentTask]:
        """Get task information"""
        return self._tasks.get(task_id)

    def get_agents_by_type(self, agent_type: str) -> List[AgentInfo]:
        """Get all agents of a specific type"""
        return [agent for agent in self._agents.values() if agent.agent_type == agent_type]

    def get_available_agents(self, capability: Optional[str] = None) -> List[AgentInfo]:
        """Get available agents for task assignment"""
        available = [
            agent for agent in self._agents.values()
            if agent.status in [AgentStatus.IDLE, AgentStatus.BUSY] and
            agent.current_load < agent.max_capacity
        ]

        if capability:
            available = [agent for agent in available if capability in agent.capabilities]

        return available

    def get_agent_tasks(self, agent_id: str) -> List[AgentTask]:
        """Get all tasks for a specific agent"""
        return [task for task in self._tasks.values() if task.assigned_to == agent_id]

    def get_pending_tasks(self) -> List[AgentTask]:
        """Get all pending tasks"""
        return [task for task in self._tasks.values() if task.status in ["pending", "pending_retry"]]

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        total_load = sum(agent.current_load for agent in self._agents.values())
        max_capacity = sum(agent.max_capacity for agent in self._agents.values())

        return {
            "total_agents": len(self._agents),
            "total_tasks": len(self._tasks),
            "pending_tasks": len(self.get_pending_tasks()),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == "completed"]),
            "failed_tasks": len([t for t in self._tasks.values() if t.status == "failed"]),
            "total_load": total_load,
            "max_capacity": max_capacity,
            "utilization": (total_load / max_capacity * 100) if max_capacity > 0 else 0,
            "active_agents": len([a for a in self._agents.values() if a.status != AgentStatus.OFFLINE])
        }

    # Private helper methods

    async def _assign_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Assign a task to an available agent"""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return False

            # Check dependencies
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id in self._tasks and self._tasks[dep_id].status != "completed":
                        # Dependency not completed yet
                        return False

            # Find suitable agent
            if task.assigned_to:
                # Specific agent requested
                agent = self._agents.get(task.assigned_to)
                if agent and agent.current_load < agent.max_capacity:
                    await self._execute_task(task_id, task.assigned_to, user_id=user_id)
                    return True
            else:
                # Find best available agent
                available_agents = self.get_available_agents()

                # Sort by current load (least busy first)
                available_agents.sort(key=lambda a: a.current_load)

                for agent in available_agents:
                    await self._execute_task(task_id, agent.agent_id, user_id=user_id)
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to assign task {task_id}: {e}")
            return False

    async def _execute_task(self, task_id: str, agent_id: str, user_id: Optional[str] = None):
        """Execute a task on a specific agent"""
        try:
            task = self._tasks[task_id]
            agent = self._agents[agent_id]

            # Update task
            task.assigned_to = agent_id
            task.status = "running"
            task.started_at = datetime.utcnow()

            # Update agent
            agent.current_load += 1
            agent.current_tasks.append(task_id)
            agent.status = AgentStatus.BUSY if agent.current_load >= agent.max_capacity else AgentStatus.PROCESSING

            # Send task to agent via HTTP streaming
            await self._streaming_service.send_agent_status_update(
                agent_id=agent_id,
                status="task_assigned",
                user_id=user_id,
                additional_data={
                    "task_id": task_id,
                    "task_type": task.task_type,
                    "task_data": task.data,
                    "current_load": agent.current_load
                }
            )

            self._polling_service.add_agent_status_event(
                agent_id=agent_id,
                status="task_assigned",
                user_id=user_id,
                additional_data={
                    "task_id": task_id,
                    "task_type": task.task_type,
                    "task_data": task.data
                }
            )

            logger.info(f"Task {task_id} assigned to agent {agent_id}")

        except Exception as e:
            logger.error(f"Failed to execute task {task_id} on agent {agent_id}: {e}")

    async def _reassign_agent_tasks(self, agent_id: str):
        """Reassign tasks from an offline agent"""
        try:
            agent_tasks = self.get_agent_tasks(agent_id)

            for task in agent_tasks:
                if task.status in ["running", "pending"]:
                    task.assigned_to = None
                    task.status = "pending"
                    await self._assign_task(task.task_id)

            logger.info(f"Reassigned {len(agent_tasks)} tasks from agent {agent_id}")

        except Exception as e:
            logger.error(f"Failed to reassign tasks from agent {agent_id}: {e}")

    async def _check_dependent_tasks(self, completed_task_id: str, user_id: Optional[str] = None):
        """Check and assign dependent tasks"""
        try:
            for task in self._tasks.values():
                if completed_task_id in task.dependencies and task.status == "pending":
                    await self._assign_task(task.task_id, user_id=user_id)

        except Exception as e:
            logger.error(f"Failed to check dependent tasks for {completed_task_id}: {e}")

    async def _retry_task(self, task_id: str, delay: int, user_id: Optional[str] = None):
        """Retry a failed task"""
        try:
            await asyncio.sleep(delay)

            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = "pending"
                task.error = None
                await self._assign_task(task_id, user_id=user_id)

        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")

    async def _heartbeat_monitor(self):
        """Monitor agent heartbeats"""
        while True:
            try:
                current_time = datetime.utcnow()
                timeout_delta = timedelta(seconds=self._heartbeat_interval * 2)  # 2 intervals

                for agent_id, agent in list(self._agents.items()):
                    if current_time - agent.last_heartbeat > timeout_delta:
                        logger.warning(f"Agent {agent_id} missed heartbeat")

                        if agent.status != AgentStatus.OFFLINE:
                            agent.status = AgentStatus.OFFLINE
                            await self._reassign_agent_tasks(agent_id)

                await asyncio.sleep(self._heartbeat_interval)

            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(60)

    async def _task_timeout_monitor(self):
        """Monitor task timeouts"""
        while True:
            try:
                current_time = datetime.utcnow()

                for task_id, task in list(self._tasks.items()):
                    if (task.status == "running" and task.started_at and
                        current_time - task.started_at > timedelta(seconds=task.timeout)):

                        logger.warning(f"Task {task_id} timed out")
                        await self.fail_task(
                            task_id=task_id,
                            error="Task timed out",
                            agent_id=task.assigned_to
                        )

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in task timeout monitor: {e}")
                await asyncio.sleep(60)

    async def _cleanup_monitor(self):
        """Clean up old completed tasks"""
        while True:
            try:
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(hours=24)  # Keep 24 hours

                tasks_to_remove = [
                    task_id for task_id, task in self._tasks.items()
                    if (task.status in ["completed", "failed"] and
                        task.completed_at and task.completed_at < cutoff_time)
                ]

                for task_id in tasks_to_remove:
                    del self._tasks[task_id]

                if tasks_to_remove:
                    logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

                await asyncio.sleep(3600)  # Run every hour

            except Exception as e:
                logger.error(f"Error in cleanup monitor: {e}")
                await asyncio.sleep(3600)


# Create singleton instance
agent_orchestrator = HTTPAgentOrchestrator()


def get_agent_orchestrator() -> HTTPAgentOrchestrator:
    """Get the agent orchestrator singleton"""
    return agent_orchestrator


# Export for use in routers
__all__ = [
    'HTTPAgentOrchestrator',
    'get_agent_orchestrator',
    'AgentStatus',
    'TaskPriority',
    'MessageType',
    'AgentTask',
    'AgentMessage',
    'AgentInfo'
]