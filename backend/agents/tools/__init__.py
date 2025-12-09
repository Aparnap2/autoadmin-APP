"""
Tools module for AutoAdmin agents.

This module provides external integrations and specialized tools
for agent capabilities.
"""

from .tavily_tools import TavilySearchTools, SearchResult
from .github_tools import GitHubTools, GitHubRepoInfo, PullRequestInfo, IssueInfo

__all__ = [
    "TavilySearchTools",
    "SearchResult",
    "GitHubTools",
    "GitHubRepoInfo",
    "PullRequestInfo",
    "IssueInfo"
]