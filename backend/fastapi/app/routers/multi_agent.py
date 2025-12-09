"""
Multi-Agent Orchestration API Endpoints
Provides REST API for load balancing, failover, health monitoring, and orchestration
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import logging

from agents.swarm.orchestrator import AgentOrchestrator
from agents.swarm.load_balancer import get_load_balancer
from agents.swarm.failover_manager import get_failover_manager
from agents.swarm.health_monitor import get_health_monitor
from database.manager import get_database_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/multi-agent", tags=["multi-agent"])

# Global orchestrator instance
_orchestrator: Optional[AgentOrchestrator] = None


# Pydantic models for API
class TaskRequest(BaseModel):
    """Task request model"""
    message: str = Field(..., description="Task message/prompt")
    priority: str = Field(default="medium", description="Task priority (low, medium, high, urgent)")
    agent_type: Optional[str] = Field(default=None, description="Preferred agent type")
    capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TaskResponse(BaseModel):
    """Task response model"""
    success: bool
    task_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    agent_assigned: Optional[str] = None
    processing_time: Optional[float] = None
    timestamp: str


class AgentStatus(BaseModel):
    """Agent status model"""
    agent_id: str
    agent_type: str
    status: str
    current_load: int
    max_concurrent_tasks: int
    success_rate: float
    average_response_time: float
    capabilities: List[str]
    last_heartbeat: Optional[str] = None
    circuit_breaker_state: Optional[str] = None


class ManualFailoverRequest(BaseModel):
    """Manual failover request"""
    agent_type: str = Field(..., description="Agent type to failover")
    reason: str = Field(..., description="Reason for failover")


class HealthAlert(BaseModel):
    """Health alert model"""
    alert_id: str
    agent_id: str
    severity: str
    message: str
    metric_type: str
    value: float
    threshold: float
    timestamp: str
    acknowledged: bool = False
    resolved: bool = False


# Dependency to get orchestrator
async def get_orchestrator() -> AgentOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        # Initialize orchestrator with default config
        config = {
            "load_balancer": {
                "strategy": "capability_based",
                "health_check_interval": 30,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_timeout": 60
            },
            "failover": {
                "hot_standby": {
                    "default_standby_count": 2,
                    "health_check_interval": 30
                },
                "monitoring_enabled": True
            },
            "health_monitor": {
                "check_interval": 30,
                "metrics_retention_hours": 24,
                "alert_thresholds": {
                    "response_time": {"warning": 5000, "critical": 10000},
                    "success_rate": {"warning": 0.9, "critical": 0.8},
                    "error_rate": {"warning": 0.1, "critical": 0.2}
                }
            }
        }

        _orchestrator = AgentOrchestrator(config)
        await _orchestrator.initialize()

    return _orchestrator


# Task management endpoints
@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_request: TaskRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Create and process a new task"""
    try:
        start_time = datetime.now()

        # Prepare task input
        task_input = {
            "id": task_request.metadata.get("task_id", f"task_{datetime.now().timestamp()}"),
            "message": task_request.message,
            "priority": task_request.priority,
            "agent_type": task_request.agent_type,
            "capabilities": task_request.capabilities,
            "metadata": task_request.metadata
        }

        # Process task with failover
        result = await orchestrator.process_task_with_failover(task_input)

        processing_time = (datetime.now() - start_time).total_seconds()

        return TaskResponse(
            success=result.get("success", False),
            task_id=task_input["id"],
            result=result.get("result") if result.get("success") else None,
            error=result.get("error"),
            agent_assigned=result.get("agent_assigned"),
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get status of a specific task"""
    try:
        # Get task from database or orchestrator
        # This would need to be implemented based on your task storage

        return {
            "task_id": task_id,
            "status": "not_found",
            "message": f"Task {task_id} not found",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent management endpoints
@router.get("/agents", response_model=List[AgentStatus])
async def get_all_agents(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get status of all agents"""
    try:
        # Get enhanced agent status from orchestrator
        status = await orchestrator.get_enhanced_agent_status()

        agents = []
        for agent_id, agent_info in status.items():
            if "error" not in agent_info:
                load_balancer_info = agent_info.get("load_balancer_info", {})

                agents.append(AgentStatus(
                    agent_id=agent_id,
                    agent_type=agent_info.get("agent_type", "unknown"),
                    status=agent_info.get("status", "unknown"),
                    current_load=load_balancer_info.get("load", 0),
                    max_concurrent_tasks=load_balancer_info.get("capacity", 5),
                    success_rate=load_balancer_info.get("success_rate", 0.0),
                    average_response_time=load_balancer_info.get("response_time", 0.0),
                    capabilities=agent_info.get("capabilities", []),
                    last_heartbeat=load_balancer_info.get("last_heartbeat"),
                    circuit_breaker_state=load_balancer_info.get("circuit_breaker_state")
                ))

        return agents

    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentStatus)
