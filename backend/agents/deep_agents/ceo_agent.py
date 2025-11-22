"""
CEO Agent for AutoAdmin system.

This agent acts as the central orchestrator, managing task delegation,
strategic decisions, and coordination between other agents.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.types import Command

from .base import BaseAgent, AgentState, AgentType, Task, TaskStatus


class CEOAgent(BaseAgent):
    """
    CEO Agent - The central orchestrator of the AutoAdmin system.

    Responsible for:
    - Strategic decision making
    - Task delegation to specialized agents
    - Coordinating multi-agent workflows
    - Reviewing and validating agent outputs
    - Ensuring business objectives are met
    """

    def __init__(self, tools: Optional[List[Any]] = None, **kwargs):
        """Initialize the CEO agent."""
        super().__init__(
            agent_type=AgentType.CEO,
            model_name="gpt-4o-mini",
            temperature=0.3,  # Lower temperature for more consistent decisions
            max_tokens=2000,
            tools=tools or []
        )

    def _get_agent_name(self) -> str:
        """Get the agent's display name."""
        return "CEO Agent"

    def _get_agent_description(self) -> str:
        """Get the agent's description."""
        return (
            "You are the CEO orchestrator for AutoAdmin. "
            "You coordinate between Strategy and DevOps agents, make strategic decisions, "
            "delegate tasks, and ensure business objectives are met. "
            "You have a high-level view of the entire operation and make decisions "
            "based on business impact, resource constraints, and strategic priorities."
        )

    def _get_capabilities(self) -> List[str]:
        """Get the list of agent capabilities."""
        return [
            "Strategic planning and decision making",
            "Task delegation and coordination",
            "Multi-agent workflow management",
            "Business impact assessment",
            "Resource allocation and prioritization",
            "Quality control and review",
            "Cross-functional communication",
            "Performance monitoring"
        ]

    async def process_task(self, task: Task, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Process a task assigned to the CEO agent.

        Args:
            task: Task to process
            state: Current agent state

        Returns:
            Command indicating next action or agent to delegate to
        """
        try:
            # Update task status
            task.status = TaskStatus.IN_PROGRESS

            # Analyze the task requirements
            task_analysis = await self._analyze_task_requirements(task, state)

            # Determine the best agent to handle this task
            target_agent = await self._determine_task_assignment(task, task_analysis)

            if target_agent == self.agent_type:
                # CEO should handle this directly
                result = await self._execute_ceo_task(task, state)
                task.result = result
                task.status = TaskStatus.COMPLETED

                # Update state with result
                state["messages"].append(AIMessage(content=result))

                return Command(update=state, goto=END)
            else:
                # Delegate to another agent
                task.status = TaskStatus.PENDING

                # Add to task queue
                if "agent_task_queue" not in state:
                    state["agent_task_queue"] = []
                state["agent_task_queue"].append(task)

                return Command(
                    update={
                        **state,
                        "agent_task_queue": state["agent_task_queue"],
                        "current_agent": target_agent.value
                    },
                    goto=target_agent.value
                )

        except Exception as e:
            error_msg = f"Error processing CEO task: {str(e)}"
            task.error = error_msg
            task.status = TaskStatus.FAILED

            logger.error(error_msg)
            return Command(
                update={
                    **state,
                    "messages": [AIMessage(content=error_msg)]
                },
                goto=END
            )

    async def perform_routine_activities(self, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Perform routine CEO activities when no specific task is assigned.

        Args:
            state: Current agent state

        Returns:
            Command indicating next action or agent
        """
        # Perform daily strategic review
        strategic_insights = await self._perform_strategic_review(state)

        # Check for any pending issues that need attention
        pending_issues = await self._check_pending_issues(state)

        # Generate morning briefing if needed
        if await self._should_generate_morning_briefing(state):
            briefing = await self._generate_morning_briefing(state)
            strategic_insights.append(briefing)

        if strategic_insights:
            # Add insights to state
            state["messages"].append(AIMessage(
                content="\n\n".join(strategic_insights),
                name="ceo_analysis"
            ))

        # Check if any proactive tasks should be triggered
        proactive_tasks = await self._identify_proactive_tasks(state)
        if proactive_tasks:
            # Add to task queue
            if "agent_task_queue" not in state:
                state["agent_task_queue"] = []
            state["agent_task_queue"].extend(proactive_tasks)

        return Command(update=state, goto=END)

    async def _analyze_task_requirements(self, task: Task, state: AgentState) -> Dict[str, Any]:
        """Analyze task requirements and characteristics."""
        analysis = {
            "complexity": "medium",
            "priority": "medium",
            "required_capabilities": [],
            "estimated_duration": "30 minutes",
            "business_impact": "medium"
        }

        # Analyze task description for key indicators
        description_lower = task.description.lower()

        # Determine complexity
        if any(word in description_lower for word in ["complex", "comprehensive", "detailed"]):
            analysis["complexity"] = "high"
        elif any(word in description_lower for word in ["simple", "quick", "basic"]):
            analysis["complexity"] = "low"

        # Determine priority
        if any(word in description_lower for word in ["urgent", "critical", "important"]):
            analysis["priority"] = "high"
        elif any(word in description_lower for word in ["later", "eventually", "sometime"]):
            analysis["priority"] = "low"

        # Determine required capabilities
        if any(word in description_lower for word in ["code", "github", "deploy", "build", "test"]):
            analysis["required_capabilities"].append("devops")
        if any(word in description_lower for word in ["research", "analyze", "market", "trend", "finance"]):
            analysis["required_capabilities"].append("strategy")

        return analysis

    async def _determine_task_assignment(self, task: Task, analysis: Dict[str, Any]) -> AgentType:
        """Determine which agent should handle the task."""
        required_capabilities = analysis.get("required_capabilities", [])

        # Direct assignment based on capabilities
        if "devops" in required_capabilities:
            return AgentType.DEVOPS
        elif "strategy" in required_capabilities:
            return AgentType.STRATEGY

        # Assignment based on task content analysis
        description_lower = task.description.lower()

        if any(word in description_lower for word in [
            "code", "github", "pull request", "deploy", "build", "test",
            "refactor", "implement", "feature", "bug fix"
        ]):
            return AgentType.DEVOPS

        elif any(word in description_lower for word in [
            "research", "market", "trend", "analyze", "strategy", "finance",
            "competition", "report", "content", "blog", "video"
        ]):
            return AgentType.STRATEGY

        # Default: CEO handles strategic coordination tasks
        return AgentType.CEO

    async def _execute_ceo_task(self, task: Task, state: AgentState) -> str:
        """Execute a task that the CEO should handle directly."""
        # This would involve strategic decision making, coordination, etc.
        # For now, return a strategic analysis
        return f"""
CEO Analysis for: {task.description}

Based on current business context and available resources:

**Strategic Assessment:**
This task aligns with our business objectives and should be prioritized.

**Recommendations:**
1. Execute the task with current resources
2. Monitor progress and adjust strategy as needed
3. Document outcomes for future reference

**Business Impact:**
Expected impact: Medium
Timeline: {analysis.get('estimated_duration', '30 minutes')}
Risk level: Low

**Next Steps:**
The task has been analyzed and is ready for implementation.
"""

    async def _perform_strategic_review(self, state: AgentState) -> List[str]:
        """Perform daily strategic review and provide insights."""
        insights = []

        # Review current business context
        business_context = state.get("business_context", {})
        if business_context:
            insights.append("📊 **Business Context Review:** Current operations aligned with strategic objectives.")

        # Review marketing queue
        marketing_queue = state.get("marketing_queue", [])
        if marketing_queue:
            insights.append(f"📈 **Marketing Pipeline:** {len(marketing_queue)} items in queue for review.")

        # Review finance alerts
        finance_alerts = state.get("finance_alerts", [])
        if finance_alerts:
            insights.append(f"💰 **Financial Status:** {len(finance_alerts)} items requiring attention.")

        # Review DevOps context
        repo_context = state.get("repo_context", {})
        if repo_context:
            open_prs = len(state.get("open_prs", []))
            insights.append(f"🔧 **Development Status:** {open_prs} open pull requests for review.")

        return insights

    async def _check_pending_issues(self, state: AgentState) -> List[str]:
        """Check for any pending issues that need CEO attention."""
        issues = []

        # Check for stuck tasks
        task_queue = state.get("agent_task_queue", [])
        if len(task_queue) > 5:
            issues.append("⚠️ **Task Queue Alert:** High number of pending tasks. Consider resource allocation.")

        # Check for long-running processes
        last_updated = state.get("last_updated", "")
        if last_updated:
            # This would involve more sophisticated time tracking in a real implementation
            pass

        return issues

    async def _should_generate_morning_briefing(self, state: AgentState) -> bool:
        """Determine if a morning briefing should be generated."""
        # In a real implementation, this would check the time of day
        # and whether a briefing has already been generated today
        return True  # For demo purposes, always generate

    async def _generate_morning_briefing(self, state: AgentState) -> str:
        """Generate a comprehensive morning briefing."""
        briefing = "🌅 **Good Morning, Boss.**\n\n"

        # Finance section
        finance_alerts = state.get("finance_alerts", [])
        if finance_alerts:
            briefing += f"💰 **Finance:** {len(finance_alerts)} alerts require attention.\n"
            for alert in finance_alerts[:2]:  # Show top 2
                briefing += f"   • {alert}\n"

        # Marketing section
        marketing_queue = state.get("marketing_queue", [])
        if marketing_queue:
            briefing += f"📈 **Marketing:** {len(marketing_queue)} items in the pipeline.\n"

        # Development section
        open_prs = state.get("open_prs", [])
        if open_prs:
            briefing += f"🔧 **Development:** {len(open_prs)} PRs ready for review.\n"

        # Current trends
        current_trends = state.get("current_trends", [])
        if current_trends:
            briefing += f"🔥 **Trends:** {len(current_trends)} relevant trends identified.\n"

        briefing += "\n**What should we execute today?**\n"
        briefing += "Please review and provide direction on priorities."

        return briefing

    async def _identify_proactive_tasks(self, state: AgentState) -> List[Task]:
        """Identify proactive tasks that should be created."""
        tasks = []

        # Example: Create research task for trending topics
        current_trends = state.get("current_trends", [])
        if current_trends:
            task = Task(
                id=str(uuid.uuid4()),
                type=AgentType.STRATEGY,
                description=f"Research and analyze trending topics: {', '.join(current_trends[:3])}",
                parameters={"trends": current_trends[:3]},
                status=TaskStatus.PENDING,
                assigned_by="ceo_agent"
            )
            tasks.append(task)

        # Example: Create code review task if there are open PRs
        open_prs = state.get("open_prs", [])
        if len(open_prs) > 0:
            task = Task(
                id=str(uuid.uuid4()),
                type=AgentType.DEVOPS,
                description=f"Review and manage {len(open_prs)} open pull requests",
                parameters={"prs": open_prs},
                status=TaskStatus.PENDING,
                assigned_by="ceo_agent"
            )
            tasks.append(task)

        return tasks