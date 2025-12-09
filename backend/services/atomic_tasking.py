"""
Atomic Tasking Engine
Breaks down large tasks into small, shippable, PR-sized units
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

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from fastapi.app.models.task import Task, TaskType, TaskPriority, TaskStatus
from services.firebase_service import get_firebase_service
from services.agent_orchestrator_http import get_http_agent_orchestrator


class TaskSize(str, Enum):
    """Task size categories"""

    TINY = "tiny"  # 15-30 minutes
    SMALL = "small"  # 30-60 minutes
    MEDIUM = "medium"  # 1-2 hours
    LARGE = "large"  # 2-4 hours
    EPIC = "epic"  # 4+ hours (needs breakdown)


class TaskComplexity(str, Enum):
    """Task complexity levels"""

    SIMPLE = "simple"  # Straightforward implementation
    MODERATE = "moderate"  # Some complexity, research needed
    COMPLEX = "complex"  # Significant complexity, multiple approaches
    VERY_COMPLEX = "very_complex"  # High complexity, architectural decisions


class AtomicTask(BaseModel):
    """An atomic, shippable task unit"""

    id: str = Field(description="Atomic task unique identifier")
    parent_task_id: str = Field(description="Parent task ID")
    title: str = Field(description="Clear, actionable title")
    description: str = Field(description="Detailed description of what to do")
    size: TaskSize = Field(description="Estimated task size")
    complexity: TaskComplexity = Field(description="Task complexity level")
    estimated_minutes: int = Field(description="Estimated time in minutes")
    acceptance_criteria: List[str] = Field(description="Clear criteria for completion")
    dependencies: List[str] = Field(description="IDs of tasks this depends on")
    deliverables: List[str] = Field(description="Expected outputs/deliverables")
    technical_notes: Optional[str] = Field(
        default=None, description="Technical implementation notes"
    )
    testing_requirements: List[str] = Field(
        default_factory=list, description="Testing requirements"
    )
    priority_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Priority within parent task"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    order: int = Field(description="Order within parent task")


class TaskBreakdownResult(BaseModel):
    """Result of breaking down a task into atomic units"""

    parent_task_id: str = Field(description="Original task ID")
    atomic_tasks: List[AtomicTask] = Field(description="Broken down atomic tasks")
    breakdown_reasoning: str = Field(description="Explanation of breakdown approach")
    estimated_total_time: int = Field(description="Total estimated time in minutes")
    risk_assessment: Dict[str, Any] = Field(
        description="Risks and mitigation strategies"
    )
    suggested_approach: str = Field(description="Recommended implementation approach")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Breakdown timestamp"
    )


class AtomicTaskingEngine:
    """Engine for breaking down tasks into atomic, shippable units"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.agent_orchestrator = get_http_agent_orchestrator()

        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,  # Low temperature for consistent task breakdown
            max_tokens=3000,
            openai_api_key=openai_api_key,
        )

        # Task size guidelines
        self.size_guidelines = {
            TaskSize.TINY: {
                "min_minutes": 15,
                "max_minutes": 30,
                "description": "Quick wins, bug fixes, simple changes",
            },
            TaskSize.SMALL: {
                "min_minutes": 30,
                "max_minutes": 60,
                "description": "Single feature additions, moderate changes",
            },
            TaskSize.MEDIUM: {
                "min_minutes": 60,
                "max_minutes": 120,
                "description": "Complex features, multiple file changes",
            },
            TaskSize.LARGE: {
                "min_minutes": 120,
                "max_minutes": 240,
                "description": "Major features, architectural changes",
            },
            TaskSize.EPIC: {
                "min_minutes": 240,
                "max_minutes": 480,
                "description": "Large initiatives requiring breakdown",
            },
        }

        # Complexity patterns
        self.complexity_patterns = {
            TaskComplexity.SIMPLE: ["straightforward", "simple", "basic", "standard"],
            TaskComplexity.MODERATE: [
                "moderate",
                "some complexity",
                "research needed",
                "integration",
            ],
            TaskComplexity.COMPLEX: [
                "complex",
                "challenging",
                "multiple approaches",
                "architectural",
            ],
            TaskComplexity.VERY_COMPLEX: [
                "very complex",
                "high complexity",
                "innovative",
                "cutting-edge",
            ],
        }

    async def breakdown_task(
        self, task_data: Dict[str, Any], user_id: str, force_breakdown: bool = False
    ) -> TaskBreakdownResult:
        """Break down a task into atomic, shippable units"""
        try:
            self.logger.info(f"Breaking down task: {task_data.get('title', 'Unknown')}")

            # Analyze task to determine if breakdown is needed
            needs_breakdown = await self._analyze_task_needs_breakdown(task_data)

            if not needs_breakdown and not force_breakdown:
                # Task is already atomic
                atomic_task = await self._create_single_atomic_task(task_data)
                return TaskBreakdownResult(
                    parent_task_id=task_data.get("id", "unknown"),
                    atomic_tasks=[atomic_task],
                    breakdown_reasoning="Task is already appropriately sized for atomic execution",
                    estimated_total_time=atomic_task.estimated_minutes,
                    risk_assessment={"level": "low", "risks": []},
                    suggested_approach="Execute as single atomic task",
                )

            # Perform intelligent task breakdown
            breakdown = await self._perform_task_breakdown(task_data, user_id)

            # Validate breakdown quality
            validated_breakdown = await self._validate_breakdown_quality(
                breakdown, task_data
            )

            # Store breakdown result
            await self._store_breakdown_result(validated_breakdown, user_id)

            self.logger.info(
                f"Successfully broke down task into {len(validated_breakdown.atomic_tasks)} atomic tasks"
            )
            return validated_breakdown

        except Exception as e:
            self.logger.error(f"Error breaking down task: {e}")
            raise

    async def _analyze_task_needs_breakdown(self, task_data: Dict[str, Any]) -> bool:
        """Analyze if a task needs to be broken down"""
        try:
            title = task_data.get("title", "")
            description = task_data.get("description", "")
            estimated_duration = task_data.get("expectedDuration", 0)

            # Check estimated duration (convert minutes to hours for analysis)
            estimated_hours = estimated_duration / 60 if estimated_duration else 0

            # Tasks over 2 hours likely need breakdown
            if estimated_hours > 2:
                return True

            # Analyze task description for complexity indicators
            complexity_indicators = [
                "multiple",
                "several",
                "various",
                "complex",
                "large",
                "major",
                "architectural",
                "system",
                "integration",
                "migration",
                "refactor",
                "redesign",
                "rebuild",
                "overhaul",
                "comprehensive",
            ]

            text_to_analyze = f"{title} {description}".lower()
            complexity_count = sum(
                1 for indicator in complexity_indicators if indicator in text_to_analyze
            )

            # Tasks with multiple complexity indicators need breakdown
            if complexity_count >= 3:
                return True

            # Check for explicit breakdown requests
            breakdown_keywords = ["break down", "split into", "divide into", "separate"]
            if any(keyword in text_to_analyze for keyword in breakdown_keywords):
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error analyzing task breakdown needs: {e}")
            return False

    async def _create_single_atomic_task(self, task_data: Dict[str, Any]) -> AtomicTask:
        """Create a single atomic task from task data"""
        try:
            task_id = task_data.get("id", f"task_{uuid.uuid4().hex[:8]}")
            estimated_minutes = task_data.get("expectedDuration", 30)

            # Determine size based on duration
            if estimated_minutes <= 30:
                size = TaskSize.TINY
            elif estimated_minutes <= 60:
                size = TaskSize.SMALL
            elif estimated_minutes <= 120:
                size = TaskSize.MEDIUM
            else:
                size = TaskSize.LARGE

            return AtomicTask(
                id=f"atomic_{uuid.uuid4().hex[:8]}",
                parent_task_id=task_id,
                title=task_data.get("title", "Task"),
                description=task_data.get("description", ""),
                size=size,
                complexity=TaskComplexity.SIMPLE,
                estimated_minutes=estimated_minutes,
                acceptance_criteria=["Task completed successfully"],
                dependencies=[],
                deliverables=["Task implementation"],
                testing_requirements=["Basic functionality test"],
                priority_score=1.0,
                order=1,
            )

        except Exception as e:
            self.logger.error(f"Error creating single atomic task: {e}")
            raise

    async def _perform_task_breakdown(
        self, task_data: Dict[str, Any], user_id: str
    ) -> TaskBreakdownResult:
        """Perform intelligent task breakdown using LLM"""
        try:
            # Prepare context for LLM
            context = {
                "title": task_data.get("title", ""),
                "description": task_data.get("description", ""),
                "type": task_data.get("type", ""),
                "priority": task_data.get("priority", ""),
                "estimated_duration": task_data.get("expectedDuration", 0),
                "project_context": task_data.get("project", ""),
                "user_id": user_id,
            }

            # Get project context if available
            project_context = await self._get_project_context(
                task_data.get("project_id")
            )

            system_prompt = """
            You are an expert project manager and software architect specializing in breaking down complex tasks into atomic, shippable units.

            Your goal is to decompose large, complex tasks into small, focused, independently shippable units that follow these principles:

            1. **Atomic Principle**: Each task should be independently valuable and shippable
            2. **Size Principle**: Tasks should be 15-120 minutes (prefer 30-60 minutes)
            3. **Dependency Principle**: Minimize dependencies between tasks
            4. **Testability Principle**: Each task should have clear acceptance criteria
            5. **Value Principle**: Each task should deliver measurable value

            For each atomic task, provide:
            - Clear, actionable title (imperative mood: "Add user authentication", not "Adding user auth")
            - Detailed description of what to implement
            - Realistic time estimate (15-120 minutes)
            - Specific acceptance criteria
            - Dependencies on other tasks
            - Expected deliverables
            - Testing requirements

            Focus on creating tasks that can be completed in a single focused session.
            """

            human_prompt = f"""
            Break down this task into atomic, shippable units:

            **Task Title:** {context["title"]}
            **Description:** {context["description"]}
            **Type:** {context["type"]}
            **Priority:** {context["priority"]}
            **Estimated Duration:** {context["estimated_duration"]} minutes
            **Project Context:** {project_context}

            Provide a detailed breakdown with the following structure:

            1. **Breakdown Reasoning**: Explain your approach to decomposing this task
            2. **Atomic Tasks**: List each atomic task with all required details
            3. **Dependencies**: Show how tasks depend on each other
            4. **Risk Assessment**: Identify potential risks and mitigation strategies
            5. **Suggested Approach**: Recommended order and strategy for implementation

            Ensure each atomic task can be completed in 15-120 minutes and has clear acceptance criteria.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse the response and create structured breakdown
            breakdown = await self._parse_breakdown_response(
                response.content, task_data
            )

            return breakdown

        except Exception as e:
            self.logger.error(f"Error performing task breakdown: {e}")
            raise

    async def _parse_breakdown_response(
        self, response_text: str, task_data: Dict[str, Any]
    ) -> TaskBreakdownResult:
        """Parse LLM response into structured breakdown"""
        try:
            parent_task_id = task_data.get("id", f"task_{uuid.uuid4().hex[:8]}")

            # Extract breakdown reasoning
            reasoning = self._extract_section(
                response_text, "Breakdown Reasoning", "Atomic Tasks"
            )

            # Extract atomic tasks (this is a simplified parsing - in production would be more robust)
            tasks_section = self._extract_section(
                response_text, "Atomic Tasks", "Dependencies"
            )

            # Parse individual tasks
            atomic_tasks = []
            task_blocks = self._split_task_blocks(tasks_section)

            for i, task_block in enumerate(task_blocks):
                atomic_task = await self._parse_atomic_task(
                    task_block, parent_task_id, i + 1
                )
                if atomic_task:
                    atomic_tasks.append(atomic_task)

            # If no tasks were parsed, create a fallback
            if not atomic_tasks:
                atomic_tasks = [await self._create_single_atomic_task(task_data)]

            # Calculate total time
            total_time = sum(task.estimated_minutes for task in atomic_tasks)

            # Extract risk assessment
            risk_section = self._extract_section(
                response_text, "Risk Assessment", "Suggested Approach"
            )
            risk_assessment = self._parse_risk_assessment(risk_section)

            # Extract suggested approach
            approach_section = self._extract_section(
                response_text, "Suggested Approach", ""
            )
            suggested_approach = (
                approach_section
                or "Execute tasks in order, completing dependencies first"
            )

            return TaskBreakdownResult(
                parent_task_id=parent_task_id,
                atomic_tasks=atomic_tasks,
                breakdown_reasoning=reasoning
                or "Task broken down into atomic units for focused execution",
                estimated_total_time=total_time,
                risk_assessment=risk_assessment,
                suggested_approach=suggested_approach,
            )

        except Exception as e:
            self.logger.error(f"Error parsing breakdown response: {e}")
            # Return fallback breakdown
            fallback_task = await self._create_single_atomic_task(task_data)
            return TaskBreakdownResult(
                parent_task_id=task_data.get("id", "unknown"),
                atomic_tasks=[fallback_task],
                breakdown_reasoning="Fallback breakdown due to parsing error",
                estimated_total_time=fallback_task.estimated_minutes,
                risk_assessment={
                    "level": "medium",
                    "risks": ["Parsing error occurred"],
                },
                suggested_approach="Execute as single task",
            )

    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        """Extract a section from text between markers"""
        try:
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return ""

            start_idx += len(start_marker)
            if end_marker:
                end_idx = text.find(end_marker, start_idx)
                if end_idx == -1:
                    return text[start_idx:].strip()
                return text[start_idx:end_idx].strip()
            else:
                return text[start_idx:].strip()

        except Exception:
            return ""

    def _split_task_blocks(self, tasks_text: str) -> List[str]:
        """Split task text into individual task blocks"""
        # Simple splitting by numbered items or bullet points
        lines = tasks_text.split("\n")
        tasks = []
        current_task = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a new task (numbered or bulleted)
            if re.match(r"^\d+\.|\*\s*|-", line):
                if current_task:
                    tasks.append("\n".join(current_task))
                    current_task = []
                current_task.append(line)
            elif current_task:
                current_task.append(line)

        if current_task:
            tasks.append("\n".join(current_task))

        return tasks

    async def _parse_atomic_task(
        self, task_block: str, parent_task_id: str, order: int
    ) -> Optional[AtomicTask]:
        """Parse a single atomic task from text block"""
        try:
            lines = task_block.split("\n")
            title = ""
            description = ""
            estimated_minutes = 30
            acceptance_criteria = []
            dependencies = []
            deliverables = []
            testing_requirements = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Extract title
                if line.startswith(("1.", "2.", "3.", "*", "-")):
                    title = line.lstrip("123.*- ").strip()
                elif "title:" in line.lower():
                    title = line.split(":", 1)[1].strip()
                elif "description:" in line.lower():
                    description = line.split(":", 1)[1].strip()
                elif "time:" in line.lower() or "duration:" in line.lower():
                    time_str = line.split(":", 1)[1].strip()
                    # Extract number from time string
                    time_match = re.search(r"(\d+)", time_str)
                    if time_match:
                        estimated_minutes = int(time_match.group(1))
                elif "acceptance:" in line.lower() or "criteria:" in line.lower():
                    criteria_text = line.split(":", 1)[1].strip()
                    acceptance_criteria.append(criteria_text)
                elif "dependencies:" in line.lower():
                    deps_text = line.split(":", 1)[1].strip()
                    dependencies.extend(
                        [d.strip() for d in deps_text.split(",") if d.strip()]
                    )
                elif "deliverables:" in line.lower():
                    deliv_text = line.split(":", 1)[1].strip()
                    deliverables.append(deliv_text)
                elif "testing:" in line.lower():
                    test_text = line.split(":", 1)[1].strip()
                    testing_requirements.append(test_text)

            if not title:
                return None

            # Determine size based on estimated time
            if estimated_minutes <= 30:
                size = TaskSize.TINY
            elif estimated_minutes <= 60:
                size = TaskSize.SMALL
            elif estimated_minutes <= 120:
                size = TaskSize.MEDIUM
            else:
                size = TaskSize.LARGE

            # Determine complexity (simplified)
            complexity = TaskComplexity.MODERATE
            if estimated_minutes <= 30:
                complexity = TaskComplexity.SIMPLE
            elif estimated_minutes >= 120:
                complexity = TaskComplexity.COMPLEX

            return AtomicTask(
                id=f"atomic_{uuid.uuid4().hex[:8]}",
                parent_task_id=parent_task_id,
                title=title,
                description=description,
                size=size,
                complexity=complexity,
                estimated_minutes=estimated_minutes,
                acceptance_criteria=acceptance_criteria
                or ["Task completed successfully"],
                dependencies=dependencies,
                deliverables=deliverables or ["Implementation completed"],
                testing_requirements=testing_requirements
                or ["Basic functionality verified"],
                priority_score=1.0 - (order * 0.1),  # Higher priority for earlier tasks
                order=order,
            )

        except Exception as e:
            self.logger.error(f"Error parsing atomic task: {e}")
            return None

    def _parse_risk_assessment(self, risk_text: str) -> Dict[str, Any]:
        """Parse risk assessment from text"""
        try:
            risk_assessment = {
                "level": "medium",
                "risks": [],
                "mitigation_strategies": [],
            }

            if not risk_text:
                return risk_assessment

            # Simple parsing
            lines = risk_text.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "high" in line.lower():
                    risk_assessment["level"] = "high"
                elif "low" in line.lower():
                    risk_assessment["level"] = "low"

                if "risk" in line.lower():
                    risk_assessment["risks"].append(line)
                elif "mitigation" in line.lower() or "strategy" in line.lower():
                    risk_assessment["mitigation_strategies"].append(line)

            return risk_assessment

        except Exception as e:
            self.logger.error(f"Error parsing risk assessment: {e}")
            return {"level": "medium", "risks": [], "mitigation_strategies": []}

    async def _validate_breakdown_quality(
        self, breakdown: TaskBreakdownResult, original_task: Dict[str, Any]
    ) -> TaskBreakdownResult:
        """Validate the quality of the task breakdown"""
        try:
            issues = []

            # Check total time vs original estimate
            original_minutes = original_task.get("expectedDuration", 0)
            if original_minutes > 0:
                total_breakdown_time = breakdown.estimated_total_time
                time_ratio = total_breakdown_time / original_minutes

                if time_ratio > 1.5:
                    issues.append(
                        f"Breakdown time ({total_breakdown_time}min) significantly exceeds original estimate ({original_minutes}min)"
                    )
                elif time_ratio < 0.5:
                    issues.append(
                        f"Breakdown time ({total_breakdown_time}min) is much less than original estimate ({original_minutes}min)"
                    )

            # Check task sizes
            oversized_tasks = [
                t for t in breakdown.atomic_tasks if t.estimated_minutes > 120
            ]
            if oversized_tasks:
                issues.append(f"{len(oversized_tasks)} tasks exceed 120-minute limit")

            # Check for missing acceptance criteria
            tasks_without_criteria = [
                t for t in breakdown.atomic_tasks if not t.acceptance_criteria
            ]
            if tasks_without_criteria:
                issues.append(
                    f"{len(tasks_without_criteria)} tasks missing acceptance criteria"
                )

            # Add validation notes to reasoning
            if issues:
                breakdown.breakdown_reasoning += f"\n\nValidation Notes:\n" + "\n".join(
                    f"- {issue}" for issue in issues
                )

            return breakdown

        except Exception as e:
            self.logger.error(f"Error validating breakdown quality: {e}")
            return breakdown

    async def _get_project_context(self, project_id: Optional[str]) -> str:
        """Get project context for better task breakdown"""
        try:
            if not project_id:
                return "No specific project context available"

            # This would query project details from Firebase
            # For now, return generic context
            return "General software development project"

        except Exception as e:
            self.logger.error(f"Error getting project context: {e}")
            return "Project context unavailable"

    async def _store_breakdown_result(
        self, breakdown: TaskBreakdownResult, user_id: str
    ):
        """Store task breakdown result"""
        try:
            data = breakdown.dict()
            data["created_at"] = data["created_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"task_breakdowns/{user_id}/{breakdown.parent_task_id}",
                json.dumps(data, indent=2, default=str),
            )

        except Exception as e:
            self.logger.error(f"Error storing breakdown result: {e}")

    async def get_task_breakdown(
        self, task_id: str, user_id: str
    ) -> Optional[TaskBreakdownResult]:
        """Retrieve a stored task breakdown"""
        try:
            # This would query Firebase
            return None

        except Exception as e:
            self.logger.error(f"Error getting task breakdown: {e}")
            return None

    async def suggest_task_improvements(
        self, task_data: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Suggest improvements to make a task more atomic"""
        try:
            suggestions = {
                "is_atomic": False,
                "improvements": [],
                "estimated_improvement": 0,
                "reasoning": "",
            }

            # Analyze task for atomicity
            title = task_data.get("title", "")
            description = task_data.get("description", "")
            estimated_duration = task_data.get("expectedDuration", 0)

            # Check size
            if estimated_duration > 120:
                suggestions["improvements"].append(
                    "Break into smaller tasks (under 2 hours each)"
                )
                suggestions["estimated_improvement"] += 30

            # Check complexity indicators
            text = f"{title} {description}".lower()
            complexity_words = [
                "multiple",
                "several",
                "various",
                "complex",
                "integration",
                "system",
            ]
            complexity_count = sum(1 for word in complexity_words if word in text)

            if complexity_count >= 2:
                suggestions["improvements"].append(
                    "Separate concerns into distinct tasks"
                )
                suggestions["estimated_improvement"] += 25

            # Check for unclear scope
            vague_words = ["etc", "various", "some", "maybe", "possibly"]
            vague_count = sum(1 for word in vague_words if word in text)

            if vague_count >= 2:
                suggestions["improvements"].append(
                    "Define specific, measurable deliverables"
                )
                suggestions["estimated_improvement"] += 20

            # Determine if already atomic
            suggestions["is_atomic"] = len(suggestions["improvements"]) == 0

            if suggestions["is_atomic"]:
                suggestions["reasoning"] = (
                    "Task appears to be appropriately sized and scoped"
                )
            else:
                suggestions["reasoning"] = (
                    f"Task could be improved by addressing {len(suggestions['improvements'])} issues"
                )

            return suggestions

        except Exception as e:
            self.logger.error(f"Error suggesting task improvements: {e}")
            return {
                "is_atomic": True,
                "improvements": [],
                "estimated_improvement": 0,
                "reasoning": "Unable to analyze task",
            }


# Global service instance
_atomic_tasking_engine = None


def get_atomic_tasking_engine(openai_api_key: str) -> AtomicTaskingEngine:
    """Get singleton atomic tasking engine"""
    global _atomic_tasking_engine
    if _atomic_tasking_engine is None:
        _atomic_tasking_engine = AtomicTaskingEngine(openai_api_key)
    return _atomic_tasking_engine
