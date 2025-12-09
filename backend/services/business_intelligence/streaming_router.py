"""
Business Intelligence Streaming Router
Enhanced streaming endpoints that integrate with the existing HTTP streaming system
and provide comprehensive real-time business intelligence updates.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse

from .streaming_integration import (
    streaming_manager,
    StreamingEventType,
    create_streaming_response,
    BIDataStreamManager
)

# Import BI engines
from .morning_briefing import MorningBriefingGenerator
from .revenue_intelligence import RevenueIntelligenceEngine
from .kpi_calculator import KPIEngine
from .alert_system import AlertManagementSystem


# Create router for streaming endpoints
streaming_router = APIRouter(
    prefix="/stream",
    tags=["Business Intelligence Streaming"]
)

# Initialize BI engines
morning_briefing_engine = MorningBriefingGenerator()
revenue_engine = RevenueIntelligenceEngine()
kpi_engine = KPIEngine()
alert_system = AlertManagementSystem()

# Configure streaming manager with BI engines
streaming_manager.set_engines(
    morning_briefing_engine=morning_briefing_engine,
    revenue_intelligence_engine=revenue_engine,
    kpi_engine=kpi_engine,
    alert_system=alert_system
)


@streaming_router.get("/dashboard/{user_id}", summary="Executive Dashboard Stream")
async def executive_dashboard_stream(
    user_id: str,
    refresh_interval: int = Query(30, description="Refresh interval in seconds", ge=5, le=300)
) -> StreamingResponse:
    """
    Real-time executive dashboard stream using Server-Sent Events.

    This endpoint provides comprehensive updates from all BI modules including:
    - Morning briefings and executive summaries
    - Revenue metrics and forecasts
    - KPI values and health status
    - Active alerts and notifications
    - System health and status updates

    Args:
        user_id: User identifier for personalized data
        refresh_interval: How often to refresh data (5-300 seconds)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        stream_generator = streaming_manager.create_executive_dashboard_stream(
            user_id=user_id,
            refresh_interval=refresh_interval
        )

        return create_streaming_response(
            stream_generator,
            "executive_dashboard"
        )

    except Exception as e:
        logging.error(f"Error creating executive dashboard stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create executive dashboard stream"
        )


@streaming_router.get("/morning-briefing/{user_id}", summary="Morning Briefing Stream")
async def morning_briefing_stream(
    user_id: str,
    refresh_interval: int = Query(30, description="Refresh interval in seconds", ge=5, le=300)
) -> StreamingResponse:
    """
    Real-time morning briefing stream using Server-Sent Events.

    Provides automated daily business health analysis including:
    - Executive summaries with health scores
    - Key priorities and critical alerts
    - Strategic opportunities
    - Competitive intelligence highlights
    - Revenue and operational metrics

    Args:
        user_id: User identifier for personalized briefings
        refresh_interval: How often to refresh data (5-300 seconds)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        stream_generator = streaming_manager.create_morning_briefing_stream(
            user_id=user_id,
            refresh_interval=refresh_interval
        )

        return create_streaming_response(
            stream_generator,
            "morning_briefing"
        )

    except Exception as e:
        logging.error(f"Error creating morning briefing stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create morning briefing stream"
        )


@streaming_router.get("/kpi-dashboard/{dashboard_id}/{user_id}", summary="KPI Dashboard Stream")
async def kpi_dashboard_stream(
    dashboard_id: str,
    user_id: str,
    refresh_interval: int = Query(60, description="Refresh interval in seconds", ge=5, le=300)
) -> StreamingResponse:
    """
    Real-time KPI dashboard stream using Server-Sent Events.

    Provides live KPI monitoring including:
    - Real-time KPI values and calculations
    - Trend analysis and forecasts
    - Health status and alert thresholds
    - Historical performance data
    - Predictive analytics

    Args:
        dashboard_id: Unique identifier for the KPI dashboard
        user_id: User identifier for authorization
        refresh_interval: How often to refresh data (5-300 seconds)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        stream_generator = streaming_manager.create_kpi_dashboard_stream(
            dashboard_id=dashboard_id,
            user_id=user_id,
            refresh_interval=refresh_interval
        )

        return create_streaming_response(
            stream_generator,
            "kpi_dashboard"
        )

    except Exception as e:
        logging.error(f"Error creating KPI dashboard stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create KPI dashboard stream"
        )


