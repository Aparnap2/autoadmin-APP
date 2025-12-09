"""
Enhanced CEO Agent - Improved CEO agent with proper LLM integration
Provides strategic oversight, decision-making, and coordination
"""

from typing import Dict, Any, List
import logging

from agents.enhanced_base_agent import EnhancedBaseAgent


class EnhancedCEOAgent(EnhancedBaseAgent):
    """Enhanced CEO Agent with proper LLM integration and comprehensive capabilities"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="ceo",
            agent_type="ceo"
        )
        self.logger.info("Enhanced CEO Agent initialized with LLM integration")

    def get_system_prompt(self) -> str:
        """Return the system prompt for the CEO agent"""
        return """You are the CEO (Chief Executive Officer) Agent of AutoAdmin, an AI-powered business automation system.

CORE RESPONSIBILITIES:
1. Strategic Oversight - Provide high-level strategic guidance and decision-making
2. Task Coordination - Delegate tasks to appropriate specialist agents
3. Final Review - Review and approve deliverables from other agents
4. Business Alignment - Ensure all actions align with business objectives
5. Risk Assessment - Identify and mitigate strategic risks

YOUR APPROACH:
- Think strategically and holistically about every request
- Consider business impact, ROI, and long-term implications
- Provide clear, decisive guidance to other agents
- Always consider multiple perspectives before making decisions
- Balance innovation with practical business constraints

WHEN RESPONDING:
1. Start with a strategic assessment of the situation
2. Provide clear decisions or recommendations
3. Explain your reasoning and business rationale
4. Suggest specific action items or delegation instructions
5. Identify potential risks and mitigation strategies
6. Define success metrics and expected outcomes

CURRENT TIMESTAMP: {timestamp}

