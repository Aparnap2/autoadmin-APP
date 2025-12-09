"""
CRM Intelligence Integration
Advanced HubSpot integration analysis with deal health scoring, pipeline optimization,
customer segmentation, and engagement pattern analysis for strategic CRM insights.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
import statistics
from decimal import Decimal

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from services.firebase_service import get_firebase_service
from services.hubspot_service import get_hubspot_service


class DealStage(str, Enum):
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    QUALIFIED_TO_BUY = "qualified_to_buy"
    PRESENTATION_SCHEDULED = "presentation_scheduled"
    DECISION_MAKER_BOUGHT_IN = "decision_maker_bought_in"
    CONTRACT_SENT = "contract_sent"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    STALLED = "stalled"


class DealHealth(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    STALLED = "stalled"


class CustomerTier(str, Enum):
    ENTERPRISE = "enterprise"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    STARTER = "starter"
    TRIAL = "trial"


class EngagementLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INACTIVE = "inactive"


@dataclass
class DealMetrics:
    """Comprehensive deal performance metrics"""
    total_deals: int
    active_deals: int
    won_deals: int
    lost_deals: int
    stalled_deals: int
    total_pipeline_value: float
    average_deal_size: float
    conversion_rates: Dict[str, float]  # stage -> conversion rate
    sales_cycle_length: float  # days
    win_rate: float
    deal_velocity: float  # value per day
    pipeline_health_score: float  # 0-100


@dataclass
class DealHealthScore:
    """Individual deal health assessment"""
    deal_id: str
    deal_name: str
    health_score: float  # 0-100
    health_status: DealHealth
    risk_factors: List[str]
    strengths: List[str]
    recommended_actions: List[str]
    next_best_action: str
    estimated_close_probability: float
    days_in_current_stage: int
    last_activity_days: int
    engagement_score: float
    scoring_factors: Dict[str, float]
    last_assessed: datetime


@dataclass
class PipelineOptimization:
    """Pipeline optimization recommendations"""
    optimization_id: str
    stage_name: str
    current_conversion_rate: float
    target_conversion_rate: float
    bottleneck_indicators: List[str]
    optimization_recommendations: List[str]
    expected_improvement: Dict[str, float]
    implementation_effort: str
    priority_score: float
    estimated_impact: str
    success_metrics: List[str]
    created_at: datetime


@dataclass
class CustomerSegment:
    """Customer segmentation analysis"""
    segment_id: str
    segment_name: str
    segment_size: int
    total_value: float
    average_customer_value: float
    characteristics: List[str]
    behaviors: List[str]
    preferences: List[str]
    tier_distribution: Dict[CustomerTier, int]
    engagement_patterns: Dict[str, Any]
    recommended_strategies: List[str]
    growth_potential: float
    churn_risk: float
    created_at: datetime


@dataclass
class EngagementAnalysis:
    """Customer engagement pattern analysis"""
    analysis_id: str
    customer_id: str
    customer_name: str
    overall_engagement_score: float
    engagement_level: EngagementLevel
    touchpoint_analysis: Dict[str, float]  # touchpoint -> score
    communication_preferences: List[str]
    optimal_contact_frequency: str
    engagement_trend: str  # increasing, stable, decreasing
    risk_indicators: List[str]
    opportunity_indicators: List[str]
    recommended_touchpoints: List[str]
    personalization_opportunities: List[str]
    last_analysis: datetime


@dataclass
class StalledDealRecovery:
    """Stalled deal recovery strategy"""
    recovery_id: str
    deal_id: str
    deal_name: str
    stall_duration: int  # days
    stall_reasons: List[str]
    recovery_strategies: List[str]
    communication_plan: List[str]
    value_proposition_adjustment: str
    incentive_options: List[str]
    estimated_recovery_probability: float
    next_action_owner: str
    recovery_timeline: str
    success_metrics: List[str]
    created_at: datetime


class CRMIntelligenceEngine:
    """Advanced CRM intelligence and HubSpot integration engine"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.hubspot_service = get_hubspot_service()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            max_tokens=2500,
            openai_api_key=openai_api_key
        )

        # Health scoring configuration
        self.health_scoring_config = {
            "weights": {
                "activity_level": 0.25,
                "engagement_score": 0.20,
                "deal_progression": 0.20,
                "timeline_compliance": 0.15,
                "buyer_signals": 0.20
            },
            "thresholds": {
                "healthy": 80,
                "warning": 60,
                "at_risk": 40,
                "critical": 20
            },
            "stall_thresholds": {
                "days_in_stage": 14,
                "last_activity": 7,
                "low_engagement": 30
            }
        }

        # Analysis cache
        self._analysis_cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 900  # 15 minutes

    async def analyze_crm_performance(
        self,
        user_id: str,
        analysis_type: str = "comprehensive",
        date_range: Tuple[datetime, datetime] = None
    ) -> Dict[str, Any]:
        """Comprehensive CRM performance analysis"""
        try:
            self.logger.info(f"Analyzing CRM performance: {analysis_type}")

            # Set default date range if not provided
            if date_range is None:
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=90)  # Last 90 days
                date_range = (start_date, end_date)

            start_date, end_date = date_range

            # Get CRM data from HubSpot
            crm_data = await self._get_crm_data(user_id, start_date, end_date)

            # Analyze deal metrics
            deal_metrics = await self._analyze_deal_metrics(crm_data)

            # Assess deal health
            deal_health_scores = await self._assess_deal_health(crm_data.get("deals", []))

            # Analyze pipeline optimization opportunities
            pipeline_optimizations = await self._analyze_pipeline_optimization(
                crm_data, deal_metrics
            )

            # Customer segmentation analysis
            customer_segments = await self._analyze_customer_segments(
                crm_data.get("customers", [])
            )

            # Engagement pattern analysis
            engagement_analysis = await self._analyze_engagement_patterns(
                crm_data.get("engagements", [])
            )

            # Identify stalled deals and recovery strategies
            stalled_deals = await self._identify_stalled_deals(
                crm_data.get("deals", [])
            )

            # Generate strategic recommendations
            strategic_recommendations = await self._generate_crm_recommendations(
                deal_metrics, deal_health_scores, pipeline_optimizations,
                customer_segments, engagement_analysis, stalled_deals
            )

            # Compile comprehensive analysis
            crm_analysis = {
                "analysis_id": f"crm_analysis_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
                "analysis_type": analysis_type,
                "date_range": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "deal_metrics": asdict(deal_metrics),
                "deal_health_summary": await self._summarize_deal_health(deal_health_scores),
                "pipeline_optimizations": [asdict(opt) for opt in pipeline_optimizations],
                "customer_segments": [asdict(seg) for seg in customer_segments],
                "engagement_insights": await self._summarize_engagement(engagement_analysis),
                "stalled_deals_analysis": {
                    "total_stalled": len(stalled_deals),
                    "total_value_at_risk": sum(deal.estimated_recovery_probability * deal.stall_duration for deal in stalled_deals),
                    "recovery_strategies": [asdict(recovery) for recovery in stalled_deals[:5]]
                },
                "strategic_recommendations": strategic_recommendations,
                "executive_summary": await self._generate_crm_executive_summary({
                    "deal_metrics": deal_metrics,
                    "deal_health": deal_health_scores,
                    "pipeline_optimizations": pipeline_optimizations,
                    "customer_segments": customer_segments,
                    "engagement_analysis": engagement_analysis,
                    "stalled_deals": stalled_deals
                }),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_quality": await self._assess_crm_data_quality(crm_data)
            }

            # Store analysis in Firebase
            await self._store_crm_analysis(crm_analysis, user_id)

            self.logger.info(f"Successfully generated CRM analysis {crm_analysis['analysis_id']}")
            return crm_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing CRM performance: {e}")
            raise

    async def _get_crm_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get CRM data from HubSpot"""
        try:
            crm_data = {
                "deals": [],
                "customers": [],
                "engagements": [],
                "activities": []
            }

            # Get deals data
            deals_data = await self.hubspot_service.get_deals(user_id, start_date, end_date)
            crm_data["deals"] = deals_data

            # Get customers/companies data
            customers_data = await self.hubspot_service.get_companies(user_id)
            crm_data["customers"] = customers_data

            # Get engagement data
            engagements_data = await self.hubspot_service.get_engagements(user_id, start_date, end_date)
            crm_data["engagements"] = engagements_data

            # Get activity data
            activities_data = await self.hubspot_service.get_activities(user_id, start_date, end_date)
            crm_data["activities"] = activities_data

            return crm_data

        except Exception as e:
            self.logger.error(f"Error getting CRM data: {e}")
            # Return empty data structure
            return {"deals": [], "customers": [], "engagements": [], "activities": []}

    async def _analyze_deal_metrics(self, crm_data: Dict[str, Any]) -> DealMetrics:
        """Analyze comprehensive deal metrics"""
        try:
            deals = crm_data.get("deals", [])

            if not deals:
                return DealMetrics(
                    total_deals=0, active_deals=0, won_deals=0, lost_deals=0,
                    stalled_deals=0, total_pipeline_value=0, average_deal_size=0,
                    conversion_rates={}, sales_cycle_length=0, win_rate=0,
                    deal_velocity=0, pipeline_health_score=0
                )

            # Basic metrics
            total_deals = len(deals)
            active_deals = len([d for d in deals if d.get("dealstage") not in ["closed_won", "closed_lost"]])
            won_deals = len([d for d in deals if d.get("dealstage") == "closed_won"])
            lost_deals = len([d for d in deals if d.get("dealstage") == "closed_lost"])

            # Calculate pipeline values
            total_pipeline_value = sum(d.get("amount", 0) for d in deals)
            active_pipeline_value = sum(d.get("amount", 0) for d in deals
                                     if d.get("dealstage") not in ["closed_won", "closed_lost"])

            average_deal_size = total_pipeline_value / max(1, total_deals)

            # Calculate conversion rates by stage
            conversion_rates = await self._calculate_stage_conversion_rates(deals)

            # Calculate sales cycle length
            sales_cycle_lengths = []
            for deal in deals:
                if deal.get("dealstage") == "closed_won" and deal.get("createdate"):
                    created_date = datetime.fromisoformat(deal["createdate"].replace('Z', '+00:00'))
                    closed_date = datetime.fromisoformat(deal["closedate"].replace('Z', '+00:00'))
                    cycle_length = (closed_date - created_date).days
                    sales_cycle_lengths.append(cycle_length)

            avg_sales_cycle = statistics.mean(sales_cycle_lengths) if sales_cycle_lengths else 0

            # Calculate win rate
            win_rate = (won_deals / max(1, won_deals + lost_deals)) * 100

            # Calculate deal velocity (value per day in pipeline)
            deal_velocity = active_pipeline_value / max(1, avg_sales_cycle) if avg_sales_cycle > 0 else 0

            # Calculate pipeline health score
            pipeline_health_score = await self._calculate_pipeline_health_score(
                conversion_rates, win_rate, avg_sales_cycle
            )

            # Identify stalled deals
            stalled_deals = await self._count_stalled_deals(deals)

            return DealMetrics(
                total_deals=total_deals,
                active_deals=active_deals,
                won_deals=won_deals,
                lost_deals=lost_deals,
                stalled_deals=stalled_deals,
                total_pipeline_value=total_pipeline_value,
                average_deal_size=average_deal_size,
                conversion_rates=conversion_rates,
                sales_cycle_length=avg_sales_cycle,
                win_rate=win_rate,
                deal_velocity=deal_velocity,
                pipeline_health_score=pipeline_health_score
            )

        except Exception as e:
            self.logger.error(f"Error analyzing deal metrics: {e}")
            return DealMetrics(
                total_deals=0, active_deals=0, won_deals=0, lost_deals=0,
                stalled_deals=0, total_pipeline_value=0, average_deal_size=0,
                conversion_rates={}, sales_cycle_length=0, win_rate=0,
                deal_velocity=0, pipeline_health_score=0
            )

    async def _calculate_stage_conversion_rates(self, deals: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate conversion rates between deal stages"""
        try:
            stage_counts = {}
            stage_transitions = {}

            # Count deals in each stage
            for deal in deals:
                stage = deal.get("dealstage", "unknown")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

            # Calculate conversion rates (simplified)
            conversion_rates = {}
            total_deals = max(1, len(deals))

            for stage, count in stage_counts.items():
                if stage != "closed_lost":
                    conversion_rates[stage] = (count / total_deals) * 100

            return conversion_rates

        except Exception as e:
            self.logger.error(f"Error calculating stage conversion rates: {e}")
            return {}

    async def _calculate_pipeline_health_score(
        self,
        conversion_rates: Dict[str, float],
        win_rate: float,
        avg_sales_cycle: float
    ) -> float:
        """Calculate overall pipeline health score"""
        try:
            health_score = 50.0  # Base score

            # Win rate impact (30% weight)
            if win_rate > 30:
                health_score += 15
            elif win_rate > 20:
                health_score += 10
            elif win_rate > 10:
                health_score += 5
            elif win_rate < 5:
                health_score -= 15

            # Sales cycle length impact (25% weight)
            if avg_sales_cycle < 30:  # Less than 30 days
                health_score += 12
            elif avg_sales_cycle < 60:
                health_score += 8
            elif avg_sales_cycle > 120:  # More than 120 days
                health_score -= 10

            # Conversion rates impact (25% weight)
            if conversion_rates:
                avg_conversion = statistics.mean(conversion_rates.values())
                if avg_conversion > 70:
                    health_score += 12
                elif avg_conversion > 50:
                    health_score += 8
                elif avg_conversion < 20:
                    health_score -= 12

            # Stage distribution impact (20% weight)
            # This would analyze if deals are distributed evenly across stages

            return min(100, max(0, health_score))

        except Exception as e:
            self.logger.error(f"Error calculating pipeline health score: {e}")
            return 50.0

    async def _count_stalled_deals(self, deals: List[Dict[str, Any]]) -> int:
        """Count stalled deals"""
        try:
            stalled_count = 0
            stall_thresholds = self.health_scoring_config["stall_thresholds"]

            for deal in deals:
                # Skip closed deals
                if deal.get("dealstage") in ["closed_won", "closed_lost"]:
                    continue

                # Check days in current stage
                if "createdate" in deal:
                    created_date = datetime.fromisoformat(deal["createdate"].replace('Z', '+00:00'))
                    days_in_stage = (datetime.now(timezone.utc) - created_date).days

                    if days_in_stage > stall_thresholds["days_in_stage"]:
                        stalled_count += 1

            return stalled_count

        except Exception as e:
            self.logger.error(f"Error counting stalled deals: {e}")
            return 0

    async def _assess_deal_health(self, deals: List[Dict[str, Any]]) -> List[DealHealthScore]:
        """Assess health of individual deals"""
        try:
            deal_health_scores = []

            for deal in deals:
                health_score = await self._calculate_individual_deal_health(deal)
                deal_health_scores.append(health_score)

            return deal_health_scores

        except Exception as e:
            self.logger.error(f"Error assessing deal health: {e}")
            return []

    async def _calculate_individual_deal_health(self, deal: Dict[str, Any]) -> DealHealthScore:
        """Calculate health score for individual deal"""
        try:
            weights = self.health_scoring_config["weights"]
            thresholds = self.health_scoring_config["thresholds"]

            # Initialize scoring factors
            scoring_factors = {
                "activity_level": 0.0,
                "engagement_score": 0.0,
                "deal_progression": 0.0,
                "timeline_compliance": 0.0,
                "buyer_signals": 0.0
            }

            # Calculate activity level
            scoring_factors["activity_level"] = await self._assess_activity_level(deal)

            # Calculate engagement score
            scoring_factors["engagement_score"] = await self._assess_deal_engagement(deal)

            # Calculate deal progression
            scoring_factors["deal_progression"] = await self._assess_deal_progression(deal)

            # Calculate timeline compliance
            scoring_factors["timeline_compliance"] = await self._assess_timeline_compliance(deal)

            # Calculate buyer signals
            scoring_factors["buyer_signals"] = await self._assess_buyer_signals(deal)

            # Calculate weighted health score
            health_score = (
                scoring_factors["activity_level"] * weights["activity_level"] +
                scoring_factors["engagement_score"] * weights["engagement_score"] +
                scoring_factors["deal_progression"] * weights["deal_progression"] +
                scoring_factors["timeline_compliance"] * weights["timeline_compliance"] +
                scoring_factors["buyer_signals"] * weights["buyer_signals"]
            ) * 100  # Convert to 0-100 scale

            # Determine health status
            if health_score >= thresholds["healthy"]:
                health_status = DealHealth.HEALTHY
            elif health_score >= thresholds["warning"]:
                health_status = DealHealth.WARNING
            elif health_score >= thresholds["at_risk"]:
                health_status = DealHealth.AT_RISK
            else:
                health_status = DealHealth.CRITICAL

            # Identify risk factors and strengths
            risk_factors = await self._identify_deal_risk_factors(deal, scoring_factors)
            strengths = await self._identify_deal_strengths(deal, scoring_factors)

            # Generate recommended actions
            recommended_actions = await self._generate_deal_recommendations(
                deal, health_status, scoring_factors
            )

            # Determine next best action
            next_best_action = await self._determine_next_best_action(deal, health_status)

            # Calculate additional metrics
            days_in_current_stage = await self._calculate_days_in_stage(deal)
            last_activity_days = await self._calculate_last_activity_days(deal)
            estimated_close_probability = health_score / 100

            return DealHealthScore(
                deal_id=deal.get("dealId", ""),
                deal_name=deal.get("dealname", "Unknown Deal"),
                health_score=round(health_score, 1),
                health_status=health_status,
                risk_factors=risk_factors,
                strengths=strengths,
                recommended_actions=recommended_actions,
                next_best_action=next_best_action,
                estimated_close_probability=estimated_close_probability,
                days_in_current_stage=days_in_current_stage,
                last_activity_days=last_activity_days,
                engagement_score=scoring_factors["engagement_score"] * 100,
                scoring_factors=scoring_factors,
                last_assessed=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error calculating individual deal health: {e}")
            # Return default health score
            return DealHealthScore(
                deal_id=deal.get("dealId", ""),
                deal_name=deal.get("dealname", "Unknown Deal"),
                health_score=50.0,
                health_status=DealHealth.WARNING,
                risk_factors=["Unable to assess health"],
                strengths=["Deal exists in system"],
                recommended_actions=["Review deal manually"],
                next_best_action="Contact sales rep",
                estimated_close_probability=0.5,
                days_in_current_stage=0,
                last_activity_days=0,
                engagement_score=50.0,
                scoring_factors={},
                last_assessed=datetime.now(timezone.utc)
            )

    async def _assess_activity_level(self, deal: Dict[str, Any]) -> float:
        """Assess activity level for deal"""
        try:
            # This would analyze recent activities related to the deal
            # For now, return a moderate score
            return 0.7

        except Exception as e:
            self.logger.error(f"Error assessing activity level: {e}")
            return 0.5

    async def _assess_deal_engagement(self, deal: Dict[str, Any]) -> float:
        """Assess engagement level for deal"""
        try:
            # This would analyze customer engagement metrics
            # For now, return based on deal stage
            stage = deal.get("dealstage", "")

            if stage in ["closed_won"]:
                return 1.0
            elif stage in ["decision_maker_bought_in", "contract_sent"]:
                return 0.9
            elif stage in ["presentation_scheduled", "qualified_to_buy"]:
                return 0.7
            elif stage in ["appointment_scheduled"]:
                return 0.6
            else:
                return 0.4

        except Exception as e:
            self.logger.error(f"Error assessing deal engagement: {e}")
            return 0.5

    async def _assess_deal_progression(self, deal: Dict[str, Any]) -> float:
        """Assess deal progression through pipeline"""
        try:
            # Map deal stages to progression scores
            stage_scores = {
                "appointment_scheduled": 0.2,
                "qualified_to_buy": 0.4,
                "presentation_scheduled": 0.6,
                "decision_maker_bought_in": 0.8,
                "contract_sent": 0.9,
                "closed_won": 1.0,
                "closed_lost": 0.0
            }

            stage = deal.get("dealstage", "")
            return stage_scores.get(stage, 0.3)

        except Exception as e:
            self.logger.error(f"Error assessing deal progression: {e}")
            return 0.5

    async def _assess_timeline_compliance(self, deal: Dict[str, Any]) -> float:
        """Assess timeline compliance"""
        try:
            # This would check if the deal is progressing according to expected timeline
            # For now, return a moderate score
            return 0.6

        except Exception as e:
            self.logger.error(f"Error assessing timeline compliance: {e}")
            return 0.5

    async def _assess_buyer_signals(self, deal: Dict[str, Any]) -> float:
        """Assess buyer signals and intent"""
        try:
            # This would analyze buyer behavior and signals
            # For now, return based on deal amount and stage
            amount = deal.get("amount", 0)
            stage = deal.get("dealstage", "")

            # Higher value deals and later stages indicate stronger buyer signals
            amount_score = min(1.0, amount / 50000)  # Normalize by $50k
            stage_score = await self._assess_deal_progression(deal)

            return (amount_score + stage_score) / 2

        except Exception as e:
            self.logger.error(f"Error assessing buyer signals: {e}")
            return 0.5

    async def _identify_deal_risk_factors(
        self,
        deal: Dict[str, Any],
        scoring_factors: Dict[str, float]
    ) -> List[str]:
        """Identify risk factors for deal"""
        try:
            risk_factors = []

            # Low activity level
            if scoring_factors.get("activity_level", 0) < 0.4:
                risk_factors.append("Low recent activity")

            # Low engagement
            if scoring_factors.get("engagement_score", 0) < 0.4:
                risk_factors.append("Poor customer engagement")

            # Slow progression
            if scoring_factors.get("deal_progression", 0) < 0.5:
                risk_factors.append("Slow pipeline progression")

            # Timeline issues
            if scoring_factors.get("timeline_compliance", 0) < 0.5:
                risk_factors.append("Behind schedule")

            # Weak buyer signals
            if scoring_factors.get("buyer_signals", 0) < 0.3:
                risk_factors.append("Weak buying signals")

            # Long time in current stage
            days_in_stage = await self._calculate_days_in_stage(deal)
            if days_in_stage > 21:  # 3 weeks
                risk_factors.append(f"Stalled for {days_in_stage} days")

            return risk_factors

        except Exception as e:
            self.logger.error(f"Error identifying deal risk factors: {e}")
            return ["Unable to assess risk factors"]

    async def _identify_deal_strengths(
        self,
        deal: Dict[str, Any],
        scoring_factors: Dict[str, float]
    ) -> List[str]:
        """Identify deal strengths"""
        try:
            strengths = []

            # High activity level
            if scoring_factors.get("activity_level", 0) > 0.8:
                strengths.append("High engagement activity")

            # Strong buyer signals
            if scoring_factors.get("buyer_signals", 0) > 0.8:
                strengths.append("Strong buying signals")

            # Good progression
            if scoring_factors.get("deal_progression", 0) > 0.7:
                strengths.append("Good pipeline progression")

            # High deal value
            amount = deal.get("amount", 0)
            if amount > 50000:
                strengths.append("High value opportunity")

            # Timeline compliance
            if scoring_factors.get("timeline_compliance", 0) > 0.8:
                strengths.append("On track timeline")

            return strengths

        except Exception as e:
            self.logger.error(f"Error identifying deal strengths: {e}")
            return ["Unable to assess strengths"]

    async def _generate_deal_recommendations(
        self,
        deal: Dict[str, Any],
        health_status: DealHealth,
        scoring_factors: Dict[str, float]
    ) -> List[str]:
        """Generate deal-specific recommendations"""
        try:
            recommendations = []

            if health_status == DealHealth.CRITICAL:
                recommendations.extend([
                    "Immediate intervention required",
                    "Re-qualify deal opportunity",
                    "Consider closing if no response"
                ])
            elif health_status == DealHealth.AT_RISK:
                recommendations.extend([
                    "Schedule immediate check-in",
                    "Identify and address objections",
                    "Provide additional value proposition"
                ])
            elif health_status == DealHealth.WARNING:
                recommendations.extend([
                    "Increase touch frequency",
                    "Identify decision makers",
                    "Address timeline concerns"
                ])
            else:  # HEALTHY
                recommendations.extend([
                    "Maintain current momentum",
                    "Prepare for next stage",
                    "Identify upsell opportunities"
                ])

            # Add specific recommendations based on scoring factors
            if scoring_factors.get("activity_level", 0) < 0.5:
                recommendations.append("Increase engagement activity")

            if scoring_factors.get("engagement_score", 0) < 0.5:
                recommendations.append("Improve customer communication")

            if scoring_factors.get("buyer_signals", 0) < 0.5:
                recommendations.append("Strengthen value proposition")

            return recommendations[:4]  # Top 4 recommendations

        except Exception as e:
            self.logger.error(f"Error generating deal recommendations: {e}")
            return ["Review deal and take appropriate action"]

    async def _determine_next_best_action(
        self,
        deal: Dict[str, Any],
        health_status: DealHealth
    ) -> str:
        """Determine next best action for deal"""
        try:
            stage = deal.get("dealstage", "")

            if health_status == DealHealth.CRITICAL:
                return "Schedule executive review call"
            elif health_status == DealHealth.AT_RISK:
                return "Conduct discovery call to identify issues"
            elif health_status == DealHealth.WARNING:
                return "Send follow-up with value proposition"
            else:  # HEALTHY
                # Based on stage
                if stage == "appointment_scheduled":
                    return "Prepare for discovery call"
                elif stage == "qualified_to_buy":
                    return "Schedule product demonstration"
                elif stage == "presentation_scheduled":
                    return "Prepare customized proposal"
                elif stage == "decision_maker_bought_in":
                    return "Send contract for review"
                elif stage == "contract_sent":
                    return "Follow up on contract review"
                else:
                    return "Maintain regular contact"

        except Exception as e:
            self.logger.error(f"Error determining next best action: {e}")
            return "Contact sales representative"

    async def _calculate_days_in_stage(self, deal: Dict[str, Any]) -> int:
        """Calculate days deal has been in current stage"""
        try:
            # This would track stage changes
            # For now, calculate from creation date
            if "createdate" in deal:
                created_date = datetime.fromisoformat(deal["createdate"].replace('Z', '+00:00'))
                return (datetime.now(timezone.utc) - created_date).days
            return 0

        except Exception as e:
            self.logger.error(f"Error calculating days in stage: {e}")
            return 0

    async def _calculate_last_activity_days(self, deal: Dict[str, Any]) -> int:
        """Calculate days since last activity"""
        try:
            # This would track actual activities
            # For now, return a mock value
            return 3

        except Exception as e:
            self.logger.error(f"Error calculating last activity days: {e}")
            return 0

    async def _analyze_pipeline_optimization(
        self,
        crm_data: Dict[str, Any],
        deal_metrics: DealMetrics
    ) -> List[PipelineOptimization]:
        """Analyze pipeline optimization opportunities"""
        try:
            optimizations = []

            # Analyze each stage for optimization opportunities
            stages = [
                "appointment_scheduled",
                "qualified_to_buy",
                "presentation_scheduled",
                "decision_maker_bought_in",
                "contract_sent"
            ]

            for stage in stages:
                optimization = await self._analyze_stage_optimization(
                    stage, deal_metrics
                )
                if optimization:
                    optimizations.append(optimization)

            return optimizations

        except Exception as e:
            self.logger.error(f"Error analyzing pipeline optimization: {e}")
            return []

    async def _analyze_stage_optimization(
        self,
        stage: str,
        deal_metrics: DealMetrics
    ) -> Optional[PipelineOptimization]:
        """Analyze specific stage for optimization"""
        try:
            conversion_rates = deal_metrics.conversion_rates
            current_rate = conversion_rates.get(stage, 0)

            # Define target rates based on industry benchmarks
            target_rates = {
                "appointment_scheduled": 80,
                "qualified_to_buy": 60,
                "presentation_scheduled": 70,
                "decision_maker_bought_in": 80,
                "contract_sent": 90
            }

            target_rate = target_rates.get(stage, 70)

            # Only create optimization if improvement is needed
            if current_rate < target_rate:
                bottleneck_indicators = await self._identify_bottleneck_indicators(stage, current_rate)
                recommendations = await self._generate_stage_recommendations(stage, bottleneck_indicators)

                optimization = PipelineOptimization(
                    optimization_id=f"opt_{stage}_{uuid.uuid4().hex[:8]}",
                    stage_name=stage.replace("_", " ").title(),
                    current_conversion_rate=current_rate,
                    target_conversion_rate=target_rate,
                    bottleneck_indicators=bottleneck_indicators,
                    optimization_recommendations=recommendations,
                    expected_improvement={
                        "conversion_increase": target_rate - current_rate,
                        "deal_velocity_increase": 15,  # percentage
                        "win_rate_increase": 5  # percentage
                    },
                    implementation_effort="medium",
                    priority_score=(target_rate - current_rate) / target_rate,
                    estimated_impact=f"Improve conversion by {target_rate - current_rate:.1f}%",
                    success_metrics=[
                        "Stage conversion rate",
                        "Deal progression speed",
                        "Sales cycle length"
                    ],
                    created_at=datetime.now(timezone.utc)
                )

                return optimization

            return None

        except Exception as e:
            self.logger.error(f"Error analyzing stage optimization for {stage}: {e}")
            return None

    async def _identify_bottleneck_indicators(self, stage: str, current_rate: float) -> List[str]:
        """Identify bottleneck indicators for stage"""
        try:
            indicators = []

            if current_rate < 30:
                indicators.append("Very low conversion rate")
            elif current_rate < 50:
                indicators.append("Below average conversion rate")

            # Stage-specific indicators
            if stage == "appointment_scheduled":
                indicators.extend(["Poor lead qualification", "Ineffective outreach"])
            elif stage == "qualified_to_buy":
                indicators.extend(["Weak value proposition", "Insufficient discovery"])
            elif stage == "presentation_scheduled":
                indicators.extend(["Poor demo preparation", "Unclear next steps"])
            elif stage == "decision_maker_bought_in":
                indicators.extend(["Stakeholder misalignment", "Budget concerns"])
            elif stage == "contract_sent":
                indicators.extend(["Contract complexity", "Legal review delays"])

            return indicators[:3]  # Top 3 indicators

        except Exception as e:
            self.logger.error(f"Error identifying bottleneck indicators: {e}")
            return ["Unable to identify specific bottlenecks"]

    async def _generate_stage_recommendations(self, stage: str, indicators: List[str]) -> List[str]:
        """Generate recommendations for stage improvement"""
        try:
            recommendations = []

            # Stage-specific recommendations
            if stage == "appointment_scheduled":
                recommendations.extend([
                    "Improve lead scoring and qualification",
                    "Enhance initial outreach messaging",
                    "Provide better discovery questions"
                ])
            elif stage == "qualified_to_buy":
                recommendations.extend([
                    "Strengthen value proposition presentation",
                    "Implement needs-based selling approach",
                    "Provide relevant case studies"
                ])
            elif stage == "presentation_scheduled":
                recommendations.extend([
                    "Customize demonstrations for prospect needs",
                    "Establish clear decision criteria",
                    "Set up technical follow-up sessions"
                ])
            elif stage == "decision_maker_bought_in":
                recommendations.extend([
                    "Identify and engage all stakeholders",
                    "Address budget and timeline concerns early",
                    "Provide ROI justification materials"
                ])
            elif stage == "contract_sent":
                recommendations.extend([
                    "Simplify contract terms where possible",
                    "Prepare for common objections",
                    "Implement efficient legal review process"
                ])

            return recommendations[:4]  # Top 4 recommendations

        except Exception as e:
            self.logger.error(f"Error generating stage recommendations: {e}")
            return ["Review stage process and implement improvements"]

    async def _analyze_customer_segments(self, customers: List[Dict[str, Any]]) -> List[CustomerSegment]:
        """Analyze customer segments"""
        try:
            if not customers:
                return []

            # Simple segmentation based on company size and revenue
            segments = []

            # Enterprise segment
            enterprise_customers = [c for c in customers if c.get("employees", 0) > 1000]
            if enterprise_customers:
                segment = await self._create_customer_segment(
                    "Enterprise", enterprise_customers
                )
                segments.append(segment)

            # Mid-market segment
            midmarket_customers = [c for c in customers if 100 < c.get("employees", 0) <= 1000]
            if midmarket_customers:
                segment = await self._create_customer_segment(
                    "Mid-Market", midmarket_customers
                )
                segments.append(segment)

            # Small business segment
            smb_customers = [c for c in customers if c.get("employees", 0) <= 100]
            if smb_customers:
                segment = await self._create_customer_segment(
                    "Small Business", smb_customers
                )
                segments.append(segment)

            return segments

        except Exception as e:
            self.logger.error(f"Error analyzing customer segments: {e}")
            return []

    async def _create_customer_segment(self, segment_name: str, customers: List[Dict[str, Any]]) -> CustomerSegment:
        """Create customer segment analysis"""
        try:
            segment_size = len(customers)
            total_value = sum(c.get("annualrevenue", 0) for c in customers)
            avg_value = total_value / max(1, segment_size)

            # Analyze characteristics
            characteristics = [
                f"Average employees: {statistics.mean([c.get('employees', 0) for c in customers]):.0f}",
                f"Geographic distribution: {len(set(c.get('city', '') for c in customers))} locations"
            ]

            # Analyze behaviors
            behaviors = [
                "Longer sales cycles",
                "Multiple stakeholder involvement",
                "Focus on ROI and integration"
            ]

            # Analyze preferences
            preferences = [
                "Comprehensive support",
                "Customization options",
                "Scalability requirements"
            ]

            # Generate recommended strategies
            strategies = [
                "Implement account-based marketing",
                "Provide dedicated customer success",
                "Offer enterprise-grade features"
            ]

            return CustomerSegment(
                segment_id=f"seg_{segment_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}",
                segment_name=segment_name,
                segment_size=segment_size,
                total_value=total_value,
                average_customer_value=avg_value,
                characteristics=characteristics,
                behaviors=behaviors,
                preferences=preferences,
                tier_distribution={},  # Would analyze actual tier distribution
                engagement_patterns={},  # Would analyze engagement data
                recommended_strategies=strategies,
                growth_potential=0.7,
                churn_risk=0.2,
                created_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error creating customer segment: {e}")
            # Return default segment
            return CustomerSegment(
                segment_id=f"seg_{segment_name.lower()}_{uuid.uuid4().hex[:8]}",
                segment_name=segment_name,
                segment_size=0,
                total_value=0,
                average_customer_value=0,
                characteristics=[],
                behaviors=[],
                preferences=[],
                tier_distribution={},
                engagement_patterns={},
                recommended_strategies=[],
                growth_potential=0.5,
                churn_risk=0.3,
                created_at=datetime.now(timezone.utc)
            )

    async def _analyze_engagement_patterns(self, engagements: List[Dict[str, Any]]) -> List[EngagementAnalysis]:
        """Analyze customer engagement patterns"""
        try:
            # Group engagements by customer
            customer_engagements = {}
            for engagement in engagements:
                customer_id = engagement.get("companyId", "")
                if customer_id not in customer_engagements:
                    customer_engagements[customer_id] = []
                customer_engagements[customer_id].append(engagement)

            # Analyze each customer's engagement
            engagement_analyses = []
            for customer_id, customer_engagement_list in customer_engagements.items():
                analysis = await self._analyze_customer_engagement(customer_id, customer_engagement_list)
                if analysis:
                    engagement_analyses.append(analysis)

            return engagement_analyses[:10]  # Top 10 analyses

        except Exception as e:
            self.logger.error(f"Error analyzing engagement patterns: {e}")
            return []

    async def _analyze_customer_engagement(
        self,
        customer_id: str,
        engagements: List[Dict[str, Any]]
    ) -> Optional[EngagementAnalysis]:
        """Analyze individual customer engagement"""
        try:
            if not engagements:
                return None

            # Calculate overall engagement score
            engagement_score = await self._calculate_engagement_score(engagements)

            # Determine engagement level
            if engagement_score > 0.8:
                engagement_level = EngagementLevel.HIGH
            elif engagement_score > 0.6:
                engagement_level = EngagementLevel.MEDIUM
            elif engagement_score > 0.3:
                engagement_level = EngagementLevel.LOW
            else:
                engagement_level = EngagementLevel.INACTIVE

            # Analyze touchpoints
            touchpoint_analysis = await self._analyze_touchpoints(engagements)

            # Identify communication preferences
            preferences = await self._identify_communication_preferences(engagements)

            # Generate recommendations
            recommendations = await self._generate_engagement_recommendations(
                engagement_level, touchpoint_analysis
            )

            return EngagementAnalysis(
                analysis_id=f"eng_{customer_id}_{uuid.uuid4().hex[:8]}",
                customer_id=customer_id,
                customer_name=f"Customer {customer_id}",  # Would get actual name
                overall_engagement_score=engagement_score * 100,
                engagement_level=engagement_level,
                touchpoint_analysis=touchpoint_analysis,
                communication_preferences=preferences,
                optimal_contact_frequency="Weekly" if engagement_level == EngagementLevel.HIGH else "Bi-weekly",
                engagement_trend="stable",  # Would calculate trend
                risk_indicators=[],  # Would analyze risks
                opportunity_indicators=[],  # Would identify opportunities
                recommended_touchpoints=recommendations,
                personalization_opportunities=[],
                last_analysis=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error analyzing customer engagement: {e}")
            return None

    async def _calculate_engagement_score(self, engagements: List[Dict[str, Any]]) -> float:
        """Calculate engagement score from engagement data"""
        try:
            # Simple calculation based on engagement frequency and type
            total_score = 0
            for engagement in engagements:
                # Score based on engagement type
                engagement_type = engagement.get("type", "").lower()
                if "call" in engagement_type:
                    total_score += 0.8
                elif "email" in engagement_type:
                    total_score += 0.4
                elif "meeting" in engagement_type:
                    total_score += 0.9
                else:
                    total_score += 0.3

            # Normalize by number of engagements and time period
            if engagements:
                return min(1.0, total_score / len(engagements))
            return 0.0

        except Exception as e:
            self.logger.error(f"Error calculating engagement score: {e}")
            return 0.5

    async def _analyze_touchpoints(self, engagements: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze engagement touchpoints"""
        try:
            touchpoints = {}
            for engagement in engagements:
                touchpoint_type = engagement.get("type", "unknown")
                touchpoints[touchpoint_type] = touchpoints.get(touchpoint_type, 0) + 1

            # Convert to scores (normalized)
            max_touchpoint = max(touchpoints.values()) if touchpoints else 1
            for touchpoint in touchpoints:
                touchpoints[touchpoint] = touchpoints[touchpoint] / max_touchpoint

            return touchpoints

        except Exception as e:
            self.logger.error(f"Error analyzing touchpoints: {e}")
            return {}

    async def _identify_communication_preferences(self, engagements: List[Dict[str, Any]]) -> List[str]:
        """Identify communication preferences"""
        try:
            # Analyze which engagement types are most successful
            engagement_types = [e.get("type", "") for e in engagements]
            type_counts = {}
            for etype in engagement_types:
                type_counts[etype] = type_counts.get(etype, 0) + 1

            # Return most common types
            sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
            return [t[0] for t in sorted_types[:3]]

        except Exception as e:
            self.logger.error(f"Error identifying communication preferences: {e}")
            return ["Email", "Phone"]

    async def _generate_engagement_recommendations(
        self,
        engagement_level: EngagementLevel,
        touchpoint_analysis: Dict[str, float]
    ) -> List[str]:
        """Generate engagement recommendations"""
        try:
            recommendations = []

            if engagement_level == EngagementLevel.HIGH:
                recommendations.extend([
                    "Maintain current engagement frequency",
                    "Focus on value-added interactions",
                    "Identify upsell opportunities"
                ])
            elif engagement_level == EngagementLevel.MEDIUM:
                recommendations.extend([
                    "Increase touchpoint frequency",
                    "Personalize communication content",
                    "Schedule regular check-ins"
                ])
            elif engagement_level == EngagementLevel.LOW:
                recommendations.extend([
                    "Re-engagement campaign needed",
                    "Identify pain points and objections",
                    "Provide additional value and resources"
                ])
            else:  # INACTIVE
                recommendations.extend([
                    "Immediate re-engagement required",
                    "Assess relationship health",
                    "Consider win-back campaign"
                ])

            return recommendations[:3]

        except Exception as e:
            self.logger.error(f"Error generating engagement recommendations: {e}")
            return ["Review engagement strategy and adjust accordingly"]

    async def _identify_stalled_deals(self, deals: List[Dict[str, Any]]) -> List[StalledDealRecovery]:
        """Identify stalled deals and create recovery strategies"""
        try:
            stalled_deals = []

            for deal in deals:
                # Check if deal is stalled
                if await self._is_deal_stalled(deal):
                    recovery = await self._create_recovery_strategy(deal)
                    if recovery:
                        stalled_deals.append(recovery)

            return stalled_deals

        except Exception as e:
            self.logger.error(f"Error identifying stalled deals: {e}")
            return []

    async def _is_deal_stalled(self, deal: Dict[str, Any]) -> bool:
        """Check if deal is stalled"""
        try:
            # Skip closed deals
            if deal.get("dealstage") in ["closed_won", "closed_lost"]:
                return False

            # Check days in current stage
            if "createdate" in deal:
                created_date = datetime.fromisoformat(deal["createdate"].replace('Z', '+00:00'))
                days_in_stage = (datetime.now(timezone.utc) - created_date).days

                stall_thresholds = self.health_scoring_config["stall_thresholds"]
                return days_in_stage > stall_thresholds["days_in_stage"]

            return False

        except Exception as e:
            self.logger.error(f"Error checking if deal is stalled: {e}")
            return False

    async def _create_recovery_strategy(self, deal: Dict[str, Any]) -> Optional[StalledDealRecovery]:
        """Create recovery strategy for stalled deal"""
        try:
            # Calculate stall duration
            if "createdate" in deal:
                created_date = datetime.fromisoformat(deal["createdate"].replace('Z', '+00:00'))
                stall_duration = (datetime.now(timezone.utc) - created_date).days
            else:
                stall_duration = 0

            # Identify stall reasons
            stall_reasons = [
                "No recent activity",
                "Extended time in current stage",
                "Potential buyer disengagement"
            ]

            # Generate recovery strategies
            recovery_strategies = [
                "Schedule executive check-in call",
                "Re-qualify deal opportunity",
                "Offer additional value proposition"
            ]

            # Create communication plan
            communication_plan = [
                "Immediate personalized outreach",
                "Value-focused follow-up within 3 days",
                "Executive involvement if no response"
            ]

            return StalledDealRecovery(
                recovery_id=f"recovery_{deal.get('dealId', '')}_{uuid.uuid4().hex[:8]}",
                deal_id=deal.get("dealId", ""),
                deal_name=deal.get("dealname", "Unknown Deal"),
                stall_duration=stall_duration,
                stall_reasons=stall_reasons,
                recovery_strategies=recovery_strategies,
                communication_plan=communication_plan,
                value_proposition_adjustment="Focus on ROI and business outcomes",
                incentive_options=["Limited-time discount", "Extended trial", "Additional services"],
                estimated_recovery_probability=0.6,
                next_action_owner="Account Executive",
                recovery_timeline="2-4 weeks",
                success_metrics=["Deal progression", "Re-engagement response", "Conversion to next stage"],
                created_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error creating recovery strategy: {e}")
            return None

    async def _summarize_deal_health(self, deal_health_scores: List[DealHealthScore]) -> Dict[str, Any]:
        """Summarize deal health across all deals"""
        try:
            if not deal_health_scores:
                return {
                    "total_deals": 0,
                    "average_health_score": 0,
                    "health_distribution": {},
                    "critical_deals": []
                }

            total_deals = len(deal_health_scores)
            avg_health_score = statistics.mean([d.health_score for d in deal_health_scores])

            # Health distribution
            health_counts = {}
            for score in deal_health_scores:
                status = score.health_status.value
                health_counts[status] = health_counts.get(status, 0) + 1

            # Critical deals requiring immediate attention
            critical_deals = [
                {
                    "deal_id": d.deal_id,
                    "deal_name": d.deal_name,
                    "health_score": d.health_score,
                    "next_best_action": d.next_best_action
                }
                for d in deal_health_scores
                if d.health_status == DealHealth.CRITICAL
            ]

            return {
                "total_deals": total_deals,
                "average_health_score": round(avg_health_score, 1),
                "health_distribution": health_counts,
                "critical_deals": critical_deals,
                "at_risk_count": len([d for d in deal_health_scores if d.health_status == DealHealth.AT_RISK])
            }

        except Exception as e:
            self.logger.error(f"Error summarizing deal health: {e}")
            return {"error": str(e)}

    async def _summarize_engagement(self, engagement_analysis: List[EngagementAnalysis]) -> Dict[str, Any]:
        """Summarize engagement analysis"""
        try:
            if not engagement_analysis:
                return {
                    "total_customers": 0,
                    "average_engagement_score": 0,
                    "engagement_distribution": {}
                }

            total_customers = len(engagement_analysis)
            avg_engagement_score = statistics.mean([e.overall_engagement_score for e in engagement_analysis])

            # Engagement distribution
            engagement_counts = {}
            for analysis in engagement_analysis:
                level = analysis.engagement_level.value
                engagement_counts[level] = engagement_counts.get(level, 0) + 1

            return {
                "total_customers": total_customers,
                "average_engagement_score": round(avg_engagement_score, 1),
                "engagement_distribution": engagement_counts,
                "high_engagement_customers": len([e for e in engagement_analysis if e.engagement_level == EngagementLevel.HIGH]),
                "inactive_customers": len([e for e in engagement_analysis if e.engagement_level == EngagementLevel.INACTIVE])
            }

        except Exception as e:
            self.logger.error(f"Error summarizing engagement: {e}")
            return {"error": str(e)}

    async def _generate_crm_recommendations(
        self,
        deal_metrics: DealMetrics,
        deal_health_scores: List[DealHealthScore],
        pipeline_optimizations: List[PipelineOptimization],
        customer_segments: List[CustomerSegment],
        engagement_analysis: List[EngagementAnalysis],
        stalled_deals: List[StalledDealRecovery]
    ) -> List[str]:
        """Generate comprehensive CRM recommendations"""
        try:
            recommendations = []

            # Deal metrics recommendations
            if deal_metrics.win_rate < 20:
                recommendations.append("Improve sales win rate through better qualification and value proposition")

            if deal_metrics.sales_cycle_length > 90:
                recommendations.append("Reduce sales cycle length through streamlined processes")

            if deal_metrics.pipeline_health_score < 60:
                recommendations.append("Address pipeline health issues through stage-specific optimizations")

            # Deal health recommendations
            critical_deals = len([d for d in deal_health_scores if d.health_status == DealHealth.CRITICAL])
            if critical_deals > 0:
                recommendations.append(f"Immediate attention needed for {critical_deals} critical deals")

            # Pipeline optimization recommendations
            if pipeline_optimizations:
                high_priority_opts = [opt for opt in pipeline_optimizations if opt.priority_score > 0.5]
                if high_priority_opts:
                    recommendations.append(f"Implement {len(high_priority_opts)} high-priority pipeline optimizations")

            # Customer segment recommendations
            high_value_segments = [seg for seg in customer_segments if seg.average_customer_value > 50000]
            if high_value_segments:
                recommendations.append(f"Focus on {high_value_segments[0].segment_name} segment with high-value opportunities")

            # Engagement recommendations
            inactive_customers = len([e for e in engagement_analysis if e.engagement_level == EngagementLevel.INACTIVE])
            if inactive_customers > 0:
                recommendations.append(f"Launch re-engagement campaign for {inactive_customers} inactive customers")

            # Stalled deals recommendations
            if stalled_deals:
                total_stalled_value = sum(d.stall_duration for d in stalled_deals)  # Simplified
                recommendations.append(f"Implement recovery strategies for {len(stalled_deals)} stalled deals")

            return recommendations[:8]  # Top 8 recommendations

        except Exception as e:
            self.logger.error(f"Error generating CRM recommendations: {e}")
            return ["Review CRM performance and implement targeted improvements"]

    async def _generate_crm_executive_summary(self, analysis_data: Dict[str, Any]) -> str:
        """Generate executive summary of CRM analysis"""
        try:
            # Prepare context for LLM
            context = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "deal_metrics": analysis_data["deal_metrics"].__dict__,
                "critical_deals": len([d for d in analysis_data["deal_health"] if d.health_status == DealHealth.CRITICAL]),
                "pipeline_optimizations": len(analysis_data["pipeline_optimizations"]),
                "customer_segments": len(analysis_data["customer_segments"]),
                "stalled_deals": len(analysis_data["stalled_deals"])
            }

            system_prompt = """
            You are a sales operations analyst creating an executive summary of CRM performance.

            Create a concise, actionable executive summary that:
            1. Highlights key CRM performance metrics
            2. Identifies critical issues requiring attention
            3. Summarizes strategic opportunities
            4. Provides actionable recommendations
            5. Maintains a professional, data-driven tone

            Keep the summary to 200-250 words maximum. Focus on insights that drive sales performance improvement.
            """

            human_prompt = f"""
            Generate an executive summary based on this CRM performance analysis:

            {json.dumps(context, indent=2)}

            Focus on the most critical insights and actionable recommendations for sales leadership.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            self.logger.error(f"Error generating CRM executive summary: {e}")
            return "Executive summary generation failed. Please review the detailed CRM analysis."

    async def _assess_crm_data_quality(self, crm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality of CRM data"""
        try:
            quality_metrics = {
                "data_completeness": 0.0,
                "data_accuracy": 0.0,
                "data_freshness": 0.0,
                "overall_quality": 0.0
            }

            # Assess completeness
            total_fields = 0
            complete_fields = 0

            for deal in crm_data.get("deals", []):
                required_fields = ["dealname", "amount", "dealstage", "closedate"]
                total_fields += len(required_fields)
                complete_fields += sum(1 for field in required_fields if deal.get(field))

            quality_metrics["data_completeness"] = (complete_fields / max(1, total_fields)) * 100

            # Assess accuracy (simplified)
            quality_metrics["data_accuracy"] = 85.0

            # Assess freshness (simplified)
            quality_metrics["data_freshness"] = 90.0

            # Calculate overall quality
            quality_metrics["overall_quality"] = (
                quality_metrics["data_completeness"] * 0.4 +
                quality_metrics["data_accuracy"] * 0.3 +
                quality_metrics["data_freshness"] * 0.3
            )

            return quality_metrics

        except Exception as e:
            self.logger.error(f"Error assessing CRM data quality: {e}")
            return {"overall_quality": 50, "error": str(e)}

    async def _store_crm_analysis(self, analysis: Dict[str, Any], user_id: str):
        """Store CRM analysis in Firebase"""
        try:
            await self.firebase_service.store_agent_file(
                f"crm_intelligence/{user_id}/analysis/{analysis['analysis_id']}",
                json.dumps(analysis, indent=2, default=str)
            )

            self.logger.info(f"Stored CRM analysis {analysis['analysis_id']}")

        except Exception as e:
            self.logger.error(f"Error storing CRM analysis: {e}")

    async def get_deal_health_insights(
        self,
        user_id: str,
        health_filter: str = None
    ) -> Dict[str, Any]:
        """Get deal health insights"""
        try:
            # Get latest analysis
            analysis_data = await self._get_latest_crm_analysis(user_id)

            if not analysis_data:
                return {"error": "No CRM analysis available"}

            deal_health_summary = analysis_data.get("deal_health_summary", {})

            # Apply filter if specified
            if health_filter:
                # Filter deals based on health status
                pass

            return {
                "summary": deal_health_summary,
                "recommendations": await self._get_health_recommendations(deal_health_summary),
                "last_updated": analysis_data.get("generated_at")
            }

        except Exception as e:
            self.logger.error(f"Error getting deal health insights: {e}")
            return {"error": str(e)}

    async def _get_latest_crm_analysis(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get latest CRM analysis"""
        try:
            analysis_files = await self.firebase_service.get_agent_files_by_prefix(
                f"crm_intelligence/{user_id}/analysis/"
            )

            if not analysis_files:
                return None

            # Sort by date and get latest
            latest_file = max(analysis_files, key=lambda x: x.get("modified", ""))
            return json.loads(latest_file.get("content", "{}"))

        except Exception as e:
            self.logger.error(f"Error getting latest CRM analysis: {e}")
            return None

    async def _get_health_recommendations(self, deal_health_summary: Dict[str, Any]) -> List[str]:
        """Get health-specific recommendations"""
        try:
            recommendations = []

            critical_count = deal_health_summary.get("critical_deals", [])
            if len(critical_count) > 0:
                recommendations.append("Immediate intervention required for critical deals")

            at_risk_count = deal_health_summary.get("at_risk_count", 0)
            if at_risk_count > 5:
                recommendations.append("Review and re-qualify at-risk deals")

            avg_health = deal_health_summary.get("average_health_score", 0)
            if avg_health < 60:
                recommendations.append("Overall pipeline health requires attention")
                recommendations.append("Implement structured health monitoring process")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error getting health recommendations: {e}")
            return ["Review deal health and implement improvement strategies"]