#!/usr/bin/env python3
"""
Mock Backend Server for Testing
Provides basic API endpoints for Maestro E2E tests
"""

import json
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Mock AutoAdmin Backend", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_DASHBOARD_DATA = {
    "active_task": {
        "task_id": "task_123",
        "title": "Implement user authentication",
        "progress_percentage": 0.6,
        "time_spent_minutes": 45,
        "priority": "high",
        "git_branch": "feature/task-123-auth",
        "pr_status": "open",
        "blockers": ["API integration pending"],
    },
    "active_tasks_count": 1,
    "wip_limit": 2,
    "wip_violations_today": 0,
    "focus_sessions_today": 2,
    "total_focus_time_today": 180,
    "focus_score_today": 0.85,
    "upcoming_tasks": [{"id": "task_456", "title": "Add validation"}],
    "recent_completions": [
        {"title": "Fix login bug", "completed_at": "2024-01-15T10:30:00Z"}
    ],
    "momentum_score": 78.5,
    "git_integration_status": {},
}

MOCK_PROJECTS = [
    {
        "id": "project_123",
        "name": "Test E-commerce Platform",
        "description": "Build a complete online shopping platform",
        "status": "active",
        "priority": "high",
        "progress_percentage": 75,
        "team_members": ["user_123", "user_456"],
    }
]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "mock-autoadmin-backend",
        "version": "1.0.0",
    }


@app.get("/api/wip/dashboard")
async def get_focus_dashboard():
    """Mock WIP dashboard data"""
    return {
        "success": True,
        "message": "Dashboard data retrieved successfully",
        "dashboard": MOCK_DASHBOARD_DATA,
    }


