"""
GitHub API router for AutoAdmin
Enhanced GitHub operations with comprehensive error handling and monitoring
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

from services.github_client import enhanced_github_client, GitHubClientError, GitHubAuthenticationError, GitHubRepositoryError
from services.github_service import github_service
from communication.github_integration import GitHubActionsIntegration
from core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/github", tags=["GitHub"])
settings = get_settings()

# Pydantic models for request/response
class RepositoryInfo(BaseModel):
    name: str
    full_name: str
    description: str
    language: str
    stars: int
    forks: int
    open_issues: int
    default_branch: str
    clone_url: str


class PullRequestInfo(BaseModel):
    number: int
    title: str
    description: str
    state: str
    author: str
    base_branch: str
    head_branch: str
    url: str
    mergeable: Optional[bool] = None


class IssueInfo(BaseModel):
    number: int
    title: str
    description: str
    state: str
    author: str
    assignees: List[str]
    labels: List[str]
    url: str


class CreateBranchRequest(BaseModel):
    repo_name: str = Field(..., description="Repository name in format 'owner/repo'")
    branch_name: str = Field(..., description="Name of the new branch")
    base_branch: Optional[str] = Field(None, description="Base branch to create from")


class CreateFileRequest(BaseModel):
    repo_name: str = Field(..., description="Repository name in format 'owner/repo'")
    file_path: str = Field(..., description="Path where to create the file")
    content: str = Field(..., description="File content")
    commit_message: str = Field(..., description="Commit message for the change")
    branch: Optional[str] = Field(None, description="Branch to create file in")


class CreatePullRequestRequest(BaseModel):
    repo_name: str = Field(..., description="Repository name in format 'owner/repo'")
    title: str = Field(..., description="Pull request title")
    description: str = Field(..., description="Pull request description")
    head_branch: str = Field(..., description="Branch with changes")
    base_branch: Optional[str] = Field(None, description="Target branch")
    labels: Optional[List[str]] = Field(None, description="List of labels to add to the PR")


class MergePullRequestRequest(BaseModel):
    repo_name: str = Field(..., description="Repository name in format 'owner/repo'")
    pr_number: int = Field(..., description="Pull request number")
    merge_method: str = Field("merge", description="Merge method ('merge', 'squash', 'rebase')")
    commit_title: Optional[str] = Field(None, description="Custom commit title")
    commit_message: Optional[str] = Field(None, description="Custom commit message")


class TriggerWorkflowRequest(BaseModel):
    workflow_name: str = Field(..., description="Name of the workflow to trigger")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Workflow inputs")


async def get_github_integration() -> GitHubActionsIntegration:
    """Get GitHub integration instance"""
    return GitHubActionsIntegration()


@router.get("/health")
async def github_health_check():
    """
    Check GitHub service health and status
    """
    try:
        # Get comprehensive health check
        health_result = await enhanced_github_client.get_service_health()

        return {
            "success": True,
            "health": health_result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"GitHub health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/status")
async def github_status():
    """
    Get comprehensive GitHub service status
    """
    try:
        # Get service status
        service_status = github_service.get_service_status()

        # Test connection
        connection_status = await github_service.test_connection()

        return {
            "success": True,
            "service": service_status,
            "connection": {
                "is_connected": connection_status.is_connected,
                "last_check": connection_status.last_check.isoformat() if connection_status.last_check else None,
                "response_time": connection_status.response_time,
                "error_message": connection_status.error_message,
                "rate_limit_remaining": connection_status.rate_limit_remaining,
                "rate_limit_reset": connection_status.rate_limit_reset.isoformat() if connection_status.rate_limit_reset else None
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"GitHub status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/repo/{repo_name}/info")
async def get_repository_info(repo_name: str):
    """
    Get comprehensive repository information
    """
    try:
        repo_info = await enhanced_github_client.get_repository_info(repo_name)

        if "error" in repo_info:
            raise HTTPException(status_code=404, detail=repo_info["error"])

        return {
            "success": True,
            "repository": repo_info
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting repository info: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting repository info: {str(e)}")


@router.post("/repo/test")
async def test_repository_access(repo_name: str = Query(..., description="Repository name in format 'owner/repo'")):
    """
    Test access to a specific repository
    """
    try:
        result = await enhanced_github_client.test_repository_access(repo_name)

        if not result.get("accessible", False):
            raise HTTPException(status_code=403, detail="Repository access failed")

        return {
            "success": True,
            "repository": result
        }

    except Exception as e:
        logger.error(f"Error testing repository access: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing repository access: {str(e)}")


@router.post("/branch/create")
async def create_branch(request: CreateBranchRequest):
    """
    Create a new branch in a repository
    """
    try:
        result = await enhanced_github_client.create_branch(
            repo_name=request.repo_name,
            branch_name=request.branch_name,
            base_branch=request.base_branch
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "branch": result
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating branch: {str(e)}")


@router.post("/file/create")
async def create_file(request: CreateFileRequest):
    """
    Create or update a file in a repository
    """
    try:
        result = await enhanced_github_client.create_file(
            repo_name=request.repo_name,
            file_path=request.file_path,
            content=request.content,
            commit_message=request.commit_message,
            branch=request.branch
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "file": result
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating file: {str(e)}")


@router.post("/pull-request/create")
async def create_pull_request(request: CreatePullRequestRequest):
    """
    Create a pull request
    """
    try:
        result = await enhanced_github_client.create_pull_request(
            repo_name=request.repo_name,
            title=request.title,
            description=request.description,
            head_branch=request.head_branch,
            base_branch=request.base_branch,
            labels=request.labels
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "pull_request": result
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating pull request: {str(e)}")


@router.get("/repo/{repo_name}/pull-requests")
async def get_pull_requests(
    repo_name: str,
    state: str = Query("open", description="Pull request state ('open', 'closed', 'all')"),
    limit: int = Query(10, description="Maximum number of pull requests to return")
):
    """
    Get pull requests from a repository
    """
    try:
        # Use enhanced GitHub client to get pull requests
        repo = await enhanced_github_client.get_repository(repo_name)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not accessible")

        prs = repo.get_pulls(state=state)[:limit]
        pr_list = []

        for pr in prs:
            pr_info = PullRequestInfo(
                number=pr.number,
                title=pr.title,
                description=pr.body or "",
                state=pr.state,
                author=pr.user.login if pr.user else "Unknown",
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                url=pr.html_url,
                mergeable=pr.mergeable if hasattr(pr, 'mergeable') else None
            )
            pr_list.append(pr_info.dict())

        return {
            "success": True,
            "pull_requests": pr_list,
            "count": len(pr_list)
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting pull requests: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting pull requests: {str(e)}")


@router.get("/repo/{repo_name}/issues")
async def get_issues(
    repo_name: str,
    state: str = Query("open", description="Issue state ('open', 'closed', 'all')"),
    limit: int = Query(10, description="Maximum number of issues to return")
):
    """
    Get issues from a repository
    """
    try:
        # Use enhanced GitHub client to get issues
        repo = await enhanced_github_client.get_repository(repo_name)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not accessible")

        issues = repo.get_issues(state=state)[:limit]
        issue_list = []

        for issue in issues:
            # Skip pull requests (they are also issues in GitHub API)
            if issue.pull_request:
                continue

            issue_info = IssueInfo(
                number=issue.number,
                title=issue.title,
                description=issue.body or "",
                state=issue.state,
                author=issue.user.login if issue.user else "Unknown",
                assignees=[assignee.login for assignee in issue.assignees],
                labels=[label.name for label in issue.labels],
                url=issue.html_url
            )
            issue_list.append(issue_info.dict())

        return {
            "success": True,
            "issues": issue_list,
            "count": len(issue_list)
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting issues: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting issues: {str(e)}")


@router.post("/pull-request/{pr_number}/merge")
async def merge_pull_request(
    pr_number: int,
    request: MergePullRequestRequest
):
    """
    Merge a pull request
    """
    try:
        if request.repo_name != repo_name:
            raise HTTPException(status_code=400, detail="Repository name mismatch")

        result = await enhanced_github_client.merge_pull_request(
            repo_name=request.repo_name,
            pr_number=pr_number,
            merge_method=request.merge_method,
            commit_title=request.commit_title,
            commit_message=request.commit_message
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "merge": result
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=str(e))
    except Exception as e:
        logger.error(f"Error merging pull request: {e}")
        raise HTTPException(status_code=500, detail=f"Error merging pull request: {str(e)}")


@router.get("/pull-request/{pr_number}/mergeable")
async def check_pr_mergeable(repo_name: str, pr_number: int):
    """
    Check if a pull request is mergeable
    """
    try:
        result = await enhanced_github_client.check_pr_mergeable(
            repo_name=repo_name,
            pr_number=pr_number
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "success": True,
            "mergeability": result
        }

    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except GitHubRepositoryError as e:
        raise HTTPException(status_code=e.status_code or 404, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking PR mergeability: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking PR mergeability: {str(e)}")


@router.post("/workflow/trigger")
async def trigger_workflow(
    request: TriggerWorkflowRequest,
    background_tasks: BackgroundTasks,
    integration: GitHubActionsIntegration = Depends(get_github_integration)
):
    """
    Trigger a GitHub workflow
    """
    try:
        # Trigger workflow asynchronously
        result = await integration.trigger_workflow(
            workflow_name=request.workflow_name,
            inputs=request.inputs
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        # Start monitoring workflow in background
        background_tasks.add_task(integration.start)

        return {
            "success": True,
            "workflow": result
        }

    except Exception as e:
        logger.error(f"Error triggering workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering workflow: {str(e)}")


@router.get("/integration/status")
async def get_integration_status(integration: GitHubActionsIntegration = Depends(get_github_integration)):
    """
    Get GitHub integration status
    """
    try:
        status = await integration.get_integration_status()

        return {
            "success": True,
            "integration": status
        }

    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting integration status: {str(e)}")


@router.post("/integration/start")
async def start_github_integration(
    background_tasks: BackgroundTasks,
    integration: GitHubActionsIntegration = Depends(get_github_integration)
):
    """
    Start GitHub integration monitoring
    """
    try:
        # Initialize first
        initialized = await integration.initialize()
        if not initialized:
            raise HTTPException(status_code=500, detail="Failed to initialize GitHub integration")

        # Start in background
        background_tasks.add_task(integration.start)

        return {
            "success": True,
            "message": "GitHub integration started"
        }

    except Exception as e:
        logger.error(f"Error starting GitHub integration: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting GitHub integration: {str(e)}")


@router.post("/integration/stop")
async def stop_github_integration(integration: GitHubActionsIntegration = Depends(get_github_integration)):
    """
    Stop GitHub integration monitoring
    """
    try:
        await integration.stop()

        return {
            "success": True,
            "message": "GitHub integration stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping GitHub integration: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping GitHub integration: {str(e)}")