"""
AI Execution Engine
Leverages LangGraph agents for intelligent task guidance and execution
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from services.firebase_service import get_firebase_service
from services.agent_orchestrator_http import get_http_agent_orchestrator
from services.atomic_tasking import get_atomic_tasking_engine
from services.git_integration import get_git_integration_service


class GuidanceType(str, Enum):
    """Types of AI guidance"""

    TASK_BREAKDOWN = "task_breakdown"
    NEXT_STEPS = "next_steps"
    BLOCKER_RESOLUTION = "blocker_resolution"
    CODE_REVIEW = "code_review"
    TIME_ESTIMATE = "time_estimate"
    PRIORITY_SUGGESTION = "priority_suggestion"


class ExecutionConfidence(str, Enum):
    """AI confidence levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


@dataclass
class TaskGuidance:
    """AI-generated task guidance"""

    guidance_id: str
    task_id: str
    guidance_type: GuidanceType
    content: str
    confidence: ExecutionConfidence
    reasoning: str
    suggestions: List[str]
    estimated_impact: float  # 0-1 scale
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ExecutionSuggestion:
    """Specific execution suggestion"""

    suggestion_id: str
    task_id: str
    title: str
    description: str
    action_type: str  # break_down, start_focus, resolve_blocker, etc.
    priority: int  # 1-10
    estimated_time: int  # minutes
    success_probability: float  # 0-1
    prerequisites: List[str]
    expected_outcome: str


@dataclass
class TaskAnalysis:
    """Comprehensive task analysis"""

    task_id: str
    complexity_score: float  # 0-1
    estimated_duration: int  # minutes
    risk_level: str  # low, medium, high
    required_skills: List[str]
    potential_blockers: List[str]
    recommended_approach: str
    success_criteria: List[str]
    alternative_approaches: List[Dict[str, Any]]
    confidence_score: float  # 0-1