@streaming_router.get("/alerts/{user_id}", summary="Real-time Alerts Stream")
async def alerts_stream(
    user_id: str,
    severity_filter: Optional[str] = Query(None, description="Filter by severity level"),
    refresh_interval: int = Query(15, description="Refresh interval in seconds", ge=5, le=300)
) -> StreamingResponse:
    """
    Real-time alerts stream using Server-Sent Events.

    Provides immediate alert notifications including:
    - New active alerts
    - Alert acknowledgments and resolutions
    - Escalation status updates
    - System health alerts
    - KPI threshold breaches

    Args:
        user_id: User identifier for personalized alerts
        severity_filter: Optional filter by severity (critical, error, warning, info)
        refresh_interval: How often to check for new alerts (5-300 seconds)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        stream_generator = streaming_manager.create_alerts_stream(
            user_id=user_id,
            refresh_interval=refresh_interval
        )

        return create_streaming_response(
            stream_generator,
            "alerts"
        )

    except Exception as e:
        logging.error(f"Error creating alerts stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create alerts stream"
        )


@streaming_router.get("/revenue/{user_id}", summary="Revenue Intelligence Stream")
async def revenue_intelligence_stream(
    user_id: str,
    refresh_interval: int = Query(60, description="Refresh interval in seconds", ge=5, le=300)
) -> StreamingResponse:
    """
    Real-time revenue intelligence stream using Server-Sent Events.

    Provides live revenue analytics including:
    - MRR and ARR updates
    - Revenue forecasts and trends
    - Churn analysis and predictions
    - Customer acquisition costs and LTV
    - Pricing optimization insights

    Args:
        user_id: User identifier for personalized data
        refresh_interval: How often to refresh data (5-300 seconds)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        connection_id = f"revenue_{user_id}_{user_id}"

        async def revenue_stream_generator():
            """Generate revenue intelligence events"""
            while True:
                try:
                    # Get current revenue metrics
                    revenue_data = await revenue_engine.get_current_metrics(user_id)

                    # Create streaming event
                    event_data = {
                        "type": "revenue_update",
                        "user_id": user_id,
                        "data": {
                            "current_mrr": getattr(revenue_data, 'current_mrr', 0),
                            "arr": getattr(revenue_data, 'arr', 0),
                            "growth_rate": getattr(revenue_data, 'growth_rate', 0),
                            "churn_rate": getattr(revenue_data, 'churn_rate', 0),
                            "forecast_mrr": getattr(revenue_data, 'forecast_mrr', 0),
                            "health_score": getattr(revenue_data, 'health_score', 0),
                            "timestamp": asyncio.get_event_loop().time()
                        }
                    }

                    yield f"event: revenue_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    await asyncio.sleep(refresh_interval)

                except Exception as e:
                    logging.error(f"Error in revenue stream: {e}")
                    error_event = {
                        "type": "error",
                        "user_id": user_id,
                        "error": str(e),
                        "context": "revenue_stream"
                    }
                    yield f"event: error\n"
                    yield f"data: {json.dumps(error_event)}\n\n"

                    await asyncio.sleep(refresh_interval)

        return create_streaming_response(
            revenue_stream_generator(),
            "revenue_intelligence"
        )

    except Exception as e:
        logging.error(f"Error creating revenue stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create revenue stream"
        )


