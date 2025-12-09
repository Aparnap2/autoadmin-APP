"""
Deep Git Integration Service
Handles automatic branch creation, PR management, and CI/CD integration
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
import re
import os
import subprocess

from pydantic import BaseModel, Field
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.Branch import Branch

from services.firebase_service import get_firebase_service


class GitProvider(str, Enum):
    """Supported Git providers"""

    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class BranchStatus(str, Enum):
    """Git branch status"""

    CREATED = "created"
    ACTIVE = "active"
    MERGED = "merged"
    CLOSED = "closed"
    DELETED = "deleted"


class PRStatus(str, Enum):
    """Pull request status"""

    DRAFT = "draft"
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"


class CIStatus(str, Enum):
    """CI/CD status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class GitBranch:
    """Git branch information"""

    name: str
    sha: str
    status: BranchStatus
    created_at: datetime
    updated_at: datetime
    task_id: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None


@dataclass
class GitCommit:
    """Git commit information"""

    sha: str
    message: str
    author: str
    timestamp: datetime
    task_id: str
    branch: str


@dataclass
class PullRequestInfo:
    """Pull request information"""

    number: int
    title: str
    description: str
    status: PRStatus
    branch: str
    base_branch: str
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime]
    task_id: str
    ci_status: CIStatus
    reviewers: List[str]
    labels: List[str]


@dataclass
class GitIntegrationStatus:
    """Overall Git integration status"""

    connected: bool
    provider: GitProvider
    repository: str
    default_branch: str
    active_branches: int
    open_prs: int
    recent_commits: int
    ci_status: CIStatus
    last_sync: datetime
    errors: List[str]