async def get_agent_status(
    agent_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get status of a specific agent"""
    try:
        # Get load balancer agent status
        load_balancer = await get_load_balancer()
        status = await load_balancer.get_agent_status(agent_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return AgentStatus(
            agent_id=status["agent_id"],
            agent_type=status["agent_type"],
            status=status["status"],
            current_load=status["current_load"],
            max_concurrent_tasks=status["max_concurrent_tasks"],
            success_rate=status["success_rate"],
            average_response_time=status["average_response_time"],
            capabilities=status["capabilities"],
            last_heartbeat=status["last_heartbeat"],
            circuit_breaker_state=status["circuit_breaker_state"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent status {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Load balancing endpoints
@router.get("/load-balancer/status")
async def get_load_balancer_status():
    """Get load balancer status and statistics"""
    try:
        load_balancer = await get_load_balancer()
        stats = await load_balancer.get_load_balancer_stats()

        return {
            "load_balancer": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get load balancer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load-balancer/strategy")
async def get_load_balancing_strategy():
    """Get current load balancing strategy"""
    try:
        load_balancer = await get_load_balancer()

        return {
            "strategy": load_balancer.strategy.value,
            "description": str(load_balancer.strategy),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get load balancing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Failover management endpoints
@router.post("/failover/trigger")
async def trigger_manual_failover(
    failover_request: ManualFailoverRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Trigger manual failover for an agent type"""
    try:
        success = await orchestrator.trigger_manual_failover(
            failover_request.agent_type,
            failover_request.reason
        )

        return {
            "success": success,
            "message": f"Manual failover {'triggered' if success else 'failed'} for {failover_request.agent_type}",
            "agent_type": failover_request.agent_type,
            "reason": failover_request.reason,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to trigger manual failover: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failover/status")
async def get_failover_status():
    """Get failover system status"""
    try:
        failover_manager = await get_failover_manager()
        status = await failover_manager.get_failover_status()

        return {
            "failover_manager": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get failover status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failover/policies")
async def get_failover_policies():
    """Get failover policies"""
    try:
        failover_manager = await get_failover_manager()
        status = await failover_manager.get_failover_status()
        policies = status.get("policies", {})

        return {
            "policies": policies,
            "total_policies": len(policies),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get failover policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failover/standby")
async def get_standby_status():
    """Get standby agent status"""
    try:
        failover_manager = await get_failover_manager()
        status = await failover_manager.get_failover_status()
        standby_status = status.get("standby_status", {})

        return {
            "standby_agents": standby_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get standby status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health monitoring endpoints
@router.get("/health/system")
async def get_system_health():
    """Get overall system health"""
    try:
        health_monitor = await get_health_monitor()
        health = await health_monitor.get_system_health()

        return {
            "system_health": health,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/agents/{agent_id}")
async def get_agent_health(agent_id: str):
    """Get health of a specific agent"""
    try:
        health_monitor = await get_health_monitor()
        result = await health_monitor.check_agent_health(agent_id)

        return {
            "agent_id": agent_id,
            "health_status": result.status.value,
            "health_score": result.score,
            "metrics": {metric_type.value: value for metric_type, value in result.metrics.items()},
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "metric_type": alert.metric_type.value,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in result.alerts
            ],
            "timestamp": result.timestamp.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get agent health {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/alerts", response_model=List[HealthAlert])
async def get_health_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status")
):
    """Get health alerts"""
    try:
        health_monitor = await get_health_monitor()
        system_health = await health_monitor.get_system_health()

        # Get alerts from health monitor
        alerts = []
        # This would need to be implemented to get all alerts from health_monitor

        # Filter alerts
        filtered_alerts = []
        for alert in alerts:
            if severity and alert.severity.value != severity:
                continue
            if agent_id and alert.agent_id != agent_id:
                continue
            if resolved is not None and alert.resolved != resolved:
                continue

            filtered_alerts.append(HealthAlert(
                alert_id=alert.alert_id,
                agent_id=alert.agent_id,
                severity=alert.severity.value,
                message=alert.message,
                metric_type=alert.metric_type.value,
                value=alert.value,
                threshold=alert.threshold,
                timestamp=alert.timestamp.isoformat(),
                acknowledged=alert.acknowledged,
                resolved=alert.resolved
            ))

        return filtered_alerts

    except Exception as e:
        logger.error(f"Failed to get health alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health/alerts/{alert_id}/acknowledge")
async def acknowledge_health_alert(
    alert_id: str,
    user_id: str = Query(..., description="User ID acknowledging the alert")
):
    """Acknowledge a health alert"""
    try:
        health_monitor = await get_health_monitor()
        success = await health_monitor.acknowledge_alert(alert_id, user_id)

        return {
            "success": success,
            "message": f"Alert {alert_id} {'acknowledged' if success else 'not found'}",
            "alert_id": alert_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health/alerts/{alert_id}/resolve")
async def resolve_health_alert(
    alert_id: str,
    resolution: str = Query(..., description="Resolution description")
):
    """Resolve a health alert"""
    try:
        health_monitor = await get_health_monitor()
        success = await health_monitor.resolve_alert(alert_id, resolution)

        return {
            "success": success,
            "message": f"Alert {alert_id} {'resolved' if success else 'not found'}",
            "alert_id": alert_id,
            "resolution": resolution,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Orchestration endpoints
@router.get("/orchestration/status")
async def get_orchestration_status(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get comprehensive orchestration status"""
    try:
        status = await orchestrator.get_orchestrator_status()

        return {
            "orchestration_status": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get orchestration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orchestration/metrics")
async def get_orchestration_metrics(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Get orchestration metrics"""
    try:
        status = await orchestrator.get_orchestrator_status()
        metrics = status.get("orchestrator", {}).get("metrics", {})

        return {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get orchestration metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orchestration/shutdown")
async def shutdown_orchestrator(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """Shutdown orchestrator gracefully"""
    try:
        await orchestrator.shutdown()

        return {
            "success": True,
            "message": "Orchestrator shutdown successfully",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to shutdown orchestrator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Database endpoints
@router.get("/database/status")
async def get_database_status():
    """Get database system status"""
    try:
        db_manager = await get_database_manager()
        health = await db_manager.health_check()
        stats = await db_manager.get_system_stats()

        return {
            "database_health": health,
            "database_stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Admin endpoints
@router.get("/admin/dashboard")
async def get_admin_dashboard():
    """Get admin dashboard overview"""
    try:
        orchestrator = await get_orchestrator()
        load_balancer = await get_load_balancer()
        failover_manager = await get_failover_manager()
        health_monitor = await get_health_monitor()
        db_manager = await get_database_manager()

        # Collect all status information
        orchestration_status = await orchestrator.get_orchestrator_status()
        load_balancer_stats = await load_balancer.get_load_balancer_stats()
        failover_status = await failover_manager.get_failover_status()
        system_health = await health_monitor.get_system_health()
        database_health = await db_manager.health_check()

        # Build dashboard summary
        dashboard = {
            "overview": {
                "total_agents": load_balancer_stats.get("total_agents", 0),
                "healthy_agents": load_balancer_stats.get("healthy_agents", 0),
                "active_tasks": load_balancer_stats.get("active_tasks", 0),
                "system_health": system_health.get("average_health_score", 0),
                "database_status": database_health.get("overall_status", "unknown"),
                "timestamp": datetime.now().isoformat()
            },
            "orchestration": orchestration_status.get("orchestrator", {}),
            "agents": load_balancer_stats.get("agents", {}),
            "failover": failover_status.get("standby_status", {}),
            "health": {
                "critical_alerts": system_health.get("critical_alerts", 0),
                "active_alerts": system_health.get("active_alerts", 0)
            }
        }

        return dashboard

    except Exception as e:
        logger.error(f"Failed to get admin dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task cleanup
@router.on_event("shutdown")
async def cleanup():
    """Cleanup resources on shutdown"""
    global _orchestrator
    if _orchestrator:
        try:
            await _orchestrator.shutdown()
            _orchestrator = None
            logger.info("Orchestrator cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup orchestrator: {e}")