@streaming_router.get("/task-delegation/{user_id}", summary="Task Delegation Stream")
async def task_delegation_stream(
    user_id: str,
    refresh_interval: int = Query(30, description="Refresh interval in seconds", ge=5, le=300)
) -> StreamingResponse:
    """
    Real-time task delegation stream using Server-Sent Events.

    Provides live task delegation updates including:
    - New task evaluations
    - Delegation decisions and confidence scores
    - Task status updates
    - Agent availability and performance
    - Delegation recommendations

    Args:
        user_id: User identifier for personalized data
        refresh_interval: How often to refresh data (5-300 seconds)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        connection_id = f"tasks_{user_id}"

        async def task_delegation_stream_generator():
            """Generate task delegation events"""
            while True:
                try:
                    # Get current delegation status (mock implementation)
                    # This would integrate with the actual task delegator

                    event_data = {
                        "type": "task_delegation_update",
                        "user_id": user_id,
                        "data": {
                            "active_tasks": 0,
                            "completed_today": 0,
                            "delegation_success_rate": 0,
                            "avg_response_time": 0,
                            "agent_status": {},
                            "timestamp": asyncio.get_event_loop().time()
                        }
                    }

                    yield f"event: task_delegation_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    await asyncio.sleep(refresh_interval)

                except Exception as e:
                    logging.error(f"Error in task delegation stream: {e}")
                    error_event = {
                        "type": "error",
                        "user_id": user_id,
                        "error": str(e),
                        "context": "task_delegation_stream"
                    }
                    yield f"event: error\n"
                    yield f"data: {json.dumps(error_event)}\n\n"

                    await asyncio.sleep(refresh_interval)

        return create_streaming_response(
            task_delegation_stream_generator(),
            "task_delegation"
        )

    except Exception as e:
        logging.error(f"Error creating task delegation stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create task delegation stream"
        )


@streaming_router.get("/competitive/{user_id}", summary="Competitive Intelligence Stream")
async def competitive_intelligence_stream(
    user_id: str,
    refresh_interval: int = Query(300, description="Refresh interval in seconds", ge=60, le=3600)
) -> StreamingResponse:
    """
    Real-time competitive intelligence stream using Server-Sent Events.

    Provides live competitive monitoring including:
    - Competitor activity updates
    - Market position changes
    - New competitive threats
    - Strategic opportunity alerts
    - Industry trend updates

    Args:
        user_id: User identifier for personalized data
        refresh_interval: How often to refresh data (60-3600 seconds, competitive data doesn't change as frequently)

    Returns:
        StreamingResponse with Server-Sent Events format
    """
    try:
        connection_id = f"competitive_{user_id}"

        async def competitive_stream_generator():
            """Generate competitive intelligence events"""
            while True:
                try:
                    # Get competitive intelligence (mock implementation)
                    # This would integrate with the actual competitive intelligence engine

                    event_data = {
                        "type": "competitive_update",
                        "user_id": user_id,
                        "data": {
                            "competitor_updates": [],
                            "market_position_changes": [],
                            "new_threats": [],
                            "opportunities": [],
                            "timestamp": asyncio.get_event_loop().time()
                        }
                    }

                    yield f"event: competitive_update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                    await asyncio.sleep(refresh_interval)

                except Exception as e:
                    logging.error(f"Error in competitive stream: {e}")
                    error_event = {
                        "type": "error",
                        "user_id": user_id,
                        "error": str(e),
                        "context": "competitive_stream"
                    }
                    yield f"event: error\n"
                    yield f"data: {json.dumps(error_event)}\n\n"

                    await asyncio.sleep(refresh_interval)

        return create_streaming_response(
            competitive_stream_generator(),
            "competitive_intelligence"
        )

    except Exception as e:
        logging.error(f"Error creating competitive stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create competitive stream"
        )


@streaming_router.get("/stats", summary="Streaming Statistics")
async def get_streaming_stats() -> Dict[str, Any]:
    """
    Get current streaming system statistics and health status.

    Returns:
        Dictionary containing streaming system statistics including:
        - Active connections count
        - Connection types and distribution
        - Event subscriber counts
        - Engine status
        - Performance metrics
    """
    try:
        stats = streaming_manager.get_streaming_stats()

        return {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            **stats
        }

    except Exception as e:
        logging.error(f"Error getting streaming stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get streaming statistics"
        )


@streaming_router.post("/cleanup", summary="Cleanup Stale Connections")
async def cleanup_stale_connections() -> Dict[str, Any]:
    """
    Manually trigger cleanup of stale streaming connections.

    This endpoint removes connections that have been inactive for more than 10 minutes
    and cancels their associated heartbeat tasks.

    Returns:
        Dictionary containing cleanup results including:
        - Number of connections cleaned up
        - Current active connection count
        - Cleanup timestamp
    """
    try:
        # Get stats before cleanup
        before_stats = streaming_manager.get_streaming_stats()
        before_count = before_stats["connections"]["total_connections"]

        # Perform cleanup
        await streaming_manager.cleanup_stale_connections()

        # Get stats after cleanup
        after_stats = streaming_manager.get_streaming_stats()
        after_count = after_stats["connections"]["total_connections"]

        return {
            "status": "success",
            "cleaned_connections": before_count - after_count,
            "active_connections": after_count,
            "timestamp": asyncio.get_event_loop().time()
        }

    except Exception as e:
        logging.error(f"Error during connection cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup stale connections"
        )


# Health check endpoint
@streaming_router.get("/health", summary="Streaming Health Check")
async def streaming_health_check() -> Dict[str, Any]:
    """
    Health check for the streaming system.

    Returns:
        Health status of the streaming system including:
        - Overall health status
        - Component status
        - Connection metrics
        - Performance indicators
    """
    try:
        stats = streaming_manager.get_streaming_stats()

        # Determine health based on various factors
        active_connections = stats["connections"]["active_connections"]
        total_engines = sum(stats["engines_status"].values())
        available_engines = len(stats["engines_status"])

        if active_connections > 1000:
            health_status = "degraded"
            health_message = "High connection load"
        elif total_engines == 0:
            health_status = "unhealthy"
            health_message = "No BI engines available"
        elif total_engines < available_engines * 0.8:
            health_status = "degraded"
            health_message = "Some BI engines unavailable"
        else:
            health_status = "healthy"
            health_message = "All systems operational"

        return {
            "status": health_status,
            "message": health_message,
            "timestamp": asyncio.get_event_loop().time(),
            "details": {
                "active_connections": active_connections,
                "engines_available": f"{total_engines}/{available_engines}",
                "heartbeat_tasks": stats["heartbeat_tasks"]
            }
        }

    except Exception as e:
        logging.error(f"Error in streaming health check: {e}")
        return {
            "status": "unhealthy",
            "message": "Health check failed",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }


# Export router
__all__ = ["streaming_router"]