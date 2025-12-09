"""
Enhanced Strategy Agent - Improved strategy agent with proper LLM integration
Handles market analysis, financial planning, and business strategy
"""

from typing import Dict, Any, List
import logging

from agents.enhanced_base_agent import EnhancedBaseAgent


class EnhancedStrategyAgent(EnhancedBaseAgent):
    """Enhanced Strategy Agent combining CMO and CFO responsibilities with proper LLM integration"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="strategy",
            agent_type="strategy"
        )
        self.logger.info("Enhanced Strategy Agent initialized with LLM integration")

    def get_system_prompt(self) -> str:
        """Return the system prompt for the Strategy agent"""
        return """You are the Strategy Agent for AutoAdmin, combining the expertise of a CMO (Chief Marketing Officer) and CFO (Chief Financial Officer).

DUAL ROLE RESPONSIBILITIES:

AS CMO (Chief Marketing Officer):
1. Market Research - Analyze market trends, competition, and customer behavior
2. Brand Strategy - Develop positioning and messaging strategies
3. Growth Planning - Create customer acquisition and growth strategies
4. Market Intelligence - Identify opportunities and threats in the market
5. Go-to-Market Strategy - Plan product launches and market entry

AS CFO (Chief Financial Officer):
1. Financial Planning - Develop budgets and financial forecasts
2. Investment Analysis - Evaluate ROI and investment opportunities
3. Risk Management - Identify and mitigate financial risks
4. Resource Optimization - Allocate resources for maximum efficiency
5. Performance Metrics - Track KPIs and financial health indicators

ANALYTICAL APPROACH:
- Use data-driven analysis for all recommendations
- Balance market opportunities with financial constraints
- Consider both short-term tactics and long-term strategy
- Provide actionable insights with clear implementation steps
- Always quantify financial implications where possible

WHEN RESPONDING:
1. Provide comprehensive market analysis (CMO perspective)
2. Include financial implications and ROI analysis (CFO perspective)
3. Offer data-driven recommendations with specific metrics
4. Identify risks and mitigation strategies
5. Suggest actionable next steps with timelines
6. Define success metrics and KPIs for tracking

CURRENT TIMESTAMP: {timestamp}

Remember: You provide the strategic foundation for all business decisions. Your analysis must be thorough, data-driven, and balanced between market opportunities and financial realities."""

    def get_capabilities(self) -> List[str]:
        """Return list of Strategy agent capabilities"""
        return [
            "market_research",
            "competitive_analysis",
            "financial_planning",
            "investment_analysis",
            "budget_optimization",
            "risk_assessment",
            "business_strategy",
            "growth_planning",
            "brand_strategy",
            "performance_metrics"
        ]

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a strategy-specific task with enhanced capabilities"""
        self.logger.info(f"[Strategy] Processing task: {task_input.get('message', '')[:100]}...")

        # Determine task type
        task_type = self._classify_strategy_task(task_input.get("message", ""))

        # Add strategy-specific context
        strategy_context = {
            **task_input,
            "task_type": task_type,
            "role": "cmo_cfo",
            "analysis_scope": "strategic"
        }

        # Process using enhanced base agent
        response = await super().process_task(strategy_context)

        # Add strategy-specific metadata
        if response.get("success"):
            response["metadata"].update({
                "analysis_type": task_type,
                "perspective": self._determine_primary_perspective(response.get("response", "")),
                "data_sources": self._identify_data_sources(response.get("response", "")),
                "financial_impact": self._extract_financial_impact(response.get("response", ""))
            })

        return response

    def _classify_strategy_task(self, message: str) -> str:
        """Classify the type of strategy task"""
        message_lower = message.lower()

        # Marketing/CMO keywords
        cmo_keywords = [
            "market", "customer", "competition", "brand", "marketing",
            "growth", "acquisition", "positioning", "campaign", "segmentation",
            "advertising", "pr", "content", "social media", "seo"
        ]

        # Financial/CFO keywords
        cfo_keywords = [
            "financial", "budget", "investment", "roi", "profit", "cost",
            "revenue", "funding", "valuation", "forecast", "analysis",
            "cash flow", "p&l", "break even", "margin", "expense"
        ]

        # Business strategy keywords
        strategy_keywords = [
            "strategy", "plan", "objective", "goal", "vision", "mission",
            "swot", "market entry", "expansion", "partnership", "joint venture"
        ]

        cmo_score = sum(1 for keyword in cmo_keywords if keyword in message_lower)
        cfo_score = sum(1 for keyword in cfo_keywords if keyword in message_lower)
        strategy_score = sum(1 for keyword in strategy_keywords if keyword in message_lower)

        if cmo_score > cfo_score and cmo_score > strategy_score:
            return "marketing_strategy"
        elif cfo_score > cmo_score and cfo_score > strategy_score:
            return "financial_strategy"
        elif strategy_score > 0:
            return "business_strategy"
        else:
            return "general_strategy"

    def _determine_primary_perspective(self, response: str) -> str:
        """Determine if response is primarily CMO or CFO perspective"""
        response_lower = response.lower()

        cmo_indicators = ["market", "customer", "brand", "campaign", "growth", "acquisition"]
        cfo_indicators = ["financial", "budget", "roi", "profit", "cost", "investment"]

        cmo_count = sum(1 for indicator in cmo_indicators if indicator in response_lower)
        cfo_count = sum(1 for indicator in cfo_indicators if indicator in response_lower)

        if cmo_count > cfo_count:
            return "cmo_primary"
        elif cfo_count > cmo_count:
            return "cfo_primary"
        else:
            return "balanced"

    def _identify_data_sources(self, response: str) -> List[str]:
        """Identify potential data sources mentioned in response"""
        data_sources = []
        response_lower = response.lower()

        potential_sources = {
            "market research": ["survey", "study", "research", "report"],
            "financial data": ["financial statement", "budget", "roi", "profit"],
            "competitive analysis": ["competitor", "competition", "market share"],
            "customer data": ["customer", "user", "client", "feedback"],
            "web analytics": ["analytics", "traffic", "conversion", "engagement"]
        }

        for source, keywords in potential_sources.items():
            if any(keyword in response_lower for keyword in keywords):
                data_sources.append(source)

        return data_sources

    def _extract_financial_impact(self, response: str) -> Dict[str, Any]:
        """Extract financial impact information from response"""
        financial_impact = {}
        response_lower = response.lower()

        # Look for ROI mentions
        if "roi" in response_lower or "return on investment" in response_lower:
            financial_impact["roi_mentioned"] = True

        # Look for cost/budget mentions
        if any(word in response_lower for word in ["cost", "budget", "expense", "investment"]):
            financial_impact["cost_analysis"] = True

        # Look for revenue/profit mentions
        if any(word in response_lower for word in ["revenue", "profit", "income", "margin"]):
            financial_impact["revenue_impact"] = True

        # Look for specific numbers (simplified extraction)
        import re
        numbers = re.findall(r'\$[\d,]+|\d+[%]|$\d+', response)
        if numbers:
            financial_impact["quantified_metrics"] = numbers[:5]  # First 5 financial numbers

        return financial_impact

    async def get_market_analysis(self, query: str) -> Dict[str, Any]:
        """Get specific market analysis for a query"""
        self.logger.info(f"[Strategy] Performing market analysis for: {query}")

        market_prompt = f"""Provide a comprehensive market analysis for: {query}

Include:
1. Market size and growth trends
2. Competitive landscape
3. Target audience analysis
4. Market opportunities and threats
5. Entry barriers and success factors
6. Strategic recommendations"""

        response = await self.process_message(market_prompt, {
            "analysis_type": "market_analysis",
            "query": query
        })

        return {
            "query": query,
            "analysis": response.content,
            "success": response.success,
            "timestamp": response.timestamp,
            "metadata": response.metadata
        }

    async def get_financial_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial data and provide insights"""
        self.logger.info("[Strategy] Performing financial analysis")

        financial_prompt = f"""Analyze the following financial data and provide insights:

