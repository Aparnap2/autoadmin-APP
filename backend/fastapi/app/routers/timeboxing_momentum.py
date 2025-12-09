"""
Timeboxing and Momentum API Routes
Provides endpoints for time management, productivity tracking, and momentum analysis
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import ValidationError

from services.timeboxing import get_timeboxing_service, DailyCycleTemplate
from services.momentum_system import get_momentum_system_service
from models.common import ErrorResponse


# Authentication dependency (placeholder)
async def get_current_user() -> str:
    """Get current authenticated user ID"""
    # This would integrate with your auth system
    return "user_123"


# OpenAI API key dependency (placeholder)
async def get_openai_api_key() -> str:
    """Get OpenAI API key"""
    # This would come from environment or config
    return "sk-placeholder"


router = APIRouter(prefix="/api/timeboxing", tags=["Timeboxing & Productivity"])


@router.post("/cycle-template")
async def create_cycle_template(
    name: str,
    wake_up_time: str,
    start_work_time: str,
    end_work_time: str,
    focus_block_duration: int = 90,
    short_break_duration: int = 10,
    long_break_duration: int = 30,
    focus_blocks_per_day: int = 4,
    user_id: str = Depends(get_current_user),
):
    """Create a daily cycle template"""
    try:
        service = get_timeboxing_service()
        template = await service.create_daily_cycle_template(
            user_id=user_id,
            name=name,
            wake_up_time=wake_up_time,
            start_work_time=start_work_time,
            end_work_time=end_work_time,
            focus_block_duration=focus_block_duration,
            short_break_duration=short_break_duration,
            long_break_duration=long_break_duration,
            focus_blocks_per_day=focus_blocks_per_day,
        )

        return {
            "success": True,
            "message": "Cycle template created successfully",
            "template": {
                "id": template.id,
                "name": template.name,
                "is_default": template.is_default,
                "wake_up_time": template.wake_up_time,
                "start_work_time": template.start_work_time,
                "end_work_time": template.end_work_time,
                "focus_block_duration": template.focus_block_duration,
                "focus_blocks_per_day": template.focus_blocks_per_day,
            },
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message="Invalid template data", error=str(e)
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error creating cycle template: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create cycle template", error=str(e)
            ).dict(),
        )


@router.post("/schedule/generate")
async def generate_daily_schedule(
    date: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    user_id: str = Depends(get_current_user),
):
    """Generate a daily schedule"""
    try:
        service = get_timeboxing_service()
        schedule = await service.generate_daily_schedule(
            user_id=user_id, date=date, tasks=tasks
        )

        return {
            "success": True,
            "message": "Daily schedule generated successfully",
            "schedule": {
                "date": schedule.date,
                "total_focus_time": schedule.total_focus_time,
                "total_break_time": schedule.total_break_time,
                "work_start_time": schedule.work_start_time,
                "work_end_time": schedule.work_end_time,
                "time_blocks": [
                    {
                        "id": block.id,
                        "type": block.type,
                        "title": block.title,
                        "start_time": block.start_time,
                        "end_time": block.end_time,
                        "duration_minutes": block.duration_minutes,
                        "task_id": block.task_id,
                    }
                    for block in schedule.time_blocks
                ],
            },
        }

    except Exception as e:
        logging.error(f"Error generating daily schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to generate daily schedule", error=str(e)
            ).dict(),
        )


@router.post("/blocks/{block_id}/start")
async def start_time_block(
    block_id: str,
    actual_start_time: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """Start a time block"""
    try:
        service = get_timeboxing_service()
        block = await service.start_time_block(
            user_id=user_id, block_id=block_id, actual_start_time=actual_start_time
        )

        return {
            "success": True,
            "message": "Time block started successfully",
            "block": {
                "id": block.id,
                "title": block.title,
                "type": block.type,
                "start_time": block.start_time,
                "end_time": block.end_time,
                "duration_minutes": block.duration_minutes,
            },
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message=str(e), error="INVALID_REQUEST"
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error starting time block: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to start time block", error=str(e)
            ).dict(),
        )


@router.post("/blocks/{block_id}/complete")
async def complete_time_block(
    block_id: str,
    actual_duration: Optional[int] = None,
    notes: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """Complete a time block"""
    try:
        service = get_timeboxing_service()
        block = await service.complete_time_block(
            user_id=user_id,
            block_id=block_id,
            actual_duration=actual_duration,
            notes=notes,
        )

        return {
            "success": True,
            "message": "Time block completed successfully",
            "block": {
                "id": block.id,
                "title": block.title,
                "type": block.type,
                "actual_duration_minutes": block.actual_duration_minutes,
                "notes": block.notes,
            },
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message=str(e), error="INVALID_REQUEST"
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error completing time block: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to complete time block", error=str(e)
            ).dict(),
        )


@router.post("/productivity/log")
async def log_daily_productivity(
    date: str,
    focus_sessions_completed: int,
    tasks_completed: int,
    total_focus_time: int,
    context_switches: int = 0,
    interruptions: int = 0,
    energy_level_start: int = 5,
    energy_level_end: int = 5,
    productivity_rating: int = 5,
    stress_level: int = 5,
    morning_notes: Optional[str] = None,
    evening_notes: Optional[str] = None,
    blockers: Optional[List[str]] = None,
    user_id: str = Depends(get_current_user),
):
    """Log daily productivity metrics"""
    try:
        service = get_timeboxing_service()
        log = await service.log_daily_productivity(
            user_id=user_id,
            date=date,
            focus_sessions_completed=focus_sessions_completed,
            tasks_completed=tasks_completed,
            total_focus_time=total_focus_time,
            context_switches=context_switches,
            interruptions=interruptions,
            energy_level_start=energy_level_start,
            energy_level_end=energy_level_end,
            productivity_rating=productivity_rating,
            stress_level=stress_level,
            morning_notes=morning_notes,
            evening_notes=evening_notes,
            blockers=blockers,
        )

        return {
            "success": True,
            "message": "Daily productivity logged successfully",
            "log": {
                "id": log.id,
                "date": log.date,
                "focus_sessions_completed": log.focus_sessions_completed,
                "tasks_completed": log.tasks_completed,
                "total_focus_time": log.total_focus_time,
                "productivity_rating": log.productivity_rating,
            },
        }

    except Exception as e:
        logging.error(f"Error logging daily productivity: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to log daily productivity", error=str(e)
            ).dict(),
        )


@router.get("/insights")
async def get_productivity_insights(
    days_back: int = 30, user_id: str = Depends(get_current_user)
):
    """Get productivity insights"""
    try:
        service = get_timeboxing_service()
        insights = await service.get_productivity_insights(
            user_id=user_id, days_back=days_back
        )

        return {
            "success": True,
            "message": "Productivity insights retrieved successfully",
            "insights": insights,
        }

    except Exception as e:
        logging.error(f"Error getting productivity insights: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to retrieve productivity insights",
                error=str(e),
            ).dict(),
        )


# Momentum System Routes
momentum_router = APIRouter(prefix="/api/momentum", tags=["Momentum System"])


@momentum_router.get("/calculate/{week_start_date}")
async def calculate_weekly_momentum(
    week_start_date: str, user_id: str = Depends(get_current_user)
):
    """Calculate weekly momentum"""
    try:
        service = get_momentum_system_service()
        momentum = await service.calculate_weekly_momentum(user_id, week_start_date)

        return {
            "success": True,
            "message": "Weekly momentum calculated successfully",
            "momentum": {
                "week_start": momentum.week_start,
                "week_end": momentum.week_end,
                "completion_rate": momentum.completion_rate,
                "focus_consistency": momentum.focus_consistency,
                "wip_adherence": momentum.wip_adherence,
                "velocity_score": momentum.velocity_score,
                "momentum_score": momentum.momentum_score,
                "tasks_created": momentum.tasks_created,
                "tasks_completed": momentum.tasks_completed,
                "total_focus_time": momentum.total_focus_time,
            },
        }

    except Exception as e:
        logging.error(f"Error calculating weekly momentum: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to calculate weekly momentum",
                error=str(e),
            ).dict(),
        )


@momentum_router.get("/insights")
async def get_momentum_insights(
    weeks_back: int = 4, user_id: str = Depends(get_current_user)
):
    """Get momentum insights and trends"""
    try:
        service = get_momentum_system_service()
        insights = await service.get_momentum_insights(user_id, weeks_back)

        return {
            "success": True,
            "message": "Momentum insights retrieved successfully",
            "insights": [
                {
                    "metric": insight.metric.value,
                    "trend": insight.trend.value,
                    "insight": insight.insight,
                    "recommendation": insight.recommendation,
                    "severity": insight.severity,
                }
                for insight in insights
            ],
        }

    except Exception as e:
        logging.error(f"Error getting momentum insights: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to retrieve momentum insights",
                error=str(e),
            ).dict(),
        )


@momentum_router.get("/portfolio")
async def get_portfolio_overview(user_id: str = Depends(get_current_user)):
    """Get portfolio overview"""
    try:
        service = get_momentum_system_service()
        portfolio = await service.get_portfolio_overview(user_id)

        return {
            "success": True,
            "message": "Portfolio overview retrieved successfully",
            "portfolio": [
                {
                    "project_id": item.project_id,
                    "name": item.name,
                    "stage": item.stage.value,
                    "progress_percentage": item.progress_percentage,
                    "momentum_score": item.momentum_score,
                    "priority_score": item.priority_score,
                    "blockers": item.blockers,
                    "team_size": item.team_size,
                }
                for item in portfolio
            ],
        }

    except Exception as e:
        logging.error(f"Error getting portfolio overview: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to retrieve portfolio overview",
                error=str(e),
            ).dict(),
        )


@momentum_router.get("/trends")
async def get_momentum_trends(
    months_back: int = 3, user_id: str = Depends(get_current_user)
):
    """Get momentum trends over time"""
    try:
        service = get_momentum_system_service()
        trends = await service.get_momentum_trends(user_id, months_back)

        return {
            "success": True,
            "message": "Momentum trends retrieved successfully",
            "trends": trends,
        }

    except Exception as e:
        logging.error(f"Error getting momentum trends: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to retrieve momentum trends",
                error=str(e),
            ).dict(),
        )


@momentum_router.get("/report/{week_start_date}")
async def generate_momentum_report(
    week_start_date: str, user_id: str = Depends(get_current_user)
):
    """Generate comprehensive momentum report"""
    try:
        service = get_momentum_system_service()
        report = await service.generate_momentum_report(user_id, week_start_date)

        return {
            "success": True,
            "message": "Momentum report generated successfully",
            "report": report,
        }

    except Exception as e:
        logging.error(f"Error generating momentum report: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to generate momentum report",
                error=str(e),
            ).dict(),
        )


# Combine routers
combined_router = APIRouter()
combined_router.include_router(router)
combined_router.include_router(momentum_router)
