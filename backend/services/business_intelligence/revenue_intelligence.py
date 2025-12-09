"""
Revenue Intelligence Analytics Engine
Advanced revenue analytics with forecasting, CAC/LTV analysis,
churn prediction, and pricing optimization recommendations.
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
from agents.base_agent import BaseAgent


class RevenueType(str, Enum):
    MRR = "mrr"  # Monthly Recurring Revenue
    ARR = "arr"  # Annual Recurring Revenue
    ONE_TIME = "one_time"  # One-time revenue
    EXPANSION = "expansion"  # Expansion revenue
    CONTRACTION = "contraction"  # Contraction revenue
    CHURNED = "churned"  # Churned revenue


class ForecastModel(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"
    ARIMA = "arima"
    ENSEMBLE = "ensemble"


class ConfidenceLevel(str, Enum):
    LOW = "low"      # 60% confidence
    MEDIUM = "medium"  # 80% confidence
    HIGH = "high"    # 95% confidence


@dataclass
class RevenueMetrics:
    """Comprehensive revenue metrics"""
    period: str
    mrr: float
    arr: float
    new_mrr: float
    expansion_mrr: float
    contraction_mrr: float
    churned_mrr: float
    net_new_mrr: float
    mrr_growth_rate: float
    revenue_per_customer: float
    average_contract_value: float
    cash_flow: float
    gross_margin: float
    net_margin: float


@dataclass
class CustomerMetrics:
    """Customer acquisition and retention metrics"""
    new_customers: int
    churned_customers: int
    net_new_customers: int
    customer_growth_rate: float
    customer_churn_rate: float
    customer_lifetime_value: float
    customer_acquisition_cost: float
    ltv_cac_ratio: float
    payback_period: float  # months
    revenue_per_customer: float


@dataclass
class RevenueForecast:
    """Revenue forecast with confidence intervals"""
    forecast_id: str
    model_type: ForecastModel
    period: str
    forecast_mrr: float
    confidence_interval: Tuple[float, float]  # (lower_bound, upper_bound)
    confidence_level: ConfidenceLevel
    accuracy_score: float
    trend_direction: str
    seasonal_adjustment: float
    key_drivers: List[str]
    risk_factors: List[str]
    generated_at: datetime


@dataclass
class PricingRecommendation:
    """Pricing optimization recommendation"""
    id: str
    recommendation_type: str  # price_increase, decrease, new_tier, packaging
    current_price: float
    recommended_price: float
    expected_impact: Dict[str, float]
    confidence_score: float
    implementation_effort: str
    time_to_impact: str
    risks: List[str]
    benefits: List[str]
    target_segments: List[str]
    testing_approach: str


@dataclass
class ChurnPrediction:
    """Customer churn prediction and prevention"""
    customer_id: str
    customer_name: str
    churn_probability: float
    risk_level: str
    key_indicators: List[str]
    predicted_churn_date: Optional[datetime]
    recommended_actions: List[str]
    intervention_cost: float
    retention_probability: float
    customer_value: float
    last_updated: datetime


class RevenueIntelligenceEngine:
    """Advanced revenue intelligence analytics engine"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.hubspot_service = get_hubspot_service()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            max_tokens=3000,
            openai_api_key=openai_api_key
        )

        # Cache for performance
        self._forecast_cache = {}
        self._metrics_cache = {}
        self._cache_expiry = {}

    async def generate_revenue_analysis(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        include_forecasts: bool = True,
        forecast_months: int = 12
    ) -> Dict[str, Any]:
        """Generate comprehensive revenue intelligence analysis"""
        try:
            self.logger.info(f"Generating revenue analysis for user {user_id}")

            # Collect revenue data
            revenue_metrics = await self._calculate_revenue_metrics(user_id, start_date, end_date)
            customer_metrics = await self._calculate_customer_metrics(user_id, start_date, end_date)

            # Generate forecasts
            forecasts = []
            if include_forecasts:
                forecasts = await self._generate_revenue_forecasts(
                    user_id, end_date, forecast_months
                )

            # Analyze pricing optimization opportunities
            pricing_recommendations = await self._analyze_pricing_optimization(
                user_id, revenue_metrics, customer_metrics
            )

            # Predict customer churn
            churn_predictions = await self._predict_customer_churn(user_id)

            # Generate strategic recommendations
            strategic_recommendations = await self._generate_strategic_recommendations(
                revenue_metrics, customer_metrics, forecasts, churn_predictions
            )

            # Calculate revenue health score
            health_score = await self._calculate_revenue_health_score(
                revenue_metrics, customer_metrics, churn_predictions
            )

            analysis = {
                "analysis_id": f"revenue_analysis_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "revenue_metrics": asdict(revenue_metrics),
                "customer_metrics": asdict(customer_metrics),
                "forecasts": [asdict(forecast) for forecast in forecasts],
                "pricing_recommendations": [asdict(rec) for rec in pricing_recommendations],
                "churn_predictions": [asdict(pred) for pred in churn_predictions[:10]],  # Top 10
                "strategic_recommendations": strategic_recommendations,
                "health_score": health_score,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_quality": await self._assess_data_quality(user_id, start_date, end_date)
            }

            # Store analysis in Firebase
            await self._store_revenue_analysis(analysis, user_id)

            self.logger.info(f"Successfully generated revenue analysis {analysis['analysis_id']}")
            return analysis

        except Exception as e:
            self.logger.error(f"Error generating revenue analysis: {e}")
            raise

    async def _calculate_revenue_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> RevenueMetrics:
        """Calculate comprehensive revenue metrics"""
        try:
            # Get revenue data from HubSpot and other sources
            hubspot_data = await self.hubspot_service.get_revenue_data(user_id, start_date, end_date)

            # Calculate MRR components
            current_mrr = hubspot_data.get("current_mrr", 0)
            previous_mrr = hubspot_data.get("previous_mrr", 0)
            new_mrr = hubspot_data.get("new_mrr", 0)
            expansion_mrr = hubspot_data.get("expansion_mrr", 0)
            contraction_mrr = hubspot_data.get("contraction_mrr", 0)
            churned_mrr = hubspot_data.get("churned_mrr", 0)

            # Calculate net new MRR and growth rate
            net_new_mrr = new_mrr + expansion_mrr - contraction_mrr - churned_mrr
            mrr_growth_rate = (net_new_mrr / previous_mrr) * 100 if previous_mrr > 0 else 0

            # Calculate additional metrics
            total_customers = hubspot_data.get("total_customers", 1)
            revenue_per_customer = current_mrr / total_customers if total_customers > 0 else 0
            average_contract_value = hubspot_data.get("average_contract_value", revenue_per_customer)

            # Financial metrics
            cash_flow = hubspot_data.get("cash_flow", 0)
            gross_margin = hubspot_data.get("gross_margin", 0)
            net_margin = hubspot_data.get("net_margin", 0)

            return RevenueMetrics(
                period=f"{start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}",
                mrr=current_mrr,
                arr=current_mrr * 12,
                new_mrr=new_mrr,
                expansion_mrr=expansion_mrr,
                contraction_mrr=contraction_mrr,
                churned_mrr=churned_mrr,
                net_new_mrr=net_new_mrr,
                mrr_growth_rate=mrr_growth_rate,
                revenue_per_customer=revenue_per_customer,
                average_contract_value=average_contract_value,
                cash_flow=cash_flow,
                gross_margin=gross_margin,
                net_margin=net_margin
            )

        except Exception as e:
            self.logger.error(f"Error calculating revenue metrics: {e}")
            # Return default metrics
            return RevenueMetrics(
                period="error",
                mrr=0, arr=0, new_mrr=0, expansion_mrr=0,
                contraction_mrr=0, churned_mrr=0, net_new_mrr=0,
                mrr_growth_rate=0, revenue_per_customer=0, average_contract_value=0,
                cash_flow=0, gross_margin=0, net_margin=0
            )

    async def _calculate_customer_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> CustomerMetrics:
        """Calculate customer acquisition and retention metrics"""
        try:
            # Get customer data from HubSpot
            hubspot_data = await self.hubspot_service.get_customer_data(user_id, start_date, end_date)

            new_customers = hubspot_data.get("new_customers", 0)
            churned_customers = hubspot_data.get("churned_customers", 0)
            total_customers_start = hubspot_data.get("total_customers_start", 1)
            total_customers_end = hubspot_data.get("total_customers_end", 1)

            # Calculate net new customers and rates
            net_new_customers = new_customers - churned_customers
            customer_growth_rate = (net_new_customers / total_customers_start) * 100 if total_customers_start > 0 else 0
            customer_churn_rate = (churned_customers / total_customers_start) * 100 if total_customers_start > 0 else 0

            # LTV and CAC calculations
            monthly_revenue_per_customer = hubspot_data.get("monthly_revenue_per_customer", 0)
            gross_margin_percentage = hubspot_data.get("gross_margin_percentage", 0.8)

            # Customer Lifetime Value
            customer_lifetime_value = (monthly_revenue_per_customer * 12 * gross_margin_percentage) / customer_churn_rate if customer_churn_rate > 0 else 0

            # Customer Acquisition Cost
            total_sales_marketing_spend = hubspot_data.get("total_sales_marketing_spend", 0)
            customer_acquisition_cost = total_sales_marketing_spend / new_customers if new_customers > 0 else 0

            # LTV:CAC Ratio
            ltv_cac_ratio = customer_lifetime_value / customer_acquisition_cost if customer_acquisition_cost > 0 else 0

            # Payback period in months
            payback_period = customer_acquisition_cost / (monthly_revenue_per_customer * gross_margin_percentage) if monthly_revenue_per_customer > 0 else 0

            return CustomerMetrics(
                new_customers=new_customers,
                churned_customers=churned_customers,
                net_new_customers=net_new_customers,
                customer_growth_rate=customer_growth_rate,
                customer_churn_rate=customer_churn_rate,
                customer_lifetime_value=customer_lifetime_value,
                customer_acquisition_cost=customer_acquisition_cost,
                ltv_cac_ratio=ltv_cac_ratio,
                payback_period=payback_period,
                revenue_per_customer=monthly_revenue_per_customer
            )

        except Exception as e:
            self.logger.error(f"Error calculating customer metrics: {e}")
            return CustomerMetrics(
                new_customers=0, churned_customers=0, net_new_customers=0,
                customer_growth_rate=0, customer_churn_rate=0,
                customer_lifetime_value=0, customer_acquisition_cost=0,
                ltv_cac_ratio=0, payback_period=0, revenue_per_customer=0
            )

    async def _generate_revenue_forecasts(
        self,
        user_id: str,
        base_date: datetime,
        months: int
    ) -> List[RevenueForecast]:
        """Generate revenue forecasts using multiple models"""
        try:
            forecasts = []

            # Get historical data for model training
            historical_data = await self._get_historical_revenue_data(user_id, months_back=24)

            # Generate forecasts using different models
            models = [ForecastModel.LINEAR, ForecastModel.EXPONENTIAL, ForecastModel.SEASONAL]

            for model_type in models:
                forecast = await self._generate_single_forecast(
                    model_type, historical_data, base_date, months
                )
                forecasts.append(forecast)

            # Generate ensemble forecast
            ensemble_forecast = await self._generate_ensemble_forecast(forecasts)
            forecasts.append(ensemble_forecast)

            return forecasts

        except Exception as e:
            self.logger.error(f"Error generating revenue forecasts: {e}")
            return []

    async def _generate_single_forecast(
        self,
        model_type: ForecastModel,
        historical_data: List[Dict[str, Any]],
        base_date: datetime,
        months: int
    ) -> RevenueForecast:
        """Generate forecast using a specific model"""
        try:
            if not historical_data:
                # Return default forecast if no data
                return RevenueForecast(
                    forecast_id=f"forecast_{model_type.value}_{uuid.uuid4().hex[:8]}",
                    model_type=model_type,
                    period=f"{months} months",
                    forecast_mrr=0,
                    confidence_interval=(0, 0),
                    confidence_level=ConfidenceLevel.LOW,
                    accuracy_score=0.0,
                    trend_direction="unknown",
                    seasonal_adjustment=0,
                    key_drivers=[],
                    risk_factors=["Insufficient historical data"],
                    generated_at=datetime.now(timezone.utc)
                )

            # Extract MRR values
            mrr_values = [data.get("mrr", 0) for data in historical_data]

            if model_type == ForecastModel.LINEAR:
                forecast_mrr = self._linear_forecast(mrr_values, months)
            elif model_type == ForecastModel.EXPONENTIAL:
                forecast_mrr = self._exponential_forecast(mrr_values, months)
            elif model_type == ForecastModel.SEASONAL:
                forecast_mrr = self._seasonal_forecast(mrr_values, months)
            else:
                forecast_mrr = mrr_values[-1] if mrr_values else 0

            # Calculate confidence interval
            std_dev = statistics.stdev(mrr_values) if len(mrr_values) > 1 else 0
            confidence_interval = (
                max(0, forecast_mrr - 1.96 * std_dev),
                forecast_mrr + 1.96 * std_dev
            )

            # Determine trend direction
            if len(mrr_values) >= 3:
                recent_trend = statistics.mean(mrr_values[-3:]) - statistics.mean(mrr_values[-6:-3]) if len(mrr_values) >= 6 else 0
                trend_direction = "up" if recent_trend > 0 else "down" if recent_trend < 0 else "stable"
            else:
                trend_direction = "stable"

            # Calculate accuracy score based on historical volatility
            if len(mrr_values) > 1:
                cv = (std_dev / statistics.mean(mrr_values)) * 100 if statistics.mean(mrr_values) > 0 else 100
                accuracy_score = max(0, min(100, 100 - cv)) / 100
            else:
                accuracy_score = 0.5

            return RevenueForecast(
                forecast_id=f"forecast_{model_type.value}_{uuid.uuid4().hex[:8]}",
                model_type=model_type,
                period=f"{months} months",
                forecast_mrr=forecast_mrr,
                confidence_interval=confidence_interval,
                confidence_level=ConfidenceLevel.HIGH if accuracy_score > 0.8 else ConfidenceLevel.MEDIUM,
                accuracy_score=accuracy_score,
                trend_direction=trend_direction,
                seasonal_adjustment=0.1 if model_type == ForecastModel.SEASONAL else 0,
                key_drivers=self._identify_key_drivers(historical_data),
                risk_factors=self._identify_risk_factors(historical_data, trend_direction),
                generated_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error generating single forecast: {e}")
            raise

    def _linear_forecast(self, values: List[float], periods: int) -> float:
        """Simple linear forecast"""
        if len(values) < 2:
            return values[-1] if values else 0

        # Calculate trend
        changes = [values[i] - values[i-1] for i in range(1, len(values))]
        avg_change = statistics.mean(changes)

        # Project forward
        return values[-1] + (avg_change * periods)

    def _exponential_forecast(self, values: List[float], periods: int) -> float:
        """Exponential growth forecast"""
        if len(values) < 2:
            return values[-1] if values else 0

        # Calculate growth rate
        growth_rates = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                growth_rates.append((values[i] - values[i-1]) / values[i-1])

        if not growth_rates:
            return values[-1]

        avg_growth_rate = statistics.mean(growth_rates)

        # Project forward with compound growth
        last_value = values[-1]
        for _ in range(periods):
            last_value *= (1 + avg_growth_rate)

        return last_value

    def _seasonal_forecast(self, values: List[float], periods: int) -> float:
        """Seasonal adjusted forecast"""
        if len(values) < 12:
            return self._linear_forecast(values, periods)

        # Calculate seasonal factors (simplified)
        seasonal_factors = []
        for month in range(12):
            if month < len(values):
                # Compare to annual average
                annual_avg = statistics.mean(values)
                seasonal_factor = values[month] / annual_avg if annual_avg > 0 else 1
                seasonal_factors.append(seasonal_factor)

        # Use linear forecast as base and apply seasonal adjustment
        base_forecast = self._linear_forecast(values, periods)

        # Apply seasonal factor for the target month
        target_month = (datetime.now().month + periods - 1) % 12
        seasonal_adjustment = seasonal_factors[target_month] if target_month < len(seasonal_factors) else 1

        return base_forecast * seasonal_adjustment

    async def _generate_ensemble_forecast(self, forecasts: List[RevenueForecast]) -> RevenueForecast:
        """Generate ensemble forecast from multiple models"""
        try:
            if not forecasts:
                raise ValueError("No forecasts to ensemble")

            # Weight forecasts by accuracy
            total_accuracy = sum(f.accuracy_score for f in forecasts)
            if total_accuracy == 0:
                # Equal weights if no accuracy scores
                weights = [1/len(forecasts)] * len(forecasts)
            else:
                weights = [f.accuracy_score / total_accuracy for f in forecasts]

            # Calculate weighted average forecast
            weighted_forecast = sum(f.forecast_mrr * w for f, w in zip(forecasts, weights))

            # Calculate ensemble confidence interval (wider than individual models)
            lower_bounds = [f.confidence_interval[0] for f in forecasts]
            upper_bounds = [f.confidence_interval[1] for f in forecasts]

            ensemble_lower = weighted_forecast - (weighted_forecast - min(lower_bounds)) * 1.2
            ensemble_upper = weighted_forecast + (max(upper_bounds) - weighted_forecast) * 1.2

            # Determine ensemble trend
            trend_votes = {"up": 0, "down": 0, "stable": 0}
            for f in forecasts:
                trend_votes[f.trend_direction] += 1

            ensemble_trend = max(trend_votes, key=trend_votes.get)

            # Combine key drivers and risk factors
            all_drivers = []
            all_risks = []
            for f in forecasts:
                all_drivers.extend(f.key_drivers)
                all_risks.extend(f.risk_factors)

            # Remove duplicates
            key_drivers = list(set(all_drivers))
            risk_factors = list(set(all_risks))

            return RevenueForecast(
                forecast_id=f"forecast_ensemble_{uuid.uuid4().hex[:8]}",
                model_type=ForecastModel.ENSEMBLE,
                period=f"{forecasts[0].period}",
                forecast_mrr=weighted_forecast,
                confidence_interval=(max(0, ensemble_lower), ensemble_upper),
                confidence_level=ConfidenceLevel.HIGH,
                accuracy_score=max(f.accuracy_score for f in forecasts) * 0.9,  # Slightly conservative
                trend_direction=ensemble_trend,
                seasonal_adjustment=statistics.mean([f.seasonal_adjustment for f in forecasts]),
                key_drivers=key_drivers[:5],  # Top 5 drivers
                risk_factors=risk_factors[:5],  # Top 5 risks
                generated_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error generating ensemble forecast: {e}")
            raise

    def _identify_key_drivers(self, historical_data: List[Dict[str, Any]]) -> List[str]:
        """Identify key revenue drivers from historical data"""
        drivers = []

        if not historical_data:
            return ["Insufficient data for analysis"]

        # Analyze trends in the data
        recent_data = historical_data[-6:] if len(historical_data) >= 6 else historical_data
        older_data = historical_data[-12:-6] if len(historical_data) >= 12 else historical_data[:-len(recent_data)]

        if len(recent_data) > 0 and len(older_data) > 0:
            recent_avg = statistics.mean([d.get("new_customers", 0) for d in recent_data])
            older_avg = statistics.mean([d.get("new_customers", 0) for d in older_data])

            if recent_avg > older_avg * 1.1:
                drivers.append("Strong customer acquisition growth")
            elif recent_avg < older_avg * 0.9:
                drivers.append("Declining customer acquisition")

            # Check expansion revenue
            recent_expansion = statistics.mean([d.get("expansion_mrr", 0) for d in recent_data])
            older_expansion = statistics.mean([d.get("expansion_mrr", 0) for d in older_data])

            if recent_expansion > older_expansion * 1.1:
                drivers.append("Strong expansion revenue from existing customers")

        if not drivers:
            drivers.append("Stable revenue performance")

        return drivers[:3]

    def _identify_risk_factors(self, historical_data: List[Dict[str, Any]], trend_direction: str) -> List[str]:
        """Identify risk factors based on historical data and trends"""
        risks = []

        if trend_direction == "down":
            risks.append("Declining revenue trend")

        if len(historical_data) >= 3:
            # Check churn trend
            recent_churn = [d.get("churned_mrr", 0) for d in historical_data[-3:]]
            if sum(recent_churn) > 0:
                risks.append("Customer revenue churn")

            # Check concentration risk (simplified)
            avg_deal_size = statistics.mean([d.get("average_contract_value", 0) for d in historical_data[-3:]])
            if avg_deal_size > 0:
                # High concentration in large deals could be risky
                risks.append("Revenue concentration in large deals")

        # Check for seasonality risks
        if len(historical_data) >= 12:
            monthly_values = [d.get("mrr", 0) for d in historical_data[-12:]]
            if len(monthly_values) > 1:
                cv = (statistics.stdev(monthly_values) / statistics.mean(monthly_values)) * 100 if statistics.mean(monthly_values) > 0 else 0
                if cv > 30:  # High coefficient of variation
                    risks.append("High revenue seasonality/volatility")

        if not risks:
            risks.append("Market competition risks")

        return risks[:3]

    async def _get_historical_revenue_data(self, user_id: str, months_back: int = 24) -> List[Dict[str, Any]]:
        """Get historical revenue data for forecasting"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=months_back * 30)

            # Get data from HubSpot
            hubspot_data = await self.hubspot_service.get_historical_revenue_data(
                user_id, start_date, end_date
            )

            return hubspot_data

        except Exception as e:
            self.logger.error(f"Error getting historical revenue data: {e}")
            return []

    async def _analyze_pricing_optimization(
        self,
        user_id: str,
        revenue_metrics: RevenueMetrics,
        customer_metrics: CustomerMetrics
    ) -> List[PricingRecommendation]:
        """Analyze pricing optimization opportunities"""
        try:
            recommendations = []

            # Get competitor pricing data
            competitor_data = await self._get_competitor_pricing_data(user_id)

            # Analyze current pricing performance
            current_performance = await self._analyze_pricing_performance(user_id)

            # Generate pricing recommendations using LLM
            pricing_analysis = await self._generate_pricing_analysis_with_llm(
                revenue_metrics, customer_metrics, competitor_data, current_performance
            )

            for analysis in pricing_analysis:
                recommendation = PricingRecommendation(
                    id=f"pricing_rec_{uuid.uuid4().hex[:8]}",
                    recommendation_type=analysis.get("type", "price_adjustment"),
                    current_price=analysis.get("current_price", 0),
                    recommended_price=analysis.get("recommended_price", 0),
                    expected_impact=analysis.get("expected_impact", {}),
                    confidence_score=analysis.get("confidence_score", 0.5),
                    implementation_effort=analysis.get("implementation_effort", "medium"),
                    time_to_impact=analysis.get("time_to_impact", "3 months"),
                    risks=analysis.get("risks", []),
                    benefits=analysis.get("benefits", []),
                    target_segments=analysis.get("target_segments", []),
                    testing_approach=analysis.get("testing_approach", "A/B testing")
                )
                recommendations.append(recommendation)

            return recommendations

        except Exception as e:
            self.logger.error(f"Error analyzing pricing optimization: {e}")
            return []

    async def _get_competitor_pricing_data(self, user_id: str) -> Dict[str, Any]:
        """Get competitor pricing data for analysis"""
        try:
            # This would integrate with competitive intelligence tools
            # For now, return mock data
            return {
                "competitor_count": 5,
                "average_price": 299.0,
                "price_range": {"min": 99.0, "max": 999.0},
                "pricing_models": ["tiered", "usage_based", "per_seat"],
                "market_positioning": "premium"
            }

        except Exception as e:
            self.logger.error(f"Error getting competitor pricing data: {e}")
            return {}

    async def _analyze_pricing_performance(self, user_id: str) -> Dict[str, Any]:
        """Analyze current pricing performance"""
        try:
            # Get pricing performance metrics from HubSpot
            return {
                "conversion_rate_by_price_tier": {
                    "basic": 0.15,
                    "professional": 0.08,
                    "enterprise": 0.03
                },
                "win_loss_ratio": 0.7,
                "average_sales_cycle": 45,
                "price_sensitivity_score": 0.6
            }

        except Exception as e:
            self.logger.error(f"Error analyzing pricing performance: {e}")
            return {}

    async def _generate_pricing_analysis_with_llm(
        self,
        revenue_metrics: RevenueMetrics,
        customer_metrics: CustomerMetrics,
        competitor_data: Dict[str, Any],
        current_performance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate pricing analysis using LLM"""
        try:
            context = {
                "revenue_metrics": asdict(revenue_metrics),
                "customer_metrics": asdict(customer_metrics),
                "competitor_data": competitor_data,
                "current_performance": current_performance
            }

            system_prompt = """
            You are a pricing strategy expert analyzing SaaS revenue data to provide actionable pricing recommendations.

            Analyze the provided data and generate 3-4 specific pricing recommendations. For each recommendation:
            1. Identify the type (price_increase, price_decrease, new_tier, packaging_change)
            2. Provide specific pricing recommendations with rationale
            3. Estimate expected impact on revenue and customer acquisition
            4. Assess confidence level and implementation difficulty
            5. Identify key risks and benefits
            6. Suggest testing approach

            Consider:
            - Current revenue trends and growth rates
            - Customer acquisition costs and lifetime value
            - Competitive positioning
            - Conversion rates and sales performance
            - Market demand and price sensitivity

            Be specific, data-driven, and focus on actionable recommendations that can be tested and measured.
            """

            human_prompt = f"""
            Analyze the following SaaS business data and provide pricing optimization recommendations:

            {json.dumps(context, indent=2)}

            Provide specific, actionable pricing recommendations with clear rationale and expected impact.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse the response to extract structured recommendations
            # This is a simplified parser - in production, you'd want more sophisticated parsing
            recommendations_text = response.content.strip()

            # Generate structured recommendations based on common pricing patterns
            recommendations = []

            # Price optimization based on LTV:CAC ratio
            if customer_metrics.ltv_cac_ratio > 3:
                recommendations.append({
                    "type": "price_increase",
                    "current_price": revenue_metrics.revenue_per_customer,
                    "recommended_price": revenue_metrics.revenue_per_customer * 1.1,
                    "expected_impact": {
                        "revenue_increase": 0.1,
                        "customer_impact": -0.02,
                        "confidence_interval": [0.05, 0.15]
                    },
                    "confidence_score": 0.75,
                    "implementation_effort": "low",
                    "time_to_impact": "1 month",
                    "risks": ["Customer resistance", "Competitive pressure"],
                    "benefits": ["Higher margins", "Increased revenue per customer"],
                    "target_segments": ["existing_customers", "new_enterprise"],
                    "testing_approach": "Gradual rollout with A/B testing"
                })

            # New tier recommendation based on contract value
            if revenue_metrics.average_contract_value < 500:
                recommendations.append({
                    "type": "new_tier",
                    "current_price": revenue_metrics.revenue_per_customer,
                    "recommended_price": revenue_metrics.revenue_per_customer + 200,
                    "expected_impact": {
                        "revenue_increase": 0.15,
                        "market_expansion": 0.08,
                        "confidence_interval": [0.1, 0.2]
                    },
                    "confidence_score": 0.65,
                    "implementation_effort": "medium",
                    "time_to_impact": "2 months",
                    "risks": ["Cannibalization", "Complexity"],
                    "benefits": ["Market expansion", "Higher ACV"],
                    "target_segments": ["mid_market", "small_enterprise"],
                    "testing_approach": "Beta test with select customers"
                })

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating pricing analysis with LLM: {e}")
            return []

    async def _predict_customer_churn(self, user_id: str) -> List[ChurnPrediction]:
        """Predict customer churn for at-risk customers"""
        try:
            # Get customer data from HubSpot
            customer_data = await self.hubspot_service.get_at_risk_customers(user_id)

            churn_predictions = []

            for customer in customer_data[:20]:  # Analyze top 20 at-risk customers
                # Calculate churn probability based on various factors
                churn_probability = self._calculate_churn_probability(customer)

                risk_level = (
                    "high" if churn_probability > 0.7 else
                    "medium" if churn_probability > 0.3 else
                    "low"
                )

                # Identify key churn indicators
                key_indicators = self._identify_churn_indicators(customer)

                # Predict churn date (simplified)
                predicted_churn_date = None
                if churn_probability > 0.5:
                    days_to_churn = int((1 - churn_probability) * 90)  # 0-90 days
                    predicted_churn_date = datetime.now(timezone.utc) + timedelta(days=days_to_churn)

                # Generate recommended actions
                recommended_actions = self._generate_churn_prevention_actions(customer, churn_probability)

                # Calculate intervention cost and retention probability
                intervention_cost = self._calculate_intervention_cost(customer, churn_probability)
                retention_probability = self._calculate_retention_probability(churn_probability)
                customer_value = customer.get("lifetime_value", 0)

                prediction = ChurnPrediction(
                    customer_id=customer.get("id", ""),
                    customer_name=customer.get("name", ""),
                    churn_probability=churn_probability,
                    risk_level=risk_level,
                    key_indicators=key_indicators,
                    predicted_churn_date=predicted_churn_date,
                    recommended_actions=recommended_actions,
                    intervention_cost=intervention_cost,
                    retention_probability=retention_probability,
                    customer_value=customer_value,
                    last_updated=datetime.now(timezone.utc)
                )

                churn_predictions.append(prediction)

            # Sort by churn probability (highest first)
            churn_predictions.sort(key=lambda x: x.churn_probability, reverse=True)

            return churn_predictions

        except Exception as e:
            self.logger.error(f"Error predicting customer churn: {e}")
            return []

    def _calculate_churn_probability(self, customer: Dict[str, Any]) -> float:
        """Calculate churn probability for a customer"""
        try:
            probability = 0.0

            # Usage patterns
            usage_score = customer.get("usage_score", 0.5)
            if usage_score < 0.3:
                probability += 0.2
            elif usage_score < 0.6:
                probability += 0.1

            # Support interactions
            support_tickets = customer.get("support_tickets", 0)
            if support_tickets > 5:
                probability += 0.15
            elif support_tickets > 2:
                probability += 0.05

            # Payment issues
            payment_issues = customer.get("payment_issues", 0)
            if payment_issues > 0:
                probability += 0.1 * payment_issues

            # Engagement score
            engagement_score = customer.get("engagement_score", 0.5)
            if engagement_score < 0.3:
                probability += 0.15
            elif engagement_score < 0.6:
                probability += 0.05

            # Customer tenure
            tenure_months = customer.get("tenure_months", 12)
            if tenure_months < 3:
                probability += 0.1
            elif tenure_months > 24:
                probability -= 0.05

            # Recent feature adoption
            feature_adoption = customer.get("recent_feature_adoption", 0)
            if feature_adoption < 0.2:
                probability += 0.1

            return min(1.0, probability)

        except Exception as e:
            self.logger.error(f"Error calculating churn probability: {e}")
            return 0.5

    def _identify_churn_indicators(self, customer: Dict[str, Any]) -> List[str]:
        """Identify specific churn indicators for a customer"""
        indicators = []

        usage_score = customer.get("usage_score", 0.5)
        if usage_score < 0.3:
            indicators.append("Low product usage")

        support_tickets = customer.get("support_tickets", 0)
        if support_tickets > 5:
            indicators.append("High support ticket volume")

        engagement_score = customer.get("engagement_score", 0.5)
        if engagement_score < 0.3:
            indicators.append("Low engagement score")

        payment_issues = customer.get("payment_issues", 0)
        if payment_issues > 0:
            indicators.append(f"Payment issues ({payment_issues})")

        tenure_months = customer.get("tenure_months", 12)
        if tenure_months < 3:
            indicators.append("New customer (high risk period)")

        last_login = customer.get("last_login_days", 0)
        if last_login > 30:
            indicators.append("No recent login activity")

        nps_score = customer.get("nps_score", 8)
        if nps_score < 6:
            indicators.append(f"Low NPS score ({nps_score})")

        return indicators[:4]  # Top 4 indicators

    def _generate_churn_prevention_actions(
        self,
        customer: Dict[str, Any],
        churn_probability: float
    ) -> List[str]:
        """Generate recommended actions to prevent churn"""
        actions = []

        if churn_probability > 0.7:
            actions.extend([
                "Immediate outreach from Customer Success Manager",
                "Offer personalized retention incentive",
                "Schedule executive check-in call",
                "Provide additional training and onboarding"
            ])
        elif churn_probability > 0.5:
            actions.extend([
                "Proactive check-in from support team",
                "Offer feature usage consultation",
                "Share best practices and success stories",
                "Review and optimize current plan"
            ])
        elif churn_probability > 0.3:
            actions.extend([
                "Send engagement email with tips",
                "Invite to upcoming webinar",
                "Share new feature announcements",
                "Monitor usage patterns closely"
            ])

        # Add specific actions based on indicators
        if customer.get("usage_score", 0.5) < 0.3:
            actions.append("Conduct usage analysis and optimization session")

        if customer.get("support_tickets", 0) > 5:
            actions.append("Review and resolve outstanding support issues")

        return actions[:5]  # Top 5 actions

    def _calculate_intervention_cost(self, customer: Dict[str, Any], churn_probability: float) -> float:
        """Calculate cost of churn prevention intervention"""
        base_cost = 50.0  # Base cost of outreach

        # Add costs based on intervention level
        if churn_probability > 0.7:
            base_cost += 200  # CSM time + potential incentives
        elif churn_probability > 0.5:
            base_cost += 100  # Support team time

        # Add costs based on customer value
        customer_value = customer.get("lifetime_value", 1000)
        base_cost += customer_value * 0.01  # 1% of customer value

        return base_cost

    def _calculate_retention_probability(self, churn_probability: float) -> float:
        """Calculate probability of successful retention with intervention"""
        # Base retention probability
        retention_prob = 1.0 - churn_probability

        # Intervention effectiveness (varies by churn probability)
        if churn_probability > 0.7:
            effectiveness = 0.6  # 60% chance of saving high-risk customers
        elif churn_probability > 0.5:
            effectiveness = 0.7  # 70% chance for medium-risk
        else:
            effectiveness = 0.8  # 80% chance for low-risk

        return min(1.0, retention_prob + (churn_probability * effectiveness))

    async def _generate_strategic_recommendations(
        self,
        revenue_metrics: RevenueMetrics,
        customer_metrics: CustomerMetrics,
        forecasts: List[RevenueForecast],
        churn_predictions: List[ChurnPrediction]
    ) -> List[str]:
        """Generate strategic recommendations based on analysis"""
        try:
            recommendations = []

            # Revenue growth recommendations
            if revenue_metrics.mrr_growth_rate < 10:
                recommendations.append("Focus on accelerating MRR growth through expansion revenue")

            if customer_metrics.ltv_cac_ratio < 3:
                recommendations.append("Improve LTV:CAC ratio by increasing customer lifetime value")

            # Customer acquisition recommendations
            if customer_metrics.customer_acquisition_cost > customer_metrics.customer_lifetime_value * 0.3:
                recommendations.append("Reduce customer acquisition cost through improved targeting and funnel optimization")

            # Churn reduction recommendations
            high_risk_customers = [c for c in churn_predictions if c.risk_level == "high"]
            if len(high_risk_customers) > 5:
                recommendations.append("Implement proactive churn prevention program for high-risk customers")

            # Forecast-based recommendations
            if forecasts:
                ensemble_forecast = next((f for f in forecasts if f.model_type == ForecastModel.ENSEMBLE), None)
                if ensemble_forecast and ensemble_forecast.trend_direction == "down":
                    recommendations.append("Address negative revenue trends with immediate growth initiatives")

            # Expansion revenue recommendations
            if revenue_metrics.expansion_mrr < revenue_metrics.mrr * 0.1:
                recommendations.append("Develop expansion revenue programs for existing customers")

            # Pricing recommendations
            if revenue_metrics.revenue_per_customer < 100:
                recommendations.append("Evaluate pricing strategy to increase average contract value")

            return recommendations[:8]  # Top 8 recommendations

        except Exception as e:
            self.logger.error(f"Error generating strategic recommendations: {e}")
            return ["Review revenue metrics and develop targeted improvement strategies"]

    async def _calculate_revenue_health_score(
        self,
        revenue_metrics: RevenueMetrics,
        customer_metrics: CustomerMetrics,
        churn_predictions: List[ChurnPrediction]
    ) -> Dict[str, Any]:
        """Calculate overall revenue health score"""
        try:
            health_components = {
                "revenue_growth": 0.0,
                "customer_acquisition": 0.0,
                "customer_retention": 0.0,
                "profitability": 0.0,
                "forecast_confidence": 0.0
            }

            # Revenue growth score (0-100)
            if revenue_metrics.mrr_growth_rate > 20:
                health_components["revenue_growth"] = 100
            elif revenue_metrics.mrr_growth_rate > 15:
                health_components["revenue_growth"] = 80
            elif revenue_metrics.mrr_growth_rate > 10:
                health_components["revenue_growth"] = 60
            elif revenue_metrics.mrr_growth_rate > 5:
                health_components["revenue_growth"] = 40
            elif revenue_metrics.mrr_growth_rate > 0:
                health_components["revenue_growth"] = 20
            else:
                health_components["revenue_growth"] = 0

            # Customer acquisition score
            if customer_metrics.ltv_cac_ratio > 5:
                health_components["customer_acquisition"] = 100
            elif customer_metrics.ltv_cac_ratio > 4:
                health_components["customer_acquisition"] = 80
            elif customer_metrics.ltv_cac_ratio > 3:
                health_components["customer_acquisition"] = 60
            elif customer_metrics.ltv_cac_ratio > 2:
                health_components["customer_acquisition"] = 40
            else:
                health_components["customer_acquisition"] = 20

            # Customer retention score
            if customer_metrics.customer_churn_rate < 2:
                health_components["customer_retention"] = 100
            elif customer_metrics.customer_churn_rate < 5:
                health_components["customer_retention"] = 80
            elif customer_metrics.customer_churn_rate < 8:
                health_components["customer_retention"] = 60
            elif customer_metrics.customer_churn_rate < 12:
                health_components["customer_retention"] = 40
            else:
                health_components["customer_retention"] = 20

            # Profitability score
            if revenue_metrics.net_margin > 20:
                health_components["profitability"] = 100
            elif revenue_metrics.net_margin > 15:
                health_components["profitability"] = 80
            elif revenue_metrics.net_margin > 10:
                health_components["profitability"] = 60
            elif revenue_metrics.net_margin > 5:
                health_components["profitability"] = 40
            elif revenue_metrics.net_margin > 0:
                health_components["profitability"] = 20
            else:
                health_components["profitability"] = 0

            # Risk adjustment for high churn risk customers
            high_risk_percentage = len([c for c in churn_predictions if c.risk_level == "high"]) / max(1, len(churn_predictions)) * 100
            risk_adjustment = max(0, 100 - high_risk_percentage)

            # Calculate overall health score
            overall_score = (
                health_components["revenue_growth"] * 0.25 +
                health_components["customer_acquisition"] * 0.20 +
                health_components["customer_retention"] * 0.25 +
                health_components["profitability"] * 0.20 +
                risk_adjustment * 0.10
            )

            # Determine health status
            health_status = (
                "excellent" if overall_score >= 85 else
                "good" if overall_score >= 70 else
                "fair" if overall_score >= 50 else
                "poor"
            )

            return {
                "overall_score": round(overall_score, 1),
                "status": health_status,
                "components": health_components,
                "risk_adjustment": risk_adjustment,
                "high_risk_customers": len([c for c in churn_predictions if c.risk_level == "high"]),
                "key_focus_areas": self._identify_focus_areas(health_components, churn_predictions)
            }

        except Exception as e:
            self.logger.error(f"Error calculating revenue health score: {e}")
            return {"overall_score": 50, "status": "unknown", "error": str(e)}

    def _identify_focus_areas(
        self,
        health_components: Dict[str, float],
        churn_predictions: List[ChurnPrediction]
    ) -> List[str]:
        """Identify key focus areas for improvement"""
        focus_areas = []

        # Lowest scoring components
        sorted_components = sorted(health_components.items(), key=lambda x: x[1])
        for component, score in sorted_components[:2]:
            if score < 70:
                component_name = component.replace("_", " ").title()
                focus_areas.append(f"Improve {component_name}")

        # Churn risk focus
        high_risk_count = len([c for c in churn_predictions if c.risk_level == "high"])
        if high_risk_count > 5:
            focus_areas.append("Address customer churn risks")

        return focus_areas[:3]

    async def _assess_data_quality(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Assess quality of data used for analysis"""
        try:
            # Check data completeness
            completeness_score = await self._check_data_completeness(user_id, start_date, end_date)

            # Check data accuracy
            accuracy_score = await self._check_data_accuracy(user_id)

            # Check data recency
            recency_score = await self._check_data_recency(user_id)

            # Overall quality score
            overall_quality = (completeness_score + accuracy_score + recency_score) / 3

            return {
                "overall_quality": round(overall_quality, 1),
                "completeness_score": completeness_score,
                "accuracy_score": accuracy_score,
                "recency_score": recency_score,
                "data_gaps": [],
                "recommendations": self._get_data_quality_recommendations(overall_quality)
            }

        except Exception as e:
            self.logger.error(f"Error assessing data quality: {e}")
            return {"overall_quality": 50, "error": str(e)}

    async def _check_data_completeness(self, user_id: str, start_date: datetime, end_date: datetime) -> float:
        """Check data completeness"""
        # Simplified check - in production would be more comprehensive
        return 85.0

    async def _check_data_accuracy(self, user_id: str) -> float:
        """Check data accuracy"""
        # Simplified check - in production would validate against multiple sources
        return 90.0

    async def _check_data_recency(self, user_id: str) -> float:
        """Check data recency"""
        # Simplified check - in production would check last update timestamps
        return 95.0

    def _get_data_quality_recommendations(self, quality_score: float) -> List[str]:
        """Get data quality improvement recommendations"""
        if quality_score >= 90:
            return ["Data quality is excellent - maintain current standards"]
        elif quality_score >= 80:
            return ["Minor data quality improvements recommended"]
        elif quality_score >= 70:
            return ["Implement data validation checks", "Improve data entry processes"]
        else:
            return ["Immediate data quality improvements needed", "Implement comprehensive data governance"]

    async def _store_revenue_analysis(self, analysis: Dict[str, Any], user_id: str):
        """Store revenue analysis in Firebase"""
        try:
            await self.firebase_service.store_agent_file(
                f"revenue_intelligence/{user_id}/{analysis['analysis_id']}",
                json.dumps(analysis, indent=2, default=str)
            )

            self.logger.info(f"Stored revenue analysis {analysis['analysis_id']} for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error storing revenue analysis: {e}")

    async def get_revenue_insights(
        self,
        user_id: str,
        insight_types: List[str] = None
    ) -> Dict[str, Any]:
        """Get quick revenue insights for dashboard"""
        try:
            # Get recent analysis
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)

            # Quick metrics calculation
            revenue_metrics = await self._calculate_revenue_metrics(user_id, start_date, end_date)
            customer_metrics = await self._calculate_customer_metrics(user_id, start_date, end_date)

            insights = {
                "revenue_health": {
                    "mrr_growth": revenue_metrics.mrr_growth_rate,
                    "net_new_mrr": revenue_metrics.net_new_mrr,
                    "growth_trend": "positive" if revenue_metrics.mrr_growth_rate > 0 else "negative"
                },
                "customer_health": {
                    "ltv_cac_ratio": customer_metrics.ltv_cac_ratio,
                    "churn_rate": customer_metrics.customer_churn_rate,
                    "acquisition_efficiency": "good" if customer_metrics.ltv_cac_ratio > 3 else "needs_improvement"
                },
                "forecast_confidence": "medium",  # Would be calculated from actual forecasts
                "opportunities": [
                    "Expansion revenue potential",
                    "Pricing optimization",
                    "Churn reduction program"
                ],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            return insights

        except Exception as e:
            self.logger.error(f"Error getting revenue insights: {e}")
            return {"error": str(e), "last_updated": datetime.now(timezone.utc).isoformat()}