"""
CEO Agent - Chief Executive Officer agent for strategic oversight and decision-making
Provides high-level strategic guidance, coordination, and final approval
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class CEOAgent:
    """CEO Agent for strategic oversight and decision-making"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "CEO Agent"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.get("model", "gpt-4"),
            temperature=config.get("temperature", 0.3),
            max_tokens=config.get("max_tokens", 2000),
            api_key=config.get("openai_api_key"),
        )

        # CEO persona and responsibilities
        self.system_prompt = """
        You are the CEO Agent of AutoAdmin, an AI-powered business automation system.

        Your core responsibilities:
        1. Strategic oversight and decision-making
        2. Task delegation and agent coordination
        3. Final review and approval of deliverables
        4. Ensuring alignment with business objectives
        5. Risk assessment and mitigation

        Your approach:
        - Think strategically and holistically
        - Consider business impact and ROI
        - Ensure tasks align with organizational goals
        - Provide clear guidance to other agents
        - Make decisive, informed decisions

        Always respond with:
        1. Strategic assessment
        2. Decision or recommendation
        3. Action items or delegation instructions
        4. Risk considerations
        5. Success metrics
        """

        self.logger.info("CEO Agent initialized")

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task requiring CEO-level oversight"""
        try:
            messages = task_input.get("messages", [])
            selected_agents = task_input.get("selected_agents", [])
            task_analysis = task_input.get("task_analysis", {})

            # Build the prompt
            prompt = self._build_ceo_prompt(messages, selected_agents, task_analysis)

            # Get CEO response
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            # Parse the response
            ceo_decision = self._parse_ceo_response(response.content)

            return {
                "agent": "ceo",
                "decision": ceo_decision,
                "selected_agents": selected_agents,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error processing CEO task: {e}")
            return {
                "agent": "ceo",
                "error": str(e),
                "decision": "defer",
                "selected_agents": ["strategy", "devops"],
            }

    async def final_review(self, review_input: Dict[str, Any]) -> Dict[str, Any]:
        """Provide final review and approval for completed work"""
        try:
            synthesis = review_input.get("synthesis", {})
            original_task = review_input.get("original_task", "")
            agent_contributions = review_input.get("agent_contributions", {})

            prompt = f"""
            TASK REVIEW AND FINAL APPROVAL

            Original Task: {original_task}

            Agent Contributions:
            {self._format_agent_contributions(agent_contributions)}

            Synthesis Summary:
            {synthesis.get('summary', 'No summary provided')}

            Results:
            {self._format_results(synthesis.get('results', {}))}

            Recommendations: {synthesis.get('recommendations', [])}
            Next Steps: {synthesis.get('next_steps', [])}

            Please provide:
            1. Final assessment of the work quality
            2. Approval or approval with conditions
            3. Strategic recommendations
            4. Business impact assessment
            5. Follow-up actions required
            """

            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            final_review = self._parse_final_review(response.content)

            return {
                "agent": "ceo",
                "review_type": "final_approval",
                "assessment": final_review,
                "approved": final_review.get("approval_status") == "approved",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error in final review: {e}")
            return {
                "agent": "ceo",
                "review_type": "final_approval",
                "error": str(e),
                "approved": False,
            }

    def _build_ceo_prompt(self, messages: List, selected_agents: List[str], task_analysis: Dict) -> str:
        """Build the prompt for CEO analysis and delegation"""
        latest_message = messages[-1].content if messages else ""

        prompt = f"""
        TASK DELEGATION AND STRATEGIC GUIDANCE

        Task Request: {latest_message}

        Task Analysis:
        - Complexity: {task_analysis.get('complexity', 'medium')}
        - Required Capabilities: {task_analysis.get('required_capabilities', [])}
        - Estimated Duration: {task_analysis.get('estimated_duration', 30)} minutes

        Available Agents:
        - Strategy Agent: Market analysis, financial planning, business strategy
        - DevOps Agent: Technical implementation, system architecture, deployment
        - CEO Agent: Strategic oversight, decision-making, coordination

        Recommended Agents: {selected_agents}

        As CEO, please provide:
        1. Strategic assessment of the task
        2. Decision on which agents should handle this task
        3. Specific guidance for the selected agents
        4. Success criteria and expected outcomes
        5. Any strategic considerations or risks
        """

        return prompt

    def _parse_ceo_response(self, response_content: str) -> Dict[str, Any]:
        """Parse CEO response into structured decision"""
        # Simple parsing - in production, use more sophisticated NLP
        content_lower = response_content.lower()

        decision = {
            "strategic_assessment": "",
            "decision": "delegate",
            "guidance": "",
            "risk_considerations": [],
            "success_metrics": [],
        }

        # Extract decision
        if any(word in content_lower for word in ["approve", "proceed", "execute"]):
            decision["decision"] = "approve"
        elif any(word in content_lower for word in ["strategy", "market", "financial"]):
            decision["decision"] = "delegate_to_strategy"
        elif any(word in content_lower for word in ["technical", "implement", "deploy"]):
            decision["decision"] = "delegate_to_devops"
        elif any(word in content_lower for word in ["defer", " postpone", "later"]):
            decision["decision"] = "defer"

        # Store full response for reference
        decision["full_response"] = response_content

        return decision

    def _parse_final_review(self, response_content: str) -> Dict[str, Any]:
        """Parse final review response"""
        content_lower = response_content.lower()

        review = {
            "approval_status": "approved_with_conditions",
            "quality_assessment": "",
            "strategic_recommendations": [],
            "business_impact": "",
            "follow_up_actions": [],
        }

        # Determine approval status
        if any(word in content_lower for word in ["approved", "excellent", "perfect"]):
            review["approval_status"] = "approved"
        elif any(word in content_lower for word in ["reject", "inadequate", "insufficient"]):
            review["approval_status"] = "rejected"
        elif any(word in content_lower for word in ["revise", "improve", "modify"]):
            review["approval_status"] = "approved_with_conditions"

        # Store full response
        review["full_review"] = response_content

        return review

    def _format_agent_contributions(self, contributions: Dict[str, Any]) -> str:
        """Format agent contributions for review"""
        formatted = []
        for agent, contribution in contributions.items():
            formatted.append(f"{agent.title()}: {contribution}")
        return "\n".join(formatted)

    def _format_results(self, results: Dict[str, Any]) -> str:
        """Format results for review"""
        if not results:
            return "No specific results provided"

        formatted = []
        for agent, result in results.items():
            formatted.append(f"{agent.title()} Agent Results:\n{result}")
        return "\n\n".join(formatted)

    async def health_check(self) -> Dict[str, Any]:
        """Health check for CEO agent"""
        return {
            "status": "healthy",
            "agent": "ceo",
            "capabilities": [
                "strategic_planning",
                "decision_making",
                "coordination",
                "oversight",
                "risk_assessment"
            ],
            "timestamp": datetime.now().isoformat(),
        }