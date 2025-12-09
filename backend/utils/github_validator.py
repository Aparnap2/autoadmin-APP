"""
GitHub Environment Variable Validator
Validates and provides guidance for GitHub integration configuration
"""

import os
import logging
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GitHubValidationResult:
    """Result of GitHub environment validation"""
    is_valid: bool
    has_token: bool
    has_repo: bool
    token_valid: bool
    repo_accessible: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]


class GitHubValidator:
    """
    Validates GitHub environment variables and configuration
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_all(self) -> GitHubValidationResult:
        """
        Perform comprehensive GitHub configuration validation
        """
        errors = []
        warnings = []
        recommendations = []

        # Check token
        token = os.getenv('GITHUB_TOKEN')
        has_token = bool(token and token.strip())

        if not has_token:
            errors.append("GITHUB_TOKEN is not set or empty")
            recommendations.append("Set GITHUB_TOKEN to a valid GitHub personal access token")
        else:
            if len(token) < 20:
                warnings.append("GITHUB_TOKEN seems too short (should be at least 20 characters)")

            if not token.startswith('ghp_') and not token.startswith('github_pat_'):
                warnings.append("GITHUB_TOKEN doesn't start with expected prefix (ghp_ or github_pat_)")

        # Check repository
        repo = os.getenv('GITHUB_REPO')
        has_repo = bool(repo and repo.strip())

        if not has_repo:
            errors.append("GITHUB_REPO is not set or empty")
            recommendations.append("Set GITHUB_REPO to format 'owner/repository'")
        else:
            if '/' not in repo:
                errors.append("GITHUB_REPO must be in format 'owner/repository'")
                recommendations.append("Update GITHUB_REPO to include both owner and repository name")
            elif repo.count('/') != 1:
                warnings.append("GITHUB_REPO format may be incorrect (multiple slashes found)")

        # Test GitHub token validity if available
        token_valid = False
        repo_accessible = False

        if has_token:
            try:
                import requests

                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }

                # Test token by getting user info
                response = requests.get(
                    'https://api.github.com/user',
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    token_valid = True
                    self.logger.info("GitHub token is valid")
                else:
                    errors.append(f"GitHub token validation failed: HTTP {response.status_code}")
                    if response.status_code == 401:
                        errors.append("GitHub token is invalid or expired")
                        recommendations.append("Generate a new GitHub personal access token")
                    elif response.status_code == 403:
                        errors.append("GitHub token has insufficient permissions")
                        recommendations.append("Ensure token has required scopes (repo, workflow, etc.)")

            except requests.RequestException as e:
                warnings.append(f"Could not validate GitHub token: {str(e)}")
                recommendations.append("Check network connectivity to api.github.com")
            except Exception as e:
                warnings.append(f"Unexpected error validating GitHub token: {str(e)}")

        # Test repository accessibility if token is valid
        if has_token and token_valid and has_repo:
            try:
                import requests

                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }

                # Test repository access
                response = requests.get(
                    f'https://api.github.com/repos/{repo}',
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    repo_accessible = True
                    self.logger.info(f"Repository {repo} is accessible")
                else:
                    if response.status_code == 404:
                        errors.append(f"Repository {repo} not found or not accessible")
                        recommendations.append(f"Verify repository exists and token has access to {repo}")
                    elif response.status_code == 403:
                        errors.append(f"Insufficient permissions to access repository {repo}")
                        recommendations.append(f"Ensure token has 'repo' scope for {repo}")
                    else:
                        errors.append(f"Failed to access repository {repo}: HTTP {response.status_code}")

            except requests.RequestException as e:
                warnings.append(f"Could not test repository access: {str(e)}")
            except Exception as e:
                warnings.append(f"Unexpected error testing repository access: {str(e)}")

        # Check additional tokens for failover
        additional_tokens = []
        for i in range(1, 6):
            token_key = f'GITHUB_TOKEN_{i}'
            if os.getenv(token_key):
                additional_tokens.append(token_key)

        if not additional_tokens:
            recommendations.append("Consider setting GITHUB_TOKEN_1, GITHUB_TOKEN_2 for failover support")
        else:
            recommendations.append(f"Found {len(additional_tokens)} additional tokens for failover")

        # Check rate limit considerations
        if has_token and token_valid:
            recommendations.append("Monitor GitHub API rate limits (5000 requests per hour for authenticated requests)")

        # Determine overall validity
        is_valid = (
            has_token and
            has_repo and
            token_valid and
            repo_accessible and
            len(errors) == 0
        )

        return GitHubValidationResult(
            is_valid=is_valid,
            has_token=has_token,
            has_repo=has_repo,
            token_valid=token_valid,
            repo_accessible=repo_accessible,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations
        )

    def validate_token_only(self, token: str) -> Dict[str, Any]:
        """
        Validate a single GitHub token
        """
        try:
            import requests

            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }

            # Test token
            response = requests.get(
                'https://api.github.com/user',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "valid": True,
                    "username": user_data.get("login"),
                    "name": user_data.get("name"),
                    "scopes": response.headers.get("X-OAuth-Scopes", "").split(", ") if response.headers.get("X-OAuth-Scopes") else [],
                    "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
                    "rate_limit_reset": response.headers.get("X-RateLimit-Reset")
                }
            else:
                return {
                    "valid": False,
                    "status_code": response.status_code,
                    "message": f"HTTP {response.status_code}: {response.text}"
                }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current GitHub configuration
        """
        return {
            "token_configured": bool(os.getenv('GITHUB_TOKEN')),
            "token_length": len(os.getenv('GITHUB_TOKEN', '')),
            "repo_configured": os.getenv('GITHUB_REPO'),
            "additional_tokens": [
                key for key in os.environ.keys()
                if key.startswith('GITHUB_TOKEN_') and os.getenv(key)
            ],
            "timestamp": datetime.now().isoformat()
        }


def validate_github_integration() -> GitHubValidationResult:
    """
    Convenience function to validate GitHub integration
    """
    validator = GitHubValidator()
    return validator.validate_all()


if __name__ == "__main__":
    # Test validation when run directly
    result = validate_github_integration()

    print("🔍 GitHub Integration Validation Results")
    print("=" * 50)
    print(f"Overall Valid: {result.is_valid}")
    print(f"Has Token: {result.has_token}")
    print(f"Token Valid: {result.token_valid}")
    print(f"Has Repository: {result.has_repo}")
    print(f"Repository Accessible: {result.repo_accessible}")

    if result.errors:
        print("\n❌ Errors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.recommendations:
        print("\n💡 Recommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")