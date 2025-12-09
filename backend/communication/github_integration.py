"""
GitHub Actions Integration for AutoAdmin
Handles GitHub webhook processing and automation with enhanced error handling
"""

import os
import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from services.firebase_service import get_firebase_service
from services.github_service import github_service
from services.github_client import enhanced_github_client, GitHubAuthenticationError, GitHubRepositoryError
from fastapi.app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class GitHubActionsIntegration:
    """Enhanced GitHub integration for automated workflows with robust error handling"""

    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.token = token or getattr(settings, 'GITHUB_TOKEN', None)
        self.repo = repo or getattr(settings, 'GITHUB_REPO', None)
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.firebase_service = get_firebase_service()
        self.logger = logging.getLogger(__name__)
        self.is_connected_flag = False
        self.last_sync = None
        self.active_workflows = []
        self._monitoring_task = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize GitHub integration with enhanced validation"""
        try:
            self.logger.info("Initializing GitHub integration...")

            # Initialize tokens in the GitHub service if not already done
            if self.token and not self._is_token_initialized():
                github_service.token_manager.add_token("integration", self.token)

            # Test connection using enhanced service
            connection_status = await github_service.test_connection()

            if connection_status.is_connected:
                self.is_connected_flag = True
                self.last_sync = datetime.now()
                self.logger.info(f"GitHub integration initialized successfully for repo: {self.repo}")

                # Log rate limit information
                if connection_status.rate_limit_remaining is not None:
                    self.logger.info(f"GitHub rate limit remaining: {connection_status.rate_limit_remaining}")

                return True
            else:
                self.logger.error(f"Failed to connect to GitHub: {connection_status.error_message}")
                return False

        except Exception as e:
            self.logger.error(f"Error initializing GitHub integration: {e}")
            self.is_connected_flag = False
            return False

    def _is_token_initialized(self) -> bool:
        """Check if the integration token is already initialized in the service"""
        status = github_service.token_manager.get_status()
        return status["valid_tokens"] > 0

    async def start(self):
        """Start GitHub integration service"""
        self.logger.info("Starting GitHub integration service...")

        # Ensure initialization
        if not self.is_connected_flag:
            await self.initialize()

        # Start monitoring loop
        if not self._monitoring_task or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self.monitoring_loop())
            self.logger.info("GitHub monitoring loop started")

    async def stop(self):
        """Stop GitHub integration service"""
        self.logger.info("Stopping GitHub integration service...")
        self.is_connected_flag = False
        self._shutdown_event.set()

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("GitHub integration service stopped")

    async def monitoring_loop(self):
        """Enhanced monitoring loop with health checks and error recovery"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        base_check_interval = 300  # 5 minutes

        while not self._shutdown_event.is_set():
            try:
                # Perform health check before monitoring
                health_status = await self._health_check()

                if not health_status["healthy"]:
                    consecutive_errors += 1
                    self.logger.warning(f"GitHub service unhealthy (error {consecutive_errors}/{max_consecutive_errors})")

                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.error("Max consecutive errors reached, attempting reconnection")
                        await self.initialize()
                        consecutive_errors = 0

                # Check for new events if healthy
                if health_status["healthy"]:
                    await self.check_github_events()
                    consecutive_errors = 0

                # Adaptive check interval based on errors
                check_interval = base_check_interval * (2 ** min(consecutive_errors, 3))

                # Wait for shutdown or interval
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=check_interval
                    )
                    break  # Shutdown event occurred
                except asyncio.TimeoutError:
                    pass  # Continue monitoring

            except asyncio.CancelledError:
                self.logger.info("GitHub monitoring loop cancelled")
                break
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error in GitHub monitoring (error {consecutive_errors}/{max_consecutive_errors}): {e}")

                # Shorter wait on errors, but with exponential backoff
                error_wait = min(60 * (2 ** min(consecutive_errors, 3)), 600)  # Max 10 minutes
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=error_wait
                    )
                    break
                except asyncio.TimeoutError:
                    pass

    async def _health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            # Get service health
            health_result = await enhanced_github_client.get_service_health()

            # Test repository access if configured
            repo_test = None
            if self.repo:
                try:
                    repo_test = await enhanced_github_client.test_repository_access(self.repo)
                except Exception as e:
                    self.logger.warning(f"Repository access test failed: {e}")
                    repo_test = {"accessible": False, "error": str(e)}

            # Determine overall health
            is_healthy = (
                health_result.get("healthy", False) and
                (repo_test is None or repo_test.get("accessible", False))
            )

            return {
                "healthy": is_healthy,
                "service_health": health_result,
                "repository_test": repo_test,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def check_github_events(self):
        """Enhanced GitHub event checking with error handling"""
        try:
            if not self.repo:
                self.logger.debug("No repository configured for event checking")
                return

            # Get repository client
            repo = await enhanced_github_client.get_repository(self.repo)
            if not repo:
                self.logger.error(f"Cannot access repository: {self.repo}")
                return

            # Check for new pull requests (last 5 minutes worth)
            since_time = self.last_sync if self.last_sync else datetime.now().timestamp() - 300

            prs = repo.get_pulls(state='open', sort='updated', direction='desc')
            recent_prs = []

            for pr in prs:
                if pr.updated_at.timestamp() > since_time:
                    recent_prs.append({
                        "number": pr.number,
                        "title": pr.title,
                        "author": pr.user.login if pr.user else "Unknown",
                        "updated_at": pr.updated_at.isoformat(),
                        "mergeable": pr.mergeable,
                        "mergeable_state": pr.mergeable_state
                    })
                else:
                    break  # PRs are sorted by updated_at

            # Check for new issues
            issues = repo.get_issues(state='open', sort='updated', direction='desc')
            recent_issues = []

            for issue in issues:
                if issue.updated_at.timestamp() > since_time and not issue.pull_request:
                    recent_issues.append({
                        "number": issue.number,
                        "title": issue.title,
                        "author": issue.user.login if issue.user else "Unknown",
                        "updated_at": issue.updated_at.isoformat(),
                        "assignees": [a.login for a in issue.assignees]
                    })
                else:
                    break  # Issues are sorted by updated_at

            # Process events
            if recent_prs or recent_issues:
                await self._process_events({
                    "pull_requests": recent_prs,
                    "issues": recent_issues
                })

            self.last_sync = datetime.now()
            self.logger.debug(f"Event check completed: {len(recent_prs)} PRs, {len(recent_issues)} issues")

        except Exception as e:
            self.logger.error(f"Error checking GitHub events: {e}")
            # Don't update last_sync on error to retry on next iteration

    async def _process_events(self, events: Dict[str, List[Dict[str, Any]]]):
        """Process GitHub events"""
        try:
            # Process pull request events
            for pr in events.get("pull_requests", []):
                await self._process_pull_request_event(pr)

            # Process issue events
            for issue in events.get("issues", []):
                await self._process_issue_event(issue)

        except Exception as e:
            self.logger.error(f"Error processing events: {e}")

    async def _process_pull_request_event(self, pr: Dict[str, Any]):
        """Process a single pull request event"""
        try:
            self.logger.info(f"Processing PR #{pr['number']}: {pr['title']}")

            # Store in Firebase for tracking
            if self.firebase_service:
                await self.firebase_service.store_github_event({
                    "type": "pull_request",
                    "data": pr,
                    "timestamp": datetime.now().isoformat(),
                    "repository": self.repo
                })

            # Update active workflows if needed
            # Add your specific workflow logic here

        except Exception as e:
            self.logger.error(f"Error processing PR event: {e}")

    async def _process_issue_event(self, issue: Dict[str, Any]):
        """Process a single issue event"""
        try:
            self.logger.info(f"Processing issue #{issue['number']}: {issue['title']}")

            # Store in Firebase for tracking
            if self.firebase_service:
                await self.firebase_service.store_github_event({
                    "type": "issue",
                    "data": issue,
                    "timestamp": datetime.now().isoformat(),
                    "repository": self.repo
                })

            # Update active workflows if needed
            # Add your specific workflow logic here

        except Exception as e:
            self.logger.error(f"Error processing issue event: {e}")

    def is_connected(self) -> bool:
        """Check if GitHub integration is connected"""
        return self.is_connected_flag

    def get_last_sync(self) -> Optional[datetime]:
        """Get last sync time"""
        return self.last_sync

    def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get active workflows"""
        return self.active_workflows

    async def trigger_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced workflow triggering with comprehensive error handling"""
        try:
            if not self.repo:
                return {"success": False, "error": "No repository configured"}

            # Use enhanced GitHub client to trigger workflow
            # This would integrate with GitHub Actions API
            # For now, we'll simulate this

            self.logger.info(f"Triggering workflow: {workflow_name} with inputs: {inputs}")

            # Store workflow trigger in Firebase
            if self.firebase_service:
                await self.firebase_service.store_workflow_trigger({
                    "workflow_name": workflow_name,
                    "inputs": inputs,
                    "repository": self.repo,
                    "timestamp": datetime.now().isoformat(),
                    "status": "triggered"
                })

            # Add to active workflows
            workflow_info = {
                "workflow_name": workflow_name,
                "inputs": inputs,
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }
            self.active_workflows.append(workflow_info)

            return {
                "success": True,
                "workflow_id": f"{workflow_name}_{int(datetime.now().timestamp())}",
                "message": f"Workflow '{workflow_name}' triggered successfully"
            }

        except Exception as e:
            error_msg = f"Error triggering workflow: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        try:
            # Get health status
            health = await self._health_check()

            # Get GitHub service status
            service_status = github_service.get_service_status()

            return {
                "integration_connected": self.is_connected_flag,
                "last_sync": self.last_sync.isoformat() if self.last_sync else None,
                "repository": self.repo,
                "active_workflows": len(self.active_workflows),
                "health": health,
                "service_status": service_status,
                "monitoring_active": self._monitoring_task and not self._monitoring_task.done() if self._monitoring_task else False
            }

        except Exception as e:
            self.logger.error(f"Error getting integration status: {e}")
            return {
                "integration_connected": False,
                "error": str(e)
            }