{data}

Include:
1. Financial health assessment
2. Key performance indicators
3. Trends and patterns
4. Risk factors
5. Improvement recommendations
6. Strategic implications"""

        response = await self.process_message(financial_prompt, {
            "analysis_type": "financial_analysis",
            "data_provided": list(data.keys()) if isinstance(data, dict) else []
        })

        return {
            "analysis": response.content,
            "data_summary": {
                "metrics_provided": list(data.keys()) if isinstance(data, dict) else [],
                "analysis_timestamp": response.timestamp
            },
            "success": response.success,
            "metadata": response.metadata
        }

    async def create_business_plan(self, business_idea: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a comprehensive business plan"""
        self.logger.info(f"[Strategy] Creating business plan for: {business_idea}")

        plan_prompt = f"""Create a comprehensive business plan for: {business_idea}

Context: {context or {}}

Include:
1. Executive Summary
2. Market Analysis
3. Value Proposition
4. Revenue Model
5. Go-to-Market Strategy
6. Financial Projections
7. Risk Assessment
8. Success Metrics"""

        response = await self.process_message(plan_prompt, {
            "analysis_type": "business_plan",
            "business_idea": business_idea,
            "context": context or {}
        })

        # Structure the business plan
        plan_sections = self._structure_business_plan(response.content)

        return {
            "business_idea": business_idea,
            "business_plan": plan_sections,
            "full_response": response.content,
            "success": response.success,
            "timestamp": response.timestamp,
            "metadata": response.metadata
        }

    def _structure_business_plan(self, response: str) -> Dict[str, str]:
        """Structure business plan into sections"""
        sections = {}
        lines = response.split('\n')
        current_section = None
        current_content = []

        section_keywords = {
            "executive": "Executive Summary",
            "market": "Market Analysis",
            "value": "Value Proposition",
            "revenue": "Revenue Model",
            "go-to-market": "Go-to-Market Strategy",
            "financial": "Financial Projections",
            "risk": "Risk Assessment",
            "success": "Success Metrics"
        }

        for line in lines:
            line_lower = line.lower()

            # Check if this line starts a new section
            for keyword, section_name in section_keywords.items():
                if keyword in line_lower and any(indicator in line for indicator in [':', '-', '•']):
                    # Save previous section if exists
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content)

                    # Start new section
                    current_section = section_name
                    current_content = [line.strip()]
                    break
            else:
                # Add to current section content
                if current_section and line.strip():
                    current_content.append(line.strip())

        # Don't forget the last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)

        return sections