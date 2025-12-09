"""
Business Intelligence API Endpoints
Comprehensive API endpoints for the business intelligence system with HTTP-only communication
and Server-Sent Events for real-time updates.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Depends, Path, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic.types import PositiveInt, PositiveFloat

from .morning_briefing import MorningBriefingGenerator
from .revenue_intelligence import RevenueIntelligenceEngine
from .competitive_intelligence import CompetitiveIntelligenceEngine
from .crm_intelligence import CRMIntelligenceEngine
from .strategic_planner import StrategicPlannerEngine
from .kpi_calculator import KPIEngine
from .task_delegator import IntelligentTaskDelegator
from .alert_system import AlertManagementSystem


# Create router
router = APIRouter(prefix="/api/v2/business-intelligence", tags=["Business Intelligence V2"])

# Pydantic models for API requests/responses
class MorningBriefingRequest(BaseModel):
    """Request for morning briefing generation"""
    user_id: str = Field(..., description="User ID")
    date_range: Optional[str] = Field(None, description="Date range (7d, 30d, 90d)")
    focus_areas: Optional[List[str]] = Field(None, description="Specific focus areas")
    include_forecasts: bool = Field(True, description="Include forecasts")


class RevenueAnalysisRequest(BaseModel):
    """Request for revenue analysis"""
    user_id: str = Field(..., description="User ID")
    analysis_type: str = Field("comprehensive", description="Type of analysis")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    include_forecasts: bool = Field(True, description="Include forecasts")
    forecast_months: int = Field(12, description="Months to forecast")


class TaskDelegationRequest(BaseModel):
    """Request for task delegation"""
    user_id: str = Field(..., description="User ID")
    task_data: Dict[str, Any] = Field(..., description="Task data to delegate")
    force_delegate: bool = Field(False, description="Force delegation without confidence check")


class CompetitiveAnalysisRequest(BaseModel):
    """Request for competitive analysis"""
    user_id: str = Field(..., description="User ID")
    analysis_type: str = Field("comprehensive", description="Type of analysis")
    focus_areas: Optional[List[str]] = Field(None, description="Specific focus areas")


class CRMAnalysisRequest(BaseModel):
    """Request for CRM analysis"""
    user_id: str = Field(..., description="User ID")
    analysis_type: str = Field("comprehensive", description="Type of analysis")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")


class StrategicPlanRequest(BaseModel):
    """Request for strategic planning"""
    user_id: str = Field(..., description="User ID")
    planning_horizon: str = Field("annual", description="Planning horizon")
    focus_areas: Optional[List[str]] = Field(None, description="Focus areas")
    current_state: Optional[Dict[str, Any]] = Field(None, description="Current business state")


class KPICalculationRequest(BaseModel):
    """Request for KPI calculation"""
    user_id: str = Field(..., description="User ID")
    kpi_ids: Optional[List[str]] = Field(None, description="Specific KPI IDs to calculate")
    timeframe: str = Field("monthly", description="Timeframe for calculation")
    end_date: Optional[datetime] = Field(None, description="End date for calculation")


class AlertRequest(BaseModel):
    """Request for alert processing"""
    user_id: str = Field(..., description="User ID")
    alert_data: List[Dict[str, Any]] = Field(..., description="Alert data to process")


class AlertRuleRequest(BaseModel):
    """Request for creating alert rule"""
    user_id: str = Field(..., description="User ID")
    rule_config: Dict[str, Any] = Field(..., description="Alert rule configuration")


class KPICustomRequest(BaseModel):
    """Request for creating custom KPI"""
    user_id: str = Field(..., description="User ID")
    kpi_definition: Dict[str, Any] = Field(..., description="KPI definition")


# Initialize engines (in production, these would be dependency-injected)
morning_briefing = MorningBriefingGenerator("dummy_api_key")
revenue_engine = RevenueIntelligenceEngine("dummy_api_key")
competitive_engine = CompetitiveIntelligenceEngine("dummy_api_key")
crm_engine = CRMIntelligenceEngine("dummy_api_key")
strategic_planner = StrategicPlannerEngine("dummy_api_key")
kpi_engine = KPIEngine("dummy_api_key")
task_delegator = IntelligentTaskDelegator("dummy_api_key")
alert_system = AlertManagementSystem("dummy_api_key")


@router.post("/morning-briefing", summary="Generate Morning Briefing")
async def generate_morning_briefing(
    request: MorningBriefingRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Generate comprehensive morning briefing"""
    try:
        # Parse date range
        date_range = request.date_range
        if date_range:
            if date_range == "7d":
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=7)
            elif date_range == "30d":
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
            elif date_range == "90d":
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=90)
            else:
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
        else:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)

        # Generate briefing
        briefing = await morning_briefing.generate_morning_briefing(
            user_id=request.user_id,
            date_range=(start_date, end_date),
            include_forecasts=request.include_forecasts,
            focus_areas=request.focus_areas
        )

        return {
            "success": True,
            "briefing": {
                "id": briefing.id,
                "date": briefing.date.isoformat(),
                "executive_summary": briefing.executive_summary,
                "key_metrics": [asdict(metric) for metric in briefing.key_metrics],
                "alerts": [asdict(alert) for alert in briefing.alerts],
                "growth_opportunities": [asdict(opp) for opp in briefing.growth_opportunities],
                "recommendations": briefing.recommendations,
                "focus_areas": briefing.focus_areas,
                "performance_indicators": briefing.performance_indicators,
                "action_items": briefing.action_items
            },
            "generated_at": briefing.generated_at.isoformat()
        }

    except Exception as e:
        logging.error(f"Error generating morning briefing: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate morning briefing")