class AIExecutionEngine:
    """AI-powered execution engine using LangGraph agents"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.agent_orchestrator = get_http_agent_orchestrator()
        self.atomic_tasking = get_atomic_tasking_engine(openai_api_key)
        self.git_integration = get_git_integration_service()

        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,  # Balanced creativity and consistency
            max_tokens=2000,
            openai_api_key=openai_api_key,
        )

        # Agent specializations for different guidance types
        self.agent_mappings = {
            GuidanceType.TASK_BREAKDOWN: "strategy_agent",  # For planning
            GuidanceType.NEXT_STEPS: "devops_agent",  # For execution
            GuidanceType.BLOCKER_RESOLUTION: "ceo_agent",  # For problem solving
            GuidanceType.CODE_REVIEW: "devops_agent",  # For technical review
            GuidanceType.TIME_ESTIMATE: "strategy_agent",  # For planning
            GuidanceType.PRIORITY_SUGGESTION: "ceo_agent",  # For prioritization
        }

    async def analyze_task(
        self, task_data: Dict[str, Any], user_id: str
    ) -> TaskAnalysis:
        """Perform comprehensive AI analysis of a task"""
        try:
            self.logger.info(f"Analyzing task: {task_data.get('title', 'Unknown')}")

            # Get existing atomic breakdown if available
            breakdown = await self.atomic_tasking.get_task_breakdown(
                task_data.get("id", ""), user_id
            )

            # Perform AI analysis
            analysis = await self._perform_task_analysis(task_data, breakdown, user_id)

            # Store analysis
            await self._store_task_analysis(analysis, user_id)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing task: {e}")
            raise

    async def get_task_guidance(
        self,
        task_id: str,
        guidance_type: GuidanceType,
        context: Dict[str, Any],
        user_id: str,
    ) -> TaskGuidance:
        """Get AI guidance for a specific task and context"""
        try:
            self.logger.info(
                f"Getting {guidance_type.value} guidance for task {task_id}"
            )

            # Get task data
            task_data = await self._get_task_data(task_id)
            if not task_data:
                raise ValueError("Task not found")

            # Generate guidance using appropriate agent
            guidance = await self._generate_guidance(
                task_data, guidance_type, context, user_id
            )

            # Store guidance
            await self._store_guidance(guidance, user_id)

            return guidance

        except Exception as e:
            self.logger.error(f"Error getting task guidance: {e}")
            raise

    async def get_execution_suggestions(
        self, task_id: str, user_id: str
    ) -> List[ExecutionSuggestion]:
        """Get prioritized execution suggestions for a task"""
        try:
            # Get task data and current status
            task_data = await self._get_task_data(task_id)
            if not task_data:
                return []

            # Analyze current situation
            current_status = await self._analyze_current_situation(task_id, user_id)

            # Generate suggestions based on status
            suggestions = await self._generate_execution_suggestions(
                task_data, current_status, user_id
            )

            # Prioritize suggestions
            suggestions.sort(key=lambda x: x.priority, reverse=True)

            return suggestions[:5]  # Top 5 suggestions

        except Exception as e:
            self.logger.error(f"Error getting execution suggestions: {e}")
            return []

    async def predict_task_outcome(
        self, task_data: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Predict task outcome and success probability"""
        try:
            prediction = {
                "success_probability": 0.0,
                "estimated_duration": 0,
                "risk_factors": [],
                "success_factors": [],
                "recommended_actions": [],
                "alternative_approaches": [],
            }

            # Analyze task characteristics
            complexity = await self._assess_task_complexity(task_data)
            user_history = await self._get_user_performance_history(user_id)
            similar_tasks = await self._find_similar_tasks(task_data, user_id)

            # Calculate success probability
            base_probability = 0.7  # Base success rate

            # Adjust for complexity
            if complexity["level"] == "high":
                base_probability -= 0.2
            elif complexity["level"] == "low":
                base_probability += 0.1

            # Adjust for user history
            if user_history.get("success_rate", 0.7) < 0.6:
                base_probability -= 0.15
            elif user_history.get("success_rate", 0.7) > 0.8:
                base_probability += 0.1

            # Adjust for similar task performance
            if similar_tasks:
                similar_success_rate = sum(
                    t.get("success", False) for t in similar_tasks
                ) / len(similar_tasks)
                base_probability = (base_probability + similar_success_rate) / 2

            prediction["success_probability"] = max(0.1, min(0.95, base_probability))

            # Generate risk factors
            prediction["risk_factors"] = await self._identify_risk_factors(
                task_data, complexity
            )

            # Generate success factors
            prediction["success_factors"] = await self._identify_success_factors(
                task_data, user_history
            )

            # Generate recommendations
            prediction["recommended_actions"] = await self._generate_recommendations(
                prediction
            )

            return prediction

        except Exception as e:
            self.logger.error(f"Error predicting task outcome: {e}")
            return {"error": str(e)}

    async def optimize_execution_plan(
        self,
        tasks: List[Dict[str, Any]],
        user_id: str,
        time_available: int,  # minutes
    ) -> Dict[str, Any]:
        """Optimize execution plan for multiple tasks"""
        try:
            optimization = {
                "recommended_order": [],
                "estimated_completion_time": 0,
                "parallel_opportunities": [],
                "bottlenecks": [],
                "time_allocations": {},
                "success_probability": 0.0,
            }

            if not tasks:
                return optimization

            # Analyze task dependencies and priorities
            task_analysis = []
            for task in tasks:
                analysis = await self.analyze_task(task, user_id)
                task_analysis.append({"task": task, "analysis": analysis})

            # Optimize order based on dependencies, priorities, and time estimates
            ordered_tasks = await self._optimize_task_order(
                task_analysis, time_available
            )

            optimization["recommended_order"] = [t["task"]["id"] for t in ordered_tasks]

            # Calculate total time
            total_time = sum(t["analysis"].estimated_duration for t in ordered_tasks)
            optimization["estimated_completion_time"] = total_time

            # Identify parallel opportunities
            optimization[
                "parallel_opportunities"
            ] = await self._identify_parallel_opportunities(ordered_tasks)

            # Identify bottlenecks
            optimization["bottlenecks"] = await self._identify_bottlenecks(
                ordered_tasks
            )

            # Allocate time
            optimization["time_allocations"] = {
                t["task"]["id"]: t["analysis"].estimated_duration for t in ordered_tasks
            }

            # Calculate overall success probability
            success_probs = [t["analysis"].confidence_score for t in ordered_tasks]
            optimization["success_probability"] = (
                sum(success_probs) / len(success_probs) if success_probs else 0.0
            )

            return optimization

        except Exception as e:
            self.logger.error(f"Error optimizing execution plan: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _perform_task_analysis(
        self, task_data: Dict[str, Any], breakdown: Optional[Any], user_id: str
    ) -> TaskAnalysis:
        """Perform comprehensive task analysis"""
        try:
            task_id = task_data.get("id", f"task_{uuid.uuid4().hex[:8]}")

            # Use LLM for analysis
            system_prompt = """
            You are an expert project manager and software engineer analyzing a task for execution planning.

            Analyze the task and provide:
            1. Complexity score (0-1, where 1 is most complex)
            2. Estimated duration in minutes
            3. Risk level (low, medium, high)
            4. Required skills and expertise
            5. Potential blockers or challenges
            6. Recommended approach
            7. Success criteria
            8. Alternative approaches
            9. Confidence score (0-1)

            Be specific and actionable in your analysis.
            """

            human_prompt = f"""
            Analyze this task for execution:

            Title: {task_data.get("title", "")}
            Description: {task_data.get("description", "")}
            Type: {task_data.get("type", "")}
            Priority: {task_data.get("priority", "")}
            Estimated Duration: {task_data.get("expectedDuration", 0)} minutes

            Break down available: {breakdown is not None}

            Provide detailed analysis with specific recommendations.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse response (simplified parsing)
            analysis_text = response.content

            # Extract metrics (simplified - would use more robust parsing)
            complexity_score = 0.5
            estimated_duration = task_data.get("expectedDuration", 60)
            risk_level = "medium"
            confidence_score = 0.7

            if "high" in analysis_text.lower():
                if "complexity" in analysis_text.lower():
                    complexity_score = 0.8
                if "risk" in analysis_text.lower():
                    risk_level = "high"

            if "low" in analysis_text.lower():
                if "complexity" in analysis_text.lower():
                    complexity_score = 0.3
                if "risk" in analysis_text.lower():
                    risk_level = "low"

            # Extract skills and blockers (simplified)
            required_skills = ["problem_solving", "technical_skills"]
            potential_blockers = ["unclear_requirements", "dependencies"]
            recommended_approach = (
                "Break down into smaller tasks and execute iteratively"
            )
            success_criteria = ["Task completed", "Quality standards met"]
            alternative_approaches = [
                {"name": "Agile approach", "description": "Iterative development"}
            ]

            return TaskAnalysis(
                task_id=task_id,
                complexity_score=complexity_score,
                estimated_duration=estimated_duration,
                risk_level=risk_level,
                required_skills=required_skills,
                potential_blockers=potential_blockers,
                recommended_approach=recommended_approach,
                success_criteria=success_criteria,
                alternative_approaches=alternative_approaches,
                confidence_score=confidence_score,
            )

        except Exception as e:
            self.logger.error(f"Error performing task analysis: {e}")
            # Return default analysis
            return TaskAnalysis(
                task_id=task_data.get("id", "unknown"),
                complexity_score=0.5,
                estimated_duration=60,
                risk_level="medium",
                required_skills=["general"],
                potential_blockers=["unknown"],
                recommended_approach="Execute task according to requirements",
                success_criteria=["Task completed successfully"],
                alternative_approaches=[],
                confidence_score=0.5,
            )

    async def _generate_guidance(
        self,
        task_data: Dict[str, Any],
        guidance_type: GuidanceType,
        context: Dict[str, Any],
        user_id: str,
    ) -> TaskGuidance:
        """Generate AI guidance using appropriate agent"""
        try:
            guidance_id = f"guidance_{uuid.uuid4().hex[:8]}"

            # Select appropriate agent
            agent_type = self.agent_mappings.get(guidance_type, "ceo_agent")

            # Prepare agent request
            agent_request = {
                "task": task_data,
                "guidance_type": guidance_type.value,
                "context": context,
                "user_id": user_id,
            }

            # Call agent orchestrator
            try:
                agent_response = await self.agent_orchestrator.process_request(
                    agent_type, agent_request, user_id
                )
                content = agent_response.get("guidance", "No guidance available")
                confidence = ExecutionConfidence(
                    agent_response.get("confidence", "medium")
                )
                reasoning = agent_response.get("reasoning", "Agent analysis")
                suggestions = agent_response.get("suggestions", [])

            except Exception:
                # Fallback to LLM if agent fails
                (
                    content,
                    confidence,
                    reasoning,
                    suggestions,
                ) = await self._fallback_guidance_generation(
                    task_data, guidance_type, context
                )

            # Calculate estimated impact
            estimated_impact = await self._calculate_guidance_impact(
                guidance_type, confidence
            )

            return TaskGuidance(
                guidance_id=guidance_id,
                task_id=task_data.get("id", ""),
                guidance_type=guidance_type,
                content=content,
                confidence=confidence,
                reasoning=reasoning,
                suggestions=suggestions,
                estimated_impact=estimated_impact,
                created_at=datetime.now(timezone.utc),
                metadata={"agent_type": agent_type, "context": context},
            )

        except Exception as e:
            self.logger.error(f"Error generating guidance: {e}")
            raise

    async def _fallback_guidance_generation(
        self,
        task_data: Dict[str, Any],
        guidance_type: GuidanceType,
        context: Dict[str, Any],
    ) -> Tuple[str, ExecutionConfidence, str, List[str]]:
        """Fallback guidance generation using LLM"""
        try:
            prompts = {
                GuidanceType.TASK_BREAKDOWN: "Break this task into smaller, actionable steps",
                GuidanceType.NEXT_STEPS: "What should be done next for this task?",
                GuidanceType.BLOCKER_RESOLUTION: "How to resolve blockers for this task?",
                GuidanceType.CODE_REVIEW: "Code review suggestions for this task",
                GuidanceType.TIME_ESTIMATE: "Refined time estimate for this task",
                GuidanceType.PRIORITY_SUGGESTION: "Priority assessment and suggestions",
            }

            system_prompt = (
                f"You are an expert providing {guidance_type.value} guidance."
            )
            human_prompt = f"""
            Task: {task_data.get("title", "")}
            Description: {task_data.get("description", "")}
            Context: {json.dumps(context, indent=2)}

            {prompts.get(guidance_type, "Provide guidance for this task")}
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            return (
                response.content,
                ExecutionConfidence.MEDIUM,
                "LLM-generated guidance",
                ["Review and adapt suggestions", "Consider specific context"],
            )

        except Exception as e:
            self.logger.error(f"Error in fallback guidance: {e}")
            return (
                "Unable to generate guidance at this time",
                ExecutionConfidence.UNCERTAIN,
                "Error occurred",
                [],
            )

    async def _generate_execution_suggestions(
        self, task_data: Dict[str, Any], current_status: Dict[str, Any], user_id: str
    ) -> List[ExecutionSuggestion]:
        """Generate execution suggestions based on task status"""
        try:
            suggestions = []

            task_id = task_data.get("id", "")
            task_status = current_status.get("status", "pending")

            # Suggestion based on status
            if task_status == "pending":
                suggestions.append(
                    ExecutionSuggestion(
                        suggestion_id=f"sugg_{uuid.uuid4().hex[:8]}",
                        task_id=task_id,
                        title="Start Task",
                        description="Begin working on this task by creating a focus session",
                        action_type="start_focus",
                        priority=10,
                        estimated_time=15,
                        success_probability=0.9,
                        prerequisites=[],
                        expected_outcome="Task moved to in_progress status",
                    )
                )

            elif task_status == "in_progress":
                # Check for blockers
                blockers = current_status.get("blockers", [])
                if blockers:
                    suggestions.append(
                        ExecutionSuggestion(
                            suggestion_id=f"sugg_{uuid.uuid4().hex[:8]}",
                            task_id=task_id,
                            title="Resolve Blockers",
                            description=f"Address {len(blockers)} blocker(s) preventing progress",
                            action_type="resolve_blocker",
                            priority=9,
                            estimated_time=30,
                            success_probability=0.7,
                            prerequisites=[],
                            expected_outcome="Blockers resolved, progress resumed",
                        )
                    )

                # Suggest breaking down if large
                estimated_time = task_data.get("expectedDuration", 0)
                if estimated_time > 120:  # Over 2 hours
                    suggestions.append(
                        ExecutionSuggestion(
                            suggestion_id=f"sugg_{uuid.uuid4().hex[:8]}",
                            task_id=task_id,
                            title="Break Down Task",
                            description="Split large task into smaller, manageable units",
                            action_type="break_down",
                            priority=8,
                            estimated_time=20,
                            success_probability=0.8,
                            prerequisites=[],
                            expected_outcome="Task decomposed into atomic units",
                        )
                    )

            # Always suggest getting AI guidance
            suggestions.append(
                ExecutionSuggestion(
                    suggestion_id=f"sugg_{uuid.uuid4().hex[:8]}",
                    task_id=task_id,
                    title="Get AI Guidance",
                    description="Receive AI-powered suggestions for next steps",
                    action_type="get_guidance",
                    priority=5,
                    estimated_time=5,
                    success_probability=0.95,
                    prerequisites=[],
                    expected_outcome="AI guidance provided for better execution",
                )
            )

            return suggestions

        except Exception as e:
            self.logger.error(f"Error generating execution suggestions: {e}")
            return []

    async def _analyze_current_situation(
        self, task_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Analyze current task situation"""
        try:
            # This would query current task status, recent activity, etc.
            return {
                "status": "in_progress",
                "blockers": [],
                "recent_activity": [],
                "time_spent": 45,
                "progress": 0.3,
            }

        except Exception as e:
            self.logger.error(f"Error analyzing current situation: {e}")
            return {"status": "unknown", "blockers": []}

    async def _calculate_guidance_impact(
        self, guidance_type: GuidanceType, confidence: ExecutionConfidence
    ) -> float:
        """Calculate estimated impact of guidance"""
        try:
            base_impact = {
                GuidanceType.TASK_BREAKDOWN: 0.8,
                GuidanceType.NEXT_STEPS: 0.6,
                GuidanceType.BLOCKER_RESOLUTION: 0.9,
                GuidanceType.CODE_REVIEW: 0.7,
                GuidanceType.TIME_ESTIMATE: 0.5,
                GuidanceType.PRIORITY_SUGGESTION: 0.6,
            }.get(guidance_type, 0.5)

            confidence_multiplier = {
                ExecutionConfidence.HIGH: 1.0,
                ExecutionConfidence.MEDIUM: 0.8,
                ExecutionConfidence.LOW: 0.6,
                ExecutionConfidence.UNCERTAIN: 0.4,
            }.get(confidence, 0.5)

            return base_impact * confidence_multiplier

        except Exception as e:
            self.logger.error(f"Error calculating guidance impact: {e}")
            return 0.5

    async def _assess_task_complexity(
        self, task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess task complexity"""
        try:
            # Simplified complexity assessment
            estimated_time = task_data.get("expectedDuration", 60)

            if estimated_time > 240:  # 4+ hours
                level = "high"
            elif estimated_time > 60:  # 1+ hours
                level = "medium"
            else:
                level = "low"

            return {"level": level, "estimated_time": estimated_time}

        except Exception as e:
            self.logger.error(f"Error assessing task complexity: {e}")
            return {"level": "medium", "estimated_time": 60}

    async def _get_user_performance_history(self, user_id: str) -> Dict[str, Any]:
        """Get user performance history"""
        try:
            # This would query user performance data
            return {"success_rate": 0.75, "average_completion_time": 90}

        except Exception as e:
            self.logger.error(f"Error getting user performance history: {e}")
            return {"success_rate": 0.7, "average_completion_time": 60}

    async def _find_similar_tasks(
        self, task_data: Dict[str, Any], user_id: str
    ) -> List[Dict[str, Any]]:
        """Find similar tasks for comparison"""
        try:
            # This would search for similar tasks
            return []

        except Exception as e:
            self.logger.error(f"Error finding similar tasks: {e}")
            return []

    async def _identify_risk_factors(
        self, task_data: Dict[str, Any], complexity: Dict[str, Any]
    ) -> List[str]:
        """Identify risk factors"""
        try:
            risks = []

            if complexity["level"] == "high":
                risks.append("High complexity may lead to delays")

            if task_data.get("expectedDuration", 0) > 120:
                risks.append("Long duration increases context switching risk")

            if "integration" in task_data.get("description", "").lower():
                risks.append("Integration work may have external dependencies")

            return risks

        except Exception as e:
            self.logger.error(f"Error identifying risk factors: {e}")
            return []

    async def _identify_success_factors(
        self, task_data: Dict[str, Any], user_history: Dict[str, Any]
    ) -> List[str]:
        """Identify success factors"""
        try:
            factors = ["Clear requirements", "Dedicated focus time"]

            if user_history.get("success_rate", 0) > 0.8:
                factors.append("Strong track record of similar tasks")

            return factors

        except Exception as e:
            self.logger.error(f"Error identifying success factors: {e}")
            return []

    async def _generate_recommendations(self, prediction: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on prediction"""
        try:
            recommendations = []

            success_prob = prediction.get("success_probability", 0.5)

            if success_prob < 0.6:
                recommendations.append("Break task into smaller units")
                recommendations.append("Get additional guidance or support")

            if success_prob > 0.8:
                recommendations.append("Proceed with standard approach")

            recommendations.append("Schedule dedicated focus time")
            recommendations.append("Monitor progress and adjust as needed")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []

    async def _optimize_task_order(
        self, task_analysis: List[Dict[str, Any]], time_available: int
    ) -> List[Dict[str, Any]]:
        """Optimize task execution order"""
        try:
            # Sort by priority and dependencies
            sorted_tasks = sorted(
                task_analysis,
                key=lambda x: (
                    x["task"].get("priority", 5),
                    -x["analysis"].estimated_duration,  # Shorter tasks first
                ),
                reverse=True,
            )

            # Filter by available time
            optimized = []
            total_time = 0

            for task_item in sorted_tasks:
                if (
                    total_time + task_item["analysis"].estimated_duration
                    <= time_available
                ):
                    optimized.append(task_item)
                    total_time += task_item["analysis"].estimated_duration

            return optimized

        except Exception as e:
            self.logger.error(f"Error optimizing task order: {e}")
            return task_analysis

    async def _identify_parallel_opportunities(
        self, ordered_tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify tasks that can be worked on in parallel"""
        try:
            # Simple analysis - tasks with no dependencies can be parallel
            parallel = []

            for task_item in ordered_tasks:
                dependencies = task_item["analysis"].potential_blockers
                if not dependencies or len(dependencies) == 0:
                    parallel.append(task_item["task"]["title"])

            return parallel[:3]  # Top 3

        except Exception as e:
            self.logger.error(f"Error identifying parallel opportunities: {e}")
            return []

    async def _identify_bottlenecks(
        self, ordered_tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify potential bottlenecks"""
        try:
            bottlenecks = []

            for task_item in ordered_tasks:
                if task_item["analysis"].complexity_score > 0.7:
                    bottlenecks.append(f"High complexity: {task_item['task']['title']}")

                if task_item["analysis"].estimated_duration > 120:
                    bottlenecks.append(f"Long duration: {task_item['task']['title']}")

            return bottlenecks[:3]  # Top 3

        except Exception as e:
            self.logger.error(f"Error identifying bottlenecks: {e}")
            return []

    async def _store_task_analysis(self, analysis: TaskAnalysis, user_id: str):
        """Store task analysis"""
        try:
            data = asdict(analysis)

            await self.firebase_service.store_agent_file(
                f"task_analysis/{user_id}/{analysis.task_id}",
                json.dumps(data, indent=2, default=str),
            )

        except Exception as e:
            self.logger.error(f"Error storing task analysis: {e}")

    async def _store_guidance(self, guidance: TaskGuidance, user_id: str):
        """Store guidance"""
        try:
            data = asdict(guidance)
            data["created_at"] = data["created_at"].isoformat()

            await self.firebase_service.store_agent_file(
                f"task_guidance/{user_id}/{guidance.guidance_id}",
                json.dumps(data, indent=2, default=str),
            )

        except Exception as e:
            self.logger.error(f"Error storing guidance: {e}")

    async def _get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data"""
        try:
            # This would query task data
            return {
                "id": task_id,
                "title": "Sample Task",
                "description": "Sample description",
            }

        except Exception as e:
            self.logger.error(f"Error getting task data: {e}")
            return None


# Global service instance
_ai_execution_engine = None


def get_ai_execution_engine(openai_api_key: str) -> AIExecutionEngine:
    """Get singleton AI execution engine"""
    global _ai_execution_engine
    if _ai_execution_engine is None:
        _ai_execution_engine = AIExecutionEngine(openai_api_key)
    return _ai_execution_engine