class GitIntegrationService:
    """Service for deep Git integration with task management"""

    def __init__(self, github_token: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()

        # Git provider clients
        self.github_client = Github(github_token) if github_token else None

        # Configuration
        self.branch_prefix = "feature/task-"
        self.pr_template_path = ".github/PULL_REQUEST_TEMPLATE.md"
        self.commit_message_template = "[{task_id}] {message}"

        # Cache for performance
        self._repo_cache = {}
        self._cache_ttl = 300  # 5 minutes

    async def create_task_branch(
        self, task_id: str, task_title: str, repository: str, base_branch: str = "main"
    ) -> GitBranch:
        """Create a Git branch for a task"""
        try:
            self.logger.info(f"Creating branch for task {task_id}: {task_title}")

            # Generate branch name
            branch_name = self._generate_branch_name(task_id, task_title)

            # Create branch via GitHub API
            repo = await self._get_repository(repository)
            if not repo:
                raise ValueError(f"Repository {repository} not found or inaccessible")

            # Get base branch
            base_ref = repo.get_branch(base_branch)
            if not base_ref:
                raise ValueError(f"Base branch {base_branch} not found")

            # Create new branch
            try:
                new_branch = repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}", sha=base_ref.commit.sha
                )
            except Exception as e:
                if "already exists" in str(e).lower():
                    # Branch already exists, get it
                    existing_branch = repo.get_branch(branch_name)
                    new_branch = existing_branch.commit
                    branch_name = existing_branch.name
                else:
                    raise

            # Create GitBranch object
            git_branch = GitBranch(
                name=branch_name,
                sha=new_branch.sha if hasattr(new_branch, "sha") else str(new_branch),
                status=BranchStatus.CREATED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                task_id=task_id,
            )

            # Store branch information
            await self._store_branch_info(git_branch, repository)

            self.logger.info(f"Created branch {branch_name} for task {task_id}")
            return git_branch

        except Exception as e:
            self.logger.error(f"Error creating task branch: {e}")
            raise

    async def create_task_pr(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        branch_name: str,
        repository: str,
        base_branch: str = "main",
    ) -> PullRequestInfo:
        """Create a pull request for a task"""
        try:
            self.logger.info(f"Creating PR for task {task_id} on branch {branch_name}")

            repo = await self._get_repository(repository)
            if not repo:
                raise ValueError(f"Repository {repository} not found")

            # Generate PR title and description
            pr_title = f"[{task_id}] {task_title}"
            pr_description = await self._generate_pr_description(
                task_id, task_title, task_description, branch_name
            )

            # Create PR
            pr = repo.create_pull(
                title=pr_title,
                body=pr_description,
                head=branch_name,
                base=base_branch,
                draft=True,  # Start as draft
            )

            # Create PullRequestInfo object
            pr_info = PullRequestInfo(
                number=pr.number,
                title=pr.title,
                description=pr.body,
                status=PRStatus.DRAFT,
                branch=branch_name,
                base_branch=base_branch,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                merged_at=None,
                task_id=task_id,
                ci_status=CIStatus.PENDING,
                reviewers=[],
                labels=[],
            )

            # Update branch with PR info
            await self._update_branch_pr_info(
                branch_name, repository, pr.number, pr.html_url
            )

            # Store PR information
            await self._store_pr_info(pr_info, repository)

            self.logger.info(f"Created PR #{pr.number} for task {task_id}")
            return pr_info

        except Exception as e:
            self.logger.error(f"Error creating task PR: {e}")
            raise

    async def commit_task_changes(
        self,
        task_id: str,
        commit_message: str,
        files_changed: List[str],
        repository: str,
        branch_name: Optional[str] = None,
    ) -> GitCommit:
        """Record a commit for a task"""
        try:
            # Get branch for task if not provided
            if not branch_name:
                branch_name = await self._get_task_branch(task_id, repository)

            if not branch_name:
                raise ValueError(f"No branch found for task {task_id}")

            # This would typically be done through Git CLI or API
            # For now, we'll simulate and store the commit info

            commit = GitCommit(
                sha=f"commit_{uuid.uuid4().hex[:8]}",  # Would be actual SHA
                message=self._format_commit_message(task_id, commit_message),
                author="task_system",  # Would be actual author
                timestamp=datetime.now(timezone.utc),
                task_id=task_id,
                branch=branch_name,
            )

            # Store commit information
            await self._store_commit_info(commit, repository)

            # Update branch last activity
            await self._update_branch_activity(branch_name, repository)

            self.logger.info(f"Recorded commit for task {task_id}: {commit.message}")
            return commit

        except Exception as e:
            self.logger.error(f"Error committing task changes: {e}")
            raise

    async def update_pr_status(
        self,
        task_id: str,
        repository: str,
        status: PRStatus,
        ci_status: Optional[CIStatus] = None,
    ) -> bool:
        """Update pull request status"""
        try:
            pr_info = await self._get_task_pr(task_id, repository)
            if not pr_info:
                self.logger.warning(f"No PR found for task {task_id}")
                return False

            # Update status
            pr_info.status = status
            pr_info.updated_at = datetime.now(timezone.utc)

            if ci_status:
                pr_info.ci_status = ci_status

            # Store updated PR info
            await self._store_pr_info(pr_info, repository)

            self.logger.info(f"Updated PR status for task {task_id} to {status.value}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating PR status: {e}")
            return False

    async def get_git_integration_status(self, repository: str) -> GitIntegrationStatus:
        """Get overall Git integration status"""
        try:
            connected = self.github_client is not None

            if not connected:
                return GitIntegrationStatus(
                    connected=False,
                    provider=GitProvider.GITHUB,
                    repository=repository,
                    default_branch="main",
                    active_branches=0,
                    open_prs=0,
                    recent_commits=0,
                    ci_status=CIStatus.PENDING,
                    last_sync=datetime.now(timezone.utc),
                    errors=["GitHub client not configured"],
                )

            # Get repository info
            repo = await self._get_repository(repository)
            if not repo:
                return GitIntegrationStatus(
                    connected=False,
                    provider=GitProvider.GITHUB,
                    repository=repository,
                    default_branch="main",
                    active_branches=0,
                    open_prs=0,
                    recent_commits=0,
                    ci_status=CIStatus.PENDING,
                    last_sync=datetime.now(timezone.utc),
                    errors=["Repository not accessible"],
                )

            # Get branch and PR counts
            branches = list(repo.get_branches())
            active_branches = len(
                [
                    b
                    for b in branches
                    if not b.name.startswith(("main", "master", "develop"))
                ]
            )

            prs = repo.get_pulls(state="open")
            open_prs = len(list(prs))

            # Get recent commits (last 24 hours)
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            commits = repo.get_commits(since=since)
            recent_commits = len(list(commits))

            # Determine CI status (simplified)
            ci_status = CIStatus.SUCCESS  # Would check actual CI status

            return GitIntegrationStatus(
                connected=True,
                provider=GitProvider.GITHUB,
                repository=repository,
                default_branch=repo.default_branch,
                active_branches=active_branches,
                open_prs=open_prs,
                recent_commits=recent_commits,
                ci_status=ci_status,
                last_sync=datetime.now(timezone.utc),
                errors=[],
            )

        except Exception as e:
            self.logger.error(f"Error getting Git integration status: {e}")
            return GitIntegrationStatus(
                connected=False,
                provider=GitProvider.GITHUB,
                repository=repository,
                default_branch="main",
                active_branches=0,
                open_prs=0,
                recent_commits=0,
                ci_status=CIStatus.PENDING,
                last_sync=datetime.now(timezone.utc),
                errors=[str(e)],
            )

    async def merge_task_pr(
        self, task_id: str, repository: str, merge_method: str = "squash"
    ) -> bool:
        """Merge a task's pull request"""
        try:
            pr_info = await self._get_task_pr(task_id, repository)
            if not pr_info:
                raise ValueError(f"No PR found for task {task_id}")

            repo = await self._get_repository(repository)
            if not repo:
                raise ValueError(f"Repository {repository} not accessible")

            pr = repo.get_pull(pr_info.number)

            # Merge the PR
            merge_result = pr.merge(
                commit_message=f"Merge {pr_info.title}", merge_method=merge_method
            )

            if merge_result.merged:
                # Update PR status
                pr_info.status = PRStatus.MERGED
                pr_info.merged_at = datetime.now(timezone.utc)
                pr_info.updated_at = datetime.now(timezone.utc)

                await self._store_pr_info(pr_info, repository)

                # Update branch status
                await self._update_branch_status(
                    pr_info.branch, repository, BranchStatus.MERGED
                )

                self.logger.info(f"Merged PR #{pr_info.number} for task {task_id}")
                return True
            else:
                self.logger.error(f"Failed to merge PR #{pr_info.number}")
                return False

        except Exception as e:
            self.logger.error(f"Error merging task PR: {e}")
            return False

    # Private helper methods

    def _generate_branch_name(self, task_id: str, task_title: str) -> str:
        """Generate a Git branch name for a task"""
        # Clean task title for branch name
        clean_title = re.sub(r"[^\w\-_]", "-", task_title.lower())
        clean_title = re.sub(r"-+", "-", clean_title).strip("-")

        # Truncate if too long
        if len(clean_title) > 30:
            clean_title = clean_title[:30].rstrip("-")

        return f"{self.branch_prefix}{task_id}-{clean_title}"

    async def _generate_pr_description(
        self, task_id: str, task_title: str, task_description: str, branch_name: str
    ) -> str:
        """Generate PR description using template"""
        try:
            template = f"""## Task: {task_title}

**Task ID:** {task_id}
**Branch:** {branch_name}

### Description
{task_description}

### Changes
<!-- Describe the changes made in this PR -->

### Testing
<!-- Describe how this was tested -->

### Checklist
- [ ] Code follows project standards
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Ready for review

### Related
- Task: {task_id}
- Branch: {branch_name}
"""

            return template

        except Exception as e:
            self.logger.error(f"Error generating PR description: {e}")
            return f"Task: {task_title}\n\n{task_description}"

    def _format_commit_message(self, task_id: str, message: str) -> str:
        """Format commit message with task ID"""
        return self.commit_message_template.format(task_id=task_id, message=message)

    async def _get_repository(self, repository: str) -> Optional[Repository]:
        """Get GitHub repository object"""
        try:
            if not self.github_client:
                return None

            # Check cache
            cache_key = f"repo_{repository}"
            if cache_key in self._repo_cache:
                cached_data, timestamp = self._repo_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_ttl:
                    return cached_data

            # Get repository
            repo = self.github_client.get_repo(repository)

            # Cache result
            self._repo_cache[cache_key] = (repo, datetime.now())

            return repo

        except Exception as e:
            self.logger.error(f"Error getting repository {repository}: {e}")
            return None

    async def _get_task_branch(self, task_id: str, repository: str) -> Optional[str]:
        """Get branch name for a task"""
        try:
            # Query Firebase for branch info
            # This would be implemented with actual Firebase queries
            return f"{self.branch_prefix}{task_id}"

        except Exception as e:
            self.logger.error(f"Error getting task branch: {e}")
            return None

    async def _get_task_pr(
        self, task_id: str, repository: str
    ) -> Optional[PullRequestInfo]:
        """Get PR info for a task"""
        try:
            # Query Firebase for PR info
            return None

        except Exception as e:
            self.logger.error(f"Error getting task PR: {e}")
            return None

    async def _store_branch_info(self, branch: GitBranch, repository: str):
        """Store branch information in Firebase"""
        try:
            data = asdict(branch)
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"git_branches/{repository}/{branch.name}", json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing branch info: {e}")

    async def _store_pr_info(self, pr: PullRequestInfo, repository: str):
        """Store PR information in Firebase"""
        try:
            data = asdict(pr)
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()
            if data.get("merged_at"):
                data["merged_at"] = data["merged_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"git_prs/{repository}/{pr.number}", json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing PR info: {e}")

    async def _store_commit_info(self, commit: GitCommit, repository: str):
        """Store commit information in Firebase"""
        try:
            data = asdict(commit)
            data["timestamp"] = data["timestamp"].isoformat()

            await self.firebase_service.store_agent_file(
                f"git_commits/{repository}/{commit.sha}", json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing commit info: {e}")

    async def _update_branch_pr_info(
        self, branch_name: str, repository: str, pr_number: int, pr_url: str
    ):
        """Update branch with PR information"""
        try:
            # This would update the stored branch info
            pass

        except Exception as e:
            self.logger.error(f"Error updating branch PR info: {e}")

    async def _update_branch_activity(self, branch_name: str, repository: str):
        """Update branch last activity timestamp"""
        try:
            # This would update the stored branch info
            pass

        except Exception as e:
            self.logger.error(f"Error updating branch activity: {e}")

    async def _update_branch_status(
        self, branch_name: str, repository: str, status: BranchStatus
    ):
        """Update branch status"""
        try:
            # This would update the stored branch info
            pass

        except Exception as e:
            self.logger.error(f"Error updating branch status: {e}")

    async def setup_repository_integration(
        self, repository: str, webhook_url: Optional[str] = None
    ) -> bool:
        """Setup Git repository integration with webhooks"""
        try:
            repo = await self._get_repository(repository)
            if not repo:
                return False

            # Create webhook for PR and push events
            if webhook_url:
                webhook_config = {
                    "url": webhook_url,
                    "content_type": "json",
                    "events": ["pull_request", "push", "status"],
                }

                repo.create_hook(
                    name="web",
                    config=webhook_config,
                    events=["pull_request", "push", "status"],
                    active=True,
                )

            # Setup branch protection rules
            default_branch = repo.default_branch
            repo.get_branch(default_branch).edit_protection(
                required_approving_review_count=1,
                dismiss_stale_reviews=True,
                require_code_owner_reviews=False,
                restrictions=None,
            )

            self.logger.info(f"Setup repository integration for {repository}")
            return True

        except Exception as e:
            self.logger.error(f"Error setting up repository integration: {e}")
            return False

    async def handle_webhook_event(
        self, event_type: str, event_data: Dict[str, Any], repository: str
    ):
        """Handle incoming webhook events from Git provider"""
        try:
            if event_type == "pull_request":
                await self._handle_pr_webhook(event_data, repository)
            elif event_type == "push":
                await self._handle_push_webhook(event_data, repository)
            elif event_type == "status":
                await self._handle_status_webhook(event_data, repository)

        except Exception as e:
            self.logger.error(f"Error handling webhook event {event_type}: {e}")

    async def _handle_pr_webhook(self, event_data: Dict[str, Any], repository: str):
        """Handle pull request webhook events"""
        try:
            action = event_data.get("action")
            pr_data = event_data.get("pull_request", {})

            if action in ["opened", "reopened", "closed", "merged"]:
                # Update PR status in our system
                pr_number = pr_data.get("number")
                if pr_number:
                    # Find associated task
                    task_id = await self._find_task_by_pr(repository, pr_number)
                    if task_id:
                        status_map = {
                            "opened": PRStatus.OPEN,
                            "reopened": PRStatus.OPEN,
                            "closed": PRStatus.CLOSED,
                            "merged": PRStatus.MERGED,
                        }
                        status = status_map.get(action, PRStatus.OPEN)
                        await self.update_pr_status(task_id, repository, status)

        except Exception as e:
            self.logger.error(f"Error handling PR webhook: {e}")

    async def _handle_push_webhook(self, event_data: Dict[str, Any], repository: str):
        """Handle push webhook events"""
        try:
            commits = event_data.get("commits", [])
            branch = event_data.get("ref", "").replace("refs/heads/", "")

            for commit_data in commits:
                message = commit_data.get("message", "")
                # Extract task ID from commit message
                task_id = self._extract_task_id_from_commit(message)
                if task_id:
                    # Record commit
                    await self.commit_task_changes(
                        task_id=task_id,
                        commit_message=message,
                        files_changed=commit_data.get("modified", []),
                        repository=repository,
                        branch_name=branch,
                    )

        except Exception as e:
            self.logger.error(f"Error handling push webhook: {e}")

    async def _handle_status_webhook(self, event_data: Dict[str, Any], repository: str):
        """Handle status (CI) webhook events"""
        try:
            state = event_data.get("state")  # success, failure, pending, error
            sha = event_data.get("sha")

            # Find associated PR and task
            pr_info = await self._find_pr_by_commit(repository, sha)
            if pr_info:
                ci_status_map = {
                    "success": CIStatus.SUCCESS,
                    "failure": CIStatus.FAILURE,
                    "error": CIStatus.FAILURE,
                    "pending": CIStatus.PENDING,
                    "running": CIStatus.RUNNING,
                }
                ci_status = ci_status_map.get(state, CIStatus.PENDING)
                await self.update_pr_status(
                    pr_info.task_id, repository, pr_info.status, ci_status
                )

        except Exception as e:
            self.logger.error(f"Error handling status webhook: {e}")

    def _extract_task_id_from_commit(self, message: str) -> Optional[str]:
        """Extract task ID from commit message"""
        # Look for pattern like [TASK-123] or [task_123]
        match = re.search(r"\[([A-Za-z]+[-_]\d+)\]", message)
        return match.group(1) if match else None

    async def _find_task_by_pr(self, repository: str, pr_number: int) -> Optional[str]:
        """Find task ID associated with a PR"""
        try:
            # Query stored PR info
            return None

        except Exception as e:
            self.logger.error(f"Error finding task by PR: {e}")
            return None

    async def _find_pr_by_commit(
        self, repository: str, sha: str
    ) -> Optional[PullRequestInfo]:
        """Find PR associated with a commit"""
        try:
            # Query stored PR info
            return None

        except Exception as e:
            self.logger.error(f"Error finding PR by commit: {e}")
            return None


# Global service instance
_git_integration_service = None


def get_git_integration_service(
    github_token: Optional[str] = None,
) -> GitIntegrationService:
    """Get singleton Git integration service"""
    global _git_integration_service
    if _git_integration_service is None:
        _git_integration_service = GitIntegrationService(github_token)
    return _git_integration_service
