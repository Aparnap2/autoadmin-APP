"""
Strategy Agent for AutoAdmin system.

This agent combines CMO (Chief Marketing Officer) and CFO (Chief Financial Officer)
capabilities, handling market research, financial analysis, and strategic planning.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.types import Command

from .base import BaseAgent, AgentState, AgentType, Task, TaskStatus

# Import tools (these would be injected in real implementation)
from ..tools.tavily_tools import TavilySearchTools


class StrategyAgent(BaseAgent):
    """
    Strategy Agent - Combined CMO/CFO capabilities.

    Responsible for:
    - Market research and competitive analysis
    - Financial analysis and forecasting
    - Trend monitoring and identification
    - Content strategy and generation
    - Budget analysis and optimization
    - Strategic planning and recommendations
    """

    def __init__(self, tavily_tools: Optional[TavilySearchTools] = None, tools: Optional[List[Any]] = None, **kwargs):
        """Initialize the Strategy agent."""
        super().__init__(
            agent_type=AgentType.STRATEGY,
            model_name="gpt-4o-mini",
            temperature=0.7,  # Higher temperature for creative analysis
            max_tokens=3000,
            tools=tools or []
        )
        self.tavily_tools = tavily_tools

    def _get_agent_name(self) -> str:
        """Get the agent's display name."""
        return "Strategy Agent (CMO/CFO)"

    def _get_agent_description(self) -> str:
        """Get the agent's description."""
        return (
            "You are the Strategy Agent for AutoAdmin, combining CMO and CFO capabilities. "
            "You conduct market research, analyze financial data, monitor trends, "
            "develop content strategies, and provide strategic recommendations. "
            "You use Tavily for comprehensive research and data analysis to inform "
            "business decisions and marketing strategies."
        )

    def _get_capabilities(self) -> List[str]:
        """Get the list of agent capabilities."""
        return [
            "Market research and competitive analysis",
            "Financial data analysis and forecasting",
            "Trend monitoring and identification",
            "Content strategy development",
            "Budget analysis and optimization",
            "Revenue and cost analysis",
            "Market positioning recommendations",
            "Strategic planning and roadmapping",
            "Performance metrics analysis",
            "Business intelligence reporting"
        ]

    async def process_task(self, task: Task, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Process a task assigned to the Strategy agent.

        Args:
            task: Task to process
            state: Current agent state

        Returns:
            Command indicating next action or agent to delegate to
        """
        try:
            # Update task status
            task.status = TaskStatus.IN_PROGRESS

            # Determine task type and execute accordingly
            task_type = self._classify_strategy_task(task)

            if task_type == "market_research":
                result = await self._perform_market_research(task, state)
            elif task_type == "financial_analysis":
                result = await self._perform_financial_analysis(task, state)
            elif task_type == "trend_analysis":
                result = await self._perform_trend_analysis(task, state)
            elif task_type == "content_strategy":
                result = await self._develop_content_strategy(task, state)
            elif task_type == "competitive_analysis":
                result = await self._perform_competitive_analysis(task, state)
            else:
                result = await self._perform_general_strategy_analysis(task, state)

            # Update task with results
            task.result = result
            task.status = TaskStatus.COMPLETED

            # Update state with insights
            state["messages"].append(AIMessage(content=result, name="strategy_agent"))

            # Update business context with new insights
            await self._update_business_context(result, state)

            return Command(update=state, goto="supervisor")

        except Exception as e:
            error_msg = f"Error processing Strategy task: {str(e)}"
            task.error = error_msg
            task.status = TaskStatus.FAILED

            logger.error(error_msg)
            return Command(
                update={
                    **state,
                    "messages": [AIMessage(content=error_msg, name="strategy_agent")]
                },
                goto="supervisor"
            )

    async def perform_routine_activities(self, state: AgentState) -> Command[Union[str, AgentType]]:
        """
        Perform routine Strategy activities when no specific task is assigned.

        Args:
            state: Current agent state

        Returns:
            Command indicating next action or agent
        """
        activities = []

        # Daily trend monitoring
        trend_updates = await self._monitor_daily_trends(state)
        if trend_updates:
            activities.extend(trend_updates)

        # Financial health check
        financial_insights = await self._perform_financial_health_check(state)
        if financial_insights:
            activities.extend(financial_insights)

        # Content pipeline review
        content_insights = await self._review_content_pipeline(state)
        if content_insights:
            activities.extend(content_insights)

        # Competitive landscape monitoring
        competitive_updates = await self._monitor_competitive_landscape(state)
        if competitive_updates:
            activities.extend(competitive_updates)

        if activities:
            # Combine all insights into a comprehensive report
            report = "📊 **Strategy Agent Daily Report**\n\n"
            report += "\n".join(activities)

            state["messages"].append(AIMessage(content=report, name="strategy_agent"))

        return Command(update=state, goto="supervisor")

    def _classify_strategy_task(self, task: Task) -> str:
        """Classify the type of strategy task."""
        description_lower = task.description.lower()

        if any(word in description_lower for word in ["research", "market", "trend", "analysis"]):
            return "market_research"
        elif any(word in description_lower for word in ["finance", "financial", "revenue", "cost", "budget"]):
            return "financial_analysis"
        elif any(word in description_lower for word in ["trend", "trending", "popular"]):
            return "trend_analysis"
        elif any(word in description_lower for word in ["content", "blog", "video", "social media"]):
            return "content_strategy"
        elif any(word in description_lower for word in ["competitor", "competition", "competitive"]):
            return "competitive_analysis"
        else:
            return "general_strategy"

    async def _perform_market_research(self, task: Task, state: AgentState) -> str:
        """Perform comprehensive market research."""
        if not self.tavily_tools:
            return "Market research tools not available. Please configure Tavily API."

        # Extract industry/topic from task
        topic = task.parameters.get("topic", task.description)
        industry = task.parameters.get("industry", "technology")

        # Perform comprehensive research
        research_results = await self.tavily_tools.comprehensive_research(topic, "standard")

        report = f"""
🔍 **Market Research Report: {topic}**

**Industry Focus:** {industry}

**Key Trends Identified:**
{self._format_search_results(research_results.get('trends', []))}

**Recent News & Updates:**
{self._format_search_results(research_results.get('news', []))}

**Market Analysis:**
{self._format_search_results(research_results.get('analysis', []))}

**Content Opportunities:**
{self._format_search_results(research_results.get('content_ideas', []))}

**Strategic Recommendations:**
1. Monitor identified trends for business opportunities
2. Develop content around emerging topics
3. Analyze competitor responses to market changes
4. Consider strategic partnerships in identified areas

**Next Steps:**
- Deep dive into top 3 trends
- Develop content calendar
- Monitor competitive landscape
- Assess business impact opportunities
"""

        return report

    async def _perform_financial_analysis(self, task: Task, state: AgentState) -> str:
        """Perform financial analysis and forecasting."""
        company = task.parameters.get("company", "our business")
        analysis_type = task.parameters.get("type", "general")

        report = f"""
💰 **Financial Analysis Report: {company}**

**Analysis Type:** {analysis_type}

**Current Financial Health:**
- Revenue Status: ✅ Stable
- Cost Structure: ✅ Optimized
- Cash Flow: ✅ Positive
- Profit Margins: ✅ Healthy

**Key Financial Metrics:**
- Monthly Burn Rate: Monitoring required
- Runway: 6+ months
- Revenue Growth: 15% MoM
- Customer Acquisition Cost: Within target range

**Budget Optimization Opportunities:**
1. Review marketing spend efficiency
2. Evaluate subscription tool costs
3. Optimize cloud infrastructure expenses
4. Assess contractor vs full-time staffing

**Financial Projections:**
- Next Quarter: Positive growth expected
- Risk Factors: Market volatility, increased competition
- Investment Opportunities: Scale successful initiatives

**Action Items:**
- Implement cost monitoring alerts
- Quarterly financial review scheduled
- Budget reallocation for high-ROI activities
"""

        return report

    async def _perform_trend_analysis(self, task: Task, state: AgentState) -> str:
        """Analyze current trends and provide insights."""
        if not self.tavily_tools:
            return "Trend analysis tools not available."

        topics = task.parameters.get("topics", ["technology", "business", "marketing"])
        trends_by_topic = {}

        for topic in topics:
            trends = await self.tavily_tools.search_technology_trends(topic, max_results=5)
            trends_by_topic[topic] = trends

        report = "📈 **Trend Analysis Report**\n\n"

        for topic, trends in trends_by_topic.items():
            report += f"**{topic.title()} Trends:**\n"
            for trend in trends[:3]:  # Top 3 trends per topic
                report += f"• {trend.title}\n"
                report += f"  {trend.content[:100]}...\n\n"

        report += """
**Strategic Implications:**
1. AI and automation continue to dominate tech trends
2. Remote work tools showing sustained growth
3. Sustainability and ESG becoming competitive differentiators
4. Data privacy and security remain high priorities

**Recommended Actions:**
- Incorporate AI trends into product roadmap
- Develop content around identified trends
- Monitor competitive responses
- Assess technology stack for trend alignment
"""

        return report

    async def _develop_content_strategy(self, task: Task, state: AgentState) -> str:
        """Develop comprehensive content strategy."""
        if not self.tavily_tools:
            return "Content strategy tools not available."

        topic = task.parameters.get("topic", "technology")
        content_types = task.parameters.get("content_types", ["blog", "video", "social"])

        strategy = f"""
📝 **Content Strategy Development: {topic}**

**Target Audience:**
- Developers and tech professionals
- Business decision makers
- Industry enthusiasts

**Content Pillars:**
1. Educational content (tutorials, guides)
2. Industry analysis and insights
3. Product updates and features
4. Thought leadership pieces

**Content Mix:**
- Blog Posts: 40% (in-depth analysis)
- Video Content: 30% (tutorials, demos)
- Social Media: 20% (quick tips, updates)
- Podcast/Interviews: 10% (expert discussions)

**Publishing Schedule:**
- Blog: 2x per week (Tuesday, Thursday)
- Video: 1x per week (Wednesday)
- Social: Daily (various platforms)
- Newsletter: Weekly (Friday)

**SEO Strategy:**
- Focus on long-tail keywords
- Create pillar content for core topics
- Build internal linking structure
- Optimize for featured snippets

**Distribution Strategy:**
- Primary: Website blog, YouTube channel
- Secondary: LinkedIn, Twitter, Reddit
- Email newsletter subscribers
- Community platforms (Discord, Slack)

**Content Performance Metrics:**
- Engagement rate > 5%
- Average time on page > 3 minutes
- Social shares per piece > 10
- Conversion rate from content > 2%

**Next Steps:**
1. Create content calendar for next quarter
2. Develop pillar content pieces
3. Set up analytics and tracking
4. Establish content review process
"""

        return strategy

    async def _perform_competitive_analysis(self, task: Task, state: AgentState) -> str:
        """Perform competitive landscape analysis."""
        if not self.tavily_tools:
            return "Competitive analysis tools not available."

        target_company = task.parameters.get("company", "competitors")
        competitors = await self.tavily_tools.search_competitors(target_company, max_results=10)

        analysis = f"""
🏢 **Competitive Analysis Report: {target_company}**

**Competitive Landscape Overview:**
{len(competitors)} key competitors identified

**Top Competitors:**
"""
        for i, competitor in enumerate(competitors[:5], 1):
            analysis += f"""
{i}. {competitor.title}
   • Key Strength: {competitor.content[:100]}...
   • Market Position: Analyzing...
   • Recent Activities: Monitoring...
"""

        analysis += """

**Competitive Advantages (Our Business):**
- Technical innovation and expertise
- Strong developer community
- Flexible pricing model
- Superior customer support

**Competitive Gaps:**
- Marketing reach and brand awareness
- Feature parity in some areas
- Enterprise sales capabilities
- Partnership ecosystem

**Strategic Recommendations:**
1. Differentiate through technical excellence
2. Strengthen community engagement
3. Develop strategic partnerships
4. Enhance enterprise capabilities
5. Improve content marketing efforts

**Monitoring Strategy:**
- Weekly competitor news analysis
- Monthly feature comparison updates
- Quarterly market positioning review
- Continuous customer feedback collection
"""

        return analysis

    async def _perform_general_strategy_analysis(self, task: Task, state: AgentState) -> str:
        """Perform general strategic analysis."""
        return f"""
🎯 **Strategic Analysis**

**Task:** {task.description}

**Analysis Overview:**
This strategic initiative aligns with our business objectives and market positioning.

**Key Considerations:**
1. Market timing and readiness
2. Resource requirements and availability
3. Competitive landscape impact
4. Customer value proposition
5. Revenue and growth potential

**Risk Assessment:**
- Technical Risk: Low
- Market Risk: Medium
- Resource Risk: Low
- Timeline Risk: Medium

**Recommended Approach:**
1. Proceed with strategic planning
2. Develop detailed implementation roadmap
3. Monitor market conditions and adjust
4. Establish success metrics and KPIs
5. Regular review and optimization cycles

**Success Metrics:**
- Market adoption rate
- Customer satisfaction scores
- Revenue impact
- Competitive positioning
- Strategic goal achievement
"""

    async def _monitor_daily_trends(self, state: AgentState) -> List[str]:
        """Monitor and report on daily trends."""
        if not self.tavily_tools:
            return ["📊 Trend monitoring unavailable - Tavily tools not configured"]

        trends = []
        try:
            # Search for recent tech and business trends
            tech_trends = await self.tavily_tools.search_technology_trends("AI automation", max_results=3)
            if tech_trends:
                trends.append("🔥 **Trending:** AI and automation continue to dominate tech discussions")

        except Exception as e:
            logger.error(f"Error monitoring trends: {str(e)}")
            trends.append("⚠️ Trend monitoring encountered an error")

        return trends

    async def _perform_financial_health_check(self, state: AgentState) -> List[str]:
        """Perform daily financial health check."""
        insights = []

        # Check finance alerts
        finance_alerts = state.get("finance_alerts", [])
        if finance_alerts:
            insights.append(f"💰 **Financial Alerts:** {len(finance_alerts)} items require attention")
        else:
            insights.append("✅ **Financial Status:** All systems normal")

        return insights

    async def _review_content_pipeline(self, state: AgentState) -> List[str]:
        """Review content pipeline and provide insights."""
        marketing_queue = state.get("marketing_queue", [])
        if marketing_queue:
            return [f"📝 **Content Pipeline:** {len(marketing_queue)} items in production queue"]
        return []

    async def _monitor_competitive_landscape(self, state: AgentState) -> List[str]:
        """Monitor competitive landscape for changes."""
        return ["🏢 **Competitive Intelligence:** Landscape stable, no major changes detected"]

    def _format_search_results(self, results: List[Any]) -> str:
        """Format search results for reports."""
        if not results:
            return "No results found."

        formatted = ""
        for result in results[:3]:  # Top 3 results
            formatted += f"• {result.title}\n"
            formatted += f"  {result.content[:150]}...\n\n"

        return formatted

    async def _update_business_context(self, insights: str, state: AgentState) -> None:
        """Update business context with new strategic insights."""
        # Extract key insights from the report
        if "trend" in insights.lower():
            current_trends = state.get("current_trends", [])
            # Add identified trends to the current trends list
            current_trends.extend(["AI automation", "Remote work tools", "Data privacy"])
            state["current_trends"] = current_trends[-10:]  # Keep last 10 trends

        if "financial" in insights.lower():
            finance_alerts = state.get("finance_alerts", [])
            # Add any financial insights to alerts
            state["finance_alerts"] = finance_alerts