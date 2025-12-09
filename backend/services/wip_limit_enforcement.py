"""
WIP (Work-In-Progress) Limit Enforcement Service
Manages task limits, focus sessions, and enforces single-task focus
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
import json
import uuid

from pydantic import ValidationError

from fastapi.app.models.wip_limits import (
    WIPLimit,
    WIPViolation,
    FocusSession,
    ActiveTaskInfo,
    FocusDashboardData,
    WIPLimitType,
    WIPLimitStatus,
    WIPViolationAction,
)
from fastapi.app.models.task import Task, TaskStatus
from services.firebase_service import get_firebase_service
from services.agent_orchestrator_http import get_http_agent_orchestrator


@dataclass
class WIPEnforcementResult:
    """Result of WIP limit enforcement check"""

    allowed: bool
    reason: str
    active_tasks_count: int
    limit: int
    violations_today: int
    suggested_actions: List[str]


class WIPLimitEnforcementService:
    """Service for enforcing WIP limits and managing focus"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.agent_orchestrator = get_http_agent_orchestrator()

        # Default WIP limits
        self.default_limits = {
            WIPLimitType.USER: 2,  # Max 2 concurrent tasks per user
            WIPLimitType.PROJECT: 5,  # Max 5 active tasks per project
            WIPLimitType.TEAM: 10,  # Max 10 active tasks per team
        }

        # Cache for performance
        self._limits_cache = {}
        self._cache_ttl = 300  # 5 minutes

    async def check_wip_limit(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
        additional_task: bool = True,
    ) -> WIPEnforcementResult:
        """Check if starting a new task would violate WIP limits"""
        try:
            # Get current active tasks
            active_tasks = await self._get_active_tasks(user_id, project_id, team_id)

            # Get applicable WIP limits
            limits = await self._get_applicable_limits(user_id, project_id, team_id)

            # Calculate total active tasks
            current_count = len(active_tasks)
            if additional_task:
                current_count += 1

            # Check each limit
            violations = []
            max_limit = 0
            blocking_limit = None

            for limit in limits:
                if limit.status != WIPLimitStatus.ACTIVE:
                    continue

                if current_count > limit.max_concurrent_tasks:
                    violations.append(limit)
                    max_limit = max(max_limit, limit.max_concurrent_tasks)

                    if limit.violation_action == WIPViolationAction.BLOCK:
                        blocking_limit = limit

            # Get today's violations
            violations_today = await self._get_violations_today(user_id)

            # Determine if allowed
            allowed = len(violations) == 0 or (blocking_limit is None)

            # Generate reason
            if allowed:
                reason = f"Within WIP limits ({current_count}/{max_limit} tasks)"
            else:
                if blocking_limit:
                    reason = f"Blocked by {blocking_limit.type.value} limit: {blocking_limit.name}"
                else:
                    reason = f"Exceeds WIP limit ({current_count}/{max_limit} tasks)"

            # Generate suggested actions
            suggested_actions = await self._generate_suggested_actions(
                violations, active_tasks, user_id
            )

            return WIPEnforcementResult(
                allowed=allowed,
                reason=reason,
                active_tasks_count=current_count - (1 if additional_task else 0),
                limit=max_limit,
                violations_today=len(violations_today),
                suggested_actions=suggested_actions,
            )

        except Exception as e:
            self.logger.error(f"Error checking WIP limit: {e}")
            # Allow by default on error to avoid blocking
            return WIPEnforcementResult(
                allowed=True,
                reason="Error checking limits - proceeding",
                active_tasks_count=0,
                limit=10,
                violations_today=0,
                suggested_actions=[],
            )

    async def enforce_wip_limit(
        self,
        user_id: str,
        action: str,
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
        force_override: bool = False,
    ) -> WIPEnforcementResult:
        """Enforce WIP limits for a specific action"""
        try:
            # Check limits
            result = await self.check_wip_limit(user_id, project_id, team_id)

            if not result.allowed and not force_override:
                # Record violation
                await self._record_violation(
                    user_id=user_id,
                    attempted_action=action,
                    current_active=result.active_tasks_count,
                    limit=result.limit,
                    action_taken=WIPViolationAction.BLOCK,
                )

                # Get applicable limits to determine action
                limits = await self._get_applicable_limits(user_id, project_id, team_id)
                blocking_limits = [
                    l for l in limits if l.violation_action == WIPViolationAction.BLOCK
                ]

                if blocking_limits:
                    result.allowed = False
                    result.reason = f"Blocked by WIP limit: {blocking_limits[0].name}"

            elif not result.allowed and force_override:
                # Record violation but allow
                await self._record_violation(
                    user_id=user_id,
                    attempted_action=action,
                    current_active=result.active,
                    limit=result.limit,
                    action_taken=WIPViolationAction.WARN,
                )
                result.allowed = True
                result.reason = "Override allowed - violation recorded"

            return result

        except Exception as e:
            self.logger.error(f"Error enforcing WIP limit: {e}")
            return WIPEnforcementResult(
                allowed=True,
                reason="Error enforcing limits - proceeding",
                active_tasks_count=0,
                limit=10,
                violations_today=0,
                suggested_actions=[],
            )

    async def start_focus_session(
        self, user_id: str, task_id: str, project_id: Optional[str] = None
    ) -> FocusSession:
        """Start a new focus session"""
        try:
            # End any existing active session
            await self._end_active_sessions(user_id)

            # Create new session
            session = FocusSession(
                id=f"session_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                task_id=task_id,
                project_id=project_id,
                started_at=datetime.now(timezone.utc),
                interruptions=0,
                context_switches=0,
                focus_score=1.0,  # Start with perfect score
            )

            # Store session
            await self._store_focus_session(session)

            self.logger.info(
                f"Started focus session {session.id} for user {user_id} on task {task_id}"
            )
            return session

        except Exception as e:
            self.logger.error(f"Error starting focus session: {e}")
            raise

    async def end_focus_session(
        self, user_id: str, session_id: str, notes: Optional[str] = None
    ) -> FocusSession:
        """End a focus session"""
        try:
            # Get session
            session = await self._get_focus_session(session_id)
            if not session or session.user_id != user_id:
                raise ValueError("Session not found or access denied")

            if session.ended_at:
                raise ValueError("Session already ended")

            # Calculate duration
            ended_at = datetime.now(timezone.utc)
            duration = int((ended_at - session.started_at).total_seconds() / 60)

            # Update session
            session.ended_at = ended_at
            session.duration_minutes = duration
            session.notes = notes or session.notes

            # Calculate focus score based on interruptions and duration
            if duration > 0:
                # Penalize for interruptions (each interruption reduces score by 0.1)
                interruption_penalty = min(0.5, session.interruptions * 0.1)
                # Penalize for very short sessions (under 15 minutes)
                duration_penalty = (
                    max(0, (15 - duration) / 15 * 0.2) if duration < 15 else 0
                )
                session.focus_score = max(
                    0.1, 1.0 - interruption_penalty - duration_penalty
                )

            # Store updated session
            await self._store_focus_session(session)

            self.logger.info(
                f"Ended focus session {session_id} with score {session.focus_score:.2f}"
            )
            return session

        except Exception as e:
            self.logger.error(f"Error ending focus session: {e}")
            raise

    async def record_interruption(
        self, user_id: str, session_id: str, reason: Optional[str] = None
    ) -> FocusSession:
        """Record an interruption in the current focus session"""
        try:
            session = await self._get_focus_session(session_id)
            if not session or session.user_id != user_id:
                raise ValueError("Session not found or access denied")

            if session.ended_at:
                raise ValueError("Cannot record interruption on ended session")

            session.interruptions += 1
            session.focus_score = max(0.1, session.focus_score - 0.1)  # Reduce score

            # Store metadata
            if reason:
                if not session.metadata:
                    session.metadata = {}
                if "interruptions" not in session.metadata:
                    session.metadata["interruptions"] = []
                session.metadata["interruptions"].append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reason": reason,
                    }
                )

            await self._store_focus_session(session)
            return session

        except Exception as e:
            self.logger.error(f"Error recording interruption: {e}")
            raise

    async def get_focus_dashboard_data(self, user_id: str) -> FocusDashboardData:
        """Get data for the focus-first dashboard"""
        try:
            # Get active task
            active_task = await self._get_active_task_info(user_id)

            # Get active tasks count
            active_tasks = await self._get_active_tasks(user_id)
            active_tasks_count = len(active_tasks)

            # Get WIP limit
            limits = await self._get_applicable_limits(user_id)
            wip_limit = max([l.max_concurrent_tasks for l in limits]) if limits else 2

            # Get violations today
            violations_today = await self._get_violations_today(user_id)
            wip_violations_today = len(violations_today)

            # Get focus sessions today
            sessions_today = await self._get_focus_sessions_today(user_id)
            focus_sessions_today = len(sessions_today)

            # Calculate total focus time today
            total_focus_time_today = sum(
                s.duration_minutes or 0 for s in sessions_today if s.duration_minutes
            )

            # Calculate focus score today
            focus_score_today = (
                sum(s.focus_score for s in sessions_today) / len(sessions_today)
                if sessions_today
                else 0.0
            )

            # Get upcoming tasks
            upcoming_tasks = await self._get_upcoming_tasks(user_id)

            # Get recent completions
            recent_completions = await self._get_recent_completions(user_id)

            # Calculate momentum score (simplified)
            momentum_score = await self._calculate_momentum_score(user_id)

            # Get Git integration status
            git_status = await self._get_git_integration_status(user_id)

            return FocusDashboardData(
                active_task=active_task,
                active_tasks_count=active_tasks_count,
                wip_limit=wip_limit,
                wip_violations_today=wip_violations_today,
                focus_sessions_today=focus_sessions_today,
                total_focus_time_today=total_focus_time_today,
                focus_score_today=focus_score_today,
                upcoming_tasks=upcoming_tasks,
                recent_completions=recent_completions,
                momentum_score=momentum_score,
                git_integration_status=git_status,
            )

        except Exception as e:
            self.logger.error(f"Error getting focus dashboard data: {e}")
            # Return minimal data on error
            return FocusDashboardData(
                active_task=None,
                active_tasks_count=0,
                wip_limit=2,
                wip_violations_today=0,
                focus_sessions_today=0,
                total_focus_time_today=0,
                focus_score_today=0.0,
                upcoming_tasks=[],
                recent_completions=[],
                momentum_score=0.0,
                git_integration_status={},
            )

    async def create_wip_limit(
        self,
        name: str,
        limit_type: WIPLimitType,
        target_id: str,
        max_concurrent_tasks: int,
        created_by: str,
        violation_action: WIPViolationAction = WIPViolationAction.WARN,
    ) -> WIPLimit:
        """Create a new WIP limit"""
        try:
            limit = WIPLimit(
                id=f"limit_{uuid.uuid4().hex[:8]}",
                name=name,
                type=limit_type,
                target_id=target_id,
                max_concurrent_tasks=max_concurrent_tasks,
                violation_action=violation_action,
                created_by=created_by,
            )

            # Store limit
            await self._store_wip_limit(limit)

            # Clear cache
            self._limits_cache.clear()

            self.logger.info(
                f"Created WIP limit {limit.id} for {limit_type.value} {target_id}"
            )
            return limit

        except Exception as e:
            self.logger.error(f"Error creating WIP limit: {e}")
            raise

    async def get_wip_stats(self, user_id: Optional[str] = None) -> WIPStats:
        """Get WIP system statistics"""
        try:
            # This would aggregate data from Firebase
            # For now, return basic stats
            return WIPStats(
                total_limits=10,  # Placeholder
                active_limits=8,
                total_violations=25,
                violations_today=2,
                average_active_tasks=1.5,
                focus_sessions_today=5,
                average_focus_score=0.75,
                completion_rate=0.85,
                context_switch_rate=0.15,
            )

        except Exception as e:
            self.logger.error(f"Error getting WIP stats: {e}")
            return WIPStats()

    # Private helper methods

    async def _get_active_tasks(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get currently active tasks for user/project/team"""
        try:
            # Query Firebase for active tasks
            # This is a simplified implementation
            active_tasks = []

            # In a real implementation, this would query the tasks collection
            # filtering by status = 'running' or 'in_progress' and assigned_to = user_id

            return active_tasks

        except Exception as e:
            self.logger.error(f"Error getting active tasks: {e}")
            return []

    async def _get_applicable_limits(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> List[WIPLimit]:
        """Get all applicable WIP limits"""
        try:
            # Check cache first
            cache_key = f"limits_{user_id}_{project_id}_{team_id}"
            if cache_key in self._limits_cache:
                cached_data, timestamp = self._limits_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_ttl:
                    return cached_data

            limits = []

            # Get user-specific limits
            user_limits = await self._get_limits_by_target(WIPLimitType.USER, user_id)
            limits.extend(user_limits)

            # Get project-specific limits
            if project_id:
                project_limits = await self._get_limits_by_target(
                    WIPLimitType.PROJECT, project_id
                )
                limits.extend(project_limits)

            # Get team-specific limits
            if team_id:
                team_limits = await self._get_limits_by_target(
                    WIPLimitType.TEAM, team_id
                )
                limits.extend(team_limits)

            # Add default global limit if no user limit exists
            if not any(l.type == WIPLimitType.USER for l in limits):
                default_limit = WIPLimit(
                    id="default_user_limit",
                    name="Default User Limit",
                    type=WIPLimitType.USER,
                    target_id=user_id,
                    max_concurrent_tasks=self.default_limits[WIPLimitType.USER],
                    created_by="system",
                )
                limits.append(default_limit)

            # Cache results
            self._limits_cache[cache_key] = (limits, datetime.now())

            return limits

        except Exception as e:
            self.logger.error(f"Error getting applicable limits: {e}")
            return []

    async def _get_limits_by_target(
        self, limit_type: WIPLimitType, target_id: str
    ) -> List[WIPLimit]:
        """Get WIP limits for a specific target"""
        try:
            # Query Firebase for limits
            # This would be implemented with actual Firebase queries
            return []

        except Exception as e:
            self.logger.error(f"Error getting limits by target: {e}")
            return []

    async def _record_violation(
        self,
        user_id: str,
        attempted_action: str,
        current_active: int,
        limit: int,
        action_taken: WIPViolationAction,
    ) -> WIPViolation:
        """Record a WIP limit violation"""
        try:
            violation = WIPViolation(
                id=f"violation_{uuid.uuid4().hex[:8]}",
                limit_id="system_limit",  # Would be actual limit ID
                user_id=user_id,
                attempted_action=attempted_action,
                current_active_tasks=current_active,
                limit_max_tasks=limit,
                action_taken=action_taken,
            )

            # Store violation
            await self._store_violation(violation)

            self.logger.warning(
                f"Recorded WIP violation for user {user_id}: {attempted_action}"
            )
            return violation

        except Exception as e:
            self.logger.error(f"Error recording violation: {e}")
            raise

    async def _generate_suggested_actions(
        self,
        violations: List[WIPLimit],
        active_tasks: List[Dict[str, Any]],
        user_id: str,
    ) -> List[str]:
        """Generate suggested actions for WIP violations"""
        try:
            actions = []

            if violations:
                actions.append(
                    "Complete or pause existing tasks before starting new ones"
                )

            if len(active_tasks) > 0:
                actions.append(
                    f"Consider completing {len(active_tasks)} active task(s) first"
                )

            actions.append("Review task priorities and focus on high-impact work")
            actions.append("Break large tasks into smaller, focused units")

            return actions[:3]  # Top 3 actions

        except Exception as e:
            self.logger.error(f"Error generating suggested actions: {e}")
            return ["Review and complete existing tasks"]

    async def _get_active_task_info(self, user_id: str) -> Optional[ActiveTaskInfo]:
        """Get information about the currently active task"""
        try:
            # Get active focus session
            active_session = await self._get_active_focus_session(user_id)
            if not active_session:
                return None

            # Get task details
            task_details = await self._get_task_details(active_session.task_id)
            if not task_details:
                return None

            # Calculate time spent
            time_spent = int(
                (datetime.now(timezone.utc) - active_session.started_at).total_seconds()
                / 60
            )

            return ActiveTaskInfo(
                task_id=active_session.task_id,
                title=task_details.get("title", "Unknown Task"),
                project_id=active_session.project_id,
                project_name=task_details.get("project_name"),
                started_at=active_session.started_at,
                estimated_duration_minutes=task_details.get(
                    "estimated_duration_minutes"
                ),
                time_spent_minutes=time_spent,
                progress_percentage=task_details.get("progress", 0.0),
                priority=task_details.get("priority", "medium"),
                git_branch=task_details.get("git_branch"),
                pr_status=task_details.get("pr_status"),
                blockers=task_details.get("blockers", []),
                next_action=task_details.get("next_action"),
            )

        except Exception as e:
            self.logger.error(f"Error getting active task info: {e}")
            return None

    async def _get_violations_today(self, user_id: str) -> List[WIPViolation]:
        """Get WIP violations for today"""
        try:
            # Query Firebase for today's violations
            return []

        except Exception as e:
            self.logger.error(f"Error getting violations today: {e}")
            return []

    async def _get_focus_sessions_today(self, user_id: str) -> List[FocusSession]:
        """Get focus sessions for today"""
        try:
            # Query Firebase for today's sessions
            return []

        except Exception as e:
            self.logger.error(f"Error getting focus sessions today: {e}")
            return []

    async def _get_upcoming_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get upcoming priority tasks"""
        try:
            # Query for pending tasks ordered by priority
            return []

        except Exception as e:
            self.logger.error(f"Error getting upcoming tasks: {e}")
            return []

    async def _get_recent_completions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get recently completed tasks"""
        try:
            # Query for recently completed tasks
            return []

        except Exception as e:
            self.logger.error(f"Error getting recent completions: {e}")
            return []

    async def _calculate_momentum_score(self, user_id: str) -> float:
        """Calculate weekly momentum score"""
        try:
            # Calculate based on completion rate vs creation rate
            # This is a simplified implementation
            return 0.75

        except Exception as e:
            self.logger.error(f"Error calculating momentum score: {e}")
            return 0.5

    async def _get_git_integration_status(self, user_id: str) -> Dict[str, Any]:
        """Get Git integration status"""
        try:
            return {
                "connected": True,
                "repositories": ["autoadmin-app"],
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "pending_prs": 2,
                "recent_commits": 5,
            }

        except Exception as e:
            self.logger.error(f"Error getting Git integration status: {e}")
            return {"connected": False, "error": str(e)}

    # Storage methods (would integrate with Firebase)

    async def _store_wip_limit(self, limit: WIPLimit):
        """Store WIP limit in Firebase"""
        try:
            data = limit.dict()
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"wip_limits/{limit.id}", json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing WIP limit: {e}")
            raise

    async def _store_violation(self, violation: WIPViolation):
        """Store violation in Firebase"""
        try:
            data = violation.dict()
            data["timestamp"] = data["timestamp"].isoformat()
            if data.get("resolution_timestamp"):
                data["resolution_timestamp"] = data["resolution_timestamp"].isoformat()

            await self.firebase_service.store_agent_file(
                f"wip_violations/{violation.id}", json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing violation: {e}")
            raise

    async def _store_focus_session(self, session: FocusSession):
        """Store focus session in Firebase"""
        try:
            data = session.dict()
            data["started_at"] = data["started_at"].isoformat()
            if data.get("ended_at"):
                data["ended_at"] = data["ended_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"focus_sessions/{session.id}", json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing focus session: {e}")
            raise

    async def _get_focus_session(self, session_id: str) -> Optional[FocusSession]:
        """Get focus session from Firebase"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting focus session: {e}")
            return None

    async def _get_active_focus_session(self, user_id: str) -> Optional[FocusSession]:
        """Get active focus session for user"""
        try:
            # Query for sessions where ended_at is None
            return None

        except Exception as e:
            self.logger.error(f"Error getting active focus session: {e}")
            return None

    async def _end_active_sessions(self, user_id: str):
        """End any active focus sessions for user"""
        try:
            # Find and end active sessions
            pass

        except Exception as e:
            self.logger.error(f"Error ending active sessions: {e}")

    async def _get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details"""
        try:
            # Query task details
            return {}

        except Exception as e:
            self.logger.error(f"Error getting task details: {e}")
            return None


# Global service instance
_wip_service_instance = None


def get_wip_limit_enforcement_service() -> WIPLimitEnforcementService:
    """Get singleton WIP limit enforcement service"""
    global _wip_service_instance
    if _wip_service_instance is None:
        _wip_service_instance = WIPLimitEnforcementService()
    return _wip_service_instance
