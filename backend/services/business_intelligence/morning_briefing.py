"""
Morning Briefing System
Generates comprehensive executive briefings with business health analysis,
key metrics, and personalized recommendations for strategic decision-making.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from agents.base_agent import BaseAgent, TaskDelegation, TaskResult, TaskStatus, AgentType
from services.firebase_service import get_firebase_service


class MetricType(str, Enum):
    REVENUE = "revenue"
    CUSTOMER_ACQUISITION = "customer_acquisition"
    PIPELINE_HEALTH = "pipeline_health"
    TEAM_PERFORMANCE = "team_performance"
    MARKET_TRENDS = "market_trends"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    FINANCIAL_HEALTH = "financial_health"
    COMPETITIVE_POSITION = "competitive_position"


class AlertLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class BusinessMetric:
    """Individual business metric with trend analysis"""
    id: str
    name: str
    type: MetricType
    current_value: float
    previous_value: Optional[float]
    target_value: Optional[float]
    unit: str
    trend: TrendDirection
    trend_percentage: Optional[float]
    status: AlertLevel
    last_updated: datetime
    description: str
    impact_assessment: str


@dataclass
class BusinessAlert:
    """Business alert with actionable recommendations"""
    id: str
    title: str
    description: str
    level: AlertLevel
    category: str
    metrics_affected: List[str]
    recommended_actions: List[str]
    urgency_score: float  # 0-10
    business_impact: str
    deadline: Optional[datetime]
    owner: Optional[str]
    created_at: datetime


@dataclass
class GrowthOpportunity:
    """Identified business growth opportunity"""
    id: str
    title: str
    description: str
    potential_value: float
    confidence_score: float  # 0-1
    time_to_value: str  # days, weeks, months
    required_resources: List[str]
    success_factors: List[str]
    risks: List[str]
    next_steps: List[str]
    priority: str  # high, medium, low


@dataclass
class MorningBriefing:
    """Complete morning briefing for executive leadership"""
    id: str
    date: datetime
    executive_summary: str
    key_metrics: List[BusinessMetric]
    alerts: List[BusinessAlert]
    growth_opportunities: List[GrowthOpportunity]
    recommendations: List[str]
    focus_areas: List[str]
    team_highlights: Dict[str, Any]
    market_insights: Dict[str, Any]
    performance_indicators: Dict[str, float]
    action_items: List[Dict[str, Any]]
    generated_at: datetime
    metadata: Dict[str, Any]


class MorningBriefingGenerator:
    """Generates comprehensive morning briefings for business executives"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=4000,
            openai_api_key=openai_api_key
        )

        # Metric configuration
        self.metric_definitions = {
            MetricType.REVENUE: {
                "unit": "USD",
                "target_growth": 0.15,  # 15% growth
                "alert_thresholds": {"critical": -0.2, "high": -0.1, "medium": -0.05}
            },
            MetricType.CUSTOMER_ACQUISITION: {
                "unit": "customers",
                "target_growth": 0.10,  # 10% growth
                "alert_thresholds": {"critical": -0.3, "high": -0.2, "medium": -0.1}
            },
            MetricType.PIPELINE_HEALTH: {
                "unit": "USD",
                "target_ratio": 3.0,  # 3x pipeline to quota
                "alert_thresholds": {"critical": 1.5, "high": 2.0, "medium": 2.5}
            }
        }

    async def generate_morning_briefing(
        self,
        user_id: str,
        date_range: Tuple[datetime, datetime] = None,
        include_forecasts: bool = True,
        focus_areas: List[str] = None
    ) -> MorningBriefing:
        """Generate a comprehensive morning briefing"""
        try:
            self.logger.info(f"Generating morning briefing for user {user_id}")

            # Default to last 30 days if no range specified
            if date_range is None:
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
                date_range = (start_date, end_date)

            start_date, end_date = date_range

            # Gather business data
            metrics_data = await self._collect_business_metrics(user_id, start_date, end_date)
            team_performance = await self._collect_team_performance(user_id, start_date, end_date)
            market_data = await self._collect_market_intelligence(user_id, start_date, end_date)

            # Analyze metrics and generate alerts
            key_metrics = await self._analyze_key_metrics(metrics_data, start_date, end_date)
            alerts = await self._generate_business_alerts(key_metrics, team_performance)
            growth_opportunities = await self._identify_growth_opportunities(
                key_metrics, market_data, team_performance
            )

            # Generate executive summary using LLM
            executive_summary = await self._generate_executive_summary(
                key_metrics, alerts, growth_opportunities, team_performance, market_data
            )

            # Generate recommendations and focus areas
            recommendations = await self._generate_strategic_recommendations(
                key_metrics, alerts, growth_opportunities, focus_areas
            )
            focus_areas = await self._determine_focus_areas(
                key_metrics, alerts, recommendations, focus_areas
            )

            # Generate action items
            action_items = await self._generate_action_items(
                alerts, growth_opportunities, recommendations
            )

            # Calculate performance indicators
            performance_indicators = await self._calculate_performance_indicators(
                key_metrics, team_performance
            )

            briefing = MorningBriefing(
                id=f"briefing_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
                date=end_date,
                executive_summary=executive_summary,
                key_metrics=key_metrics,
                alerts=alerts,
                growth_opportunities=growth_opportunities,
                recommendations=recommendations,
                focus_areas=focus_areas,
                team_highlights=team_performance,
                market_insights=market_data,
                performance_indicators=performance_indicators,
                action_items=action_items,
                generated_at=datetime.now(timezone.utc),
                metadata={
                    "user_id": user_id,
                    "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                    "include_forecasts": include_forecasts,
                    "data_sources": ["metrics", "team_performance", "market_intelligence"]
                }
            )

            # Store briefing in Firebase
            await self._store_briefing(briefing, user_id)

            self.logger.info(f"Successfully generated morning briefing {briefing.id}")
            return briefing

        except Exception as e:
            self.logger.error(f"Error generating morning briefing: {e}")
            raise

    async def _collect_business_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Collect business metrics from various data sources"""
        try:
            # Get revenue data
            revenue_data = await self._get_revenue_metrics(user_id, start_date, end_date)

            # Get customer acquisition data
            customer_data = await self._get_customer_acquisition_metrics(user_id, start_date, end_date)

            # Get pipeline data
            pipeline_data = await self._get_pipeline_metrics(user_id, start_date, end_date)

            # Get operational metrics
            operational_data = await self._get_operational_metrics(user_id, start_date, end_date)

            return {
                "revenue": revenue_data,
                "customer_acquisition": customer_data,
                "pipeline": pipeline_data,
                "operational": operational_data
            }

        except Exception as e:
            self.logger.error(f"Error collecting business metrics: {e}")
            return {}

    async def _get_revenue_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get revenue metrics from HubSpot and other sources"""
        try:
            # This would integrate with HubSpot API for actual revenue data
            # For now, simulate with mock data
            current_revenue = 125000.0
            previous_revenue = 110000.0
            target_revenue = 130000.0

            return {
                "current": current_revenue,
                "previous": previous_revenue,
                "target": target_revenue,
                "growth_rate": (current_revenue - previous_revenue) / previous_revenue,
                "trend": "up" if current_revenue > previous_revenue else "down",
                "forecast": current_revenue * 1.05  # 5% growth forecast
            }

        except Exception as e:
            self.logger.error(f"Error getting revenue metrics: {e}")
            return {"current": 0, "previous": 0, "target": 0, "growth_rate": 0}

    async def _get_customer_acquisition_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get customer acquisition metrics"""
        try:
            # Mock data - would integrate with CRM
            current_customers = 145
            previous_customers = 128
            target_customers = 150

            cac = 250.0  # Customer acquisition cost
            ltv = 2500.0  # Lifetime value

            return {
                "current": current_customers,
                "previous": previous_customers,
                "target": target_customers,
                "growth_rate": (current_customers - previous_customers) / previous_customers,
                "cac": cac,
                "ltv": ltv,
                "ltv_cac_ratio": ltv / cac,
                "churn_rate": 0.05  # 5% monthly churn
            }

        except Exception as e:
            self.logger.error(f"Error getting customer acquisition metrics: {e}")
            return {"current": 0, "previous": 0, "target": 0, "growth_rate": 0}

    async def _get_pipeline_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get sales pipeline metrics"""
        try:
            # Mock pipeline data
            total_pipeline = 450000.0
            qualified_pipeline = 180000.0
            closing_pipeline = 85000.0
            monthly_quota = 120000.0

            return {
                "total": total_pipeline,
                "qualified": qualified_pipeline,
                "closing": closing_pipeline,
                "quota": monthly_quota,
                "pipeline_to_quota_ratio": total_pipeline / monthly_quota,
                "conversion_rates": {
                    "qualified_to_closed": 0.25,
                    "total_to_qualified": 0.40
                },
                "average_deal_size": 25000.0,
                "sales_cycle_length": 45  # days
            }

        except Exception as e:
            self.logger.error(f"Error getting pipeline metrics: {e}")
            return {"total": 0, "qualified": 0, "closing": 0, "quota": 0}

    async def _get_operational_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get operational efficiency metrics"""
        try:
            # Mock operational data
            return {
                "team_productivity": {
                    "tasks_completed": 1247,
                    "on_time_completion_rate": 0.87,
                    "quality_score": 0.92
                },
                "resource_utilization": {
                    "developer_utilization": 0.78,
                    "sales_utilization": 0.85,
                    "support_utilization": 0.72
                },
                "process_efficiency": {
                    "average_task_completion_time": 2.3,  # hours
                    "process_cycle_time": 1.8,  # days
                    "automation_rate": 0.65
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting operational metrics: {e}")
            return {}

    async def _collect_team_performance(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Collect team performance data from agent orchestration system"""
        try:
            # Get agent performance data
            agents_data = await self.firebase_service.get_agents_data(user_id)

            team_highlights = {
                "top_performers": [],
                "improvement_areas": [],
                "achievements": [],
                "collaboration_score": 0.85,
                "overall_productivity": 0.82,
                "task_completion_trends": "increasing"
            }

            # Analyze individual agent performance
            for agent_data in agents_data:
                if agent_data.get("success_rate", 0) > 0.9:
                    team_highlights["top_performers"].append({
                        "agent_id": agent_data.get("agent_id"),
                        "success_rate": agent_data.get("success_rate"),
                        "tasks_completed": agent_data.get("tasks_completed", 0)
                    })

            return team_highlights

        except Exception as e:
            self.logger.error(f"Error collecting team performance: {e}")
            return {}

    async def _collect_market_intelligence(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Collect market intelligence and competitive data"""
        try:
            # This would integrate with competitive intelligence tools
            # For now, provide mock market data
            return {
                "market_trends": {
                    "industry_growth": 0.12,
                    "market_size": 2500000000,  # $2.5B
                    "competitor_count": 15,
                    "customer_demand": "high"
                },
                "competitive_position": {
                    "market_share": 0.08,
                    "ranking": 3,
                    "competitive_advantages": [
                        "AI-powered automation",
                        "Superior customer support",
                        "Faster time-to-value"
                    ],
                    "competitive_threats": [
                        "New market entrants",
                        "Price competition",
                        "Technology disruption"
                    ]
                },
                "opportunity_indicators": {
                    "emerging_markets": ["Asia Pacific", "Latin America"],
                    "technology_trends": ["AI/ML", "Automation", "Remote work tools"],
                    "customer_pain_points": ["Manual processes", "Data silos", "Integration challenges"]
                }
            }

        except Exception as e:
            self.logger.error(f"Error collecting market intelligence: {e}")
            return {}

    async def _analyze_key_metrics(
        self,
        metrics_data: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> List[BusinessMetric]:
        """Analyze metrics data and create key metrics list"""
        try:
            key_metrics = []

            # Revenue metric
            if "revenue" in metrics_data:
                revenue_data = metrics_data["revenue"]
                revenue_metric = BusinessMetric(
                    id=f"revenue_{end_date.strftime('%Y%m%d')}",
                    name="Monthly Revenue",
                    type=MetricType.REVENUE,
                    current_value=revenue_data.get("current", 0),
                    previous_value=revenue_data.get("previous", 0),
                    target_value=revenue_data.get("target", 0),
                    unit="USD",
                    trend=TrendDirection(revenue_data.get("trend", "stable")),
                    trend_percentage=revenue_data.get("growth_rate", 0) * 100,
                    status=self._calculate_alert_level(MetricType.REVENUE, revenue_data.get("growth_rate", 0)),
                    last_updated=end_date,
                    description="Total monthly recurring revenue",
                    impact_assessment="Direct impact on company valuation and growth trajectory"
                )
                key_metrics.append(revenue_metric)

            # Customer acquisition metric
            if "customer_acquisition" in metrics_data:
                customer_data = metrics_data["customer_acquisition"]
                customer_metric = BusinessMetric(
                    id=f"customers_{end_date.strftime('%Y%m%d')}",
                    name="New Customers",
                    type=MetricType.CUSTOMER_ACQUISITION,
                    current_value=customer_data.get("current", 0),
                    previous_value=customer_data.get("previous", 0),
                    target_value=customer_data.get("target", 0),
                    unit="customers",
                    trend=TrendDirection.UP if customer_data.get("current", 0) > customer_data.get("previous", 0) else TrendDirection.DOWN,
                    trend_percentage=customer_data.get("growth_rate", 0) * 100,
                    status=self._calculate_alert_level(MetricType.CUSTOMER_ACQUISITION, customer_data.get("growth_rate", 0)),
                    last_updated=end_date,
                    description="Number of new customers acquired this month",
                    impact_assessment="Key indicator of market fit and growth potential"
                )
                key_metrics.append(customer_metric)

            # Pipeline health metric
            if "pipeline" in metrics_data:
                pipeline_data = metrics_data["pipeline"]
                pipeline_metric = BusinessMetric(
                    id=f"pipeline_{end_date.strftime('%Y%m%d')}",
                    name="Pipeline Health",
                    type=MetricType.PIPELINE_HEALTH,
                    current_value=pipeline_data.get("pipeline_to_quota_ratio", 0),
                    target_value=3.0,
                    unit="ratio",
                    trend=TrendDirection.STABLE,
                    trend_percentage=0,
                    status=self._calculate_pipeline_alert_level(pipeline_data.get("pipeline_to_quota_ratio", 0)),
                    last_updated=end_date,
                    description="Pipeline value relative to monthly sales quota",
                    impact_assessment="Predicts future revenue and sales team performance"
                )
                key_metrics.append(pipeline_metric)

            return key_metrics

        except Exception as e:
            self.logger.error(f"Error analyzing key metrics: {e}")
            return []

    def _calculate_alert_level(self, metric_type: MetricType, value: float) -> AlertLevel:
        """Calculate alert level based on metric value"""
        try:
            if metric_type not in self.metric_definitions:
                return AlertLevel.INFO

            thresholds = self.metric_definitions[metric_type].get("alert_thresholds", {})

            if value <= thresholds.get("critical", -0.2):
                return AlertLevel.CRITICAL
            elif value <= thresholds.get("high", -0.1):
                return AlertLevel.HIGH
            elif value <= thresholds.get("medium", -0.05):
                return AlertLevel.MEDIUM
            else:
                return AlertLevel.INFO

        except Exception:
            return AlertLevel.INFO

    def _calculate_pipeline_alert_level(self, ratio: float) -> AlertLevel:
        """Calculate pipeline health alert level"""
        if ratio <= 1.5:
            return AlertLevel.CRITICAL
        elif ratio <= 2.0:
            return AlertLevel.HIGH
        elif ratio <= 2.5:
            return AlertLevel.MEDIUM
        else:
            return AlertLevel.INFO

    async def _generate_business_alerts(
        self,
        key_metrics: List[BusinessMetric],
        team_performance: Dict[str, Any]
    ) -> List[BusinessAlert]:
        """Generate business alerts based on metrics analysis"""
        try:
            alerts = []

            for metric in key_metrics:
                if metric.status in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
                    alert = BusinessAlert(
                        id=f"alert_{metric.id}",
                        title=f"{metric.name} Alert",
                        description=f"{metric.name} is {metric.status.value}: {metric.current_value} {metric.unit}",
                        level=metric.status,
                        category=metric.type.value,
                        metrics_affected=[metric.id],
                        recommended_actions=await self._generate_metric_recommendations(metric),
                        urgency_score=8.0 if metric.status == AlertLevel.CRITICAL else 6.0,
                        business_impact=metric.impact_assessment,
                        deadline=datetime.now(timezone.utc) + timedelta(days=7),
                        owner=None,  # Would be assigned based on responsibility matrix
                        created_at=datetime.now(timezone.utc)
                    )
                    alerts.append(alert)

            return alerts

        except Exception as e:
            self.logger.error(f"Error generating business alerts: {e}")
            return []

    async def _generate_metric_recommendations(self, metric: BusinessMetric) -> List[str]:
        """Generate recommendations for a specific metric"""
        try:
            recommendations = []

            if metric.type == MetricType.REVENUE:
                if metric.trend == TrendDirection.DOWN:
                    recommendations.extend([
                        "Review pricing strategy and competitor positioning",
                        "Accelerate sales prospecting and pipeline building",
                        "Analyze customer churn and implement retention programs",
                        "Explore upsell opportunities with existing customers"
                    ])

            elif metric.type == MetricType.CUSTOMER_ACQUISITION:
                if metric.current_value < metric.target_value:
                    recommendations.extend([
                        "Increase marketing spend and campaign optimization",
                        "Refine ideal customer profile and targeting",
                        "Improve conversion rates in sales funnel",
                        "Launch referral programs and customer advocacy"
                    ])

            elif metric.type == MetricType.PIPELINE_HEALTH:
                if metric.current_value < 2.5:
                    recommendations.extend([
                        "Increase sales prospecting activity",
                        "Improve qualification process and lead scoring",
                        "Focus on larger deal sizes",
                        "Reduce sales cycle length"
                    ])

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating metric recommendations: {e}")
            return ["Review metric performance and take appropriate action"]

    async def _identify_growth_opportunities(
        self,
        key_metrics: List[BusinessMetric],
        market_data: Dict[str, Any],
        team_performance: Dict[str, Any]
    ) -> List[GrowthOpportunity]:
        """Identify business growth opportunities"""
        try:
            opportunities = []

            # Analyze market opportunities
            if "competitive_position" in market_data:
                competitive_data = market_data["competitive_position"]

                if competitive_data.get("market_share", 0) < 0.15:  # Less than 15% market share
                    opportunity = GrowthOpportunity(
                        id=f"market_expansion_{datetime.now().strftime('%Y%m%d')}",
                        title="Market Share Expansion",
                        description="Increase market share through targeted campaigns and competitive positioning",
                        potential_value=500000.0,  # $500k potential revenue
                        confidence_score=0.75,
                        time_to_value="6 months",
                        required_resources=["Marketing budget", "Sales team", "Product development"],
                        success_factors=["Clear value proposition", "Competitive pricing", "Strong sales execution"],
                        risks=["Competitor response", "Market saturation", "Economic factors"],
                        next_steps=[
                            "Conduct market analysis and competitive landscape review",
                            "Define target segments and value propositions",
                            "Allocate marketing and sales resources",
                            "Launch targeted campaigns"
                        ],
                        priority="high"
                    )
                    opportunities.append(opportunity)

            # Analyze customer retention opportunities
            customer_metrics = [m for m in key_metrics if m.type == MetricType.CUSTOMER_ACQUISITION]
            if customer_metrics:
                # Opportunity to increase customer lifetime value
                opportunity = GrowthOpportunity(
                    id=f"customer_retention_{datetime.now().strftime('%Y%m%d')}",
                    title="Customer Retention & Expansion",
                    description="Increase customer lifetime value through retention programs and upselling",
                    potential_value=300000.0,  # $300k potential revenue
                    confidence_score=0.85,
                    time_to_value="3 months",
                    required_resources=["Customer success team", "Product improvements", "Marketing automation"],
                    success_factors=["Customer satisfaction", "Product value", "Proactive engagement"],
                    risks=["Competitive offers", "Product limitations", "Resource constraints"],
                    next_steps=[
                        "Analyze customer churn patterns",
                        "Implement customer success programs",
                        "Develop upsell/cross-sell strategies",
                        "Measure and optimize customer satisfaction"
                    ],
                    priority="high"
                )
                opportunities.append(opportunity)

            return opportunities

        except Exception as e:
            self.logger.error(f"Error identifying growth opportunities: {e}")
            return []

    async def _generate_executive_summary(
        self,
        key_metrics: List[BusinessMetric],
        alerts: List[BusinessAlert],
        growth_opportunities: List[GrowthOpportunity],
        team_performance: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> str:
        """Generate executive summary using LLM"""
        try:
            # Prepare context for LLM
            context = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "key_metrics": [asdict(metric) for metric in key_metrics],
                "alerts": [asdict(alert) for alert in alerts],
                "growth_opportunities": [asdict(opp) for opp in growth_opportunities],
                "team_performance": team_performance,
                "market_data": market_data
            }

            system_prompt = """
            You are a seasoned business analyst and strategic advisor generating executive briefings.

            Your task is to create a concise, actionable executive summary that:
            1. Highlights the most important business insights
            2. Identifies critical issues requiring immediate attention
            3. Presents growth opportunities with clear business impact
            4. Provides strategic recommendations for leadership
            5. Maintains a professional, data-driven tone

            Structure your response with:
            - Business Performance Overview (2-3 sentences)
            - Critical Issues & Alerts (if any)
            - Key Opportunities (2-3 main opportunities)
            - Strategic Focus Areas (2-3 priorities)
            - Immediate Action Items (1-2 critical next steps)

            Keep the summary to 250-300 words maximum. Be specific and actionable.
            """

            human_prompt = f"""
            Generate an executive summary based on the following business data:

            {json.dumps(context, indent=2)}

            Focus on insights that drive strategic decision-making and immediate action.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            self.logger.error(f"Error generating executive summary: {e}")
            return "Executive summary generation failed. Please review the detailed metrics and alerts below."

    async def _generate_strategic_recommendations(
        self,
        key_metrics: List[BusinessMetric],
        alerts: List[BusinessAlert],
        growth_opportunities: List[GrowthOpportunity],
        focus_areas: List[str] = None
    ) -> List[str]:
        """Generate strategic recommendations based on business analysis"""
        try:
            recommendations = []

            # Add recommendations from alerts
            for alert in alerts:
                recommendations.extend(alert.recommended_actions)

            # Add recommendations from growth opportunities
            for opportunity in growth_opportunities:
                recommendations.extend(opportunity.next_steps[:2])  # Top 2 next steps

            # Analyze metrics for strategic insights
            revenue_metrics = [m for m in key_metrics if m.type == MetricType.REVENUE]
            if revenue_metrics and revenue_metrics[0].trend == TrendDirection.DOWN:
                recommendations.append("Implement revenue recovery plan with specific growth initiatives")
                recommendations.append("Review and optimize pricing strategy for competitive advantage")

            customer_metrics = [m for m in key_metrics if m.type == MetricType.CUSTOMER_ACQUISITION]
            if customer_metrics and customer_metrics[0].current_value < customer_metrics[0].target_value:
                recommendations.append("Accelerate customer acquisition through targeted marketing campaigns")
                recommendations.append("Optimize conversion funnel and reduce customer acquisition costs")

            # Remove duplicates and prioritize
            unique_recommendations = list(set(recommendations))
            return unique_recommendations[:8]  # Top 8 recommendations

        except Exception as e:
            self.logger.error(f"Error generating strategic recommendations: {e}")
            return ["Review business metrics and develop action plans for improvement areas"]

    async def _determine_focus_areas(
        self,
        key_metrics: List[BusinessMetric],
        alerts: List[BusinessAlert],
        recommendations: List[str],
        requested_focus_areas: List[str] = None
    ) -> List[str]:
        """Determine key focus areas based on current business state"""
        try:
            focus_areas = []

            # Add focus areas based on alerts
            for alert in alerts:
                if alert.level in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
                    if alert.category not in focus_areas:
                        focus_areas.append(alert.category)

            # Add focus areas based on critical metrics
            for metric in key_metrics:
                if metric.status in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
                    focus_area = f"{metric.type.value}_improvement"
                    if focus_area not in focus_areas:
                        focus_areas.append(focus_area)

            # Add requested focus areas
            if requested_focus_areas:
                for area in requested_focus_areas:
                    if area not in focus_areas:
                        focus_areas.append(area)

            # Default focus areas if none identified
            if not focus_areas:
                focus_areas = ["revenue_growth", "customer_acquisition", "operational_efficiency"]

            return focus_areas[:5]  # Top 5 focus areas

        except Exception as e:
            self.logger.error(f"Error determining focus areas: {e}")
            return ["business_performance_review"]

    async def _generate_action_items(
        self,
        alerts: List[BusinessAlert],
        growth_opportunities: List[GrowthOpportunity],
        recommendations: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate specific, actionable items from analysis"""
        try:
            action_items = []

            # Convert alerts to action items
            for alert in alerts:
                for action in alert.recommended_actions[:2]:  # Top 2 actions per alert
                    action_item = {
                        "id": f"action_{uuid.uuid4().hex[:8]}",
                        "title": action,
                        "category": alert.category,
                        "priority": alert.level.value,
                        "source": "alert",
                        "source_id": alert.id,
                        "deadline": (alert.deadline or datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                        "owner": None,  # Would be assigned based on role
                        "status": "pending",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    action_items.append(action_item)

            # Convert growth opportunities to action items
            for opportunity in growth_opportunities:
                for i, action in enumerate(opportunity.next_steps[:3]):  # Top 3 actions per opportunity
                    action_item = {
                        "id": f"action_{uuid.uuid4().hex[:8]}",
                        "title": action,
                        "category": "growth_opportunity",
                        "priority": opportunity.priority,
                        "source": "opportunity",
                        "source_id": opportunity.id,
                        "deadline": (datetime.now(timezone.utc) + timedelta(days=7 * (i + 1))).isoformat(),
                        "owner": None,
                        "status": "pending",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "potential_value": opportunity.potential_value / len(opportunity.next_steps)
                    }
                    action_items.append(action_item)

            return action_items

        except Exception as e:
            self.logger.error(f"Error generating action items: {e}")
            return []

    async def _calculate_performance_indicators(
        self,
        key_metrics: List[BusinessMetric],
        team_performance: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate overall performance indicators"""
        try:
            indicators = {
                "overall_health": 0.0,
                "growth_velocity": 0.0,
                "operational_efficiency": 0.0,
                "team_productivity": 0.0,
                "market_position": 0.0
            }

            # Calculate overall health from metrics
            if key_metrics:
                health_scores = []
                for metric in key_metrics:
                    # Convert alert levels to scores
                    score_map = {
                        AlertLevel.CRITICAL: 0.2,
                        AlertLevel.HIGH: 0.4,
                        AlertLevel.MEDIUM: 0.6,
                        AlertLevel.LOW: 0.8,
                        AlertLevel.INFO: 1.0
                    }
                    health_scores.append(score_map.get(metric.status, 0.5))
                indicators["overall_health"] = sum(health_scores) / len(health_scores)

            # Calculate growth velocity
            revenue_metrics = [m for m in key_metrics if m.type == MetricType.REVENUE]
            if revenue_metrics:
                growth_rate = revenue_metrics[0].trend_percentage or 0
                indicators["growth_velocity"] = max(0, min(1, (growth_rate + 20) / 40))  # Normalize to 0-1

            # Calculate team productivity
            if team_performance:
                indicators["team_productivity"] = team_performance.get("overall_productivity", 0.8)
                indicators["operational_efficiency"] = team_performance.get("task_completion_trends", 0.8)

            return indicators

        except Exception as e:
            self.logger.error(f"Error calculating performance indicators: {e}")
            return {}

    async def _store_briefing(self, briefing: MorningBriefing, user_id: str):
        """Store morning briefing in Firebase"""
        try:
            briefing_data = asdict(briefing)

            # Store in morning_briefings collection
            await self.firebase_service.store_agent_file(
                f"morning_briefings/{user_id}/{briefing.id}",
                json.dumps(briefing_data, indent=2, default=str)
            )

            self.logger.info(f"Stored morning briefing {briefing.id} for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error storing briefing: {e}")

    async def get_briefing_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[MorningBriefing]:
        """Get historical morning briefings"""
        try:
            # Retrieve briefings from Firebase
            briefings_data = await self.firebase_service.get_agent_files_by_prefix(
                f"morning_briefings/{user_id}/"
            )

            briefings = []
            for briefing_data in briefings_data[-limit:]:
                # Convert data back to MorningBriefing object
                briefing = MorningBriefing(**json.loads(briefing_data.get("content", "{}")))
                briefings.append(briefing)

            return briefings

        except Exception as e:
            self.logger.error(f"Error getting briefing history: {e}")
            return []

    async def generate_quick_insights(
        self,
        user_id: str,
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """Generate quick insights for dashboard display"""
        try:
            # Get latest metrics
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)  # Last 7 days

            metrics_data = await self._collect_business_metrics(user_id, start_date, end_date)
            key_metrics = await self._analyze_key_metrics(metrics_data, start_date, end_date)

            insights = {
                "key_metrics": [asdict(metric) for metric in key_metrics[:5]],
                "alerts_count": len([m for m in key_metrics if m.status in [AlertLevel.CRITICAL, AlertLevel.HIGH]]),
                "growth_indicators": {
                    "revenue_trend": "up" if key_metrics and key_metrics[0].trend == TrendDirection.UP else "down",
                    "customer_growth": "positive" if len([m for m in key_metrics if m.type == MetricType.CUSTOMER_ACQUISITION and m.trend == TrendDirection.UP]) > 0 else "negative",
                    "pipeline_health": "healthy" if key_metrics and any(m.type == MetricType.PIPELINE_HEALTH and m.current_value >= 2.5 for m in key_metrics) else "needs_attention"
                },
                "focus_areas": focus_areas or ["revenue_growth", "customer_retention"],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            return insights

        except Exception as e:
            self.logger.error(f"Error generating quick insights: {e}")
            return {}