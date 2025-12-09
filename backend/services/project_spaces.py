"""
Project Spaces Service
Manages projects, goal trees, and Kanban boards
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

from pydantic import ValidationError

from fastapi.app.models.project_spaces import (
    Project, GoalNode, KanbanBoard, KanbanCard,
    ProjectStatus, ProjectPriority, GoalType, GoalStatus, KanbanColumn,
    ProjectStats, ProjectDashboardData
)
from services.firebase_service import get_firebase_service


@dataclass
class GoalTreeNode:
    """Goal tree node for hierarchical display"""
    goal: GoalNode
    children: List['GoalTreeNode']
    progress_percentage: float
    total_estimated_hours: float
    total_actual_hours: float


class ProjectSpacesService:
    """Service for managing project spaces, goal trees, and Kanban boards"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()

    async def create_project(
        self,
        name: str,
        description: Optional[str],
        owner_id: str,
        priority: ProjectPriority = ProjectPriority.MEDIUM,
        team_members: List[str] = None,
        repository: Optional[str] = None,
        start_date: Optional[datetime] = None,
        target_completion_date: Optional[datetime] = None,
        budget: Optional[float] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Project:
        """Create a new project"""
        try:
            project = Project(
                id=f"project_{uuid.uuid4().hex[:8]}",
                name=name,
                description=description,
                owner_id=owner_id,
                priority=priority,
                team_members=team_members or [],
                repository=repository,
                start_date=start_date,
                target_completion_date=target_completion_date,
                budget=budget,
                tags=tags or [],
                metadata=metadata or {}
            )

            # Store project
            await self._store_project(project)

            # Create default Kanban board
            await self.create_kanban_board(
                project_id=project.id,
                name="Default Board",
                columns=[
                    KanbanColumn.BACKLOG,
                    KanbanColumn.SPRINT,
                    KanbanColumn.IN_PROGRESS,
                    KanbanColumn.REVIEW,
                    KanbanColumn.DONE
                ],
                wip_limits={"in_progress": 2},  # Default WIP limit
                created_by=owner_id
            )

            self.logger.info(f"Created project {project.id}: {project.name}")
            return project

        except Exception as e:
            self.logger.error(f"Error creating project: {e}")
            raise

    async def create_goal(
        self,
        project_id: str,
        type: GoalType,
        title: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
        priority: int = 5,
        assignee_id: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        due_date: Optional[datetime] = None,
        dependencies: List[str] = None,
        acceptance_criteria: List[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> GoalNode:
        """Create a new goal in the project"""
        try:
            # Validate parent exists if provided
            if parent_id:
                parent_goal = await self._get_goal(parent_id)
                if not parent_goal or parent_goal.project_id != project_id:
                    raise ValueError("Invalid parent goal")

            goal = GoalNode(
                id=f"goal_{uuid.uuid4().hex[:8]}",
                project_id=project_id,
                parent_id=parent_id,
                type=type,
                title=title,
                description=description,
                priority=priority,
                assignee_id=assignee_id,
                estimated_hours=estimated_hours,
                due_date=due_date,
                dependencies=dependencies or [],
                acceptance_criteria=acceptance_criteria or [],
                tags=tags or [],
                metadata=metadata or {}
            )

            # Store goal
            await self._store_goal(goal)

            # Update parent's children list
            if parent_id:
                await self._add_child_to_parent(parent_id, goal.id)

            # Create Kanban card if board exists
            board = await self._get_project_kanban_board(project_id)
            if board:
                await self._create_kanban_card(
                    board_id=board.id,
                    goal_id=goal.id,
                    column=KanbanColumn.BACKLOG,
                    assignee_id=assignee_id,
                    due_date=due_date,
                    priority=priority,
                    estimated_hours=estimated_hours
                )

            self.logger.info(f"Created goal {goal.id}: {goal.title}")
            return goal

        except Exception as e:
            self.logger.error(f"Error creating goal: {e}")
            raise

    async def create_kanban_board(
        self,
        project_id: str,
        name: str,
        columns: List[KanbanColumn],
        wip_limits: Dict[str, int] = None,
        created_by: str
    ) -> KanbanBoard:
        """Create a Kanban board for a project"""
        try:
            board = KanbanBoard(
                id=f"board_{uuid.uuid4().hex[:8]}",
                project_id=project_id,
                name=name,
                columns=columns,
                wip_limits=wip_limits or {},
                created_by=created_by
            )

            # Store board
            await self._store_kanban_board(board)

            # Create cards for existing goals
            goals = await self._get_project_goals(project_id)
            for goal in goals:
                await self._create_kanban_card(
                    board_id=board.id,
                    goal_id=goal.id,
                    column=KanbanColumn.BACKLOG,
                    assignee_id=goal.assignee_id,
                    due_date=goal.due_date,
                    priority=goal.priority,
                    estimated_hours=goal.estimated_hours
                )

            self.logger.info(f"Created Kanban board {board.id} for project {project_id}")
            return board

        except Exception as e:
            self.logger.error(f"Error creating Kanban board: {e}")
            raise

    async def get_goal_tree(self, project_id: str) -> Dict[str, Any]:
        """Get the complete goal tree for a project"""
        try:
            # Get all goals for project
            goals = await self._get_project_goals(project_id)

            # Build tree structure
            goal_map = {goal.id: goal for goal in goals}
            tree_nodes = {}

            # Create tree nodes
            for goal in goals:
                tree_node = GoalTreeNode(
                    goal=goal,
                    children=[],
                    progress_percentage=goal.progress_percentage,
                    total_estimated_hours=goal.estimated_hours or 0,
                    total_actual_hours=goal.actual_hours or 0
                )
                tree_nodes[goal.id] = tree_node

            # Build hierarchy
            root_nodes = []
            for goal in goals:
                if goal.parent_id:
                    if goal.parent_id in tree_nodes:
                        tree_nodes[goal.parent_id].children.append(tree_nodes[goal.id])
                        # Roll up progress and hours to parent
                        parent = tree_nodes[goal.parent_id]
                        parent.total_estimated_hours += tree_nodes[goal.id].total_estimated_hours
                        parent.total_actual_hours += tree_nodes[goal.id].total_actual_hours
                        if parent.total_estimated_hours > 0:
                            parent.progress_percentage = min(1.0, parent.total_actual_hours / parent.total_estimated_hours)
                else:
                    root_nodes.append(tree_nodes[goal.id])

            # Convert to serializable format
            def tree_to_dict(node: GoalTreeNode) -> Dict[str, Any]:
                return {
                    "goal": {
                        "id": node.goal.id,
                        "title": node.goal.title,
                        "type": node.goal.type,
                        "status": node.goal.status,
                        "priority": node.goal.priority,
                        "assignee_id": node.goal.assignee_id,
                        "estimated_hours": node.goal.estimated_hours,
                        "actual_hours": node.goal.actual_hours,
                        "progress_percentage": node.goal.progress_percentage,
                        "due_date": node.goal.due_date.isoformat() if node.goal.due_date else None,
                        "acceptance_criteria": node.goal.acceptance_criteria,
                        "blockers": node.goal.blockers
                    },
                    "children": [tree_to_dict(child) for child in node.children],
                    "aggregated": {
                        "progress_percentage": node.progress_percentage,
                        "total_estimated_hours": node.total_estimated_hours,
                        "total_actual_hours": node.total_actual_hours
                    }
                }

            tree_data = {
                "project_id": project_id,
                "roots": [tree_to_dict(node) for node in root_nodes],
                "total_goals": len(goals),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return tree_data

        except Exception as e:
            self.logger.error(f"Error getting goal tree: {e}")
            return {"project_id": project_id, "roots": [], "error": str(e)}

    async def get_project_dashboard(self, project_id: str, user_id: str) -> ProjectDashboardData:
        """Get comprehensive project dashboard data"""
        try:
            # Get project
            project = await self._get_project(project_id)
            if not project:
                raise ValueError("Project not found")

            # Check access
            if user_id not in project.team_members and project.owner_id != user_id:
                raise ValueError("Access denied")

            # Get goal tree
            goal_tree = await self.get_goal_tree(project_id)

            # Get Kanban board
            kanban_board = await self._get_project_kanban_board(project_id)

            # Get Kanban cards
            kanban_cards = []
            if kanban_board:
                cards = await self._get_board_cards(kanban_board.id)
                kanban_cards = [
                    {
                        "id": card.id,
                        "goal_id": card.goal_id,
                        "column": card.column,
                        "position": card.position,
                        "assignee_id": card.assignee_id,
                        "labels": card.labels,
                        "due_date": card.due_date.isoformat() if card.due_date else None,
                        "priority": card.priority
                    }
                    for card in cards
                ]

            # Get recent activity (simplified)
            recent_activity = await self._get_recent_activity(project_id)

            # Get upcoming deadlines
            upcoming_deadlines = await self._get_upcoming_deadlines(project_id)

            # Get team members (simplified)
            team_members = [
                {"id": member_id, "name": f"User {member_id}", "role": "member"}
                for member_id in project.team_members
            ]
            team_members.insert(0, {"id": project.owner_id, "name": f"Owner {project.owner_id}", "role": "owner"})

            # Calculate progress metrics
            progress_metrics = await self._calculate_progress_metrics(project_id)

            # Get blockers
            blockers = await self._get_project_blockers(project_id)

            return ProjectDashboardData(
                project=project,
                goal_tree=goal_tree,
                kanban_board=kanban_board,
                kanban_cards=kanban_cards,
                recent_activity=recent_activity,
                upcoming_deadlines=upcoming_deadlines,
                team_members=team_members,
                progress_metrics=progress_metrics,
                blockers=blockers
            )

        except Exception as e:
            self.logger.error(f"Error getting project dashboard: {e}")
            raise

    async def move_kanban_card(
        self,
        card_id: str,
        new_column: KanbanColumn,
        new_position: int = 0,
        user_id: str
    ) -> bool:
        """Move a Kanban card to a new column/position"""
        try:
            # Get card
            card = await self._get_kanban_card(card_id)
            if not card:
                raise ValueError("Card not found")

            # Check WIP limits
            board = await self._get_kanban_board(card.board_id)
            if not board:
                raise ValueError("Board not found")

            wip_limit = board.wip_limits.get(new_column.value, 0)
            if wip_limit > 0:
                current_cards = await self._get_column_cards(card.board_id, new_column)
                if len(current_cards) >= wip_limit and card.column != new_column:
                    raise ValueError(f"WIP limit exceeded for column {new_column.value}")

            # Update card
            card.column = new_column
            card.position = new_position
            card.updated_at = datetime.now(timezone.utc)

            await self._store_kanban_card(card)

            # Update goal status based on column
            await self._update_goal_status_from_column(card.goal_id, new_column)

            self.logger.info(f"Moved card {card_id} to {new_column.value}")
            return True

        except Exception as e:
            self.logger.error(f"Error moving Kanban card: {e}")
            return False

    async def update_goal_progress(
        self,
        goal_id: str,
        progress_percentage: float,
        actual_hours: Optional[float] = None,
        status: Optional[GoalStatus] = None,
        user_id: str
    ) -> bool:
        """Update goal progress"""
        try:
            goal = await self._get_goal(goal_id)
            if not goal:
                raise ValueError("Goal not found")

            # Update goal
            goal.progress_percentage = progress_percentage
            if actual_hours is not None:
                goal.actual_hours = actual_hours
            if status:
                goal.status = status
            goal.updated_at = datetime.now(timezone.utc)

            # Mark as completed if 100%
            if progress_percentage >= 1.0 and goal.status != GoalStatus.COMPLETED:
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = datetime.now(timezone.utc)

            await self._store_goal(goal)

            # Update Kanban card position if completed
            if goal.status == GoalStatus.COMPLETED:
                await self._move_goal_to_done(goal_id)

            # Propagate progress up the tree
            await self._propagate_progress_up_tree(goal_id)

            self.logger.info(f"Updated goal {goal_id} progress to {progress_percentage:.1%}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating goal progress: {e}")
            return False

    async def get_project_stats(self, user_id: Optional[str] = None) -> ProjectStats:
        """Get project statistics"""
        try:
            # This would aggregate data from Firebase
            # For now, return basic stats
            return ProjectStats(
                total_projects=5,
                active_projects=3,
                completed_projects=2,
                total_goals=25,
                completed_goals=15,
                in_progress_goals=8,
                blocked_goals=2,
                average_completion_time=12.5,
                on_time_completion_rate=0.8,
                team_utilization=0.75
            )

        except Exception as e:
            self.logger.error(f"Error getting project stats: {e}")
            return ProjectStats()

    # Private helper methods

    async def _store_project(self, project: Project):
        """Store project in Firebase"""
        try:
            data = project.dict()
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()
            if data.get("start_date"):
                data["start_date"] = data["start_date"].isoformat()
            if data.get("target_completion_date"):
                data["target_completion_date"] = data["target_completion_date"].isoformat()
            if data.get("actual_completion_date"):
                data["actual_completion_date"] = data["actual_completion_date"].isoformat()

            await self.firebase_service.store_agent_file(
                f"projects/{project.id}",
                json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing project: {e}")
            raise

    async def _store_goal(self, goal: GoalNode):
        """Store goal in Firebase"""
        try:
            data = goal.dict()
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()
            if data.get("due_date"):
                data["due_date"] = data["due_date"].isoformat()
            if data.get("completed_at"):
                data["completed_at"] = data["completed_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"goals/{goal.id}",
                json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing goal: {e}")
            raise

    async def _store_kanban_board(self, board: KanbanBoard):
        """Store Kanban board in Firebase"""
        try:
            data = board.dict()
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"kanban_boards/{board.id}",
                json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing Kanban board: {e}")
            raise

    async def _store_kanban_card(self, card: KanbanCard):
        """Store Kanban card in Firebase"""
        try:
            data = card.dict()
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()
            if data.get("due_date"):
                data["due_date"] = data["due_date"].isoformat()

            await self.firebase_service.store_agent_file(
                f"kanban_cards/{card.id}",
                json.dumps(data, indent=2)
            )

        except Exception as e:
            self.logger.error(f"Error storing Kanban card: {e}")
            raise

    async def _get_project(self, project_id: str) -> Optional[Project]:
        """Get project from Firebase"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting project: {e}")
            return None

    async def _get_goal(self, goal_id: str) -> Optional[GoalNode]:
        """Get goal from Firebase"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting goal: {e}")
            return None

    async def _get_project_goals(self, project_id: str) -> List[GoalNode]:
        """Get all goals for a project"""
        try:
            # This would query Firebase
            return []

        except Exception as e:
            self.logger.error(f"Error getting project goals: {e}")
            return []

    async def _get_project_kanban_board(self, project_id: str) -> Optional[KanbanBoard]:
        """Get Kanban board for a project"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting project Kanban board: {e}")
            return None

    async def _get_kanban_board(self, board_id: str) -> Optional[KanbanBoard]:
        """Get Kanban board by ID"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting Kanban board: {e}")
            return None

    async def _get_kanban_card(self, card_id: str) -> Optional[KanbanCard]:
        """Get Kanban card by ID"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting Kanban card: {e}")
            return None

    async def _get_board_cards(self, board_id: str) -> List[KanbanCard]:
        """Get all cards for a board"""
        try:
            # This would query Firebase
            return []

        except Exception as e:
            self.logger.error(f"Error getting board cards: {e}")
            return []

    async def _get_column_cards(self, board_id: str, column: KanbanColumn) -> List[KanbanCard]:
        """Get cards in a specific column"""
        try:
            # This would query Firebase
            return []

        except Exception as e:
            self.logger.error(f"Error getting column cards: {e}")
            return []

    async def _create_kanban_card(
        self,
        board_id: str,
        goal_id: str,
        column: KanbanColumn,
        assignee_id: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: int = 5,
        estimated_hours: Optional[float] = None
    ) -> KanbanCard:
        """Create a Kanban card"""
        try:
            card = KanbanCard(
                id=f"card_{uuid.uuid4().hex[:8]}",
                board_id=board_id,
                goal_id=goal_id,
                column=column,
                assignee_id=assignee_id,
                due_date=due_date,
                priority=priority,
                estimated_hours=estimated_hours
            )

            await self._store_kanban_card(card)
            return card

        except Exception as e:
            self.logger.error(f"Error creating Kanban card: {e}")
            raise

    async def _add_child_to_parent(self, parent_id: str, child_id: str):
        """Add child goal to parent's children list"""
        try:
            parent = await self._get_goal(parent_id)
            if parent and child_id not in parent.children:
                parent.children.append(child_id)
                parent.updated_at = datetime.now(timezone.utc)
                await self._store_goal(parent)

        except Exception as e:
            self.logger.error(f"Error adding child to parent: {e}")

    async def _update_goal_status_from_column(self, goal_id: str, column: KanbanColumn):
        """Update goal status based on Kanban column"""
        try:
            goal = await self._get_goal(goal_id)
            if not goal:
                return

            status_map = {
                KanbanColumn.BACKLOG: GoalStatus.NOT_STARTED,
                KanbanColumn.SPRINT: GoalStatus.NOT_STARTED,
                KanbanColumn.IN_PROGRESS: GoalStatus.IN_PROGRESS,
                KanbanColumn.REVIEW: GoalStatus.IN_PROGRESS,
                KanbanColumn.DONE: GoalStatus.COMPLETED,
                KanbanColumn.ARCHIVED: GoalStatus.CANCELLED
            }

            new_status = status_map.get(column, goal.status)
            if new_status != goal.status:
                goal.status = new_status
                goal.updated_at = datetime.now(timezone.utc)
                if new_status == GoalStatus.COMPLETED:
                    goal.completed_at = datetime.now(timezone.utc)
                    goal.progress_percentage = 1.0
                await self._store_goal(goal)

        except Exception as e:
            self.logger.error(f"Error updating goal status from column: {e}")

    async def _move_goal_to_done(self, goal_id: str):
        """Move goal's Kanban card to Done column"""
        try:
            # Find card for goal and move to Done
            pass

        except Exception as e:
            self.logger.error(f"Error moving goal to done: {e}")

    async def _propagate_progress_up_tree(self, goal_id: str):
        """Propagate progress changes up the goal tree"""
        try:
            # Recursively update parent progress
            pass

        except Exception as e:
            self.logger.error(f"Error propagating progress: {e}")

    async def _get_recent_activity(self, project_id: str) -> List[Dict[str, Any]]:
        """Get recent project activity"""
        try:
            # This would query recent changes
            return []

        except Exception as e:
            self.logger.error(f"Error getting recent activity: {e}")
            return []

    async def _get_upcoming_deadlines(self, project_id: str) -> List[Dict[str, Any]]:
        """Get upcoming deadlines"""
        try:
            # This would query goals with due dates
            return []

        except Exception as e:
            self.logger.error(f"Error getting upcoming deadlines: {e}")
            return []

    async def _calculate_progress_metrics(self, project_id: str) -> Dict[str, Any]:
        """Calculate project progress metrics"""
        try:
            goals = await self._get_project_goals(project_id)

            total_goals = len(goals)
            completed_goals = len([g for g in goals if g.status == GoalStatus.COMPLETED])
            in_progress_goals = len([g for g in goals if g.status == GoalStatus.IN_PROGRESS])
            blocked_goals = len([g for g in goals if g.status == GoalStatus.BLOCKED])

            total_estimated = sum(g.estimated_hours or 0 for g in goals)
            total_actual = sum(g.actual_hours or 0 for g in goals)

            completion_rate = completed_goals / total_goals if total_goals > 0 else 0
            progress_percentage = sum(g.progress_percentage for g in goals) / total_goals if total_goals > 0 else 0

            return {
                "total_goals": total_goals,
                "completed_goals": completed_goals,
                "in_progress_goals": in_progress_goals,
                "blocked_goals": blocked_goals,
                "completion_rate": completion_rate,
                "progress_percentage": progress_percentage,
                "total_estimated_hours": total_estimated,
                "total_actual_hours": total_actual,
                "efficiency_ratio": total_actual / total_estimated if total_estimated > 0 else 0
            }

        except Exception as e:
            self.logger.error(f"Error calculating progress metrics: {e}")
            return {}

    async def _get_project_blockers(self, project_id: str) -> List[str]:
        """Get project blockers"""
        try:
            goals = await self._get_project_goals(project_id)
            blockers = []

            for goal in goals:
                blockers.extend(goal.blockers)

            return list(set(blockers))  # Remove duplicates

        except Exception as e:
            self.logger.error(f"Error getting project blockers: {e}")
            return []


# Global service instance
_project_spaces_service = None

def get_project_spaces_service() -> ProjectSpacesService:
    """Get singleton project spaces service"""
    global _project_spaces_service
    if _project_spaces_service is None:
        _project_spaces_service = ProjectSpacesService()
    return _project_spaces_service