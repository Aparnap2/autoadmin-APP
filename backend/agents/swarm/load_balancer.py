"""
Load Balancer for Multi-Agent System
Provides intelligent task distribution with load-aware routing and failover capabilities
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import uuid

from ...database.manager import get_database_manager

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESPONSE_TIME_BASED = "response_time_based"
    CAPABILITY_BASED = "capability_based"


class AgentStatus(Enum):
    """Agent health status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"
    FAILED = "failed"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""

    agent_id: str
    agent_type: str
    current_load: int = 0
    max_concurrent_tasks: int = 5
    average_response_time: float = 0.0  # milliseconds
    success_rate: float = 1.0
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    total_tasks_processed: int = 0
    weight: float = 1.0
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.HEALTHY
    consecutive_failures: int = 0
    recovery_attempts: int = 0


@dataclass
class TaskAssignment:
    """Task assignment record"""

    task_id: str
    agent_id: str
    assigned_at: datetime
    priority: str
    expected_duration: int
    capabilities_required: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


class CircuitBreaker:
    """Circuit breaker for preventing cascade failures"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        return (
            self.last_failure_time
            and datetime.now() - self.last_failure_time
            > timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class AgentLoadBalancer:
    """Advanced load balancer for multi-agent system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Load balancing strategy
        self.strategy = LoadBalancingStrategy(
            config.get("strategy", "capability_based")
        )

        # Agent registry and metrics
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.task_assignments: Dict[str, TaskAssignment] = {}

        # Circuit breakers for each agent
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Load balancing state
        self.round_robin_index = 0
        self.weighted_round_robin_weights: Dict[str, float] = {}

        # Hot standby agents for critical roles
        self.hot_standby_agents: Dict[str, List[str]] = {
            "ceo": ["ceo_backup_1", "ceo_backup_2"],
            "strategy": ["strategy_backup_1"],
            "devops": ["devops_backup_1"],
        }

        # Database manager for persistence
        self.db_manager = None

        # Health monitoring
        self.health_check_interval = config.get("health_check_interval", 30)
        self.agent_timeout = config.get("agent_timeout", 120)

        self.logger.info("Agent Load Balancer initialized")

    async def initialize(self):
        """Initialize load balancer"""
        try:
            self.db_manager = await get_database_manager()

            # Load existing agent metrics from database
            await self._load_agent_metrics()

            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())

            self.logger.info("Load balancer initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize load balancer: {e}")
            return False

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        max_concurrent_tasks: int = 5,
        weight: float = 1.0,
    ) -> bool:
        """Register a new agent for load balancing"""
        try:
            metrics = AgentMetrics(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=capabilities,
                max_concurrent_tasks=max_concurrent_tasks,
                weight=weight,
                last_heartbeat=datetime.now(),
            )

            self.agent_metrics[agent_id] = metrics

            # Create circuit breaker for agent
            self.circuit_breakers[agent_id] = CircuitBreaker(
                failure_threshold=self.config.get("circuit_breaker_threshold", 5),
                recovery_timeout=self.config.get("circuit_breaker_timeout", 60),
            )

            # Store in database
            await self._store_agent_metrics(metrics)

            self.logger.info(f"Registered agent: {agent_id} ({agent_type})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def assign_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Assign task to best available agent"""
        try:
            task_id = task_data.get("id", str(uuid.uuid4()))
            task_type = task_data.get("type", "general")
            priority = task_data.get("priority", "medium")
            capabilities_required = task_data.get("capabilities_required", [])

            # Get eligible agents
            eligible_agents = await self._get_eligible_agents(
                task_type, capabilities_required, priority
            )

            if not eligible_agents:
                self.logger.warning(f"No eligible agents for task {task_id}")
                # Try failover to hot standby agents
                return await self._attempt_failover_assignment(task_data)

            # Select best agent based on strategy
            selected_agent_id = await self._select_agent(eligible_agents, task_data)

            if not selected_agent_id:
                self.logger.warning(f"Failed to select agent for task {task_id}")
                return None

            # Create task assignment
            assignment = TaskAssignment(
                task_id=task_id,
                agent_id=selected_agent_id,
                assigned_at=datetime.now(),
                priority=priority,
                expected_duration=task_data.get("expected_duration", 300),
                capabilities_required=capabilities_required,
            )

            self.task_assignments[task_id] = assignment

            # Update agent load
            self.agent_metrics[selected_agent_id].current_load += 1

            # Store assignment in database
            await self._store_task_assignment(assignment)

            self.logger.info(f"Assigned task {task_id} to agent {selected_agent_id}")
            return selected_agent_id

        except Exception as e:
            self.logger.error(f"Failed to assign task: {e}")
            return None

    async def complete_task(
        self, task_id: str, success: bool, response_time: float = 0.0
    ):
        """Mark task as completed and update agent metrics"""
        try:
            if task_id not in self.task_assignments:
                self.logger.warning(f"Task assignment not found: {task_id}")
                return

            assignment = self.task_assignments[task_id]
            agent_id = assignment.agent_id

            if agent_id not in self.agent_metrics:
                self.logger.warning(f"Agent not found: {agent_id}")
                return

            metrics = self.agent_metrics[agent_id]

            # Update metrics
            metrics.current_load = max(0, metrics.current_load - 1)
            metrics.total_tasks_processed += 1
            metrics.last_heartbeat = datetime.now()

            if success:
                # Update success rate
                metrics.success_rate = metrics.success_rate * 0.9 + 1.0 * 0.1
                # Update response time
                if response_time > 0:
                    metrics.average_response_time = (
                        metrics.average_response_time * 0.8 + response_time * 0.2
                    )
                # Reset consecutive failures
                metrics.consecutive_failures = 0

                # Update circuit breaker
                if agent_id in self.circuit_breakers:
                    self.circuit_breakers[agent_id]._on_success()
            else:
                # Update error metrics
                metrics.error_count += 1
                metrics.consecutive_failures += 1

                # Update success rate
                metrics.success_rate = metrics.success_rate * 0.9

                # Update circuit breaker
                if agent_id in self.circuit_breakers:
                    self.circuit_breakers[agent_id]._on_failure()

                # Check if agent needs to be marked as unhealthy
                if metrics.consecutive_failures >= 5:
                    metrics.status = AgentStatus.UNHEALTHY
                    self.logger.warning(
                        f"Agent {agent_id} marked as unhealthy due to consecutive failures"
                    )

            # Clean up assignment
            del self.task_assignments[task_id]

            # Store updated metrics
            await self._store_agent_metrics(metrics)

            self.logger.info(
                f"Completed task {task_id} by agent {agent_id}, success: {success}"
            )

        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")

    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an agent"""
        try:
            if agent_id not in self.agent_metrics:
                return None

            metrics = self.agent_metrics[agent_id]
            circuit_breaker = self.circuit_breakers.get(agent_id)

            return {
                "agent_id": metrics.agent_id,
                "agent_type": metrics.agent_type,
                "status": metrics.status.value,
                "current_load": metrics.current_load,
                "max_concurrent_tasks": metrics.max_concurrent_tasks,
                "success_rate": metrics.success_rate,
                "average_response_time": metrics.average_response_time,
                "error_count": metrics.error_count,
                "total_tasks_processed": metrics.total_tasks_processed,
                "capabilities": metrics.capabilities,
                "last_heartbeat": metrics.last_heartbeat.isoformat()
                if metrics.last_heartbeat
                else None,
                "circuit_breaker_state": circuit_breaker.state
                if circuit_breaker
                else "UNKNOWN",
                "consecutive_failures": metrics.consecutive_failures,
            }

        except Exception as e:
            self.logger.error(f"Failed to get agent status {agent_id}: {e}")
            return None

    async def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics"""
        try:
            stats = {
                "total_agents": len(self.agent_metrics),
                "healthy_agents": sum(
                    1
                    for m in self.agent_metrics.values()
                    if m.status == AgentStatus.HEALTHY
                ),
                "degraded_agents": sum(
                    1
                    for m in self.agent_metrics.values()
                    if m.status == AgentStatus.DEGRADED
                ),
                "unhealthy_agents": sum(
                    1
                    for m in self.agent_metrics.values()
                    if m.status == AgentStatus.UNHEALTHY
                ),
                "active_tasks": len(self.task_assignments),
                "total_capacity": sum(
                    m.max_concurrent_tasks for m in self.agent_metrics.values()
                ),
                "current_load": sum(
                    m.current_load for m in self.agent_metrics.values()
                ),
                "load_percentage": 0.0,
                "strategy": self.strategy.value,
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate load percentage
            if stats["total_capacity"] > 0:
                stats["load_percentage"] = (
                    stats["current_load"] / stats["total_capacity"]
                ) * 100

            # Per-agent breakdown
            stats["agents"] = {}
            for agent_id, metrics in self.agent_metrics.items():
                circuit_breaker = self.circuit_breakers.get(agent_id)
                stats["agents"][agent_id] = {
                    "type": metrics.agent_type,
                    "status": metrics.status.value,
                    "load": metrics.current_load,
                    "capacity": metrics.max_concurrent_tasks,
                    "utilization": (metrics.current_load / metrics.max_concurrent_tasks)
                    * 100
                    if metrics.max_concurrent_tasks > 0
                    else 0,
                    "success_rate": metrics.success_rate,
                    "response_time": metrics.average_response_time,
                    "circuit_breaker": circuit_breaker.state
                    if circuit_breaker
                    else "UNKNOWN",
                }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get load balancer stats: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def _get_eligible_agents(
        self, task_type: str, capabilities_required: List[str], priority: str
    ) -> List[str]:
        """Get list of eligible agents for task"""
        eligible = []

        for agent_id, metrics in self.agent_metrics.items():
            # Check agent status
            if metrics.status not in [AgentStatus.HEALTHY, AgentStatus.DEGRADED]:
                continue

            # Check circuit breaker
            if agent_id in self.circuit_breakers:
                cb = self.circuit_breakers[agent_id]
                if cb.state == "OPEN":
                    continue

            # Check capacity
            if metrics.current_load >= metrics.max_concurrent_tasks:
                continue

            # Check capabilities
            if capabilities_required:
                if not any(
                    cap in metrics.capabilities for cap in capabilities_required
                ):
                    continue

            # Check agent type compatibility
            if task_type != "general" and task_type not in metrics.agent_type:
                continue

            eligible.append(agent_id)

        return eligible

    async def _select_agent(
        self, eligible_agents: List[str], task_data: Dict[str, Any]
    ) -> Optional[str]:
        """Select best agent based on load balancing strategy"""
        if not eligible_agents:
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(eligible_agents)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(eligible_agents)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(eligible_agents)
        elif self.strategy == LoadBalancingStrategy.RESPONSE_TIME_BASED:
            return self._response_time_based_select(eligible_agents)
        elif self.strategy == LoadBalancingStrategy.CAPABILITY_BASED:
            return self._capability_based_select(eligible_agents, task_data)
        else:
            # Default to round robin
            return self._round_robin_select(eligible_agents)

    def _round_robin_select(self, eligible_agents: List[str]) -> str:
        """Round robin agent selection"""
        agent = eligible_agents[self.round_robin_index % len(eligible_agents)]
        self.round_robin_index += 1
        return agent

    def _least_connections_select(self, eligible_agents: List[str]) -> str:
        """Select agent with least current connections"""
        return min(
            eligible_agents, key=lambda aid: self.agent_metrics[aid].current_load
        )

    def _weighted_round_robin_select(self, eligible_agents: List[str]) -> str:
        """Weighted round robin selection"""
        # Calculate weights
        weights = []
        for agent_id in eligible_agents:
            metrics = self.agent_metrics[agent_id]
            weight = metrics.weight

            # Adjust weight based on current load
            load_factor = 1.0 - (metrics.current_load / metrics.max_concurrent_tasks)
            adjusted_weight = weight * load_factor
            weights.append((agent_id, adjusted_weight))

        # Select based on highest adjusted weight
        weights.sort(key=lambda x: x[1], reverse=True)
        return weights[0][0]

    def _response_time_based_select(self, eligible_agents: List[str]) -> str:
        """Select agent based on response time"""
        return min(
            eligible_agents,
            key=lambda aid: self.agent_metrics[aid].average_response_time,
        )

    def _capability_based_select(
        self, eligible_agents: List[str], task_data: Dict[str, Any]
    ) -> str:
        """Select agent based on capability matching and performance"""
        capabilities_required = task_data.get("capabilities_required", [])

        if not capabilities_required:
            return self._least_connections_select(eligible_agents)

        # Score agents based on capability match and performance
        scores = []
        for agent_id in eligible_agents:
            metrics = self.agent_metrics[agent_id]

            # Capability match score
            capability_score = 0
            for cap in capabilities_required:
                if cap in metrics.capabilities:
                    capability_score += 1

            capability_score = capability_score / len(capabilities_required)

            # Performance score
            performance_score = metrics.success_rate
            load_factor = 1.0 - (metrics.current_load / metrics.max_concurrent_tasks)

            # Combined score
            total_score = (
                capability_score * 0.4 + performance_score * 0.3 + load_factor * 0.3
            )
            scores.append((agent_id, total_score))

        # Select agent with highest score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    async def _attempt_failover_assignment(
        self, task_data: Dict[str, Any]
    ) -> Optional[str]:
        """Attempt to assign task to hot standby agents"""
        try:
            task_type = task_data.get("type", "general")

            # Get hot standby agents for this task type
            standby_agents = self.hot_standby_agents.get(task_type, [])

            for standby_id in standby_agents:
                if standby_id in self.agent_metrics:
                    metrics = self.agent_metrics[standby_id]

                    # Check if standby agent is available
                    if (
                        metrics.status == AgentStatus.HEALTHY
                        and metrics.current_load < metrics.max_concurrent_tasks
                    ):
                        self.logger.info(
                            f"Failing over task to standby agent: {standby_id}"
                        )
                        return await self.assign_task(
                            {
                                **task_data,
                                "force_agent": standby_id,
                                "is_failover": True,
                            }
                        )

            self.logger.warning(
                f"No available standby agents for task type: {task_type}"
            )
            return None

        except Exception as e:
            self.logger.error(f"Failover assignment failed: {e}")
            return None

    async def _health_monitoring_loop(self):
        """Monitor agent health and update status"""
        while True:
            try:
                await self._check_agent_health()
                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)

    async def _check_agent_health(self):
        """Check health of all registered agents"""
        current_time = datetime.now()

        for agent_id, metrics in self.agent_metrics.items():
            # Check heartbeat timeout
            if metrics.last_heartbeat:
                time_since_heartbeat = current_time - metrics.last_heartbeat
                if time_since_heartbeat > timedelta(seconds=self.agent_timeout):
                    if metrics.status == AgentStatus.HEALTHY:
                        metrics.status = AgentStatus.DEGRADED
                        self.logger.warning(
                            f"Agent {agent_id} degraded due to heartbeat timeout"
                        )
                    elif time_since_heartbeat > timedelta(
                        seconds=self.agent_timeout * 2
                    ):
                        metrics.status = AgentStatus.UNHEALTHY
                        self.logger.warning(f"Agent {agent_id} marked as unhealthy")

            # Check error rate
            if metrics.total_tasks_processed > 10:
                error_rate = metrics.error_count / metrics.total_tasks_processed
                if error_rate > 0.3:  # 30% error rate threshold
                    metrics.status = AgentStatus.UNHEALTHY
                    self.logger.warning(
                        f"Agent {agent_id} marked as unhealthy due to high error rate: {error_rate:.2f}"
                    )

            # Store updated metrics
            await self._store_agent_metrics(metrics)

    async def _load_agent_metrics(self):
        """Load agent metrics from database"""
        try:
            if not self.db_manager:
                return

            # Implementation would load from database
            # For now, start with empty registry
            pass

        except Exception as e:
            self.logger.error(f"Failed to load agent metrics: {e}")

    async def _store_agent_metrics(self, metrics: AgentMetrics):
        """Store agent metrics in database"""
        try:
            if not self.db_manager:
                return

            metrics_data = {
                "agent_id": metrics.agent_id,
                "agent_type": metrics.agent_type,
                "current_load": metrics.current_load,
                "max_concurrent_tasks": metrics.max_concurrent_tasks,
                "average_response_time": metrics.average_response_time,
                "success_rate": metrics.success_rate,
                "error_count": metrics.error_count,
                "total_tasks_processed": metrics.total_tasks_processed,
                "weight": metrics.weight,
                "capabilities": metrics.capabilities,
                "status": metrics.status.value,
                "consecutive_failures": metrics.consecutive_failures,
                "last_heartbeat": metrics.last_heartbeat.isoformat()
                if metrics.last_heartbeat
                else None,
                "updated_at": datetime.now().isoformat(),
            }

            # Store in database (implementation depends on schema)
            await self.db_manager.update_agent_state(metrics.agent_id, metrics_data)

        except Exception as e:
            self.logger.error(f"Failed to store agent metrics: {e}")

    async def _store_task_assignment(self, assignment: TaskAssignment):
        """Store task assignment in database"""
        try:
            if not self.db_manager:
                return

            assignment_data = {
                "task_id": assignment.task_id,
                "agent_id": assignment.agent_id,
                "assigned_at": assignment.assigned_at.isoformat(),
                "priority": assignment.priority,
                "expected_duration": assignment.expected_duration,
                "capabilities_required": assignment.capabilities_required,
                "retry_count": assignment.retry_count,
                "max_retries": assignment.max_retries,
            }

            # Store in database
            await self.db_manager.create_agent_task(
                {
                    **assignment_data,
                    "task_type": "load_balanced",
                    "assigned_agent": assignment.agent_id,
                    "task_status": "assigned",
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to store task assignment: {e}")


# Global load balancer instance
_load_balancer: Optional[AgentLoadBalancer] = None


async def get_load_balancer(
    config: Optional[Dict[str, Any]] = None,
) -> AgentLoadBalancer:
    """Get global load balancer instance"""
    global _load_balancer
    if _load_balancer is None:
        default_config = {
            "strategy": "capability_based",
            "health_check_interval": 30,
            "agent_timeout": 120,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 60,
        }
        _load_balancer = AgentLoadBalancer(config or default_config)
        await _load_balancer.initialize()
    return _load_balancer
