"""
GitHub integration tools for AutoAdmin DevOps agents.

This module provides GitHub operations for code management,
PR creation, issue tracking, and repository analysis.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from github import Github, GithubException, Repository, PullRequest, Issue
from github.ContentFile import ContentFile


@dataclass
class GitHubRepoInfo:
    """Information about a GitHub repository."""
    name: str
    full_name: str
    description: str
    language: str
    stars: int
    forks: int
    open_issues: int
    default_branch: str
    clone_url: str


@dataclass
class PullRequestInfo:
    """Information about a pull request."""
    number: int
    title: str
    description: str
    state: str
    author: str
    base_branch: str
    head_branch: str
    url: str
    mergeable: Optional[bool] = None


@dataclass
class IssueInfo:
    """Information about a GitHub issue."""
    number: int
    title: str
    description: str
    state: str
    author: str
    assignees: List[str]
    labels: List[str]
    url: str


logger = logging.getLogger(__name__)


class GitHubTools:
    """
    Enhanced GitHub integration tools for DevOps agents.

    Provides comprehensive GitHub operations including repository management,
    pull request creation, issue tracking, and code analysis with robust error handling.
    """

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with authentication token."""
        self.token = token
        self._enhanced_client = None
        try:
            from services.github_client import enhanced_github_client
            self._enhanced_client = enhanced_github_client
        except ImportError:
            logger.warning("Enhanced GitHub client not available, falling back to basic client")
            if token:
                self.client = Github(token)
            else:
                raise ValueError("Token required when enhanced client is not available")

    async def get_repository(self, repo_name: str) -> Optional[Repository.Repository]:
        """
        Get a repository object by name.

        Args:
            repo_name: Repository name in format 'owner/repo'

        Returns:
            Repository object or None if not found
        """
        try:
            repo = self.client.get_repo(repo_name)
            logger.info(f"Successfully accessed repository: {repo_name}")
            return repo
        except GithubException as e:
            logger.error(f"Error accessing repository {repo_name}: {str(e)}")
            return None

    async def get_repository_info(self, repo_name: str) -> Optional[GitHubRepoInfo]:
        """
        Get detailed information about a repository.

        Args:
            repo_name: Repository name in format 'owner/repo'

        Returns:
            Repository information or None if error
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return None

            return GitHubRepoInfo(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description or "",
                language=repo.language or "",
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                open_issues=repo.open_issues_count,
                default_branch=repo.default_branch,
                clone_url=repo.clone_url
            )
        except Exception as e:
            logger.error(f"Error getting repository info: {str(e)}")
            return None

    async def create_branch(self, repo_name: str, branch_name: str, base_branch: Optional[str] = None) -> bool:
        """
        Create a new branch in a repository.

        Args:
            repo_name: Repository name in format 'owner/repo'
            branch_name: Name of the new branch
            base_branch: Base branch to create from (default: default branch)

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return False

            # Get the base branch
            if not base_branch:
                base_branch = repo.default_branch

            # Get the reference to the base branch
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            sha = base_ref.object.sha

            # Create the new branch
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)
            logger.info(f"Created branch '{branch_name}' from '{base_branch}' in {repo_name}")
            return True

        except GithubException as e:
            logger.error(f"Error creating branch '{branch_name}': {str(e)}")
            return False

    async def get_file_content(self, repo_name: str, file_path: str, branch: Optional[str] = None) -> Optional[str]:
        """
        Get the content of a file from the repository.

        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path to the file in the repository
            branch: Branch to get file from (default: default branch)

        Returns:
            File content as string or None if error
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return None

            file_content = repo.get_contents(file_path, ref=branch)
            if isinstance(file_content, ContentFile):
                content = file_content.decoded_content.decode('utf-8')
                logger.debug(f"Retrieved file content: {file_path}")
                return content
            return None

        except GithubException as e:
            logger.error(f"Error getting file content '{file_path}': {str(e)}")
            return None

    async def create_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: Optional[str] = None
    ) -> bool:
        """
        Create or update a file in the repository.

        Args:
            repo_name: Repository name in format 'owner/repo'
            file_path: Path where to create the file
            content: File content
            commit_message: Commit message for the change
            branch: Branch to create file in (default: default branch)

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return False

            repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch or repo.default_branch
            )
            logger.info(f"Created/updated file '{file_path}' in {repo_name}")
            return True

        except GithubException as e:
            logger.error(f"Error creating file '{file_path}': {str(e)}")
            return False

    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        description: str,
        head_branch: str,
        base_branch: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[PullRequestInfo]:
        """
        Create a pull request.

        Args:
            repo_name: Repository name in format 'owner/repo'
            title: PR title
            description: PR description
            head_branch: Branch with changes
            base_branch: Target branch (default: default branch)
            labels: List of labels to add to the PR

        Returns:
            Pull request information or None if error
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return None

            if not base_branch:
                base_branch = repo.default_branch

            pr = repo.create_pull(
                title=title,
                body=description,
                head=head_branch,
                base=base_branch
            )

            # Add labels if provided
            if labels:
                pr.add_to_labels(*labels)

            pr_info = PullRequestInfo(
                number=pr.number,
                title=pr.title,
                description=pr.body or "",
                state=pr.state,
                author=pr.user.login if pr.user else "Unknown",
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                url=pr.html_url,
                mergeable=None  # Will be checked separately
            )

            logger.info(f"Created PR #{pr.number}: {title} in {repo_name}")
            return pr_info

        except GithubException as e:
            logger.error(f"Error creating pull request: {str(e)}")
            return None

    async def get_pull_requests(self, repo_name: str, state: str = "open") -> List[PullRequestInfo]:
        """
        Get pull requests from a repository.

        Args:
            repo_name: Repository name in format 'owner/repo'
            state: PR state ('open', 'closed', 'all')

        Returns:
            List of pull request information
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return []

            prs = repo.get_pulls(state=state)
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
                pr_list.append(pr_info)

            logger.info(f"Retrieved {len(pr_list)} PRs with state '{state}' from {repo_name}")
            return pr_list

        except Exception as e:
            logger.error(f"Error getting pull requests: {str(e)}")
            return []

    async def create_issue(
        self,
        repo_name: str,
        title: str,
        description: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Optional[IssueInfo]:
        """
        Create an issue in the repository.

        Args:
            repo_name: Repository name in format 'owner/repo'
            title: Issue title
            description: Issue description
            labels: List of labels to add to the issue
            assignees: List of users to assign to the issue

        Returns:
            Issue information or None if error
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return None

            issue = repo.create_issue(
                title=title,
                body=description,
                labels=labels or [],
                assignees=assignees or []
            )

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

            logger.info(f"Created issue #{issue.number}: {title} in {repo_name}")
            return issue_info

        except GithubException as e:
            logger.error(f"Error creating issue: {str(e)}")
            return None

    async def get_issues(self, repo_name: str, state: str = "open") -> List[IssueInfo]:
        """
        Get issues from a repository.

        Args:
            repo_name: Repository name in format 'owner/repo'
            state: Issue state ('open', 'closed', 'all')

        Returns:
            List of issue information
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return []

            issues = repo.get_issues(state=state)
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
                issue_list.append(issue_info)

            logger.info(f"Retrieved {len(issue_list)} issues with state '{state}' from {repo_name}")
            return issue_list

        except Exception as e:
            logger.error(f"Error getting issues: {str(e)}")
            return []

    async def analyze_code_structure(self, repo_name: str) -> Dict[str, Any]:
        """
        Analyze the code structure of a repository.

        Args:
            repo_name: Repository name in format 'owner/repo'

        Returns:
            Dictionary with code structure analysis
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return {}

            # Get directory structure
            contents = repo.get_contents("")
            file_stats = {"total": 0, "by_extension": {}}
            directories = []
            important_files = []

            def process_contents(contents, current_path=""):
                nonlocal file_stats, directories, important_files

                for item in contents:
                    if item.type == "dir":
                        directories.append(f"{current_path}{item.name}/")
                        try:
                            sub_contents = repo.get_contents(f"{current_path}{item.name}")
                            process_contents(sub_contents, f"{current_path}{item.name}/")
                        except:
                            pass  # Skip directories we can't access
                    else:
                        file_stats["total"] += 1
                        if "." in item.name:
                            ext = item.name.split(".")[-1].lower()
                            file_stats["by_extension"][ext] = file_stats["by_extension"].get(ext, 0) + 1

                        # Check for important files
                        if item.name.lower() in ["readme.md", "package.json", "requirements.txt", "dockerfile", "github workflows"]:
                            important_files.append(f"{current_path}{item.name}")

            process_contents(contents)

            # Get languages
            languages = repo.get_languages()

            analysis = {
                "file_count": file_stats["total"],
                "file_extensions": file_stats["by_extension"],
                "directories": directories,
                "important_files": important_files,
                "languages": languages,
                "main_language": max(languages.items(), key=lambda x: x[1])[0] if languages else None
            }

            logger.info(f"Analyzed code structure for {repo_name}: {analysis['file_count']} files")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing code structure: {str(e)}")
            return {}

    async def merge_pull_request(self, repo_name: str, pr_number: int, merge_method: str = "merge") -> bool:
        """
        Merge a pull request.

        Args:
            repo_name: Repository name in format 'owner/repo'
            pr_number: Pull request number
            merge_method: Merge method ('merge', 'squash', 'rebase')

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return False

            pr = repo.get_pull(pr_number)
            pr.merge(merge_method=merge_method)
            logger.info(f"Merged PR #{pr_number} in {repo_name}")
            return True

        except GithubException as e:
            logger.error(f"Error merging PR #{pr_number}: {str(e)}")
            return False

    async def add_comment_to_pr(self, repo_name: str, pr_number: int, comment: str) -> bool:
        """
        Add a comment to a pull request.

        Args:
            repo_name: Repository name in format 'owner/repo'
            pr_number: Pull request number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = await self.get_repository(repo_name)
            if not repo:
                return False

            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            logger.info(f"Added comment to PR #{pr_number} in {repo_name}")
            return True

        except GithubException as e:
            logger.error(f"Error adding comment to PR #{pr_number}: {str(e)}")
            return False