@app.get("/api/projects")
async def get_projects():
    """Mock projects list"""
    return {
        "success": True,
        "message": "Projects retrieved successfully",
        "data": MOCK_PROJECTS,
        "total": len(MOCK_PROJECTS),
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


@app.post("/api/projects")
async def create_project(project_data: dict):
    """Mock project creation"""
    new_project = {
        "id": f"project_{len(MOCK_PROJECTS) + 1}",
        "name": project_data.get("name", "New Project"),
        "description": project_data.get("description", ""),
        "status": "planning",
        "priority": project_data.get("priority", "medium"),
        "owner_id": "user_123",
    }
    MOCK_PROJECTS.append(new_project)

    return {
        "success": True,
        "message": "Project created successfully",
        "project": new_project,
    }


@app.get("/api/projects/{project_id}/dashboard")
async def get_project_dashboard(project_id: str):
    """Mock project dashboard"""
    project = next((p for p in MOCK_PROJECTS if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "success": True,
        "message": "Project dashboard retrieved successfully",
        "dashboard": {
            "project": project,
            "goal_tree": {"roots": []},
            "kanban_board": {"columns": ["Backlog", "In Progress", "Review", "Done"]},
            "kanban_cards": [],
            "progress_metrics": {"completion_rate": 0.75},
            "blockers": [],
            "recent_activity": [],
            "upcoming_deadlines": [],
            "team_members": [{"id": "user_123", "name": "Test User", "role": "owner"}],
        },
    }


@app.post("/api/projects/{project_id}/goals")
async def create_goal(project_id: str, goal_data: dict):
    """Mock goal creation"""
    new_goal = {
        "id": f"goal_{len(MOCK_PROJECTS) * 10 + 1}",
        "project_id": project_id,
        "title": goal_data.get("title", "New Goal"),
        "type": goal_data.get("type", "task"),
        "status": "not_started",
        "priority": goal_data.get("priority", 5),
    }

    return {"success": True, "message": "Goal created successfully", "goal": new_goal}


@app.post("/api/wip/activate-task")
async def activate_task(task_data: dict):
    """Mock task activation"""
    return {
        "success": True,
        "message": "Task activated successfully",
        "task_id": task_data.get("task_id", "task_123"),
    }


@app.post("/api/wip/focus/start")
async def start_focus_session(session_data: dict):
    """Mock focus session start"""
    return {
        "success": True,
        "message": "Focus session started successfully",
        "session": {
            "id": "session_123",
            "user_id": "user_123",
            "task_id": session_data.get("task_id", "task_123"),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "focus_score": 1.0,
        },
    }


@app.post("/api/git/branch/create")
async def create_git_branch(branch_data: dict):
    """Mock Git branch creation"""
    return {
        "success": True,
        "message": f"Branch '{branch_data.get('task_title', 'task').lower().replace(' ', '-')}' created successfully",
        "branch": {
            "name": f"feature/task-{branch_data.get('task_id', '123')}-{branch_data.get('task_title', 'task').lower().replace(' ', '-')}",
            "sha": "abc123def456",
            "status": "created",
            "task_id": branch_data.get("task_id", "task_123"),
        },
    }


@app.post("/api/git/pr/create")
async def create_pull_request(pr_data: dict):
    """Mock PR creation"""
    return {
        "success": True,
        "message": "Pull request created successfully",
        "pr": {
            "number": 42,
            "title": f"[{pr_data.get('task_id', 'task_123')}] {pr_data.get('task_title', 'Task')}",
            "status": "draft",
            "branch": pr_data.get("branch_name", "feature/task-branch"),
            "task_id": pr_data.get("task_id", "task_123"),
        },
    }


@app.post("/api/atomic/breakdown")
async def breakdown_task(task_data: dict):
    """Mock task breakdown"""
    return {
        "success": True,
        "message": "Task successfully broken down into atomic units",
        "breakdown": {
            "parent_task_id": task_data.get("id", "task_123"),
            "atomic_tasks": [
                {
                    "id": "atomic_1",
                    "title": "Set up project structure",
                    "size": "small",
                    "complexity": "simple",
                    "estimated_minutes": 60,
                    "acceptance_criteria": ["Project structure created"],
                    "order": 1,
                },
                {
                    "id": "atomic_2",
                    "title": "Implement core functionality",
                    "size": "medium",
                    "complexity": "moderate",
                    "estimated_minutes": 120,
                    "acceptance_criteria": ["Core functionality working"],
                    "order": 2,
                },
            ],
            "breakdown_reasoning": "Task broken into manageable units",
            "estimated_total_time": 180,
            "suggested_approach": "Execute in order",
        },
    }


@app.post("/api/ai-execution/guidance/{task_id}")
async def get_ai_guidance(task_id: str, guidance_data: dict = None):
    """Mock AI guidance"""
    return {
        "success": True,
        "message": "Task guidance generated successfully",
        "guidance": {
            "guidance_id": f"guidance_{task_id}",
            "task_id": task_id,
            "guidance_type": guidance_data.get("guidance_type", "next_steps")
            if guidance_data
            else "next_steps",
            "content": "Start by breaking down the task into smaller, manageable components. Focus on the most critical functionality first.",
            "confidence": "high",
            "reasoning": "Based on task complexity and best practices",
            "suggestions": [
                "Create a task breakdown",
                "Set up development environment",
                "Implement core functionality first",
            ],
            "estimated_impact": 0.8,
        },
    }


@app.get("/api/timeboxing/insights")
async def get_productivity_insights():
    """Mock productivity insights"""
    return {
        "success": True,
        "message": "Productivity insights retrieved successfully",
        "insights": {
            "period": "30 days",
            "metrics": {
                "average_daily_focus_time": 240,
                "average_productivity_rating": 7.2,
                "total_focus_sessions": 45,
            },
            "recommendations": [
                "Consider adding planning sessions",
                "Your most productive hours are 9-11 AM",
            ],
        },
    }


@app.post("/api/timeboxing/productivity/log")
async def log_productivity(log_data: dict):
    """Mock productivity logging"""
    return {
        "success": True,
        "message": "Daily productivity logged successfully",
        "log": {
            "id": "log_123",
            "productivity_rating": log_data.get("productivity_rating", 7),
            "total_focus_time": log_data.get("total_focus_time", 240),
        },
    }


@app.get("/api/momentum/portfolio")
async def get_portfolio_overview():
    """Mock portfolio overview"""
    return {
        "success": True,
        "message": "Portfolio overview retrieved successfully",
        "portfolio": [
            {
                "project_id": "project_1",
                "name": "E-commerce Platform",
                "stage": "mvp",
                "progress_percentage": 0.75,
                "momentum_score": 82.0,
                "priority_score": 85.0,
                "blockers": ["API integration pending"],
            }
        ],
    }


if __name__ == "__main__":
    print("🚀 Starting Mock AutoAdmin Backend for Testing...")
    print("📍 Server will run on http://localhost:8000")
    print("🎯 Ready for Maestro E2E tests")

    uvicorn.run(
        "mock_backend:app", host="0.0.0.0", port=8000, reload=False, log_level="info"
    )