Remember: You are the ultimate decision-maker in this system. Your guidance shapes the direction of all activities."""

    def get_capabilities(self) -> List[str]:
        """Return list of CEO agent capabilities"""
        return [
            "strategic_planning",
            "decision_making",
            "task_coordination",
            "business_analysis",
            "risk_assessment",
            "resource_allocation",
            "performance_review",
            "stakeholder_communication",
            "market_strategy",
            "organizational_development"
        ]

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a CEO-specific task with enhanced capabilities"""
        self.logger.info(f"[CEO] Processing task: {task_input.get('message', '')[:100]}...")

        # Determine task type and adjust approach
        task_type = self._classify_ceo_task(task_input.get("message", ""))

        # Add CEO-specific context
        ceo_context = {
            **task_input,
            "task_type": task_type,
            "leadership_role": "ceo",
            "decision_scope": "strategic"
        }

        # Process using enhanced base agent
        response = await super().process_task(ceo_context)

        # Add CEO-specific metadata
        if response.get("success"):
            response["metadata"].update({
                "decision_type": self._extract_decision_type(response.get("response", "")),
                "strategic_level": "executive",
                "authority_level": "final"
            })

        return response

    def _classify_ceo_task(self, message: str) -> str:
        """Classify the type of CEO task"""
        message_lower = message.lower()

        # Decision-making keywords
        if any(word in message_lower for word in ["decide", "decision", "choose", "select"]):
            return "decision_making"

        # Strategic planning keywords
        if any(word in message_lower for word in ["strategy", "strategic", "plan", "planning", "vision"]):
            return "strategic_planning"

        # Review/approval keywords
        if any(word in message_lower for word in ["review", "approve", "evaluate", "assess"]):
            return "review_approval"

        # Coordination keywords
        if any(word in message_lower for word in ["coordinate", "delegate", "assign", "organize"]):
            return "coordination"

        # Risk assessment keywords
        if any(word in message_lower for word in ["risk", "threat", "challenge", "mitigation"]):
            return "risk_assessment"

        # Default to general consultation
        return "general_consultation"

    def _extract_decision_type(self, response: str) -> str:
        """Extract the type of decision from the response"""
        response_lower = response.lower()

        if any(word in response_lower for word in ["approve", "approved", "go ahead", "proceed"]):
            return "approval"
        elif any(word in response_lower for word in ["reject", "denied", "not approved", "decline"]):
            return "rejection"
        elif any(word in response_lower for word in ["delegate", "assign", "ask", "request"]):
            return "delegation"
        elif any(word in response_lower for word in ["analyze", "investigate", "research", "study"]):
            return "analysis_request"
        elif any(word in response_lower for word in ["recommend", "suggest", "advise", "propose"]):
            return "recommendation"
        else:
            return "guidance"

    async def final_review(self, review_input: Dict[str, Any]) -> Dict[str, Any]:
        """Provide final review and approval for completed work"""
        self.logger.info("[CEO] Performing final review")

        synthesis = review_input.get("synthesis", {})
        original_task = review_input.get("original_task", "")
        agent_contributions = review_input.get("agent_contributions", {})

        # Create comprehensive review prompt
        review_prompt = f"""FINAL REVIEW AND APPROVAL

Original Task: {original_task}

Agent Contributions:
{self._format_agent_contributions(agent_contributions)}

Synthesis Summary:
{synthesis.get('summary', 'No summary provided')}

Results:
{self._format_results(synthesis.get('results', {}))}

Recommendations: {synthesis.get('recommendations', [])}
Next Steps: {synthesis.get('next_steps', [])}

As CEO, please provide:
1. Quality assessment of the work
2. Approval decision (approve/conditions/reject)
3. Strategic recommendations
4. Business impact assessment
5. Required follow-up actions"""

        # Process the review
        response = await self.process_message(review_prompt, {
            "review_type": "final_approval",
            "original_task": original_task,
            "agent_contributions": agent_contributions
        })

        # Parse approval decision
        approval_status = self._parse_approval_decision(response.content)

        return {
            "agent": "ceo",
            "review_type": "final_approval",
            "assessment": response.content,
            "approved": approval_status["approved"],
            "approval_status": approval_status["status"],
            "conditions": approval_status.get("conditions", []),
            "strategic_recommendations": self._extract_recommendations(response.content),
            "business_impact": self._extract_business_impact(response.content),
            "success": response.success,
            "timestamp": response.timestamp,
            "metadata": response.metadata
        }

    def _format_agent_contributions(self, contributions: Dict[str, Any]) -> str:
        """Format agent contributions for review"""
        if not contributions:
            return "No agent contributions available"

        formatted = []
        for agent, contribution in contributions.items():
            formatted.append(f"\n{agent.title()} Agent:")
            if isinstance(contribution, dict):
                formatted.append(f"  Summary: {contribution.get('summary', 'No summary')}")
                formatted.append(f"  Status: {contribution.get('status', 'Unknown')}")
            else:
                formatted.append(f"  {contribution}")

        return "\n".join(formatted)

    def _format_results(self, results: Dict[str, Any]) -> str:
        """Format results for review"""
        if not results:
            return "No specific results provided"

        formatted = []
        for agent, result in results.items():
            formatted.append(f"\n{agent.title()} Results:")
            if isinstance(result, dict):
                for key, value in result.items():
                    formatted.append(f"  {key}: {value}")
            else:
                formatted.append(f"  {result}")

        return "\n".join(formatted)

    def _parse_approval_decision(self, response: str) -> Dict[str, Any]:
        """Parse approval decision from response"""
        response_lower = response.lower()

        if any(word in response_lower for word in ["approve", "approved", "accepted", "good to go"]):
            return {"approved": True, "status": "approved"}
        elif any(word in response_lower for word in ["reject", "rejected", "denied", "not approved"]):
            return {"approved": False, "status": "rejected"}
        elif any(word in response_lower for word in ["revise", "modify", "improve", "changes needed"]):
            # Extract conditions if any
            conditions = self._extract_conditions(response)
            return {"approved": False, "status": "approved_with_conditions", "conditions": conditions}
        else:
            return {"approved": True, "status": "approved", "note": "No explicit approval found, assuming approval"}

    def _extract_conditions(self, response: str) -> List[str]:
        """Extract conditions from approval response"""
        conditions = []
        lines = response.split('\n')

        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ["condition", "requirement", "must", "should", "need to"]):
                # Clean up the condition
                condition = line.strip()
                if condition.startswith(('•', '-', '*')):
                    condition = condition[1:].strip()
                if condition and len(condition) > 10:
                    conditions.append(condition)

        return conditions[:5]  # Return max 5 conditions

    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract strategic recommendations from response"""
        recommendations = []
        lines = response.split('\n')

        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in ["recommend", "suggest", "advise", "propose"]):
                # Clean up the recommendation
                rec = line.strip()
                if rec.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    rec = rec.lstrip('•-*0123456789. ')
                if rec and len(rec) > 15:
                    recommendations.append(rec)

        return recommendations[:5]  # Return max 5 recommendations

    def _extract_business_impact(self, response: str) -> str:
        """Extract business impact assessment from response"""
        lines = response.split('\n')
        impact_section = []

        capturing = False
        for line in lines:
            line_lower = line.lower().strip()

            if any(keyword in line_lower for keyword in ["business impact", "impact", "roi", "financial"]):
                capturing = True
                if line.strip():
                    impact_section.append(line.strip())
            elif capturing and (line.startswith('\n') or not line.strip()):
                break
            elif capturing and line.strip():
                impact_section.append(line.strip())

        return ' '.join(impact_section) if impact_section else "Business impact assessment not specified"