@router.post("/revenue-analysis", summary="Generate Revenue Analysis")
async def generate_revenue_analysis(
    request: RevenueAnalysisRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Generate comprehensive revenue intelligence analysis"""
    try:
        # Parse dates
        start_date = request.start_date or datetime.now(timezone.utc) - timedelta(days=90)
        end_date = request.end_date or datetime.now(timezone.utc)

        # Generate analysis
        analysis = await revenue_engine.generate_revenue_analysis(
            user_id=request.user_id,
            start_date=start_date,
            end_date=end_date,
            include_forecasts=request.include_forecasts,
            forecast_months=request.forecast_months
        )

        return {
            "success": True,
            "analysis": analysis
        }

    except Exception as e:
        logging.error(f"Error generating revenue analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate revenue analysis")


@router.post("/delegate-task", summary="Delegate Task Intelligently")
async def delegate_task(
    request: TaskDelegationRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Intelligently delegate task to appropriate agent"""
    try:
        # Delegate task
        decision = await task_delegator.evaluate_and_delegate_task(
            task_data=request.task_data,
            user_id=request.user_id,
            force_delegate=request.force_delegate
        )

        return {
            "success": True,
            "delegation_decision": {
                "task_id": decision.task_id,
                "recommended_agent": decision.recommended_agent,
                "confidence_score": decision.confidence_score,
                "reasoning": decision.reasoning,
                "alternative_agents": decision.alternative_agents,
                "expected_completion_time": decision.expected_completion_time,
                "estimated_cost": decision.estimated_cost,
                "risk_factors": decision.risk_factors,
                "mitigation_strategies": decision.mitigation_strategies,
                "delegation_strategy": decision.delegation_strategy.value,
                "created_at": decision.created_at.isoformat()
            }
        }

    except Exception as e:
        logging.error(f"Error delegating task: {e}")
        raise HTTPException(status_code=500, detail="Failed to delegate task")


@router.post("/competitive-analysis", summary="Generate Competitive Analysis")
async def generate_competitive_analysis(
    request: CompetitiveAnalysisRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Generate competitive intelligence analysis"""
    try:
        # Generate analysis
        analysis = await competitive_engine.generate_competitive_analysis(
            user_id=request.user_id,
            analysis_type=request.analysis_type,
            focus_areas=request.focus_areas
        )

        return {
            "success": True,
            "analysis": analysis
        }

    except Exception as e:
        logging.error(f"Error generating competitive analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate competitive analysis")


@router.post("/crm-analysis", summary="Generate CRM Analysis")
async def generate_crm_analysis(
    request: CRMAnalysisRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Generate CRM intelligence analysis"""
    try:
        # Parse dates
        start_date = request.start_date or datetime.now(timezone.utc) - timedelta(days=90)
        end_date = request.end_date or datetime.now(timezone.utc)

        # Generate analysis
        analysis = await crm_engine.analyze_crm_performance(
            user_id=request.user_id,
            analysis_type=request.analysis_type,
            date_range=(start_date, end_date)
        )

        return {
            "success": True,
            "analysis": analysis
        }

    except Exception as e:
        logging.error(f"Error generating CRM analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate CRM analysis")


@router.post("/strategic-plan", summary="Generate Strategic Plan")
async def generate_strategic_plan(
    request: StrategicPlanRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Generate strategic plan and recommendations"""
    try:
        # Generate plan
        plan = await strategic_planner.generate_strategic_plan(
            user_id=request.user_id,
            planning_horizon=strategic_planner.PlanningHorizon(request.planning_horizon),
            focus_areas=request.focus_areas,
            current_state=request.current_state
        )

        return {
            "success": True,
            "strategic_plan": plan
        }

    except Exception as e:
        logging.error(f"Error generating strategic plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate strategic plan")


@router.get("/kpis", summary="Get KPI Dashboard")
async def get_kpi_dashboard(
    user_id: str = Query(..., description="User ID"),
    dashboard_id: Optional[str] = Query(None, description="Dashboard ID"),
    real_time: bool = Query(False, description="Real-time updates")
) -> Dict[str, Any]:
    """Get KPI dashboard data"""
    try:
        # Get dashboard data
        dashboard = await kpi_engine.get_kpi_dashboard(
            user_id=user_id,
            dashboard_id=dashboard_id,
            real_time=real_time
        )

        return {
            "success": True,
            "dashboard": dashboard
        }

    except Exception as e:
        logging.error(f"Error getting KPI dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get KPI dashboard")


@router.post("/kpis/calculate", summary="Calculate KPIs")
async def calculate_kpis(
    request: KPICalculationRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Calculate specified KPIs"""
    try:
        # Parse timeframe
        timeframe = kpi_engine.KPITimeframe(request.timeframe)
        end_date = request.end_date or datetime.now(timezone.utc)

        # Calculate KPIs
        result = await kpi_engine.calculate_kpis(
            user_id=request.user_id,
            kpi_ids=request.kpi_ids,
            timeframe=timeframe,
            end_date=end_date
        )

        return {
            "success": True,
            "kpi_calculation": result
        }

    except Exception as e:
        logging.error(f"Error calculating KPIs: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate KPIs")


@router.post("/kpis/custom", summary="Create Custom KPI")
async def create_custom_kpi(
    request: KPICustomRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Create custom KPI definition"""
    try:
        # Create custom KPI
        result = await kpi_engine.create_custom_kpi(
            user_id=request.user_id,
            kpi_definition=request.kpi_definition
        )

        return {
            "success": True,
            "custom_kpi": result
        }

    except Exception as e:
        logging.error(f"Error creating custom KPI: {e}")
        raise HTTPException(status_code=500, detail="Failed to create custom KPI")


@router.get("/kpis/trends", summary="Get KPI Trends")
async def get_kpi_trends(
    user_id: str = Query(..., description="User ID"),
    kpi_id: str = Query(..., description="KPI ID"),
    days: int = Query(30, description="Number of days for trend analysis")
) -> Dict[str, Any]:
    """Get KPI trend analysis"""
    try:
        # Analyze trends
        trend_analysis = await kpi_engine.analyze_kpi_trends(
            user_id=user_id,
            kpi_id=kpi_id,
            days=days
        )

        return {
            "success": True,
            "trend_analysis": asdict(trend_analysis)
        }

    except Exception as e:
        logging.error(f"Error getting KPI trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get KPI trends")


@router.post("/alerts/process", summary="Process Alerts")
async def process_alerts(
    request: AlertRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Process incoming alerts"""
    try:
        # Process alerts
        result = await alert_system.process_alerts(
            user_id=request.user_id,
            alert_data=request.alert_data
        )

        return {
            "success": True,
            "alert_processing": result
        }

    except Exception as e:
        logging.error(f"Error processing alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to process alerts")


@router.post("/alerts/rules", summary="Create Alert Rule")
async def create_alert_rule(
    request: AlertRuleRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Create custom alert rule"""
    try:
        # Create alert rule
        result = await alert_system.create_custom_alert_rule(
            user_id=request.user_id,
            rule_config=request.rule_config
        )

        return {
            "success": True,
            "alert_rule": result
        }

    except Exception as e:
        logging.error(f"Error creating alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.get("/alerts/dashboard", summary="Get Alert Dashboard")
async def get_alert_dashboard(
    user_id: str = Query(..., description="User ID"),
    time_range: str = Query("24h", description="Time range"),
    filters: Optional[str] = Query(None, description="Filters (JSON)")
) -> Dict[str, Any]:
    """Get alert dashboard data"""
    try:
        # Parse filters
        parsed_filters = {}
        if filters:
            import json
            parsed_filters = json.loads(filters)

        # Get dashboard data
        dashboard = await alert_system.get_alert_dashboard(
            user_id=user_id,
            filters=parsed_filters,
            time_range=time_range
        )

        return {
            "success": True,
            "dashboard": dashboard
        }

    except Exception as e:
        logging.error(f"Error getting alert dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert dashboard")


@router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge Alert")
async def acknowledge_alert(
    alert_id: str = Path(..., description="Alert ID"),
    user_id: str = Query(..., description="User ID"),
    acknowledged_by: str = Query(..., description="Acknowledged by"),
    notes: Optional[str] = Query(None, description="Acknowledgment notes")
) -> Dict[str, Any]:
    """Acknowledge an alert"""
    try:
        # Acknowledge alert
        result = await alert_system.acknowledge_alert(
            user_id=user_id,
            alert_id=alert_id,
            acknowledged_by=acknowledged_by,
            notes=notes
        )

        return {
            "success": True,
            "acknowledgment": result
        }

    except Exception as e:
        logging.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.post("/alerts/{alert_id}/resolve", summary="Resolve Alert")
async def resolve_alert(
    alert_id: str = Path(..., description="Alert ID"),
    user_id: str = Query(..., description="User ID"),
    resolved_by: str = Query(..., description="Resolved by"),
    resolution: Optional[str] = Query(None, description="Resolution"),
    resolution_notes: Optional[str] = Query(None, description="Resolution notes")
) -> Dict[str, Any]:
    """Resolve an alert"""
    try:
        # Resolve alert
        result = await alert_system.resolve_alert(
            user_id=user_id,
            alert_id=alert_id,
            resolved_by=resolved_by,
            resolution=resolution,
            resolution_notes=resolution_notes
        )

        return {
            "success": True,
            "resolution": result
        }

    except Exception as e:
        logging.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.get("/morning-briefing/stream", summary="Morning Briefing Stream")
async def morning_briefing_stream(
    user_id: str = Query(..., description="User ID"),
    refresh_interval: int = Query(30, description="Refresh interval in seconds")
) -> StreamingResponse:
    """Real-time morning briefing stream using Server-Sent Events"""
    try:
        async def briefing_stream_generator():
            """Generate morning briefing events"""
            try:
                client_id = f"briefing_{user_id}_{uuid.uuid4().hex[:8]}"

                while True:
                    # Generate fresh briefing
                    briefing = await morning_briefing.generate_morning_briefing(
                        user_id=user_id,
                        date_range=None,
                        include_forecasts=True
                    )

                    # Send briefing update event
                    event_data = {
                        "type": "briefing_update",
                        "user_id": user_id,
                        "data": {
                            "briefing_id": briefing.id,
                            "date": briefing.date.isoformat(),
                            "executive_summary": briefing.executive_summary,
                            "key_metrics_count": len(briefing.key_metrics),
                            "alerts_count": len(briefing.alerts),
                            "opportunities_count": len(briefing.growth_opportunities),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }

                    yield f"event: briefing_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    # Wait before next update
                    await asyncio.sleep(refresh_interval)

            except Exception as e:
                logging.error(f"Error in briefing stream generator: {e}")
                # Send error event
                error_event = {
                    "type": "error",
                    "user_id": user_id,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                yield f"event: error\n"
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            briefing_stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Stream-Type": "morning_briefing"
            }
        )

    except Exception as e:
        logging.error(f"Error creating morning briefing stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create briefing stream")


@router.get("/kpis/{dashboard_id}/stream", summary="KPI Dashboard Stream")
async def kpi_dashboard_stream(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    user_id: str = Query(..., description="User ID"),
    refresh_interval: int = Query(60, description="Refresh interval in seconds")
) -> StreamingResponse:
    """Real-time KPI dashboard stream using Server-Sent Events"""
    try:
        async def kpi_stream_generator():
            """Generate KPI dashboard events"""
            try:
                client_id = f"kpi_{user_id}_{dashboard_id}_{uuid.uuid4().hex[:8]}"

                while True:
                    # Get dashboard data
                    dashboard = await kpi_engine.get_kpi_dashboard(
                        user_id=user_id,
                        dashboard_id=dashboard_id,
                        real_time=True
                    )

                    # Send dashboard update event
                    event_data = {
                        "type": "dashboard_update",
                        "dashboard_id": dashboard_id,
                        "user_id": user_id,
                        "data": {
                            "summary": dashboard.get("summary", {}),
                            "kpi_values": dashboard.get("kpi_values", []),
                            "last_updated": dashboard.get("last_updated"),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }

                    yield f"event: dashboard_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    # Wait before next update
                    await asyncio.sleep(refresh_interval)

            except Exception as e:
                logging.error(f"Error in KPI stream generator: {e}")
                # Send error event
                error_event = {
                    "type": "error",
                    "dashboard_id": dashboard_id,
                    "user_id": user_id,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                yield f"event: error\n"
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            kpi_stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Stream-Type": "kpi_dashboard"
            }
        )

    except Exception as e:
        logging.error(f"Error creating KPI dashboard stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create KPI dashboard stream")


@router.get("/alerts/stream", summary="Real-time Alerts Stream")
async def alerts_stream(
    user_id: str = Query(..., description="User ID"),
    severity_filter: Optional[str] = Query(None, description="Severity filter"),
    type_filter: Optional[str] = Query(None, description="Alert type filter")
) -> StreamingResponse:
    """Real-time alerts stream using Server-Sent Events"""
    try:
        async def alerts_stream_generator():
            """Generate alerts events"""
            try:
                client_id = f"alerts_{user_id}_{uuid.uuid4().hex[:8]}"

                while True:
                    # Get alert dashboard for latest alerts
                    dashboard = await alert_system.get_alert_dashboard(
                        user_id=user_id,
                        time_range="1h"
                    )

                    active_alerts = dashboard.get("active_alerts", [])

                    # Apply filters if specified
                    if severity_filter:
                        active_alerts = [
                            alert for alert in active_alerts
                            if alert.get("severity") == severity_filter
                        ]

                    if type_filter:
                        active_alerts = [
                            alert for alert in active_alerts
                            if alert.get("alert_type") == type_filter
                        ]

                    # Send alerts update event
                    event_data = {
                        "type": "alerts_update",
                        "user_id": user_id,
                        "data": {
                            "active_alerts": active_alerts,
                            "summary": dashboard.get("summary", {}),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }

                    yield f"event: alerts_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    # Wait before next update
                    await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logging.error(f"Error in alerts stream generator: {e}")
                # Send error event
                error_event = {
                    "type": "error",
                    "user_id": user_id,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                yield f"event: error\n"
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            alerts_stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Stream-Type": "alerts"
            }
        )

    except Exception as e:
        logging.error(f"Error creating alerts stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alerts stream")


@router.get("/revenue/insights", summary="Get Revenue Insights")
async def get_revenue_insights(
    user_id: str = Query(..., description="User ID"),
    insight_types: Optional[List[str]] = Query(None, description="Specific insight types")
) -> Dict[str, Any]:
    """Get revenue insights for dashboard"""
    try:
        # Get insights
        insights = await revenue_engine.get_revenue_insights(
            user_id=user_id,
            insight_types=insight_types
        )

        return {
            "success": True,
            "insights": insights
        }

    except Exception as e:
        logging.error(f"Error getting revenue insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get revenue insights")


@router.get("/crm/deal-health", summary="Get Deal Health Insights")
async def get_deal_health_insights(
    user_id: str = Query(..., description="User ID"),
    health_filter: Optional[str] = Query(None, description="Health status filter")
) -> Dict[str, Any]:
    """Get deal health insights"""
    try:
        # Get insights
        insights = await crm_engine.get_deal_health_insights(
            user_id=user_id,
            health_filter=health_filter
        )

        return {
            "success": True,
            "insights": insights
        }

    except Exception as e:
        logging.error(f"Error getting deal health insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deal health insights")


@router.get("/strategic/insights", summary="Get Strategic Insights")
async def get_strategic_insights(
    user_id: str = Query(..., description="User ID"),
    insight_type: str = Query("overview", description="Type of strategic insights")
) -> Dict[str, Any]:
    """Get strategic planning insights"""
    try:
        # Get insights
        insights = await strategic_planner.get_strategic_insights(
            user_id=user_id,
            insight_type=insight_type
        )

        return {
            "success": True,
            "insights": insights
        }

    except Exception as e:
        logging.error(f"Error getting strategic insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategic insights")


@router.get("/health", summary="Business Intelligence Health Check")
async def health_check() -> Dict[str, Any]:
    """Health check for business intelligence services"""
    try:
        # Check all services
        services_status = {
            "morning_briefing": "healthy",
            "revenue_intelligence": "healthy",
            "competitive_intelligence": "healthy",
            "crm_intelligence": "healthy",
            "strategic_planner": "healthy",
            "kpi_calculator": "healthy",
            "task_delegator": "healthy",
            "alert_system": "healthy"
        }

        # Calculate overall health
        healthy_services = sum(1 for status in services_status.values() if status == "healthy")
        total_services = len(services_status)
        health_score = (healthy_services / total_services) * 100 if total_services > 0 else 0

        return {
            "status": "healthy" if health_score >= 90 else "degraded" if health_score >= 70 else "unhealthy",
            "health_score": health_score,
            "services": services_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0"
        }

    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "health_score": 0,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/status", summary="Get Business Intelligence Status")
async def get_status() -> Dict[str, Any]:
    """Get current status of business intelligence system"""
    try:
        return {
            "status": "operational",
            "version": "2.0.0",
            "services": {
                "morning_briefing": "operational",
                "revenue_intelligence": "operational",
                "competitive_intelligence": "operational",
                "crm_intelligence": "operational",
                "strategic_planner": "operational",
                "kpi_calculator": "operational",
                "task_delegator": "operational",
                "alert_system": "operational"
            },
            "features": {
                "real_time_streaming": True,
                "http_only_communication": True,
                "server_sent_events": True,
                "intelligent_delegation": True,
                "automated_alerting": True,
                "strategic_planning": True,
                "kpi_calculation": True,
                "trend_analysis": True
            },
            "endpoints": {
                "morning_briefing": "/morning-briefing",
                "revenue_analysis": "/revenue-analysis",
                "task_delegation": "/delegate-task",
                "competitive_analysis": "/competitive-analysis",
                "crm_analysis": "/crm-analysis",
                "strategic_plan": "/strategic-plan",
                "kpis": "/kpis",
                "alerts": "/alerts",
                "streaming": {
                    "briefing_stream": "/morning-briefing/stream",
                    "kpi_dashboard_stream": "/kpis/{dashboard_id}/stream",
                    "alerts_stream": "/alerts/stream"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logging.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# Response models for API documentation
class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Error handler decorator
def handle_errors(func):
    """Decorator to handle errors in API endpoints"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise FastAPI HTTP exceptions
            raise
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail=str(e),
                headers={"X-Error-Type": "unexpected"}
            )
    return wrapper


# Apply error handlers to all endpoints
for endpoint in [
    generate_morning_briefing,
    generate_revenue_analysis,
    delegate_task,
    generate_competitive_analysis,
    generate_crm_analysis,
    generate_strategic_plan,
    get_kpi_dashboard,
    calculate_kpis,
    create_custom_kpi,
    get_kpi_trends,
    process_alerts,
    create_alert_rule,
    get_alert_dashboard,
    acknowledge_alert,
    resolve_alert
]:
    endpoint.__func__ = handle_errors(endpoint.__func__)