"""
Enhanced GitHub client with comprehensive error handling and recovery mechanisms
Integrates with the GitHubService for robust GitHub API operations
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from github import Github, GithubException, Repository, PullRequest, Issue
from github.ContentFile import ContentFile
from .github_service import github_service
from backend.communication.github_integration import GitHubActionsIntegration
from backend.fastapi.app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """Base exception for GitHub client errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class GitHubAuthenticationError(GitHubClientError):
    """Authentication related errors"""

    pass


class GitHubRateLimitError(GitHubClientError):
    """Rate limit related errors"""

    def __init__(self, message: str, reset_time: Optional[datetime] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.reset_time = reset_time


class GitHubRepositoryError(GitHubClientError):
    """Repository operation errors"""

    pass


class EnhancedGitHubClient:
    """
    Enhanced GitHub client with comprehensive error handling and retry logic
    """

    def __init__(self):
        self.service = github_service
        self._client_cache = None
        self._last_client_update = None

    async def get_client(self) -> Github:
        """Get authenticated GitHub client with caching"""
        now = datetime.now()

        # Cache client for 5 minutes to avoid re-authentication
        if (
            self._client_cache
            and self._last_client_update
            and (now - self._last_client_update).seconds < 300
        ):
            return self._client_cache

        client = await self.service.execute_with_retry(self.service.get_github_client)
        if client:
            self._client_cache = client
            self._last_client_update = now
            logger.info("GitHub client initialized and cached")
        else:
            raise GitHubAuthenticationError("Failed to initialize GitHub client")

        return client

    async def test_repository_access(self, repo_name: str) -> Dict[str, Any]:
        """Test access to a specific repository"""
        try:
            client = await self.get_client()
            repo = client.get_repo(repo_name)

            # Basic repository info
            repo_info = {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "permissions": repo.permissions.to_dict() if repo.permissions else None,
                "accessible": True,
            }

            logger.info(f"Successfully tested access to repository: {repo_name}")
            return repo_info

        except GithubException as e:
            error_message = f"Failed to access repository {repo_name}: {str(e)}"
            logger.error(error_message)

            return {
                "name": repo_name,
                "accessible": False,
                "error": {
                    "message": str(e),
                    "status": e.status if hasattr(e, "status") else None,
                },
            }

    async def get_repository(self, repo_name: str) -> Optional[Repository]:
        """
        Get repository with enhanced error handling

        Args:
            repo_name: Repository name in format 'owner/repo'

        Returns:
            Repository object or None if not accessible

        Raises:
            GitHubAuthenticationError: For authentication issues
            GitHubRepositoryError: For repository access issues
        """
        try:
            client = await self.get_client()
            repo = client.get_repo(repo_name)
            logger.info(f"Successfully accessed repository: {repo_name}")
            return repo

        except GithubException as e:
            if e.status == 401:
                raise GitHubAuthenticationError(
                    "Authentication failed", status_code=401
                )
            elif e.status == 404:
                raise GitHubRepositoryError(
                    f"Repository '{repo_name}' not found", status_code=404
                )
            elif e.status == 403:
                raise GitHubAuthenticationError("Access forbidden", status_code=403)
            else:
                raise GitHubRepositoryError(
                    f"Error accessing repository: {str(e)}", status_code=e.status
                )
        except Exception as e:
            raise GitHubRepositoryError(
                f"Unexpected error accessing repository: {str(e)}"
            )

    async def get_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """
        Get comprehensive repository information

        Args:
            repo_name: Repository name in format 'owner/repo'

        Returns:
            Dictionary with repository information
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {"error": "Repository not accessible"}

            # Get languages with error handling
            languages = {}
            try:
                languages = repo.get_languages()
            except Exception as e:
                logger.warning(f"Failed to get languages for {repo_name}: {e}")

            # Get contributors (limited to avoid API rate limits)
            contributors = []
            try:
                contributors_list = repo.get_contributors()[:10]  # Limit to 10
                contributors = [
                    {
                        "login": contributor.login,
                        "type": contributor.type,
                        "contributions": contributor.contributions,
                    }
                    for contributor in contributors_list
                ]
            except Exception as e:
                logger.warning(f"Failed to get contributors for {repo_name}: {e}")

            # Get recent commits
            recent_commits = []
            try:
                commits = repo.get_commits()[:5]  # Limit to 5
                recent_commits = [
                    {
                        "sha": commit.sha,
                        "message": commit.commit.message.split("\n")[0],
                        "author": commit.commit.author.name
                        if commit.commit.author
                        else "Unknown",
                        "date": commit.commit.author.date.isoformat()
                        if commit.commit.author
                        else None,
                    }
                    for commit in commits
                ]
            except Exception as e:
                logger.warning(f"Failed to get commits for {repo_name}: {e}")

            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "default_branch": repo.default_branch,
                "private": repo.private,
                "language": repo.language,
                "languages": languages,
                "size": repo.size,
                "stargazers_count": repo.stargazers_count,
                "watchers_count": repo.watchers_count,
                "forks_count": repo.forks_count,
                "open_issues_count": repo.open_issues_count,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "pushed_at": repo.pushed_at.isoformat(),
                "contributors": contributors,
                "recent_commits": recent_commits,
                "permissions": repo.permissions.to_dict() if repo.permissions else None,
                "has_issues": repo.has_issues,
                "has_projects": repo.has_projects,
                "has_wiki": repo.has_wiki,
                "has_pages": repo.has_pages,
                "has_downloads": repo.has_downloads,
                "archived": repo.archived,
                "disabled": repo.disabled,
                "license": repo.license.name if repo.license else None,
            }

        except (GitHubAuthenticationError, GitHubRepositoryError) as e:
            return {"error": str(e), "type": e.__class__.__name__}
        except Exception as e:
            logger.error(f"Unexpected error getting repository info: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    async def create_branch(
        self, repo_name: str, branch_name: str, base_branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new branch with comprehensive error handling

        Args:
            repo_name: Repository name in format 'owner/repo'
            branch_name: Name of the new branch
            base_branch: Base branch to create from (default: default branch)

        Returns:
            Dictionary with operation result
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {"success": False, "error": "Repository not accessible"}

            # Get the base branch
            if not base_branch:
                base_branch = repo.default_branch

            # Get the reference to the base branch
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            sha = base_ref.object.sha

            # Create the new branch
            new_ref = repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)

            result = {
                "success": True,
                "branch_name": branch_name,
                "base_branch": base_branch,
                "sha": sha,
                "ref": new_ref.ref,
                "url": f"https://github.com/{repo_name}/tree/{branch_name}",
            }

            logger.info(
                f"Created branch '{branch_name}' from '{base_branch}' in {repo_name}"
            )
            return result

        except GithubException as e:
            error_msg = f"Failed to create branch '{branch_name}': {str(e)}"
            logger.error(error_msg)

            result = {
                "success": False,
                "error": error_msg,
                "status_code": e.status if hasattr(e, "status") else None,
            }

            # Handle specific error cases
            if e.status == 409:
                result["error"] = f"Branch '{branch_name}' already exists"
            elif e.status == 422:
                result["error"] = f"Invalid branch name or reference: {branch_name}"

            return result

        except Exception as e:
            error_msg = f"Unexpected error creating branch: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def create_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a file with comprehensive error handling

        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path where to create the file
            content: File content
            commit_message: Commit message for the change
            branch: Branch to create file in (default: default branch)

        Returns:
            Dictionary with operation result
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {"success": False, "error": "Repository not accessible"}

            target_branch = branch or repo.default_branch

            # Check if file already exists to get its SHA
            sha = None
            try:
                existing_file = repo.get_contents(file_path, ref=target_branch)
                if isinstance(existing_file, ContentFile):
                    sha = existing_file.sha
            except:
                pass  # File doesn't exist, which is fine for creation

            # Create or update the file
            file_result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=target_branch,
                sha=sha,  # Required for updates
            )

            result = {
                "success": True,
                "file_path": file_path,
                "branch": target_branch,
                "commit_sha": file_result["commit"].sha,
                "content_url": file_result["content"].html_url,
                "commit_url": file_result["commit"].html_url,
                "action": "updated" if sha else "created",
            }

            action_str = "updated" if sha else "created"
            logger.info(f"{action_str.title()} file '{file_path}' in {repo_name}")
            return result

        except GithubException as e:
            error_msg = f"Failed to create file '{file_path}': {str(e)}"
            logger.error(error_msg)

            result = {
                "success": False,
                "error": error_msg,
                "status_code": e.status if hasattr(e, "status") else None,
            }

            # Handle specific error cases
            if e.status == 413:
                result["error"] = f"File too large: {file_path}"
            elif e.status == 422:
                result["error"] = f"Invalid file path or content: {file_path}"

            return result

        except Exception as e:
            error_msg = f"Unexpected error creating file: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        description: str,
        head_branch: str,
        base_branch: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a pull request with comprehensive error handling

        Args:
            repo_name: Repository name in format 'owner/repo'
            title: PR title
            description: PR description
            head_branch: Branch with changes
            base_branch: Target branch (default: default branch)
            labels: List of labels to add to the PR

        Returns:
            Dictionary with operation result
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {"success": False, "error": "Repository not accessible"}

            target_base_branch = base_branch or repo.default_branch

            # Create the pull request
            pr = repo.create_pull(
                title=title, body=description, head=head_branch, base=target_base_branch
            )

            # Add labels if provided
            if labels:
                pr.add_to_labels(*labels)

            result = {
                "success": True,
                "pr_number": pr.number,
                "title": pr.title,
                "description": pr.body or "",
                "state": pr.state,
                "author": pr.user.login if pr.user else "Unknown",
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "url": pr.html_url,
                "diff_url": pr.diff_url,
                "patch_url": pr.patch_url,
                "mergeable": None,  # Will be checked separately
                "labels": [label.name for label in pr.labels],
            }

            logger.info(f"Created PR #{pr.number}: {title} in {repo_name}")
            return result

        except GithubException as e:
            error_msg = f"Failed to create pull request: {str(e)}"
            logger.error(error_msg)

            result = {
                "success": False,
                "error": error_msg,
                "status_code": e.status if hasattr(e, "status") else None,
            }

            # Handle specific error cases
            if e.status == 422:
                result["error"] = f"Pull request already exists or branches are invalid"
            elif e.status == 403:
                result["error"] = f"Insufficient permissions to create pull request"

            return result

        except Exception as e:
            error_msg = f"Unexpected error creating pull request: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def check_pr_mergeable(
        self, repo_name: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Check if a pull request is mergeable

        Args:
            repo_name: Repository name in format 'owner/repo'
            pr_number: Pull request number

        Returns:
            Dictionary with mergeability information
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {"success": False, "error": "Repository not accessible"}

            pr = repo.get_pull(pr_number)

            # Refresh mergeable status (GitHub needs time to calculate this)
            await asyncio.sleep(2)
            pr.update()

            result = {
                "success": True,
                "pr_number": pr.number,
                "mergeable": pr.mergeable,
                "mergeable_state": pr.mergeable_state,
                "merge_commits": pr.merge_commit_sha,
                "review_status": pr.get_reviews().totalCount if pr.get_reviews() else 0,
                "status_checks": pr.get_statuses().totalCount
                if pr.get_statuses()
                else 0,
            }

            logger.info(f"Checked mergeability for PR #{pr_number}: {pr.mergeable}")
            return result

        except GithubException as e:
            error_msg = f"Failed to check PR mergeability: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "status_code": e.status if hasattr(e, "status") else None,
            }

        except Exception as e:
            error_msg = f"Unexpected error checking PR mergeability: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def merge_pull_request(
        self,
        repo_name: str,
        pr_number: int,
        merge_method: str = "merge",
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge a pull request with comprehensive error handling

        Args:
            repo_name: Repository name in format 'owner/repo'
            pr_number: Pull request number
            merge_method: Merge method ('merge', 'squash', 'rebase')
            commit_title: Custom commit title
            commit_message: Custom commit message

        Returns:
            Dictionary with operation result
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {"success": False, "error": "Repository not accessible"}

            pr = repo.get_pull(pr_number)

            # Check if PR is mergeable
            if not pr.mergeable:
                return {
                    "success": False,
                    "error": f"PR #{pr_number} is not mergeable",
                    "mergeable_state": pr.mergeable_state,
                }

            # Merge the pull request
            merge_result = pr.merge(
                merge_method=merge_method,
                commit_title=commit_title,
                commit_message=commit_message,
            )

            result = {
                "success": True,
                "pr_number": pr_number,
                "merged": merge_result.merged,
                "sha": merge_result.sha,
                "message": merge_result.message,
                "merge_method": merge_method,
            }

            logger.info(f"Merged PR #{pr_number} in {repo_name}")
            return result

        except GithubException as e:
            error_msg = f"Failed to merge PR #{pr_number}: {str(e)}"
            logger.error(error_msg)

            result = {
                "success": False,
                "error": error_msg,
                "status_code": e.status if hasattr(e, "status") else None,
            }

            # Handle specific error cases
            if e.status == 405:
                result["error"] = (
                    f"PR #{pr_number} cannot be merged (likely not approved or conflicts)"
                )
            elif e.status == 409:
                result["error"] = f"Merge conflict in PR #{pr_number}"

            return result

        except Exception as e:
            error_msg = f"Unexpected error merging PR: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def get_service_health(self) -> Dict[str, Any]:
        """Get comprehensive GitHub service health status"""
        try:
            # Test connection
            connection_status = await self.service.test_connection()

            # Get service status
            service_status = self.service.get_service_status()

            # Test repository access if we have a repo configured
            repo_test = None
            if (
                hasattr(self.service, "service")
                and hasattr(settings, "GITHUB_REPO")
                and settings.GITHUB_REPO
            ):
                repo_test = await self.test_repository_access(settings.GITHUB_REPO)

            # Determine overall health
            is_healthy = (
                connection_status.is_connected
                and service_status["circuit_breaker"]["state"] == "closed"
                and service_status["tokens"]["valid_tokens"] > 0
                and (repo_test is None or repo_test.get("accessible", False))
            )

            return {
                "healthy": is_healthy,
                "timestamp": datetime.now().isoformat(),
                "connection": {
                    "is_connected": connection_status.is_connected,
                    "last_check": connection_status.last_check.isoformat()
                    if connection_status.last_check
                    else None,
                    "response_time": connection_status.response_time,
                    "error_message": connection_status.error_message,
                },
                "service": service_status,
                "repository_test": repo_test,
            }

        except Exception as e:
            logger.error(f"Error getting service health: {e}")
            return {
                "healthy": False,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }


# Global enhanced client instance
enhanced_github_client = EnhancedGitHubClient()
