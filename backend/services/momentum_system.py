"""
Momentum System and Portfolio View
Tracks weekly momentum, velocity, and provides portfolio overview
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
import statistics

from pydantic import BaseModel, Field

from services.firebase_service import get_firebase_service
from services.project_spaces import get_project_spaces_service
from services.wip_limit_enforcement import get_wip_limit_enforcement_service
from services.timeboxing import get_timeboxing_service


class MomentumMetric(str, Enum):
    """Momentum tracking metrics"""

    TASK_COMPLETION_RATE = "task_completion_rate"
    FOCUS_TIME_CONSISTENCY = "focus_time_consistency"
    WIP_LIMIT_ADHERENCE = "wip_limit_adherence"
    PROJECT_PROGRESS_VELOCITY = "project_progress_velocity"
    GOAL_ACHIEVEMENT_RATE = "goal_achievement_rate"
    TIME_ESTIMATE_ACCURACY = "time_estimate_accuracy"


class MomentumTrend(str, Enum):
    """Momentum trend direction"""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class ProjectStage(str, Enum):
    """Project development stages"""

    IDEA = "idea"  # Initial concept
    PLANNING = "planning"  # Requirements gathering
    MVP = "mvp"  # Minimum viable product
    GROWTH = "growth"  # Feature expansion
    MATURITY = "maturity"  # Stable product
    SUNSET = "sunset"  # End of life


@dataclass
class WeeklyMomentumData:
    """Weekly momentum calculation data"""

    week_start: str
    week_end: str

    # Task metrics
    tasks_created: int = 0
    tasks_completed: int = 0
    tasks_in_progress: int = 0
    tasks_blocked: int = 0

    # Time metrics
    total_focus_time: int = 0  # minutes
    total_work_time: int = 0  # minutes
    average_focus_score: float = 0.0

    # WIP metrics
    wip_violations: int = 0
    average_active_tasks: float = 0.0

    # Project metrics
    projects_active: int = 0
    goals_completed: int = 0
    goals_created: int = 0

    # Calculated scores
    completion_rate: float = 0.0
    focus_consistency: float = 0.0
    wip_adherence: float = 0.0
    velocity_score: float = 0.0
    momentum_score: float = 0.0


@dataclass
class MomentumInsight:
    """Individual momentum insight"""

    metric: MomentumMetric
    current_value: float
    previous_value: float
    trend: MomentumTrend
    insight: str
    recommendation: str
    severity: str  # low, medium, high


@dataclass
class ProjectPortfolioItem:
    """Project item for portfolio view"""

    project_id: str
    name: str
    stage: ProjectStage
    progress_percentage: float
    momentum_score: float
    last_activity: datetime
    next_milestone: Optional[str]
    team_size: int
    blockers: List[str]
    priority_score: float


class MomentumSystemService:
    """Service for tracking momentum and providing portfolio insights"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.project_service = get_project_spaces_service()
        self.wip_service = get_wip_limit_enforcement_service()
        self.timeboxing_service = get_timeboxing_service()

    async def calculate_weekly_momentum(
        self, user_id: str, week_start_date: str
    ) -> WeeklyMomentumData:
        """Calculate momentum metrics for a week"""
        try:
            # Parse dates
            week_start = datetime.strptime(week_start_date, "%Y-%m-%d")
            week_end = week_start + timedelta(days=6)
            week_end_str = week_end.strftime("%Y-%m-%d")

            momentum_data = WeeklyMomentumData(
                week_start=week_start_date, week_end=week_end_str
            )

            # Get data from various services
            await self._collect_task_metrics(
                user_id, week_start, week_end, momentum_data
            )
            await self._collect_time_metrics(
                user_id, week_start, week_end, momentum_data
            )
            await self._collect_wip_metrics(
                user_id, week_start, week_end, momentum_data
            )
            await self._collect_project_metrics(
                user_id, week_start, week_end, momentum_data
            )

            # Calculate derived scores
            await self._calculate_momentum_scores(momentum_data)

            # Store momentum data
            await self._store_weekly_momentum(user_id, momentum_data)

            self.logger.info(
                f"Calculated weekly momentum for {user_id}: score {momentum_data.momentum_score:.1f}"
            )
            return momentum_data

        except Exception as e:
            self.logger.error(f"Error calculating weekly momentum: {e}")
            raise

    async def get_momentum_insights(
        self, user_id: str, weeks_back: int = 4
    ) -> List[MomentumInsight]:
        """Get momentum insights and trends"""
        try:
            insights = []

            # Get momentum data for recent weeks
            end_date = datetime.now(timezone.utc)
            momentum_weeks = []

            for i in range(weeks_back):
                week_start = end_date - timedelta(days=(i * 7) + end_date.weekday())
                week_start_str = week_start.strftime("%Y-%m-%d")

                momentum = await self._get_weekly_momentum(user_id, week_start_str)
                if momentum:
                    momentum_weeks.append(momentum)

            if len(momentum_weeks) < 2:
                return insights  # Need at least 2 weeks for comparison

            # Sort by week (most recent first)
            momentum_weeks.sort(key=lambda x: x.week_start, reverse=True)
            current = momentum_weeks[0]
            previous = momentum_weeks[1]

            # Analyze each metric
            insights.extend(await self._analyze_completion_rate(current, previous))
            insights.extend(await self._analyze_focus_consistency(current, previous))
            insights.extend(await self._analyze_wip_adherence(current, previous))
            insights.extend(await self._analyze_velocity(current, previous))

            # Sort by severity
            severity_order = {"high": 3, "medium": 2, "low": 1}
            insights.sort(key=lambda x: severity_order.get(x.severity, 0), reverse=True)

            return insights[:10]  # Top 10 insights

        except Exception as e:
            self.logger.error(f"Error getting momentum insights: {e}")
            return []

    async def get_portfolio_overview(self, user_id: str) -> List[ProjectPortfolioItem]:
        """Get portfolio overview of all projects"""
        try:
            portfolio_items = []

            # Get all projects for user
            projects = await self._get_user_projects(user_id)

            for project in projects:
                # Get project dashboard data
                dashboard = await self.project_service.get_project_dashboard(
                    project.id, user_id
                )

                # Calculate momentum score for project
                momentum_score = await self._calculate_project_momentum(
                    project.id, user_id
                )

                # Determine project stage
                stage = await self._determine_project_stage(project, dashboard)

                # Get next milestone
                next_milestone = await self._get_next_milestone(project.id)

                # Get blockers
                blockers = dashboard.blockers[:3]  # Top 3 blockers

                # Calculate priority score
                priority_score = await self._calculate_project_priority(
                    project, dashboard, momentum_score
                )

                item = ProjectPortfolioItem(
                    project_id=project.id,
                    name=project.name,
                    stage=stage,
                    progress_percentage=dashboard.progress_metrics.get(
                        "progress_percentage", 0.0
                    ),
                    momentum_score=momentum_score,
                    last_activity=dashboard.timestamp,
                    next_milestone=next_milestone,
                    team_size=len(dashboard.team_members),
                    blockers=blockers,
                    priority_score=priority_score,
                )

                portfolio_items.append(item)

            # Sort by priority score
            portfolio_items.sort(key=lambda x: x.priority_score, reverse=True)

            return portfolio_items

        except Exception as e:
            self.logger.error(f"Error getting portfolio overview: {e}")
            return []

    async def get_momentum_trends(
        self, user_id: str, months_back: int = 3
    ) -> Dict[str, Any]:
        """Get momentum trends over time"""
        try:
            trends = {
                "period": f"{months_back} months",
                "metrics": {},
                "trends": {},
                "predictions": {},
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Get momentum data for the period
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=months_back * 30)

            # This would analyze trends in momentum scores
            # For now, return basic trend data

            trends["metrics"] = {
                "average_momentum": 72.5,
                "momentum_volatility": 0.15,
                "best_week": "2024-W15",
                "worst_week": "2024-W08",
                "improvement_rate": 0.08,  # 8% improvement over period
            }

            trends["trends"] = {
                "overall_trend": "improving",
                "focus_consistency": "stable",
                "completion_rate": "improving",
                "velocity": "declining",
            }

            trends["predictions"] = {
                "next_week_momentum": 75.2,
                "confidence": 0.78,
                "factors": ["Consistent focus sessions", "Reduced WIP violations"],
            }

            return trends

        except Exception as e:
            self.logger.error(f"Error getting momentum trends: {e}")
            return {"error": str(e)}

    async def generate_momentum_report(
        self, user_id: str, week_start_date: str
    ) -> Dict[str, Any]:
        """Generate comprehensive momentum report"""
        try:
            # Get weekly momentum
            momentum = await self.calculate_weekly_momentum(user_id, week_start_date)

            # Get insights
            insights = await self.get_momentum_insights(user_id)

            # Get portfolio
            portfolio = await self.get_portfolio_overview(user_id)

            # Generate recommendations
            recommendations = await self._generate_momentum_recommendations(
                momentum, insights
            )

            report = {
                "week": f"{momentum.week_start} to {momentum.week_end}",
                "momentum_score": momentum.momentum_score,
                "momentum_grade": self._get_momentum_grade(momentum.momentum_score),
                "key_metrics": {
                    "completion_rate": f"{momentum.completion_rate:.1%}",
                    "focus_consistency": f"{momentum.focus_consistency:.1%}",
                    "wip_adherence": f"{momentum.wip_adherence:.1%}",
                    "velocity_score": f"{momentum.velocity_score:.1f}",
                },
                "insights": [
                    {
                        "metric": insight.metric.value,
                        "trend": insight.trend.value,
                        "insight": insight.insight,
                        "recommendation": insight.recommendation,
                        "severity": insight.severity,
                    }
                    for insight in insights[:5]  # Top 5 insights
                ],
                "portfolio_highlights": [
                    {
                        "project": item.name,
                        "stage": item.stage.value,
                        "progress": f"{item.progress_percentage:.1%}",
                        "momentum": f"{item.momentum_score:.1f}",
                        "priority": "high"
                        if item.priority_score > 80
                        else "medium"
                        if item.priority_score > 60
                        else "low",
                    }
                    for item in portfolio[:3]  # Top 3 projects
                ],
                "recommendations": recommendations,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            return report

        except Exception as e:
            self.logger.error(f"Error generating momentum report: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _collect_task_metrics(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        momentum: WeeklyMomentumData,
    ):
        """Collect task-related metrics"""
        try:
            # This would query task data from Firebase
            # For now, use placeholder data
            momentum.tasks_created = 12
            momentum.tasks_completed = 8
            momentum.tasks_in_progress = 3
            momentum.tasks_blocked = 1

        except Exception as e:
            self.logger.error(f"Error collecting task metrics: {e}")

    async def _collect_time_metrics(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        momentum: WeeklyMomentumData,
    ):
        """Collect time-related metrics"""
        try:
            # Get timeboxing data
            weekly_report = await self.timeboxing_service.generate_weekly_report(
                user_id, week_start.strftime("%Y-%m-%d")
            )

            momentum.total_focus_time = weekly_report.total_focus_time
            momentum.average_focus_score = weekly_report.average_focus_score

        except Exception as e:
            self.logger.error(f"Error collecting time metrics: {e}")

    async def _collect_wip_metrics(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        momentum: WeeklyMomentumData,
    ):
        """Collect WIP-related metrics"""
        try:
            # Get WIP stats
            wip_stats = await self.wip_service.get_wip_stats(user_id)

            momentum.wip_violations = (
                wip_stats.violations_today
            )  # This should be weekly
            momentum.average_active_tasks = wip_stats.average_active_tasks

        except Exception as e:
            self.logger.error(f"Error collecting WIP metrics: {e}")

    async def _collect_project_metrics(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        momentum: WeeklyMomentumData,
    ):
        """Collect project-related metrics"""
        try:
            # Get project stats
            project_stats = await self.project_service.get_project_stats(user_id)

            momentum.projects_active = project_stats.active_projects
            momentum.goals_completed = project_stats.completed_goals
            momentum.goals_created = (
                project_stats.total_goals - project_stats.completed_goals
            )  # Approximation

        except Exception as e:
            self.logger.error(f"Error collecting project metrics: {e}")

    async def _calculate_momentum_scores(self, momentum: WeeklyMomentumData):
        """Calculate derived momentum scores"""
        try:
            # Completion rate
            total_tasks = momentum.tasks_created + momentum.tasks_completed
            if total_tasks > 0:
                momentum.completion_rate = momentum.tasks_completed / total_tasks

            # Focus consistency (based on focus time vs expected)
            expected_weekly_focus = 20 * 60  # 20 hours = 1200 minutes
            momentum.focus_consistency = min(
                1.0, momentum.total_focus_time / expected_weekly_focus
            )

            # WIP adherence (inverse of violations)
            max_expected_violations = 5  # Allow some violations
            momentum.wip_adherence = max(
                0.0, 1.0 - (momentum.wip_violations / max_expected_violations)
            )

            # Velocity score (tasks completed per hour of focus time)
            if momentum.total_focus_time > 0:
                momentum.velocity_score = momentum.tasks_completed / (
                    momentum.total_focus_time / 60
                )

            # Overall momentum score (weighted average)
            weights = {
                "completion_rate": 0.3,
                "focus_consistency": 0.25,
                "wip_adherence": 0.2,
                "velocity_score": 0.25,
            }

            # Normalize velocity score (assuming 0.5 tasks/hour is good)
            normalized_velocity = min(1.0, momentum.velocity_score / 0.5)

            momentum.momentum_score = (
                momentum.completion_rate * weights["completion_rate"]
                + momentum.focus_consistency * weights["focus_consistency"]
                + momentum.wip_adherence * weights["wip_adherence"]
                + normalized_velocity * weights["velocity_score"]
            ) * 100  # Convert to 0-100 scale

        except Exception as e:
            self.logger.error(f"Error calculating momentum scores: {e}")

    async def _analyze_completion_rate(
        self, current: WeeklyMomentumData, previous: WeeklyMomentumData
    ) -> List[MomentumInsight]:
        """Analyze task completion rate trends"""
        try:
            insights = []

            change = current.completion_rate - previous.completion_rate
            trend = self._determine_trend(change)

            if abs(change) > 0.1:  # 10% change
                severity = "high" if abs(change) > 0.2 else "medium"

                if trend == MomentumTrend.IMPROVING:
                    insight = f"Task completion rate improved by {change:.1%} this week"
                    recommendation = "Continue current task management practices"
                elif trend == MomentumTrend.DECLINING:
                    insight = (
                        f"Task completion rate declined by {abs(change):.1%} this week"
                    )
                    recommendation = "Review blockers and consider reducing WIP limits"
                else:
                    insight = f"Task completion rate is {trend.value}"
                    recommendation = "Monitor for changes in work patterns"

                insights.append(
                    MomentumInsight(
                        metric=MomentumMetric.TASK_COMPLETION_RATE,
                        current_value=current.completion_rate,
                        previous_value=previous.completion_rate,
                        trend=trend,
                        insight=insight,
                        recommendation=recommendation,
                        severity=severity,
                    )
                )

            return insights

        except Exception as e:
            self.logger.error(f"Error analyzing completion rate: {e}")
            return []

    async def _analyze_focus_consistency(
        self, current: WeeklyMomentumData, previous: WeeklyMomentumData
    ) -> List[MomentumInsight]:
        """Analyze focus time consistency"""
        try:
            insights = []

            change = current.focus_consistency - previous.focus_consistency
            trend = self._determine_trend(change)

            if current.focus_consistency < 0.7:  # Below 70% consistency
                insights.append(
                    MomentumInsight(
                        metric=MomentumMetric.FOCUS_TIME_CONSISTENCY,
                        current_value=current.focus_consistency,
                        previous_value=previous.focus_consistency,
                        trend=trend,
                        insight=f"Focus time consistency is low at {current.focus_consistency:.1%}",
                        recommendation="Schedule dedicated focus blocks and minimize interruptions",
                        severity="high",
                    )
                )

            return insights

        except Exception as e:
            self.logger.error(f"Error analyzing focus consistency: {e}")
            return []

    async def _analyze_wip_adherence(
        self, current: WeeklyMomentumData, previous: WeeklyMomentumData
    ) -> List[MomentumInsight]:
        """Analyze WIP limit adherence"""
        try:
            insights = []

            if current.wip_violations > 3:  # Multiple violations
                insights.append(
                    MomentumInsight(
                        metric=MomentumMetric.WIP_LIMIT_ADHERENCE,
                        current_value=current.wip_adherence,
                        previous_value=previous.wip_adherence,
                        trend=MomentumTrend.DECLINING,
                        insight=f"High WIP violations ({current.wip_violations}) indicate context switching",
                        recommendation="Enforce WIP limits more strictly and complete current tasks first",
                        severity="high",
                    )
                )

            return insights

        except Exception as e:
            self.logger.error(f"Error analyzing WIP adherence: {e}")
            return []

    async def _analyze_velocity(
        self, current: WeeklyMomentumData, previous: WeeklyMomentumData
    ) -> List[MomentumInsight]:
        """Analyze project velocity"""
        try:
            insights = []

            change = current.velocity_score - previous.velocity_score
            trend = self._determine_trend(change)

            if current.velocity_score < 0.3:  # Low velocity
                insights.append(
                    MomentumInsight(
                        metric=MomentumMetric.PROJECT_PROGRESS_VELOCITY,
                        current_value=current.velocity_score,
                        previous_value=previous.velocity_score,
                        trend=trend,
                        insight="Project velocity is low - tasks are taking longer than expected",
                        recommendation="Review time estimates and identify bottlenecks",
                        severity="medium",
                    )
                )

            return insights

        except Exception as e:
            self.logger.error(f"Error analyzing velocity: {e}")
            return []

    def _determine_trend(self, change: float) -> MomentumTrend:
        """Determine trend direction from change value"""
        if change > 0.05:  # 5% improvement
            return MomentumTrend.IMPROVING
        elif change < -0.05:  # 5% decline
            return MomentumTrend.DECLINING
        else:
            return MomentumTrend.STABLE

    def _get_momentum_grade(self, score: float) -> str:
        """Convert momentum score to letter grade"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    async def _generate_momentum_recommendations(
        self, momentum: WeeklyMomentumData, insights: List[MomentumInsight]
    ) -> List[str]:
        """Generate momentum-based recommendations"""
        try:
            recommendations = []

            if momentum.momentum_score < 60:
                recommendations.append(
                    "Focus on completing existing tasks before starting new ones"
                )
                recommendations.append(
                    "Schedule dedicated focus time blocks without interruptions"
                )

            if momentum.wip_violations > 2:
                recommendations.append(
                    "Reduce work-in-progress by enforcing stricter limits"
                )

            if momentum.completion_rate < 0.6:
                recommendations.append(
                    "Break large tasks into smaller, achievable units"
                )

            if momentum.focus_consistency < 0.7:
                recommendations.append(
                    "Establish a consistent daily routine with fixed focus periods"
                )

            # Add insight-based recommendations
            for insight in insights[:3]:  # Top 3 insights
                if insight.recommendation not in recommendations:
                    recommendations.append(insight.recommendation)

            return recommendations[:5]  # Top 5 recommendations

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Continue monitoring momentum metrics"]

    async def _store_weekly_momentum(self, user_id: str, momentum: WeeklyMomentumData):
        """Store weekly momentum data"""
        try:
            data = asdict(momentum)

            await self.firebase_service.store_agent_file(
                f"momentum/{user_id}/{momentum.week_start}",
                json.dumps(data, indent=2, default=str),
            )

        except Exception as e:
            self.logger.error(f"Error storing weekly momentum: {e}")

    async def _get_weekly_momentum(
        self, user_id: str, week_start: str
    ) -> Optional[WeeklyMomentumData]:
        """Get stored weekly momentum data"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting weekly momentum: {e}")
            return None

    async def _get_user_projects(self, user_id: str) -> List[Any]:
        """Get all projects for user"""
        try:
            # This would query Firebase for user's projects
            return []

        except Exception as e:
            self.logger.error(f"Error getting user projects: {e}")
            return []

    async def _calculate_project_momentum(self, project_id: str, user_id: str) -> float:
        """Calculate momentum score for a specific project"""
        try:
            # Simplified calculation based on recent activity
            return 75.0

        except Exception as e:
            self.logger.error(f"Error calculating project momentum: {e}")
            return 50.0

    async def _determine_project_stage(
        self, project: Any, dashboard: Any
    ) -> ProjectStage:
        """Determine project development stage"""
        try:
            progress = dashboard.progress_metrics.get("progress_percentage", 0.0)

            if progress < 0.1:
                return ProjectStage.IDEA
            elif progress < 0.3:
                return ProjectStage.PLANNING
            elif progress < 0.6:
                return ProjectStage.MVP
            elif progress < 0.8:
                return ProjectStage.GROWTH
            elif progress < 0.95:
                return ProjectStage.MATURITY
            else:
                return ProjectStage.SUNSET

        except Exception as e:
            self.logger.error(f"Error determining project stage: {e}")
            return ProjectStage.PLANNING

    async def _get_next_milestone(self, project_id: str) -> Optional[str]:
        """Get next milestone for project"""
        try:
            # This would query project goals for next milestone
            return "Complete MVP features"

        except Exception as e:
            self.logger.error(f"Error getting next milestone: {e}")
            return None

    async def _calculate_project_priority(
        self, project: Any, dashboard: Any, momentum: float
    ) -> float:
        """Calculate project priority score"""
        try:
            # Factors: progress, momentum, deadlines, blockers
            progress_factor = dashboard.progress_metrics.get("progress_percentage", 0.0)
            momentum_factor = momentum / 100.0
            blocker_penalty = len(dashboard.blockers) * 0.1

            priority = (
                progress_factor * 0.4
                + momentum_factor * 0.4
                + (1 - blocker_penalty) * 0.2
            ) * 100
            return min(100.0, max(0.0, priority))

        except Exception as e:
            self.logger.error(f"Error calculating project priority: {e}")
            return 50.0


# Global service instance
_momentum_service = None


def get_momentum_system_service() -> MomentumSystemService:
    """Get singleton momentum system service"""
    global _momentum_service
    if _momentum_service is None:
        _momentum_service = MomentumSystemService()
    return _momentum_service
