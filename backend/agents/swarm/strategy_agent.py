"""
Strategy Agent - Combined CMO/CFO agent for market analysis and financial planning
Handles business strategy, competitive analysis, market research, and financial planning
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

logger = logging.getLogger(__name__)


class StrategyAgent:
    """Strategy Agent combining CMO and CFO responsibilities"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "Strategy Agent (CMO/CFO)"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.get("model", "gpt-4"),
            temperature=config.get("temperature", 0.2),
            max_tokens=config.get("max_tokens", 2000),
            api_key=config.get("openai_api_key"),
        )

        # Initialize Tavily for web search
        self.tavily_client = TavilyClient(
            api_key=config.get("tavily_api_key")
        ) if config.get("tavily_api_key") else None

        # Strategy agent persona
        self.system_prompt = """
        You are the Strategy Agent for AutoAdmin, combining the expertise of a CMO and CFO.

        Your core responsibilities:

        AS CMO (Chief Marketing Officer):
        1. Market research and competitive analysis
        2. Brand strategy and positioning
        3. Customer acquisition and growth strategies
        4. Market trend identification
        5. Go-to-market strategy development

        AS CFO (Chief Financial Officer):
        1. Financial planning and analysis
        2. Budget allocation and optimization
        3. ROI analysis and investment decisions
        4. Risk assessment and mitigation
        5. Financial modeling and forecasting

        Your approach:
        - Use data-driven analysis and insights
        - Consider both market opportunities and financial implications
        - Provide actionable strategic recommendations
        - Balance growth objectives with financial responsibility
        - Focus on sustainable business development

        Always respond with:
        1. Strategic analysis and insights
        2. Data-driven recommendations
        3. Financial implications and ROI considerations
        4. Risk assessment and mitigation strategies
        5. Actionable next steps and timelines
        """

        self.logger.info("Strategy Agent initialized")

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a strategy-related task"""
        try:
            messages = task_input.get("messages", [])
            ceo_guidance = task_input.get("ceo_guidance", {})
            task_analysis = task_input.get("task_analysis", {})

            # Determine task type and gather data
            task_type = self._classify_strategy_task(messages)
            research_data = await self._gather_research_data(messages, task_type)

            # Build strategy prompt
            prompt = self._build_strategy_prompt(messages, ceo_guidance, task_analysis, research_data)

            # Get strategy response
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            # Parse and structure the response
            strategy_result = self._parse_strategy_response(response.content, task_type)

            return {
                "agent": "strategy",
                "task_type": task_type,
                "analysis": strategy_result,
                "research_data": research_data,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error processing strategy task: {e}")
            return {
                "agent": "strategy",
                "error": str(e),
                "task_type": "unknown",
                "analysis": {},
            }

    def _classify_strategy_task(self, messages: List) -> str:
        """Classify the type of strategy task"""
        if not messages:
            return "general_strategy"

        content = messages[-1].content.lower()

        # CMO-related keywords
        cmo_keywords = [
            "market", "customer", "competition", "brand", "marketing",
            "growth", "acquisition", "positioning", "campaign", "segmentation"
        ]

        # CFO-related keywords
        cfo_keywords = [
            "financial", "budget", "investment", "roi", "profit", "cost",
            "revenue", "funding", "valuation", "forecast", "analysis"
        ]

        cmo_score = sum(1 for keyword in cmo_keywords if keyword in content)
        cfo_score = sum(1 for keyword in cfo_keywords if keyword in content)

        if cmo_score > cfo_score:
            return "marketing_strategy"
        elif cfo_score > cmo_score:
            return "financial_strategy"
        else:
            return "business_strategy"

    async def _gather_research_data(self, messages: List, task_type: str) -> Dict[str, Any]:
        """Gather relevant research data using web search"""
        research_data = {
            "web_search_results": [],
            "market_data": {},
            "competitor_analysis": {},
        }

        if not self.tavily_client:
            return research_data

        try:
            # Extract key terms for search
            content = messages[-1].content if messages else ""
            search_query = self._extract_search_query(content, task_type)

            if search_query:
                # Perform web search
                search_results = self.tavily_client.search(
                    query=search_query,
                    search_depth="advanced",
                    max_results=5,
                    include_domains=None,
                    exclude_domains=None
                )

                research_data["web_search_results"] = search_results.get("results", [])

            self.logger.info(f"Gathered {len(research_data['web_search_results'])} research results")

        except Exception as e:
            self.logger.error(f"Error gathering research data: {e}")

        return research_data

    def _extract_search_query(self, content: str, task_type: str) -> str:
        """Extract relevant search query from content"""
        # Simple extraction - in production, use more sophisticated NLP
        content_lower = content.lower()

        if "market research" in content_lower:
            return "market trends industry analysis 2024"
        elif "competitive analysis" in content_lower:
            return "competitive landscape market share analysis"
        elif "financial planning" in content_lower:
            return "financial planning business forecast 2024"
        elif "investment analysis" in content_lower:
            return "investment opportunities ROI analysis"
        else:
            # Extract key terms from the content
            words = content_lower.split()
            key_terms = [word for word in words if len(word) > 3][:5]
            return " ".join(key_terms) if key_terms else "business strategy analysis"

    def _build_strategy_prompt(self, messages: List, ceo_guidance: Dict, task_analysis: Dict, research_data: Dict) -> str:
        """Build the strategy analysis prompt"""
        latest_message = messages[-1].content if messages else ""

        prompt = f"""
        STRATEGIC ANALYSIS REQUEST

        Task: {latest_message}

        CEO Guidance: {ceo_guidance.get('full_response', 'No specific guidance provided')}

        Task Analysis: {task_analysis}

        Research Data Available: {len(research_data.get('web_search_results', []))} web sources found

        As Strategy Agent (CMO/CFO), please provide:

        1. MARKET ANALYSIS (CMO):
           - Market size and trends
           - Competitive landscape
           - Target audience insights
           - Market opportunities and threats

        2. FINANCIAL ANALYSIS (CFO):
           - Financial implications and requirements
           - ROI analysis and projections
           - Budget recommendations
           - Financial risk assessment

        3. STRATEGIC RECOMMENDATIONS:
           - Actionable strategic initiatives
           - Implementation timeline
           - Resource requirements
           - Success metrics and KPIs

        4. RISK MITIGATION:
           - Potential risks and challenges
           - Mitigation strategies
           - Contingency planning

        Please provide specific, data-driven recommendations that align with business objectives.
        """

        return prompt

    def _parse_strategy_response(self, response_content: str, task_type: str) -> Dict[str, Any]:
        """Parse and structure the strategy response"""
        analysis = {
            "market_analysis": {},
            "financial_analysis": {},
            "recommendations": [],
            "risk_assessment": [],
            "implementation_plan": {},
            "success_metrics": [],
        }

        # Simple parsing - in production, use more sophisticated NLP
        content_lower = response_content.lower()

        # Extract key sections based on patterns
        sections = {
            "market": "market_analysis",
            "financial": "financial_analysis",
            "recommend": "recommendations",
            "risk": "risk_assessment",
            "implement": "implementation_plan",
            "metric": "success_metrics",
        }

        # For now, store the full response and basic classification
        analysis["full_analysis"] = response_content
        analysis["task_type"] = task_type
        analysis["key_insights"] = self._extract_key_insights(response_content)

        return analysis

    def _extract_key_insights(self, content: str) -> List[str]:
        """Extract key insights from the response"""
        insights = []

        # Look for bullet points or numbered lists
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # Look for bullet points, numbered lists, or key phrases
            if (line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')) or
                any(keyword in line.lower() for keyword in [
                    'key insight', 'important', 'critical', 'essential',
                    'recommend', 'should', 'must', 'consider'
                ])):
                insights.append(line)

        return insights[:10]  # Return top 10 insights

    async def get_market_analysis(self, query: str) -> Dict[str, Any]:
        """Get specific market analysis for a query"""
        try:
            if not self.tavily_client:
                return {"error": "Web search not available"}

            search_results = self.tavily_client.search(
                query=f"market analysis {query}",
                max_results=5,
                search_depth="advanced"
            )

            return {
                "query": query,
                "results": search_results.get("results", []),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error in market analysis: {e}")
            return {"error": str(e)}

    async def get_financial_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial data and provide insights"""
        try:
            prompt = f"""
            FINANCIAL ANALYSIS REQUEST

            Financial Data: {json.dumps(data, indent=2)}

            As CFO, please analyze this data and provide:
            1. Financial health assessment
            2. Key performance indicators
            3. Trends and patterns
            4. Risk factors
            5. Recommendations for improvement
            """

            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            return {
                "analysis": response.content,
                "data_summary": {
                    "metrics_provided": list(data.keys()) if isinstance(data, dict) else [],
                    "analysis_timestamp": datetime.now().isoformat(),
                }
            }

        except Exception as e:
            self.logger.error(f"Error in financial analysis: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Strategy agent"""
        return {
            "status": "healthy",
            "agent": "strategy",
            "capabilities": [
                "market_research",
                "competitive_analysis",
                "financial_planning",
                "investment_analysis",
                "budget_optimization",
                "risk_assessment"
            ],
            "services": {
                "web_search": self.tavily_client is not None,
                "llm_ready": True,
            },
            "timestamp": datetime.now().isoformat(),
        }