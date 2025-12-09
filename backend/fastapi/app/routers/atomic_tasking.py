"""
Atomic Tasking API Routes
Provides endpoints for breaking down tasks into atomic units
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import ValidationError

from models.task import Task
from services.atomic_tasking import get_atomic_tasking_engine
from services.firebase_service import get_firebase_service
from models.common import ErrorResponse, BaseResponse


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


router = APIRouter(prefix="/api/atomic", tags=["Atomic Tasking"])


@router.post("/breakdown")
async def breakdown_task(
    task_data: Dict[str, Any],
    force_breakdown: bool = False,
    user_id: str = Depends(get_current_user),
    openai_key: str = Depends(get_openai_api_key),
):
    """Break down a task into atomic, shippable units"""
    try:
        engine = get_atomic_tasking_engine(openai_key)
        breakdown = await engine.breakdown_task(task_data, user_id, force_breakdown)

        return {
            "success": True,
            "message": "Task successfully broken down into atomic units",
            "breakdown": {
                "parent_task_id": breakdown.parent_task_id,
                "atomic_tasks_count": len(breakdown.atomic_tasks),
                "estimated_total_time": breakdown.estimated_total_time,
                "breakdown_reasoning": breakdown.breakdown_reasoning,
                "suggested_approach": breakdown.suggested_approach,
                "risk_assessment": breakdown.risk_assessment,
                "atomic_tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "size": task.size,
                        "complexity": task.complexity,
                        "estimated_minutes": task.estimated_minutes,
                        "acceptance_criteria": task.acceptance_criteria,
                        "dependencies": task.dependencies,
                        "deliverables": task.deliverables,
                        "testing_requirements": task.testing_requirements,
                        "priority_score": task.priority_score,
                        "order": task.order,
                    }
                    for task in breakdown.atomic_tasks
                ],
            },
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                success=False, message="Invalid task data", error=str(e)
            ).dict(),
        )
    except Exception as e:
        logging.error(f"Error breaking down task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to break down task", error=str(e)
            ).dict(),
        )


@router.get("/breakdown/{task_id}")
async def get_task_breakdown(
    task_id: str,
    user_id: str = Depends(get_current_user),
    openai_key: str = Depends(get_openai_api_key),
):
    """Get stored breakdown for a task"""
    try:
        engine = get_atomic_tasking_engine(openai_key)
        breakdown = await engine.get_task_breakdown(task_id, user_id)

        if not breakdown:
            return {"success": False, "message": "No breakdown found for this task"}

        return {
            "success": True,
            "message": "Task breakdown retrieved successfully",
            "breakdown": {
                "parent_task_id": breakdown.parent_task_id,
                "atomic_tasks_count": len(breakdown.atomic_tasks),
                "estimated_total_time": breakdown.estimated_total_time,
                "breakdown_reasoning": breakdown.breakdown_reasoning,
                "suggested_approach": breakdown.suggested_approach,
                "risk_assessment": breakdown.risk_assessment,
                "created_at": breakdown.created_at.isoformat(),
                "atomic_tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "size": task.size,
                        "complexity": task.complexity,
                        "estimated_minutes": task.estimated_minutes,
                        "acceptance_criteria": task.acceptance_criteria,
                        "dependencies": task.dependencies,
                        "deliverables": task.deliverables,
                        "testing_requirements": task.testing_requirements,
                        "priority_score": task.priority_score,
                        "order": task.order,
                        "created_at": task.created_at.isoformat(),
                    }
                    for task in breakdown.atomic_tasks
                ],
            },
        }

    except Exception as e:
        logging.error(f"Error getting task breakdown: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve task breakdown", error=str(e)
            ).dict(),
        )


@router.post("/suggest-improvements")
async def suggest_task_improvements(
    task_data: Dict[str, Any],
    user_id: str = Depends(get_current_user),
    openai_key: str = Depends(get_openai_api_key),
):
    """Suggest improvements to make a task more atomic"""
    try:
        engine = get_atomic_tasking_engine(openai_key)
        suggestions = await engine.suggest_task_improvements(task_data, user_id)

        return {
            "success": True,
            "message": "Task improvement suggestions generated",
            "suggestions": suggestions,
        }

    except Exception as e:
        logging.error(f"Error suggesting task improvements: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to generate task improvement suggestions",
                error=str(e),
            ).dict(),
        )


@router.post("/validate-atomic")
async def validate_atomic_task(
    task_data: Dict[str, Any], user_id: str = Depends(get_current_user)
):
    """Validate if a task is atomic and shippable"""
    try:
        # Simple validation logic
        title = task_data.get("title", "")
        description = task_data.get("description", "")
        estimated_duration = task_data.get("expectedDuration", 0)

        issues = []

        # Check size (should be under 2 hours)
        if estimated_duration > 120:
            issues.append("Task is too large (>2 hours)")

        # Check for multiple deliverables
        deliverables_keywords = ["and", "also", "plus", "additionally", "furthermore"]
        deliverables_count = sum(
            1
            for keyword in deliverables_keywords
            if keyword in f"{title} {description}".lower()
        )
        if deliverables_count > 2:
            issues.append("Task appears to have multiple deliverables")

        # Check for complex dependencies
        dependencies = task_data.get("dependencies", [])
        if len(dependencies) > 2:
            issues.append("Too many dependencies for an atomic task")

        # Check for vague language
        vague_words = ["etc", "various", "some", "maybe", "possibly", "stuff"]
        vague_count = sum(
            1 for word in vague_words if word in f"{title} {description}".lower()
        )
        if vague_count > 1:
            issues.append("Task contains vague or unclear requirements")

        is_atomic = len(issues) == 0

        return {
            "success": True,
            "is_atomic": is_atomic,
            "issues": issues,
            "recommendations": [
                "Break into smaller tasks under 2 hours each",
                "Define specific, measurable acceptance criteria",
                "Minimize dependencies between tasks",
                "Use clear, imperative language in task titles",
            ]
            if not is_atomic
            else [],
        }

    except Exception as e:
        logging.error(f"Error validating atomic task: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to validate atomic task", error=str(e)
            ).dict(),
        )


@router.get("/guidelines")
async def get_atomic_guidelines():
    """Get guidelines for creating atomic tasks"""
    return {
        "success": True,
        "guidelines": {
            "size_principles": {
                "tiny": {"minutes": "15-30", "description": "Quick wins, bug fixes"},
                "small": {
                    "minutes": "30-60",
                    "description": "Single features, moderate changes",
                },
                "medium": {
                    "minutes": "60-120",
                    "description": "Complex features, multiple files",
                },
                "large": {
                    "minutes": "120-240",
                    "description": "Major features (consider breaking down)",
                },
            },
            "atomic_principles": [
                "Single Responsibility: One clear outcome",
                "Independent: No blocking dependencies",
                "Testable: Clear acceptance criteria",
                "Shippable: Can be deployed independently",
                "Valuable: Provides measurable business value",
            ],
            "red_flags": [
                "Words like 'and', 'also', 'plus' in title",
                "Multiple deliverables listed",
                "Vague terms like 'etc', 'various', 'some'",
                "Time estimates over 2 hours",
                "More than 2 dependencies",
            ],
            "best_practices": [
                "Use imperative mood: 'Add user login' not 'Adding user login'",
                "Include specific acceptance criteria",
                "Estimate time realistically (include testing)",
                "Consider edge cases and error handling",
                "Think about deployment and rollback",
            ],
        },
    }
