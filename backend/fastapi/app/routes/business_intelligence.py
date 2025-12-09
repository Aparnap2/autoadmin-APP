"""
HTTP-based Business Intelligence Router for AutoAdmin Backend
Replaces WebSocket-based real-time analytics with Server-Sent Events and HTTP polling
Provides comprehensive business intelligence through standard HTTP protocols
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Path, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic.types import PositiveInt, PositiveFloat

from app.services.http_streaming import get_streaming_service, EventType
from app.services.long_polling import get_long_polling_service
from app.services.agent_orchestrator import get_agent_orchestrator
from app.core.logging import get_logger
from app.middleware.error_handler import ValidationException

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/business-intelligence", tags=["Business Intelligence"])

# Pydantic models
class DateRange(BaseModel):
    """Date range for analytics queries"""
    start_date: datetime = Field(..., description="Start date for analytics")
    end_date: datetime = Field(..., description="End date for analytics")


class MetricFilter(BaseModel):
    """Filter for business metrics"""
    metric_name: Optional[str] = Field(None, description="Specific metric name")
    agent_types: Optional[List[str]] = Field(None, description="Filter by agent types")
    user_ids: Optional[List[str]] = Field(None, description="Filter by user IDs")
    task_types: Optional[List[str]] = Field(None, description="Filter by task types")
    status: Optional[List[str]] = Field(None, description="Filter by status")


class KPIRequest(BaseModel):
    """KPI calculation request"""
    kpi_types: List[str] = Field(..., description="KPI types to calculate")
    date_range: Optional[DateRange] = Field(None, description="Date range for KPIs")
    filters: Optional[MetricFilter] = Field(None, description="Filters for KPI calculation")
    comparison_period: Optional[str] = Field(None, description="Comparison period (week, month, quarter)")


class ReportRequest(BaseModel):
    """Business intelligence report request"""
    report_type: str = Field(..., description="Type of report to generate")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Report parameters")
    date_range: Optional[DateRange] = Field(None, description="Date range for report")
    format: str = Field(default="json", description="Output format (json, csv, xlsx)")
    delivery: Optional[str] = Field(None, description="Delivery method (download, email)")


class DashboardConfig(BaseModel):
    """Dashboard configuration"""
    dashboard_id: str = Field(..., description="Dashboard ID")
    widgets: List[Dict[str, Any]] = Field(..., description="Dashboard widgets")
    refresh_interval: int = Field(default=60, description="Refresh interval in seconds")
    filters: Optional[MetricFilter] = Field(None, description="Default filters")


class AlertRule(BaseModel):
    """Business intelligence alert rule"""
    rule_id: str = Field(..., description="Alert rule ID")
    name: str = Field(..., description="Alert rule name")
    condition: Dict[str, Any] = Field(..., description="Alert condition")
    threshold: Union[float, int, str] = Field(..., description="Alert threshold")
    severity: str = Field(default="medium", description="Alert severity (low, medium, high, critical)")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")


class KPICalculation(BaseModel):
    """KPI calculation result"""
    kpi_name: str
    value: Union[float, int, Decimal]
    unit: str
    trend: Optional[float] = None
    change_percentage: Optional[float] = None
    target: Optional[Union[float, int]] = None
    target_achievement: Optional[float] = None
    last_updated: datetime


class BusinessMetrics(BaseModel):
    """Comprehensive business metrics"""
    period: DateRange
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_task_duration: float
    agent_utilization: float
    task_success_rate: float
    user_engagement: Dict[str, Any]
    revenue_metrics: Optional[Dict[str, Any]] = None
    cost_metrics: Optional[Dict[str, Any]] = None
    efficiency_metrics: Dict[str, Any]


# In-memory storage for business intelligence data (in production, use database)
bi_storage = {
    "dashboards": {},
    "kpis": {},
    "reports": {},
    "alerts": {},
    "metrics_cache": {},
    "real_time_data": {}
}


@router.post("/kpis/calculate", summary="Calculate KPIs")
async def calculate_kpis(
    request: KPIRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate business KPIs with real-time updates

    Args:
        request: KPI calculation request
        background_tasks: FastAPI background tasks
        user_id: User ID for filtering

    Returns:
        Dict: KPI calculation results
    """
    try:
        orchestrator = get_agent_orchestrator()
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        # Get current statistics
        stats = orchestrator.get_orchestrator_stats()

        kpis = {}
        calculation_id = str(uuid.uuid4())

        # Calculate requested KPIs
        for kpi_type in request.kpi_types:
            kpi = await _calculate_single_kpi(kpi_type, stats, request, user_id)
            kpis[kpi_type] = kpi

        # Store KPI results
        bi_storage["kpis"][calculation_id] = {
            "id": calculation_id,
            "kpis": kpis,
            "calculated_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "filters": request.filters.dict() if request.filters else {},
            "date_range": request.date_range.dict() if request.date_range else None
        }

        # Send real-time KPI updates
        await streaming_service.send_system_notification(
            message=f"KPIs calculated: {', '.join(request.kpi_types)}",
            level="info",
            user_id=user_id
        )

        polling_service.add_notification_event(
            message=f"KPIs calculated: {', '.join(request.kpi_types)}",
            level="info",
            user_id=user_id,
            data={"calculation_id": calculation_id, "kpis": kpis}
        )

        # Schedule periodic KPI updates
        if request.date_range and request.date_range.end_date > datetime.utcnow():
            background_tasks.add_task(
                _schedule_kpi_updates,
                calculation_id,
                request,
                user_id
            )

        return {
            "success": True,
            "calculation_id": calculation_id,
            "kpis": kpis,
            "calculated_at": datetime.utcnow().isoformat(),
            "next_update": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to calculate KPIs: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate KPIs")


@router.get("/kpis/{calculation_id}", summary="Get KPI Results")
async def get_kpi_results(
    calculation_id: str = Path(..., description="KPI calculation ID"),
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get previously calculated KPI results

    Args:
        calculation_id: KPI calculation ID
        user_id: User ID for filtering

    Returns:
        Dict: KPI results
    """
    try:
        if calculation_id not in bi_storage["kpis"]:
            raise HTTPException(status_code=404, detail="KPI calculation not found")

        kpi_data = bi_storage["kpis"][calculation_id]

        # Check user permissions
        if user_id and kpi_data.get("user_id") and kpi_data["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "success": True,
            "calculation_id": calculation_id,
            "kpis": kpi_data["kpis"],
            "calculated_at": kpi_data["calculated_at"],
            "filters": kpi_data.get("filters", {}),
            "date_range": kpi_data.get("date_range")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get KPI results: {e}")
        raise HTTPException(status_code=500, detail="Failed to get KPI results")


@router.post("/dashboards", summary="Create Dashboard")
async def create_dashboard(
    config: DashboardConfig,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new business intelligence dashboard

    Args:
        config: Dashboard configuration
        user_id: User ID for filtering

    Returns:
        Dict: Dashboard creation result
    """
    try:
        dashboard_id = config.dashboard_id or str(uuid.uuid4())

        dashboard = {
            "id": dashboard_id,
            "config": config.dict(),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user_id,
            "last_accessed": None,
            "access_count": 0
        }

        bi_storage["dashboards"][dashboard_id] = dashboard

        # Send dashboard creation notification
        streaming_service = get_streaming_service()
        await streaming_service.send_system_notification(
            message=f"Dashboard '{config.dashboard_id}' created successfully",
            level="info",
            user_id=user_id
        )

        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "message": "Dashboard created successfully",
            "config": config.dict(),
            "created_at": dashboard["created_at"]
        }

    except Exception as e:
        logger.error(f"Failed to create dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to create dashboard")


@router.get("/dashboards/{dashboard_id}", summary="Get Dashboard")
async def get_dashboard(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get dashboard configuration and data

    Args:
        dashboard_id: Dashboard ID
        user_id: User ID for filtering

    Returns:
        Dict: Dashboard data
    """
    try:
        if dashboard_id not in bi_storage["dashboards"]:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        dashboard = bi_storage["dashboards"][dashboard_id]

        # Check user permissions
        if user_id and dashboard.get("created_by") and dashboard["created_by"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update access tracking
        dashboard["last_accessed"] = datetime.utcnow().isoformat()
        dashboard["access_count"] = dashboard.get("access_count", 0) + 1

        # Get real-time data for dashboard widgets
        streaming_service = get_streaming_service()
        orchestrator = get_agent_orchestrator()

        real_time_data = {}
        for widget in dashboard["config"]["widgets"]:
            widget_data = await _get_widget_data(widget, orchestrator, streaming_service, user_id)
            real_time_data[widget.get("id", f"widget_{len(real_time_data)}")] = widget_data

        return {
            "success": True,
            "dashboard_id": dashboard_id,
            "config": dashboard["config"],
            "real_time_data": real_time_data,
            "created_at": dashboard["created_at"],
            "last_accessed": dashboard["last_accessed"],
            "access_count": dashboard["access_count"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard")


@router.get("/dashboards/{dashboard_id}/stream", summary="Dashboard Real-time Stream")
async def get_dashboard_stream(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    user_id: Optional[str] = None,
    refresh_interval: int = Query(default=30, description="Refresh interval in seconds")
) -> StreamingResponse:
    """
    Get real-time data stream for dashboard using Server-Sent Events

    Args:
        dashboard_id: Dashboard ID
        user_id: User ID for filtering
        refresh_interval: Refresh interval in seconds

    Returns:
        StreamingResponse: SSE stream for dashboard data
    """
    try:
        if dashboard_id not in bi_storage["dashboards"]:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        dashboard = bi_storage["dashboards"][dashboard_id]

        # Check user permissions
        if user_id and dashboard.get("created_by") and dashboard["created_by"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        streaming_service = get_streaming_service()
        orchestrator = get_agent_orchestrator()

        # Create streaming connection
        client_id = await streaming_service.create_connection(
            user_id=user_id,
            filters={
                "dashboard_id": dashboard_id,
                "component": "business_intelligence"
            }
        )

        async def dashboard_data_generator():
            """Generate dashboard data events"""
            try:
                # Initial data
                config = dashboard["config"]
                widgets = config.get("widgets", [])

                for widget in widgets:
                    widget_data = await _get_widget_data(widget, orchestrator, streaming_service, user_id)
                    event_data = {
                        "dashboard_id": dashboard_id,
                        "widget_id": widget.get("id"),
                        "widget_type": widget.get("type"),
                        "data": widget_data,
                        "timestamp": datetime.utcnow().isoformat()
                    }

                    # Format as SSE
                    yield f"event: dashboard_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                # Continuous updates
                while True:
                    await asyncio.sleep(refresh_interval)

                    for widget in widgets:
                        widget_data = await _get_widget_data(widget, orchestrator, streaming_service, user_id)
                        event_data = {
                            "dashboard_id": dashboard_id,
                            "widget_id": widget.get("id"),
                            "widget_type": widget.get("type"),
                            "data": widget_data,
                            "timestamp": datetime.utcnow().isoformat()
                        }

                        yield f"event: dashboard_update\n"
                        yield f"data: {json.dumps(event_data)}\n\n"

            except Exception as e:
                logger.error(f"Error in dashboard stream: {e}")
                error_event = {
                    "dashboard_id": dashboard_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"event: dashboard_error\n"
                yield f"data: {json.dumps(error_event)}\n\n"
            finally:
                # Clean up connection
                await streaming_service.remove_connection(client_id)

        return StreamingResponse(
            dashboard_data_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Dashboard-ID": dashboard_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create dashboard stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create dashboard stream")


@router.post("/reports/generate", summary="Generate Business Report")
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a business intelligence report

    Args:
        request: Report generation request
        background_tasks: FastAPI background tasks
        user_id: User ID for filtering

    Returns:
        Dict: Report generation result
    """
    try:
        report_id = str(uuid.uuid4())

        # Initialize report
        report = {
            "id": report_id,
            "type": request.report_type,
            "status": "generating",
            "parameters": request.parameters,
            "date_range": request.date_range.dict() if request.date_range else None,
            "format": request.format,
            "delivery": request.delivery,
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "data": None,
            "error": None
        }

        bi_storage["reports"][report_id] = report

        # Send report generation started notification
        streaming_service = get_streaming_service()
        await streaming_service.send_system_notification(
            message=f"Report generation started: {request.report_type}",
            level="info",
            user_id=user_id
        )

        # Generate report in background
        background_tasks.add_task(
            _generate_report_data,
            report_id,
            request,
            user_id
        )

        return {
            "success": True,
            "report_id": report_id,
            "status": "generating",
            "message": "Report generation started",
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/reports/{report_id}", summary="Get Report Status")
async def get_report_status(
    report_id: str = Path(..., description="Report ID"),
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get report generation status and results

    Args:
        report_id: Report ID
        user_id: User ID for filtering

    Returns:
        Dict: Report status and data
    """
    try:
        if report_id not in bi_storage["reports"]:
            raise HTTPException(status_code=404, detail="Report not found")

        report = bi_storage["reports"][report_id]

        # Check user permissions
        if user_id and report.get("created_by") and report["created_by"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        response = {
            "success": True,
            "report_id": report_id,
            "status": report["status"],
            "created_at": report["created_at"],
            "type": report["type"],
            "format": report["format"]
        }

        if report["status"] == "completed":
            response["completed_at"] = report["completed_at"]
            response["data"] = report["data"]
        elif report["status"] == "failed":
            response["error"] = report["error"]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get report status")


@router.post("/alerts/rules", summary="Create Alert Rule")
async def create_alert_rule(
    rule: AlertRule,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a business intelligence alert rule

    Args:
        rule: Alert rule configuration
        user_id: User ID for filtering

    Returns:
        Dict: Alert rule creation result
    """
    try:
        rule_id = rule.rule_id or str(uuid.uuid4())

        alert_rule = {
            "id": rule_id,
            "name": rule.name,
            "condition": rule.condition,
            "threshold": rule.threshold,
            "severity": rule.severity,
            "enabled": rule.enabled,
            "notification_channels": rule.notification_channels,
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_triggered": None,
            "trigger_count": 0
        }

        bi_storage["alerts"][rule_id] = alert_rule

        # Send alert rule creation notification
        streaming_service = get_streaming_service()
        await streaming_service.send_system_notification(
            message=f"Alert rule '{rule.name}' created successfully",
            level="info",
            user_id=user_id
        )

        # Start monitoring for this rule
        if rule.enabled:
            streaming_service.send_agent_status_update(
                agent_id="alert_monitor",
                status="rule_added",
                user_id=user_id,
                additional_data={"rule_id": rule_id, "rule_name": rule.name}
            )

        return {
            "success": True,
            "rule_id": rule_id,
            "message": "Alert rule created successfully",
            "rule": alert_rule
        }

    except Exception as e:
        logger.error(f"Failed to create alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.get("/metrics/real-time", summary="Get Real-time Metrics")
async def get_real_time_metrics(
    metric_types: Optional[List[str]] = Query(None, description="Metric types to retrieve"),
    agent_types: Optional[List[str]] = Query(None, description="Filter by agent types"),
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get real-time business metrics

    Args:
        metric_types: Specific metric types to retrieve
        agent_types: Filter by agent types
        user_id: User ID for filtering

    Returns:
        Dict: Real-time metrics
    """
    try:
        orchestrator = get_agent_orchestrator()
        streaming_service = get_streaming_service()

        # Get current orchestrator stats
        stats = orchestrator.get_orchestrator_stats()

        # Get real-time streaming stats
        streaming_stats = await streaming_service.get_connection_stats()

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_metrics": stats,
            "streaming_metrics": streaming_stats,
            "performance_metrics": {
                "active_connections": streaming_stats["active_connections"],
                "total_events": streaming_stats["event_queue_size"],
                "system_load": _calculate_system_load()
            }
        }

        # Filter by agent types if specified
        if agent_types:
            metrics["agent_metrics"] = _filter_agent_metrics(stats, agent_types)

        # Filter by metric types if specified
        if metric_types:
            metrics = _filter_metrics(metrics, metric_types)

        return {
            "success": True,
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get real-time metrics")


@router.get("/health", summary="Business Intelligence Health Check")
async def health_check() -> Dict[str, Any]:
    """
    Health check for business intelligence services

    Returns:
        Dict: Health status
    """
    try:
        orchestrator = get_agent_orchestrator()
        streaming_service = get_streaming_service()
        polling_service = get_long_polling_service()

        # Get service statistics
        stats = orchestrator.get_orchestrator_stats()
        streaming_stats = await streaming_service.get_connection_stats()
        polling_stats = polling_service.get_stats()

        # Calculate health indicators
        health_score = _calculate_health_score(stats, streaming_stats, polling_stats)

        return {
            "status": "healthy" if health_score > 80 else "degraded",
            "health_score": health_score,
            "services": {
                "agent_orchestrator": {
                    "status": "healthy",
                    "agents": stats["total_agents"],
                    "active_agents": stats["active_agents"],
                    "utilization": stats["utilization"]
                },
                "streaming_service": {
                    "status": "healthy",
                    "connections": streaming_stats["active_connections"],
                    "event_queue_size": streaming_stats["event_queue_size"]
                },
                "polling_service": {
                    "status": "healthy",
                    "sessions": polling_stats["active_sessions"],
                    "events": polling_stats["total_events"]
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Helper functions

async def _calculate_single_kpi(
    kpi_type: str,
    stats: Dict[str, Any],
    request: KPIRequest,
    user_id: Optional[str]
) -> KPICalculation:
    """Calculate a single KPI based on type"""

    current_time = datetime.utcnow()

    if kpi_type == "agent_utilization":
        value = stats.get("utilization", 0)
        return KPICalculation(
            kpi_name="Agent Utilization",
            value=value,
            unit="%",
            target=80.0,
            target_achievement=(value / 80.0) * 100 if 80.0 > 0 else 0,
            last_updated=current_time
        )

    elif kpi_type == "task_completion_rate":
        total_tasks = stats.get("total_tasks", 1)
        completed_tasks = stats.get("completed_tasks", 0)
        value = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        return KPICalculation(
            kpi_name="Task Completion Rate",
            value=value,
            unit="%",
            target=95.0,
            target_achievement=(value / 95.0) * 100 if 95.0 > 0 else 0,
            last_updated=current_time
        )

    elif kpi_type == "agent_efficiency":
        active_agents = stats.get("active_agents", 1)
        completed_tasks = stats.get("completed_tasks", 0)
        value = completed_tasks / active_agents if active_agents > 0 else 0
        return KPICalculation(
            kpi_name="Agent Efficiency",
            value=value,
            unit="tasks/agent",
            target=10.0,
            target_achievement=(value / 10.0) * 100 if 10.0 > 0 else 0,
            last_updated=current_time
        )

    else:
        return KPICalculation(
            kpi_name=kpi_type,
            value=0.0,
            unit="unknown",
            last_updated=current_time
        )


async def _get_widget_data(
    widget: Dict[str, Any],
    orchestrator,
    streaming_service,
    user_id: Optional[str]
) -> Dict[str, Any]:
    """Get data for a specific dashboard widget"""

    widget_type = widget.get("type")

    if widget_type == "agent_status":
        stats = orchestrator.get_orchestrator_stats()
        return {
            "total_agents": stats["total_agents"],
            "active_agents": stats["active_agents"],
            "utilization": stats["utilization"],
            "status": "healthy" if stats["utilization"] < 90 else "high_load"
        }

    elif widget_type == "task_summary":
        stats = orchestrator.get_orchestrator_stats()
        return {
            "total_tasks": stats["total_tasks"],
            "completed_tasks": stats["completed_tasks"],
            "failed_tasks": stats["failed_tasks"],
            "pending_tasks": stats["pending_tasks"]
        }

    elif widget_type == "real_time_activity":
        streaming_stats = await streaming_service.get_connection_stats()
        return {
            "active_connections": streaming_stats["active_connections"],
            "event_queue_size": streaming_stats["event_queue_size"],
            "last_activity": datetime.utcnow().isoformat()
        }

    else:
        return {"message": "Unknown widget type", "type": widget_type}


async def _generate_report_data(
    report_id: str,
    request: ReportRequest,
    user_id: Optional[str]
):
    """Generate report data in background"""
    try:
        # Update report status
        bi_storage["reports"][report_id]["status"] = "processing"

        orchestrator = get_agent_orchestrator()
        stats = orchestrator.get_orchestrator_stats()

        # Generate report data based on type
        if request.report_type == "agent_performance":
            report_data = await _generate_agent_performance_report(stats, request)
        elif request.report_type == "task_summary":
            report_data = await _generate_task_summary_report(stats, request)
        elif request.report_type == "business_metrics":
            report_data = await _generate_business_metrics_report(stats, request)
        else:
            raise ValueError(f"Unknown report type: {request.report_type}")

        # Update report with results
        bi_storage["reports"][report_id].update({
            "status": "completed",
            "data": report_data,
            "completed_at": datetime.utcnow().isoformat()
        })

        # Send completion notification
        streaming_service = get_streaming_service()
        await streaming_service.send_system_notification(
            message=f"Report '{request.report_type}' completed successfully",
            level="info",
            user_id=user_id
        )

    except Exception as e:
        # Update report with error
        bi_storage["reports"][report_id].update({
            "status": "failed",
            "error": str(e)
        })

        logger.error(f"Failed to generate report {report_id}: {e}")


async def _schedule_kpi_updates(
    calculation_id: str,
    request: KPIRequest,
    user_id: Optional[str]
):
    """Schedule periodic KPI updates"""
    try:
        while True:
            await asyncio.sleep(300)  # Update every 5 minutes

            orchestrator = get_agent_orchestrator()
            stats = orchestrator.get_orchestrator_stats()

            # Recalculate KPIs
            kpis = {}
            for kpi_type in request.kpi_types:
                kpi = await _calculate_single_kpi(kpi_type, stats, request, user_id)
                kpis[kpi_type] = kpi.dict()

            # Update stored KPIs
            if calculation_id in bi_storage["kpis"]:
                bi_storage["kpis"][calculation_id]["kpis"] = kpis
                bi_storage["kpis"][calculation_id]["last_updated"] = datetime.utcnow().isoformat()

                # Send update notification
                streaming_service = get_streaming_service()
                await streaming_service.send_system_notification(
                    message="KPIs updated automatically",
                    level="info",
                    user_id=user_id
                )

    except Exception as e:
        logger.error(f"Error in KPI update scheduling: {e}")


def _calculate_system_load() -> float:
    """Calculate current system load"""
    # Simplified system load calculation
    import psutil
    try:
        return psutil.cpu_percent(interval=1)
    except:
        return 0.0


def _filter_agent_metrics(stats: Dict[str, Any], agent_types: List[str]) -> Dict[str, Any]:
    """Filter agent metrics by agent types"""
    # This would need to be implemented based on actual agent data structure
    return stats


def _filter_metrics(metrics: Dict[str, Any], metric_types: List[str]) -> Dict[str, Any]:
    """Filter metrics by metric types"""
    filtered = {}
    for metric_type in metric_types:
        if metric_type in metrics:
            filtered[metric_type] = metrics[metric_type]
    return filtered


def _calculate_health_score(
    stats: Dict[str, Any],
    streaming_stats: Dict[str, Any],
    polling_stats: Dict[str, Any]
) -> float:
    """Calculate overall health score"""
    score = 100.0

    # Deduct for high utilization
    utilization = stats.get("utilization", 0)
    if utilization > 90:
        score -= 20
    elif utilization > 80:
        score -= 10

    # Deduct for connection issues
    if streaming_stats.get("active_connections", 0) == 0:
        score -= 30

    # Deduct for polling issues
    if polling_stats.get("active_sessions", 0) == 0:
        score -= 30

    return max(0.0, score)


# Report generation functions (simplified)
async def _generate_agent_performance_report(stats: Dict[str, Any], request: ReportRequest) -> Dict[str, Any]:
    """Generate agent performance report"""
    return {
        "report_type": "agent_performance",
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "summary": {
                "total_agents": stats["total_agents"],
                "active_agents": stats["active_agents"],
                "average_utilization": stats["utilization"]
            },
            "performance_breakdown": []
        }
    }


async def _generate_task_summary_report(stats: Dict[str, Any], request: ReportRequest) -> Dict[str, Any]:
    """Generate task summary report"""
    return {
        "report_type": "task_summary",
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "summary": {
                "total_tasks": stats["total_tasks"],
                "completed_tasks": stats["completed_tasks"],
                "failed_tasks": stats["failed_tasks"],
                "success_rate": (stats["completed_tasks"] / max(1, stats["total_tasks"])) * 100
            },
            "task_breakdown": []
        }
    }


async def _generate_business_metrics_report(stats: Dict[str, Any], request: ReportRequest) -> Dict[str, Any]:
    """Generate business metrics report"""
    return {
        "report_type": "business_metrics",
        "generated_at": datetime.utcnow().isoformat(),
        "data": {
            "efficiency_metrics": {
                "agent_efficiency": stats.get("active_agents", 0),
                "task_completion_rate": (stats["completed_tasks"] / max(1, stats["total_tasks"])) * 100,
                "system_utilization": stats["utilization"]
            },
            "performance_trends": []
        }
    }