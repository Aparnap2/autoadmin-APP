"""
Git Integration API Routes
Provides endpoints for Git branch management, PR creation, and CI/CD integration
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import ValidationError

from services.git_integration import get_git_integration_service
from models.common import ErrorResponse, BaseResponse


# Authentication dependency (placeholder)
async def get_current_user() -> str:
    """Get current authenticated user ID"""
    # This would integrate with your auth system
    return "user_123"


# GitHub token dependency (placeholder)
async def get_github_token() -> Optional[str]:
    """Get GitHub token for API access"""
    # This would come from user config or environment
    return None  # Will use public access for now


router = APIRouter(prefix="/api/git", tags=["Git Integration"])


@router.post("/branch/create")
async def create_task_branch(
    task_id: str,
    task_title: str,
    repository: str,
    base_branch: str = "main",
    github_token: Optional[str] = Depends(get_github_token),
):
    """Create a Git branch for a task"""
    try:
        service = get_git_integration_service(github_token)
        branch = await service.create_task_branch(
            task_id=task_id,
            task_title=task_title,
            repository=repository,
            base_branch=base_branch,
        )

        return {
            "success": True,
            "message": f"Branch '{branch.name}' created successfully",
            "branch": {
                "name": branch.name,
                "sha": branch.sha,
                "status": branch.status,
                "task_id": branch.task_id,
                "created_at": branch.created_at.isoformat(),
                "updated_at": branch.updated_at.isoformat(),
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
        logging.error(f"Error creating task branch: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create Git branch", error=str(e)
            ).dict(),
        )


@router.post("/pr/create")
async def create_task_pr(
    task_id: str,
    task_title: str,
    task_description: str,
    branch_name: str,
    repository: str,
    base_branch: str = "main",
    github_token: Optional[str] = Depends(get_github_token),
):
    """Create a pull request for a task"""
    try:
        service = get_git_integration_service(github_token)
        pr = await service.create_task_pr(
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            branch_name=branch_name,
            repository=repository,
            base_branch=base_branch,
        )

        return {
            "success": True,
            "message": f"Pull request #{pr.number} created successfully",
            "pr": {
                "number": pr.number,
                "title": pr.title,
                "status": pr.status,
                "branch": pr.branch,
                "base_branch": pr.base_branch,
                "task_id": pr.task_id,
                "ci_status": pr.ci_status,
                "url": pr.pr_url,
                "created_at": pr.created_at.isoformat(),
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
        logging.error(f"Error creating task PR: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to create pull request", error=str(e)
            ).dict(),
        )


@router.post("/commit")
async def commit_task_changes(
    task_id: str,
    commit_message: str,
    files_changed: List[str],
    repository: str,
    branch_name: Optional[str] = None,
    github_token: Optional[str] = Depends(get_github_token),
):
    """Record a commit for a task"""
    try:
        service = get_git_integration_service(github_token)
        commit = await service.commit_task_changes(
            task_id=task_id,
            commit_message=commit_message,
            files_changed=files_changed,
            repository=repository,
            branch_name=branch_name,
        )

        return {
            "success": True,
            "message": "Commit recorded successfully",
            "commit": {
                "sha": commit.sha,
                "message": commit.message,
                "author": commit.author,
                "task_id": commit.task_id,
                "branch": commit.branch,
                "timestamp": commit.timestamp.isoformat(),
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
        logging.error(f"Error recording commit: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to record commit", error=str(e)
            ).dict(),
        )


@router.post("/pr/merge")
async def merge_task_pr(
    task_id: str,
    repository: str,
    merge_method: str = "squash",
    github_token: Optional[str] = Depends(get_github_token),
):
    """Merge a task's pull request"""
    try:
        service = get_git_integration_service(github_token)
        success = await service.merge_task_pr(
            task_id=task_id, repository=repository, merge_method=merge_method
        )

        if success:
            return {"success": True, "message": "Pull request merged successfully"}
        else:
            return {"success": False, "message": "Failed to merge pull request"}

    except Exception as e:
        logging.error(f"Error merging PR: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to merge pull request", error=str(e)
            ).dict(),
        )


