"""
Failover Manager for Multi-Agent System
Provides robust failover mechanisms with hot standby agents and automatic recovery
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import json
import uuid

from ...database.manager import get_database_manager
from .load_balancer import get_load_balancer, AgentStatus

logger = logging.getLogger(__name__)


class FailoverStrategy(Enum):
    """Failover strategies"""

    HOT_STANDBY = "hot_standby"
    COLD_STANDBY = "cold_standby"
    ACTIVE_ACTIVE = "active_active"
    GRACEFUL_DEGRADATION = "graceful_degradation"


class RecoveryAction(Enum):
    """Recovery actions"""

    RESTART_AGENT = "restart_agent"
    FAILOVER_TO_STANDBY = "failover_to_standby"
    SCALE_UP = "scale_up"
    RESET_CIRCUIT_BREAKER = "reset_circuit_breaker"
    UPDATE_CONFIG = "update_config"


@dataclass
class FailoverPolicy:
    """Failover policy configuration"""

    agent_type: str
    strategy: FailoverStrategy
    max_failures: int = 3
    failure_window: int = 300  # seconds
    recovery_timeout: int = 60  # seconds
    retry_attempts: int = 3
    hot_standby_count: int = 1
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    health_check_interval: int = 30
    escalation_threshold: float = 0.5  # 50% failure rate


@dataclass
class FailoverEvent:
    """Failover event record"""

    event_id: str
    agent_id: str
    agent_type: str
    failure_type: str
    timestamp: datetime
    recovery_action: Optional[RecoveryAction] = None
    recovery_status: str = "pending"  # pending, in_progress, completed, failed
    standby_activated: Optional[str] = None
    recovery_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HotStandbyManager:
    """Manages hot standby agents for critical services"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Hot standby pool for each agent type
        self.standby_pools: Dict[str, List[str]] = {}

        # Standby agent configs
        self.standby_configs: Dict[str, Dict[str, Any]] = {}

        # Active and status tracking
        self.active_standby_agents: Dict[str, Dict[str, Any]] = {}
        self.standby_health: Dict[str, Dict[str, Any]] = {}

        # Load balancer reference
        self.load_balancer = None

        self.logger.info("Hot Standby Manager initialized")

    async def initialize(self):
        """Initialize hot standby manager"""
        try:
            self.load_balancer = await get_load_balancer()

            # Initialize standby pools
            await self._initialize_standby_pools()

            # Start health monitoring for standby agents
            asyncio.create_task(self._standby_health_monitoring())

            self.logger.info("Hot standby manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize hot standby manager: {e}")
            return False

    async def create_standby_agent(
        self, agent_type: str, config: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new standby agent"""
        try:
            standby_id = f"{agent_type}_standby_{uuid.uuid4().hex[:8]}"

            # Create standby configuration
            standby_config = {
                **config,
                "standby_id": standby_id,
                "standby_type": agent_type,
                "is_standby": True,
                "hot_standby": True,
                "auto_activate": True,
                "activation_delay": 0,  # Immediate activation
            }

            # Store standby config
            self.standby_configs[standby_id] = standby_config

            # Add to standby pool
            if agent_type not in self.standby_pools:
                self.standby_pools[agent_type] = []
            self.standby_pools[agent_type].append(standby_id)

            # Initialize standby agent
            await self._initialize_standby_agent(standby_id, standby_config)

            # Register with load balancer
            await self.load_balancer.register_agent(
                standby_id,
                agent_type,
                standby_config.get("capabilities", []),
                max_concurrent_tasks=standby_config.get("max_concurrent_tasks", 5),
                weight=standby_config.get("weight", 0.5),  # Lower weight for standby
            )

            self.logger.info(
                f"Created standby agent: {standby_id} for type: {agent_type}"
            )
            return standby_id

        except Exception as e:
            self.logger.error(f"Failed to create standby agent: {e}")
            return None

    async def activate_standby_agent(
        self, standby_id: str, primary_agent_id: str
    ) -> bool:
        """Activate a standby agent to replace a failed primary"""
        try:
            if standby_id not in self.standby_configs:
                self.logger.error(f"Standby agent not found: {standby_id}")
                return False

            standby_config = self.standby_configs[standby_id]

            # Update standby agent configuration for activation
            activation_config = {
                **standby_config,
                "is_active": True,
                "is_standby": False,
                "replacing_agent": primary_agent_id,
                "activated_at": datetime.now().isoformat(),
            }

            # Mark standby as active
            self.active_standby_agents[standby_id] = {
                "primary_agent": primary_agent_id,
                "activated_at": datetime.now(),
                "activation_config": activation_config,
            }

            # Update agent in load balancer with higher priority
            self.load_balancer.agent_metrics[standby_id].weight = 1.0
            self.load_balancer.agent_metrics[standby_id].status = AgentStatus.HEALTHY

            # Re-register with updated configuration
            await self.load_balancer.register_agent(
                standby_id,
                standby_config["standby_type"],
                standby_config.get("capabilities", []),
                max_concurrent_tasks=standby_config.get(
                    "max_concurrent_tasks", 10
                ),  # Increase capacity
                weight=1.0,  # Full weight for active agent
            )

            self.logger.info(
                f"Activated standby agent: {standby_id} to replace: {primary_agent_id}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to activate standby agent {standby_id}: {e}")
            return False

    async def deactivate_standby_agent(self, standby_id: str) -> bool:
        """Deactivate a standby agent (return to standby mode)"""
        try:
            if standby_id not in self.active_standby_agents:
                self.logger.warning(f"Standby agent not active: {standby_id}")
                return False

            # Remove from active agents
            del self.active_standby_agents[standby_id]

            # Reset agent configuration
            standby_config = self.standby_configs.get(standby_id, {})
            standby_config.update(
                {"is_active": False, "is_standby": True, "replacing_agent": None}
            )

            # Update agent in load balancer with lower priority
            if standby_id in self.load_balancer.agent_metrics:
                self.load_balancer.agent_metrics[standby_id].weight = 0.5
                self.load_balancer.agent_metrics[
                    standby_id
                ].status = AgentStatus.HEALTHY

            self.logger.info(f"Deactivated standby agent: {standby_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to deactivate standby agent {standby_id}: {e}")
            return False

    async def get_standby_status(self) -> Dict[str, Any]:
        """Get comprehensive standby status"""
        try:
            status = {
                "total_standby_agents": len(self.standby_configs),
                "active_standby_agents": len(self.active_standby_agents),
                "standby_pools": {},
                "health_status": {},
                "timestamp": datetime.now().isoformat(),
            }

            # Pool status
            for agent_type, pool in self.standby_pools.items():
                status["standby_pools"][agent_type] = {
                    "total": len(pool),
                    "available": len(
                        [sid for sid in pool if sid not in self.active_standby_agents]
                    ),
                    "active": len(
                        [sid for sid in pool if sid in self.active_standby_agents]
                    ),
                }

            # Health status
            for standby_id, config in self.standby_configs.items():
                agent_type = config["standby_type"]
                health = await self._check_standby_health(standby_id)
                status["health_status"][standby_id] = {
                    "agent_type": agent_type,
                    "is_active": standby_id in self.active_standby_agents,
                    "health": health,
                }

            return status

        except Exception as e:
            self.logger.error(f"Failed to get standby status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def _initialize_standby_pools(self):
        """Initialize default standby pools"""
        try:
            default_standby_config = {
                "max_concurrent_tasks": 5,
                "weight": 0.5,
                "health_check_interval": 30,
                "capabilities": [],
            }

            # Create standby agents for critical roles
            critical_roles = ["ceo", "strategy", "devops"]

            for role in critical_roles:
                # Create 2 standby agents for each critical role
                for i in range(2):
                    role_config = {
                        **default_standby_config,
                        "capabilities": self._get_role_capabilities(role),
                    }
                    await self.create_standby_agent(role, role_config)

        except Exception as e:
            self.logger.error(f"Failed to initialize standby pools: {e}")

    async def _initialize_standby_agent(self, standby_id: str, config: Dict[str, Any]):
        """Initialize a specific standby agent"""
        try:
            # This would initialize the actual agent
            # For now, just set up the configuration
            pass

        except Exception as e:
            self.logger.error(f"Failed to initialize standby agent {standby_id}: {e}")

    async def _standby_health_monitoring(self):
        """Monitor health of standby agents"""
        while True:
            try:
                for standby_id, config in self.standby_configs.items():
                    health = await self._check_standby_health(standby_id)
                    self.standby_health[standby_id] = health

                    # If health is poor and agent is not active, attempt recovery
                    if (
                        health.get("status") == "unhealthy"
                        and standby_id not in self.active_standby_agents
                    ):
                        await self._recover_standby_agent(standby_id)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Standby health monitoring error: {e}")
                await asyncio.sleep(60)

    async def _check_standby_health(self, standby_id: str) -> Dict[str, Any]:
        """Check health of a standby agent"""
        try:
            if standby_id not in self.load_balancer.agent_metrics:
                return {"status": "not_found"}

            metrics = self.load_balancer.agent_metrics[standby_id]

            # Simple health check
            if metrics.status == AgentStatus.HEALTHY:
                return {"status": "healthy"}
            elif metrics.status == AgentStatus.DEGRADED:
                return {"status": "degraded"}
            else:
                return {"status": "unhealthy"}

        except Exception as e:
            self.logger.error(f"Failed to check standby health {standby_id}: {e}")
            return {"status": "error", "error": str(e)}

    async def _recover_standby_agent(self, standby_id: str):
        """Recover a failed standby agent"""
        try:
            self.logger.info(f"Recovering standby agent: {standby_id}")

            # Reset agent metrics
            if standby_id in self.load_balancer.agent_metrics:
                metrics = self.load_balancer.agent_metrics[standby_id]
                metrics.status = AgentStatus.HEALTHY
                metrics.consecutive_failures = 0
                metrics.error_count = 0

            # Reset circuit breaker
            if standby_id in self.load_balancer.circuit_breakers:
                self.load_balancer.circuit_breakers[standby_id].state = "CLOSED"
                self.load_balancer.circuit_breakers[standby_id].failure_count = 0

            self.logger.info(f"Recovery completed for standby agent: {standby_id}")

        except Exception as e:
            self.logger.error(f"Failed to recover standby agent {standby_id}: {e}")

    def _get_role_capabilities(self, role: str) -> List[str]:
        """Get capabilities for a specific role"""
        capabilities = {
            "ceo": [
                "strategic_planning",
                "decision_making",
                "coordination",
                "oversight",
                "risk_assessment",
                "business_development",
            ],
            "strategy": [
                "market_research",
                "competitive_analysis",
                "financial_planning",
                "business_strategy",
                "investment_analysis",
                "growth_planning",
            ],
            "devops": [
                "technical_architecture",
                "system_design",
                "infrastructure_planning",
                "security_assessment",
                "performance_optimization",
                "cicd_implementation",
            ],
        }
        return capabilities.get(role, [])


class FailoverManager:
    """Main failover manager for multi-agent system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Failover policies
        self.policies: Dict[str, FailoverPolicy] = {}

        # Failover events tracking
        self.failover_events: Dict[str, FailoverEvent] = []

        # Hot standby manager
        self.standby_manager = HotStandbyManager(config.get("hot_standby", {}))

        # Database manager
        self.db_manager = None

        # Recovery handlers
        self.recovery_handlers: Dict[RecoveryAction, Callable] = {}

        # Monitoring
        self.monitoring_enabled = config.get("monitoring_enabled", True)
        self.monitoring_interval = config.get("monitoring_interval", 30)

        self.logger.info("Failover Manager initialized")

    async def initialize(self):
        """Initialize failover manager"""
        try:
            self.db_manager = await get_database_manager()

            # Initialize standby manager
            await self.standby_manager.initialize()

            # Setup default failover policies
            await self._setup_default_policies()

            # Setup recovery handlers
            await self._setup_recovery_handlers()

            # Start monitoring if enabled
            if self.monitoring_enabled:
                asyncio.create_task(self._monitoring_loop())

            self.logger.info("Failover manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize failover manager: {e}")
            return False

    async def handle_agent_failure(
        self, agent_id: str, failure_type: str, error_details: str
    ) -> bool:
        """Handle agent failure with appropriate failover action"""
        try:
            self.logger.warning(f"Agent failure detected: {agent_id} ({failure_type})")

            # Create failover event
            event_id = str(uuid.uuid4())
            event = FailoverEvent(
                event_id=event_id,
                agent_id=agent_id,
                agent_type=self._get_agent_type(agent_id),
                failure_type=failure_type,
                timestamp=datetime.now(),
                metadata={"error_details": error_details},
            )

            self.failover_events[event_id] = event

            # Get failover policy for agent type
            agent_type = event.agent_type
            policy = self.policies.get(agent_type)

            if not policy:
                self.logger.error(f"No failover policy for agent type: {agent_type}")
                return False

            # Check if failover should be triggered
            if not await self._should_trigger_failover(agent_id, policy):
                self.logger.info(f"Failover not triggered for agent: {agent_id}")
                return True

            # Execute failover strategy
            success = await self._execute_failover_strategy(agent_id, policy, event)

            # Update event status
            event.recovery_status = "completed" if success else "failed"

            # Store event in database
            await self._store_failover_event(event)

            self.logger.info(f"Failover handled for agent {agent_id}: {success}")
            return success

        except Exception as e:
            self.logger.error(f"Failed to handle agent failure {agent_id}: {e}")
            return False

    async def trigger_manual_failover(self, agent_id: str, reason: str) -> bool:
        """Trigger manual failover for an agent"""
        try:
            self.logger.info(
                f"Manual failover triggered for agent: {agent_id} ({reason})"
            )

            return await self.handle_agent_failure(
                agent_id, "manual_failover", f"Manual failover: {reason}"
            )

        except Exception as e:
            self.logger.error(f"Failed to trigger manual failover {agent_id}: {e}")
            return False

    async def add_failover_policy(self, policy: FailoverPolicy) -> bool:
        """Add or update failover policy"""
        try:
            self.policies[policy.agent_type] = policy
            await self._store_failover_policy(policy)
            self.logger.info(f"Added failover policy for: {policy.agent_type}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add failover policy: {e}")
            return False

    async def get_failover_status(self) -> Dict[str, Any]:
        """Get comprehensive failover status"""
        try:
            status = {
                "policies": {
                    ptype: policy.__dict__ for ptype, policy in self.policies.items()
                },
                "recent_events": [],
                "standby_status": await self.standby_manager.get_standby_status(),
                "statistics": await self._get_failover_statistics(),
                "timestamp": datetime.now().isoformat(),
            }

            # Recent failover events (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            for event in self.failover_events.values():
                if event.timestamp > cutoff_time:
                    status["recent_events"].append(
                        {
                            "event_id": event.event_id,
                            "agent_id": event.agent_id,
                            "agent_type": event.agent_type,
                            "failure_type": event.failure_type,
                            "timestamp": event.timestamp.isoformat(),
                            "recovery_action": event.recovery_action.value
                            if event.recovery_action
                            else None,
                            "recovery_status": event.recovery_status,
                            "standby_activated": event.standby_activated,
                            "recovery_time": event.recovery_time,
                        }
                    )

            return status

        except Exception as e:
            self.logger.error(f"Failed to get failover status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def _should_trigger_failover(
        self, agent_id: str, policy: FailoverPolicy
    ) -> bool:
        """Check if failover should be triggered based on policy"""
        try:
            # Get recent failures for this agent
            recent_failures = [
                event
                for event in self.failover_events.values()
                if event.agent_id == agent_id
                and event.timestamp
                > datetime.now() - timedelta(seconds=policy.failure_window)
            ]

            # Check failure count threshold
            if len(recent_failures) >= policy.max_failures:
                return True

            # Check escalation threshold
            if policy.escalation_threshold > 0:
                # Get failure rate (would need agent metrics for this)
                # For now, trigger on consecutive failures
                if len(recent_failures) >= 2:  # Simple threshold
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to check failover conditions: {e}")
            return False

    async def _execute_failover_strategy(
        self, agent_id: str, policy: FailoverPolicy, event: FailoverEvent
    ) -> bool:
        """Execute the appropriate failover strategy"""
        try:
            if policy.strategy == FailoverStrategy.HOT_STANDBY:
                return await self._execute_hot_standby_failover(agent_id, policy, event)
            elif policy.strategy == FailoverStrategy.COLD_STANDBY:
                return await self._execute_cold_standby_failover(
                    agent_id, policy, event
                )
            elif policy.strategy == FailoverStrategy.ACTIVE_ACTIVE:
                return await self._execute_active_active_failover(
                    agent_id, policy, event
                )
            elif policy.strategy == FailoverStrategy.GRACEFUL_DEGRADATION:
                return await self._execute_graceful_degradation(agent_id, policy, event)
            else:
                self.logger.error(f"Unknown failover strategy: {policy.strategy}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to execute failover strategy: {e}")
            return False

    async def _execute_hot_standby_failover(
        self, agent_id: str, policy: FailoverPolicy, event: FailoverEvent
    ) -> bool:
        """Execute hot standby failover"""
        try:
            start_time = datetime.now()

            # Get available standby agent
            agent_type = event.agent_type
            standby_pool = self.standby_manager.standby_pools.get(agent_type, [])

            # Find available standby agent
            available_standby = None
            for standby_id in standby_pool:
                if standby_id not in self.standby_manager.active_standby_agents:
                    health = await self.standby_manager._check_standby_health(
                        standby_id
                    )
                    if health.get("status") == "healthy":
                        available_standby = standby_id
                        break

            if not available_standby:
                self.logger.error(f"No available standby agent for: {agent_type}")
                return False

            # Activate standby agent
            success = await self.standby_manager.activate_standby_agent(
                available_standby, agent_id
            )

            if success:
                # Update event details
                event.recovery_action = RecoveryAction.FAILOVER_TO_STANDBY
                event.standby_activated = available_standby
                event.recovery_time = (datetime.now() - start_time).total_seconds()

                self.logger.info(
                    f"Hot standby failover completed: {agent_id} -> {available_standby}"
                )
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to execute hot standby failover: {e}")
            return False

    async def _execute_cold_standby_failover(
        self, agent_id: str, policy: FailoverPolicy, event: FailoverEvent
    ) -> bool:
        """Execute cold standby failover"""
        try:
            # For cold standby, we need to create a new agent instance
            # This would involve provisioning resources and initializing the agent
            self.logger.info("Cold standby failover not yet implemented")
            return False

        except Exception as e:
            self.logger.error(f"Failed to execute cold standby failover: {e}")
            return False

    async def _execute_active_active_failover(
        self, agent_id: str, policy: FailoverPolicy, event: FailoverEvent
    ) -> bool:
        """Execute active-active failover"""
        try:
            # For active-active, simply redirect traffic to other active agents
            # This would involve updating load balancer weights
            self.logger.info("Active-active failover not yet implemented")
            return False

        except Exception as e:
            self.logger.error(f"Failed to execute active-active failover: {e}")
            return False

    async def _execute_graceful_degradation(
        self, agent_id: str, policy: FailoverPolicy, event: FailoverEvent
    ) -> bool:
        """Execute graceful degradation"""
        try:
            # Mark agent as degraded but don't failover immediately
            # Allow system to continue with reduced capacity
            self.logger.info("Graceful degradation not yet implemented")
            return True

        except Exception as e:
            self.logger.error(f"Failed to execute graceful degradation: {e}")
            return False

    async def _setup_default_policies(self):
        """Setup default failover policies for critical agent types"""
        try:
            default_policies = [
                FailoverPolicy(
                    agent_type="ceo",
                    strategy=FailoverStrategy.HOT_STANDBY,
                    max_failures=2,
                    failure_window=300,
                    recovery_timeout=60,
                    hot_standby_count=2,
                    recovery_actions=[
                        RecoveryAction.FAILOVER_TO_STANDBY,
                        RecoveryAction.RESTART_AGENT,
                    ],
                ),
                FailoverPolicy(
                    agent_type="strategy",
                    strategy=FailoverStrategy.HOT_STANDBY,
                    max_failures=3,
                    failure_window=300,
                    recovery_timeout=60,
                    hot_standby_count=1,
                    recovery_actions=[RecoveryAction.FAILOVER_TO_STANDBY],
                ),
                FailoverPolicy(
                    agent_type="devops",
                    strategy=FailoverStrategy.HOT_STANDBY,
                    max_failures=3,
                    failure_window=300,
                    recovery_timeout=60,
                    hot_standby_count=1,
                    recovery_actions=[RecoveryAction.FAILOVER_TO_STANDBY],
                ),
            ]

            for policy in default_policies:
                await self.add_failover_policy(policy)

        except Exception as e:
            self.logger.error(f"Failed to setup default policies: {e}")

    async def _setup_recovery_handlers(self):
        """Setup recovery action handlers"""
        try:
            self.recovery_handlers[RecoveryAction.RESTART_AGENT] = (
                self._handle_restart_agent
            )
            self.recovery_handlers[RecoveryAction.FAILOVER_TO_STANDBY] = (
                self._handle_failover_to_standby
            )
            self.recovery_handlers[RecoveryAction.SCALE_UP] = self._handle_scale_up
            self.recovery_handlers[RecoveryAction.RESET_CIRCUIT_BREAKER] = (
                self._handle_reset_circuit_breaker
            )
            self.recovery_handlers[RecoveryAction.UPDATE_CONFIG] = (
                self._handle_update_config
            )

        except Exception as e:
            self.logger.error(f"Failed to setup recovery handlers: {e}")

    async def _monitoring_loop(self):
        """Main monitoring loop for failover detection"""
        while True:
            try:
                await self._monitor_agent_health()
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Failover monitoring error: {e}")
                await asyncio.sleep(60)

    async def _monitor_agent_health(self):
        """Monitor health of all agents and trigger failover if needed"""
        try:
            # Get load balancer status
            load_balancer = await get_load_balancer()
            stats = await load_balancer.get_load_balancer_stats()

            # Check each agent
            for agent_id, agent_info in stats.get("agents", {}).items():
                status = agent_info.get("status")
                consecutive_failures = agent_info.get("consecutive_failures", 0)

                if status == "unhealthy" or consecutive_failures >= 3:
                    await self.handle_agent_failure(
                        agent_id,
                        "health_monitoring",
                        f"Agent status: {status}, consecutive failures: {consecutive_failures}",
                    )

        except Exception as e:
            self.logger.error(f"Failed to monitor agent health: {e}")

    def _get_agent_type(self, agent_id: str) -> str:
        """Extract agent type from agent ID"""
        for prefix in ["ceo", "strategy", "devops"]:
            if agent_id.startswith(prefix):
                return prefix
        return "unknown"

    async def _store_failover_event(self, event: FailoverEvent):
        """Store failover event in database"""
        try:
            if not self.db_manager:
                return

            event_data = {
                "event_id": event.event_id,
                "agent_id": event.agent_id,
                "agent_type": event.agent_type,
                "failure_type": event.failure_type,
                "timestamp": event.timestamp.isoformat(),
                "recovery_action": event.recovery_action.value
                if event.recovery_action
                else None,
                "recovery_status": event.recovery_status,
                "standby_activated": event.standby_activated,
                "recovery_time": event.recovery_time,
                "metadata": event.metadata,
            }

            # Store in database (implementation depends on schema)
            await self.db_manager.create_agent_task(
                {
                    **event_data,
                    "task_type": "failover_event",
                    "task_status": event.recovery_status,
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to store failover event: {e}")

    async def _store_failover_policy(self, policy: FailoverPolicy):
        """Store failover policy in database"""
        try:
            if not self.db_manager:
                return

            policy_data = {
                "agent_type": policy.agent_type,
                "strategy": policy.strategy.value,
                "max_failures": policy.max_failures,
                "failure_window": policy.failure_window,
                "recovery_timeout": policy.recovery_timeout,
                "retry_attempts": policy.retry_attempts,
                "hot_standby_count": policy.hot_standby_count,
                "recovery_actions": [
                    action.value for action in policy.recovery_actions
                ],
                "health_check_interval": policy.health_check_interval,
                "escalation_threshold": policy.escalation_threshold,
            }

            # Store in database
            await self.db_manager.store_agent_memory("failover_policy", policy_data)

        except Exception as e:
            self.logger.error(f"Failed to store failover policy: {e}")

    async def _get_failover_statistics(self) -> Dict[str, Any]:
        """Get failover statistics"""
        try:
            cutoff_time = datetime.now() - timedelta(days=7)  # Last 7 days

            recent_events = [
                event
                for event in self.failover_events.values()
                if event.timestamp > cutoff_time
            ]

            return {
                "total_failover_events": len(recent_events),
                "successful_failovers": len(
                    [e for e in recent_events if e.recovery_status == "completed"]
                ),
                "failed_failovers": len(
                    [e for e in recent_events if e.recovery_status == "failed"]
                ),
                "average_recovery_time": sum(
                    e.recovery_time or 0 for e in recent_events
                )
                / len(recent_events)
                if recent_events
                else 0,
                "failovers_by_agent_type": {
                    agent_type: len(
                        [e for e in recent_events if e.agent_type == agent_type]
                    )
                    for agent_type in set(e.agent_type for e in recent_events)
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get failover statistics: {e}")
            return {}

    # Recovery action handlers
    async def _handle_restart_agent(self, agent_id: str, event: FailoverEvent) -> bool:
        """Handle agent restart"""
        try:
            # Implementation would restart the agent
            self.logger.info(f"Restarting agent: {agent_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False

    async def _handle_failover_to_standby(
        self, agent_id: str, event: FailoverEvent
    ) -> bool:
        """Handle failover to standby agent"""
        try:
            # This is handled in hot standby failover
            return True

        except Exception as e:
            self.logger.error(f"Failed to failover to standby: {e}")
            return False

    async def _handle_scale_up(self, agent_id: str, event: FailoverEvent) -> bool:
        """Handle scaling up resources"""
        try:
            # Implementation would scale up agent resources
            self.logger.info(f"Scaling up resources for agent: {agent_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to scale up agent {agent_id}: {e}")
            return False

    async def _handle_reset_circuit_breaker(
        self, agent_id: str, event: FailoverEvent
    ) -> bool:
        """Handle circuit breaker reset"""
        try:
            load_balancer = await get_load_balancer()
            if agent_id in load_balancer.circuit_breakers:
                load_balancer.circuit_breakers[agent_id].state = "CLOSED"
                load_balancer.circuit_breakers[agent_id].failure_count = 0

            self.logger.info(f"Reset circuit breaker for agent: {agent_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset circuit breaker {agent_id}: {e}")
            return False

    async def _handle_update_config(self, agent_id: str, event: FailoverEvent) -> bool:
        """Handle configuration update"""
        try:
            # Implementation would update agent configuration
            self.logger.info(f"Updating configuration for agent: {agent_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update config for agent {agent_id}: {e}")
            return False


# Global failover manager instance
_failover_manager: Optional[FailoverManager] = None


async def get_failover_manager(
    config: Optional[Dict[str, Any]] = None,
) -> FailoverManager:
    """Get global failover manager instance"""
    global _failover_manager
    if _failover_manager is None:
        default_config = {
            "hot_standby": {"default_standby_count": 2, "health_check_interval": 30},
            "monitoring_enabled": True,
            "monitoring_interval": 30,
        }
        _failover_manager = FailoverManager(config or default_config)
        await _failover_manager.initialize()
    return _failover_manager