@router.get("/status")
async def get_git_integration_status(
    repository: str, github_token: Optional[str] = Depends(get_github_token)
):
    """Get Git integration status"""
    try:
        service = get_git_integration_service(github_token)
        status = await service.get_git_integration_status(repository)

        return {
            "success": True,
            "message": "Git integration status retrieved",
            "status": {
                "connected": status.connected,
                "provider": status.provider,
                "repository": status.repository,
                "default_branch": status.default_branch,
                "active_branches": status.active_branches,
                "open_prs": status.open_prs,
                "recent_commits": status.recent_commits,
                "ci_status": status.ci_status,
                "last_sync": status.last_sync.isoformat(),
                "errors": status.errors,
            },
        }

    except Exception as e:
        logging.error(f"Error getting Git status: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to get Git integration status",
                error=str(e),
            ).dict(),
        )


@router.post("/setup-integration")
async def setup_repository_integration(
    repository: str,
    webhook_url: Optional[str] = None,
    github_token: Optional[str] = Depends(get_github_token),
):
    """Setup Git repository integration"""
    try:
        service = get_git_integration_service(github_token)
        success = await service.setup_repository_integration(
            repository=repository, webhook_url=webhook_url
        )

        if success:
            return {
                "success": True,
                "message": "Repository integration setup successfully",
            }
        else:
            return {
                "success": False,
                "message": "Failed to setup repository integration",
            }

    except Exception as e:
        logging.error(f"Error setting up repository integration: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False,
                message="Failed to setup repository integration",
                error=str(e),
            ).dict(),
        )


@router.post("/webhook")
async def handle_git_webhook(
    event_type: str,
    event_data: Dict[str, Any],
    repository: str,
    background_tasks: BackgroundTasks,
    github_token: Optional[str] = Depends(get_github_token),
):
    """Handle incoming Git webhook events"""
    try:
        # Add background task to process webhook
        background_tasks.add_task(
            process_git_webhook_background,
            event_type,
            event_data,
            repository,
            github_token,
        )

        return {"success": True, "message": "Webhook event queued for processing"}

    except Exception as e:
        logging.error(f"Error handling Git webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to process webhook", error=str(e)
            ).dict(),
        )


async def process_git_webhook_background(
    event_type: str,
    event_data: Dict[str, Any],
    repository: str,
    github_token: Optional[str],
):
    """Process Git webhook event in background"""
    try:
        service = get_git_integration_service(github_token)
        await service.handle_webhook_event(event_type, event_data, repository)
        logging.info(f"Processed {event_type} webhook for {repository}")

    except Exception as e:
        logging.error(f"Error processing webhook background task: {e}")


@router.get("/branches")
async def get_task_branches(
    task_id: Optional[str] = None,
    repository: str = Query(...),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    github_token: Optional[str] = Depends(get_github_token),
):
    """Get Git branches (optionally filtered by task)"""
    try:
        # This would query stored branch information
        # For now, return mock data
        branches = []

        return {
            "success": True,
            "message": "Branches retrieved successfully",
            "branches": branches,
            "total": len(branches),
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
        }

    except Exception as e:
        logging.error(f"Error getting branches: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve branches", error=str(e)
            ).dict(),
        )


@router.get("/prs")
async def get_task_prs(
    task_id: Optional[str] = None,
    repository: str = Query(...),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    github_token: Optional[str] = Depends(get_github_token),
):
    """Get pull requests (optionally filtered by task)"""
    try:
        # This would query stored PR information
        # For now, return mock data
        prs = []

        return {
            "success": True,
            "message": "Pull requests retrieved successfully",
            "prs": prs,
            "total": len(prs),
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
        }

    except Exception as e:
        logging.error(f"Error getting PRs: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve pull requests", error=str(e)
            ).dict(),
        )


@router.get("/commits")
async def get_task_commits(
    task_id: Optional[str] = None,
    repository: str = Query(...),
    branch: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    github_token: Optional[str] = Depends(get_github_token),
):
    """Get commits (optionally filtered by task)"""
    try:
        # This would query stored commit information
        # For now, return mock data
        commits = []

        return {
            "success": True,
            "message": "Commits retrieved successfully",
            "commits": commits,
            "total": len(commits),
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
        }

    except Exception as e:
        logging.error(f"Error getting commits: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                success=False, message="Failed to retrieve commits", error=str(e)
            ).dict(),
        )
