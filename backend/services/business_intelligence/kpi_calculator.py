"""
KPI Calculation Engine
Advanced Key Performance Indicator calculation, tracking, and analysis engine
with real-time monitoring, trend analysis, and predictive capabilities.
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
from .revenue_intelligence import RevenueIntelligenceEngine
from .crm_intelligence import CRMIntelligenceEngine


class KPICategory(str, Enum):
    FINANCIAL = "financial"
    SALES = "sales"
    MARKETING = "marketing"
    CUSTOMER_SUCCESS = "customer_success"
    OPERATIONAL = "operational"
    PRODUCT = "product"
    TEAM = "team"
    STRATEGIC = "strategic"


class KPITimeframe(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class KPITrend(str, Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"


class KPIStatus(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class KPIDefinition:
    """KPI definition with calculation method and targets"""
    kpi_id: str
    name: str
    description: str
    category: KPICategory
    unit: str
    calculation_method: str
    data_sources: List[str]
    target_value: float
    minimum_acceptable: float
    stretch_target: float
    timeframe: KPITimeframe
    owner: str
    reporting_frequency: str
    benchmark_value: Optional[float]
    industry_average: Optional[float]
    created_at: datetime


@dataclass
class KPIValue:
    """Individual KPI value with metadata"""
    kpi_id: str
    value: float
    previous_value: Optional[float]
    target_value: float
    achievement_rate: float  # percentage of target achieved
    trend: KPITrend
    status: KPIStatus
    variance: float  # difference from target
    variance_percentage: float
    confidence_level: float  # 0-1 confidence in data quality
    data_quality_score: float  # 0-100
    calculation_timestamp: datetime
    period_start: datetime
    period_end: datetime
    metadata: Dict[str, Any]


@dataclass
class KPITrendAnalysis:
    """KPI trend analysis over time"""
    kpi_id: str
    period_days: int
    trend_direction: KPITrend
    trend_strength: float  # 0-1
    seasonality_detected: bool
    growth_rate: float  # percentage change over period
    volatility: float  # standard deviation normalized
    forecast_next_period: float
    forecast_confidence: float
    key_drivers: List[str]
    recommendations: List[str]
    analysis_timestamp: datetime


@dataclass
class KPIDashboard:
    """KPI dashboard configuration"""
    dashboard_id: str
    name: str
    description: str
    kpis: List[str]  # KPI IDs
    layout_config: Dict[str, Any]
    refresh_interval: int  # seconds
    filters: List[str]
    stakeholders: List[str]
    alert_thresholds: Dict[str, float]
    created_at: datetime
    last_updated: datetime


@dataclass
class KPIAlert:
    """KPI alert definition"""
    alert_id: str
    kpi_id: str
    alert_type: str  # threshold_breach, trend_anomaly, data_quality
    condition: str
    threshold_value: float
    severity: str  # low, medium, high, critical
    notification_channels: List[str]
    message_template: str
    enabled: bool
    created_at: datetime
    last_triggered: Optional[datetime]


class KPIEngine:
    """Advanced KPI calculation and monitoring engine"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            max_tokens=2000,
            openai_api_key=openai_api_key
        )

        # Initialize specialized engines
        self.revenue_engine = RevenueIntelligenceEngine(openai_api_key)
        self.crm_engine = CRMIntelligenceEngine(openai_api_key)

        # KPI calculation configurations
        self.kpi_configurations = {
            "financial_kpis": [
                {
                    "name": "Monthly Recurring Revenue (MRR)",
                    "category": "financial",
                    "unit": "USD",
                    "targets": {"minimum": 100000, "target": 150000, "stretch": 200000}
                },
                {
                    "name": "Customer Lifetime Value (LTV)",
                    "category": "financial",
                    "unit": "USD",
                    "targets": {"minimum": 5000, "target": 7500, "stretch": 10000}
                },
                {
                    "name": "Customer Acquisition Cost (CAC)",
                    "category": "financial",
                    "unit": "USD",
                    "targets": {"minimum": 0, "target": 300, "stretch": 200}
                }
            ],
            "sales_kpis": [
                {
                    "name": "Sales Pipeline Value",
                    "category": "sales",
                    "unit": "USD",
                    "targets": {"minimum": 500000, "target": 750000, "stretch": 1000000}
                },
                {
                    "name": "Win Rate",
                    "category": "sales",
                    "unit": "%",
                    "targets": {"minimum": 20, "target": 30, "stretch": 40}
                },
                {
                    "name": "Average Deal Size",
                    "category": "sales",
                    "unit": "USD",
                    "targets": {"minimum": 20000, "target": 30000, "stretch": 50000}
                }
            ],
            "customer_kpis": [
                {
                    "name": "Customer Satisfaction Score (CSAT)",
                    "category": "customer_success",
                    "unit": "score",
                    "targets": {"minimum": 7, "target": 8.5, "stretch": 9.5}
                },
                {
                    "name": "Net Promoter Score (NPS)",
                    "category": "customer_success",
                    "unit": "score",
                    "targets": {"minimum": 30, "target": 50, "stretch": 70}
                },
                {
                    "name": "Customer Churn Rate",
                    "category": "customer_success",
                    "unit": "%",
                    "targets": {"minimum": 0, "target": 5, "stretch": 2}
                }
            ]
        }

        # Data quality thresholds
        self.data_quality_thresholds = {
            "completeness": 0.9,  # 90% completeness required
            "accuracy": 0.95,     # 95% accuracy required
            "timeliness": 0.8,    # 80% timeliness required
            "consistency": 0.85   # 85% consistency required
        }

        # Cache for KPI calculations
        self._kpi_cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 300  # 5 minutes

    async def initialize_kpi_system(self, user_id: str) -> Dict[str, Any]:
        """Initialize KPI system with standard KPIs"""
        try:
            self.logger.info(f"Initializing KPI system for user {user_id}")

            # Create standard KPI definitions
            kpi_definitions = await self._create_standard_kpi_definitions()

            # Store KPI definitions
            for kpi_def in kpi_definitions:
                await self._store_kpi_definition(kpi_def, user_id)

            # Create default dashboards
            dashboards = await self._create_default_dashboards()
            for dashboard in dashboards:
                await self._store_dashboard(dashboard, user_id)

            # Set up default alerts
            alerts = await self._create_default_alerts(kpi_definitions)
            for alert in alerts:
                await self._store_alert(alert, user_id)

            # Calculate initial KPI values
            initial_values = await self._calculate_all_kpis(user_id)

            return {
                "success": True,
                "kpi_definitions_created": len(kpi_definitions),
                "dashboards_created": len(dashboards),
                "alerts_created": len(alerts),
                "initial_calculations": len(initial_values),
                "system_ready": True
            }

        except Exception as e:
            self.logger.error(f"Error initializing KPI system: {e}")
            raise

    async def calculate_kpis(
        self,
        user_id: str,
        kpi_ids: List[str] = None,
        timeframe: KPITimeframe = KPITimeframe.MONTHLY,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Calculate specified KPIs"""
        try:
            if end_date is None:
                end_date = datetime.now(timezone.utc)

            # Get KPI definitions to calculate
            if kpi_ids is None:
                kpi_ids = await self._get_all_kpi_ids(user_id)

            kpi_definitions = await self._get_kpi_definitions(user_id, kpi_ids)

            # Calculate KPI values
            kpi_values = []
            for kpi_def in kpi_definitions:
                try:
                    kpi_value = await self._calculate_single_kpi(kpi_def, timeframe, end_date)
                    kpi_values.append(kpi_value)
                except Exception as e:
                    self.logger.error(f"Error calculating KPI {kpi_def.name}: {e}")
                    continue

            # Store KPI values
            for kpi_value in kpi_values:
                await self._store_kpi_value(kpi_value, user_id)

            # Check for alerts
            await self._check_kpi_alerts(kpi_values, user_id)

            return {
                "success": True,
                "kpi_values_calculated": len(kpi_values),
                "timeframe": timeframe.value,
                "period_end": end_date.isoformat(),
                "kpi_values": [asdict(kpi) for kpi in kpi_values],
                "alerts_triggered": len([kpi for kpi in kpi_values if kpi.status == KPIStatus.CRITICAL])
            }

        except Exception as e:
            self.logger.error(f"Error calculating KPIs: {e}")
            raise

    async def get_kpi_dashboard(
        self,
        user_id: str,
        dashboard_id: str = None,
        real_time: bool = False
    ) -> Dict[str, Any]:
        """Get KPI dashboard data"""
        try:
            if dashboard_id is None:
                dashboard_id = "executive_overview"  # Default dashboard

            # Get dashboard configuration
            dashboard = await self._get_dashboard(user_id, dashboard_id)
            if not dashboard:
                return {"error": "Dashboard not found"}

            # Get KPI values for dashboard
            kpi_values = []
            for kpi_id in dashboard.kpis:
                kpi_value = await self._get_latest_kpi_value(user_id, kpi_id)
                if kpi_value:
                    kpi_values.append(kpi_value)

            # Add trend analysis for real-time dashboards
            if real_time:
                enhanced_kpis = []
                for kpi_value in kpi_values:
                    trend_analysis = await self._analyze_kpi_trend(kpi_value.kpi_id, days=30)
                    enhanced_kpis.append({
                        **asdict(kpi_value),
                        "trend_analysis": asdict(trend_analysis) if trend_analysis else None
                    })
                kpi_values = enhanced_kpis

            # Calculate dashboard summary
            dashboard_summary = await self._calculate_dashboard_summary(kpi_values)

            return {
                "dashboard_id": dashboard_id,
                "dashboard_name": dashboard.name,
                "kpi_values": kpi_values,
                "summary": dashboard_summary,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "layout_config": dashboard.layout_config
            }

        except Exception as e:
            self.logger.error(f"Error getting KPI dashboard: {e}")
            return {"error": str(e)}

    async def create_custom_kpi(
        self,
        user_id: str,
        kpi_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create custom KPI definition"""
        try:
            # Validate KPI definition
            validation_result = await self._validate_kpi_definition(kpi_definition)
            if not validation_result["valid"]:
                return {"error": "Invalid KPI definition", "issues": validation_result["issues"]}

            # Create KPI definition object
            kpi_def = KPIDefinition(
                kpi_id=f"kpi_{uuid.uuid4().hex[:8]}",
                name=kpi_definition["name"],
                description=kpi_definition.get("description", ""),
                category=KPICategory(kpi_definition["category"]),
                unit=kpi_definition.get("unit", ""),
                calculation_method=kpi_definition["calculation_method"],
                data_sources=kpi_definition.get("data_sources", []),
                target_value=kpi_definition.get("target_value", 0),
                minimum_acceptable=kpi_definition.get("minimum_acceptable", 0),
                stretch_target=kpi_definition.get("stretch_target", 0),
                timeframe=KPITimeframe(kpi_definition.get("timeframe", "monthly")),
                owner=kpi_definition.get("owner", "Unassigned"),
                reporting_frequency=kpi_definition.get("reporting_frequency", "monthly"),
                benchmark_value=kpi_definition.get("benchmark_value"),
                industry_average=kpi_definition.get("industry_average"),
                created_at=datetime.now(timezone.utc)
            )

            # Store KPI definition
            await self._store_kpi_definition(kpi_def, user_id)

            # Calculate initial value
            try:
                initial_value = await self._calculate_single_kpi(
                    kpi_def,
                    KPITimeframe(kpi_def.timeframe),
                    datetime.now(timezone.utc)
                )
                await self._store_kpi_value(initial_value, user_id)
            except Exception as e:
                self.logger.warning(f"Could not calculate initial value for custom KPI: {e}")

            return {
                "success": True,
                "kpi_id": kpi_def.kpi_id,
                "kpi_name": kpi_def.name,
                "message": "Custom KPI created successfully"
            }

        except Exception as e:
            self.logger.error(f"Error creating custom KPI: {e}")
            return {"error": str(e)}

    async def analyze_kpi_trends(
        self,
        user_id: str,
        kpi_id: str,
        days: int = 30
    ) -> KPITrendAnalysis:
        """Analyze KPI trends over specified period"""
        try:
            # Get historical KPI values
            historical_values = await self._get_historical_kpi_values(user_id, kpi_id, days)

            if len(historical_values) < 2:
                # Not enough data for trend analysis
                return KPITrendAnalysis(
                    kpi_id=kpi_id,
                    period_days=days,
                    trend_direction=KPITrend.STABLE,
                    trend_strength=0.0,
                    seasonality_detected=False,
                    growth_rate=0.0,
                    volatility=0.0,
                    forecast_next_period=0.0,
                    forecast_confidence=0.0,
                    key_drivers=["Insufficient data for analysis"],
                    recommendations=["Collect more data points for trend analysis"],
                    analysis_timestamp=datetime.now(timezone.utc)
                )

            # Calculate trend metrics
            values = [kpi.value for kpi in historical_values]
            timestamps = [kpi.calculation_timestamp for kpi in historical_values]

            # Trend direction
            if len(values) >= 3:
                # Linear regression to determine trend
                x = list(range(len(values)))
                slope = self._calculate_slope(x, values)

                if slope > 0.01:
                    trend_direction = KPITrend.IMPROVING
                elif slope < -0.01:
                    trend_direction = KPITrend.DECLINING
                else:
                    trend_direction = KPITrend.STABLE

                # Trend strength (R-squared)
                trend_strength = self._calculate_r_squared(x, values, slope)
            else:
                trend_direction = KPITrend.STABLE
                trend_strength = 0.0

            # Growth rate
            if values[0] != 0:
                growth_rate = ((values[-1] - values[0]) / values[0]) * 100
            else:
                growth_rate = 0.0

            # Volatility (coefficient of variation)
            if statistics.mean(values) != 0:
                volatility = (statistics.stdev(values) / statistics.mean(values)) * 100
            else:
                volatility = 0.0

            # Forecast next period
            forecast_value = self._forecast_next_value(values)
            forecast_confidence = max(0.0, min(1.0, trend_strength))

            # Detect seasonality (simplified)
            seasonality_detected = len(values) >= 12 and self._detect_seasonality(values)

            # Generate insights using LLM
            insights = await self._generate_trend_insights(
                kpi_id, values, trend_direction, growth_rate, volatility
            )

            return KPITrendAnalysis(
                kpi_id=kpi_id,
                period_days=days,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                seasonality_detected=seasonality_detected,
                growth_rate=growth_rate,
                volatility=volatility,
                forecast_next_period=forecast_value,
                forecast_confidence=forecast_confidence,
                key_drivers=insights.get("drivers", []),
                recommendations=insights.get("recommendations", []),
                analysis_timestamp=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error analyzing KPI trends: {e}")
            raise

    async def _create_standard_kpi_definitions(self) -> List[KPIDefinition]:
        """Create standard KPI definitions"""
        try:
            definitions = []

            # Process all KPI configurations
            all_kpis = []
            for category_kpis in self.kpi_configurations.values():
                all_kpis.extend(category_kpis)

            for kpi_config in all_kpis:
                definition = KPIDefinition(
                    kpi_id=f"kpi_{uuid.uuid4().hex[:8]}",
                    name=kpi_config["name"],
                    description=f"Standard KPI for {kpi_config['category']} metrics",
                    category=KPICategory(kpi_config["category"]),
                    unit=kpi_config["unit"],
                    calculation_method="automated",
                    data_sources=[kpi_config["category"], "hubspot", "internal_systems"],
                    target_value=kpi_config["targets"]["target"],
                    minimum_acceptable=kpi_config["targets"]["minimum"],
                    stretch_target=kpi_config["targets"]["stretch"],
                    timeframe=KPITimeframe.MONTHLY,
                    owner="Department Head",
                    reporting_frequency="monthly",
                    benchmark_value=None,
                    industry_average=None,
                    created_at=datetime.now(timezone.utc)
                )
                definitions.append(definition)

            return definitions

        except Exception as e:
            self.logger.error(f"Error creating standard KPI definitions: {e}")
            return []

    async def _create_default_dashboards(self) -> List[KPIDashboard]:
        """Create default KPI dashboards"""
        try:
            dashboards = []

            # Executive Overview Dashboard
            exec_dashboard = KPIDashboard(
                dashboard_id="executive_overview",
                name="Executive Overview",
                description="High-level KPIs for executive leadership",
                kpis=["kpi_mrr", "kpi_win_rate", "kpi_csat", "kpi_churn"],
                layout_config={
                    "grid": "2x2",
                    "chart_types": ["gauge", "trend", "bar", "indicator"]
                },
                refresh_interval=300,  # 5 minutes
                filters=["timeframe", "department"],
                stakeholders=["CEO", "CFO", "COO"],
                alert_thresholds={"critical": 0, "warning": 2},
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            dashboards.append(exec_dashboard)

            # Sales Dashboard
            sales_dashboard = KPIDashboard(
                dashboard_id="sales_performance",
                name="Sales Performance",
                description="Sales team KPIs and metrics",
                kpis=["kpi_pipeline_value", "kpi_win_rate", "kpi_deal_size", "kpi_sales_cycle"],
                layout_config={
                    "grid": "2x2",
                    "chart_types": ["funnel", "trend", "comparison", "leaderboard"]
                },
                refresh_interval=600,  # 10 minutes
                filters=["timeframe", "region", "team"],
                stakeholders=["VP of Sales", "Sales Managers"],
                alert_thresholds={"critical": 1, "warning": 3},
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            dashboards.append(sales_dashboard)

            # Customer Success Dashboard
            cs_dashboard = KPIDashboard(
                dashboard_id="customer_success",
                name="Customer Success",
                description="Customer satisfaction and retention metrics",
                kpis=["kpi_csat", "kpi_nps", "kpi_churn", "kpi_ltv"],
                layout_config={
                    "grid": "2x2",
                    "chart_types": ["gauge", "trend", "distribution", "health"]
                },
                refresh_interval=900,  # 15 minutes
                filters=["timeframe", "segment", "tier"],
                stakeholders=["VP of Customer Success", "Support Managers"],
                alert_thresholds={"critical": 2, "warning": 4},
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            dashboards.append(cs_dashboard)

            return dashboards

        except Exception as e:
            self.logger.error(f"Error creating default dashboards: {e}")
            return []

    async def _create_default_alerts(self, kpi_definitions: List[KPIDefinition]) -> List[KPIAlert]:
        """Create default KPI alerts"""
        try:
            alerts = []

            # Critical alerts for key KPIs
            critical_kpis = ["Monthly Recurring Revenue (MRR)", "Customer Churn Rate", "Win Rate"]

            for kpi_def in kpi_definitions:
                if kpi_def.name in critical_kpis:
                    alert = KPIAlert(
                        alert_id=f"alert_{uuid.uuid4().hex[:8]}",
                        kpi_id=kpi_def.kpi_id,
                        alert_type="threshold_breach",
                        condition="below_minimum",
                        threshold_value=kpi_def.minimum_acceptable,
                        severity="critical",
                        notification_channels=["email", "slack"],
                        message_template=f"ALERT: {kpi_def.name} has fallen below minimum acceptable threshold",
                        enabled=True,
                        created_at=datetime.now(timezone.utc),
                        last_triggered=None
                    )
                    alerts.append(alert)

            # Warning alerts for other KPIs
            for kpi_def in kpi_definitions:
                if kpi_def.name not in critical_kpis:
                    alert = KPIAlert(
                        alert_id=f"alert_{uuid.uuid4().hex[:8]}",
                        kpi_id=kpi_def.kpi_id,
                        alert_type="threshold_breach",
                        condition="below_target",
                        threshold_value=kpi_def.target_value * 0.8,  # 80% of target
                        severity="medium",
                        notification_channels=["email"],
                        message_template=f"WARNING: {kpi_def.name} is below target threshold",
                        enabled=True,
                        created_at=datetime.now(timezone.utc),
                        last_triggered=None
                    )
                    alerts.append(alert)

            return alerts

        except Exception as e:
            self.logger.error(f"Error creating default alerts: {e}")
            return []

    async def _calculate_all_kpis(self, user_id: str) -> List[KPIValue]:
        """Calculate all KPIs for initial setup"""
        try:
            # Get all KPI definitions
            kpi_definitions = await self._get_all_kpi_definitions(user_id)

            kpi_values = []
            for kpi_def in kpi_definitions:
                try:
                    kpi_value = await self._calculate_single_kpi(
                        kpi_def,
                        KPITimeframe(kpi_def.timeframe),
                        datetime.now(timezone.utc)
                    )
                    kpi_values.append(kpi_value)
                except Exception as e:
                    self.logger.error(f"Error calculating KPI {kpi_def.name}: {e}")

            return kpi_values

        except Exception as e:
            self.logger.error(f"Error calculating all KPIs: {e}")
            return []

    async def _calculate_single_kpi(
        self,
        kpi_def: KPIDefinition,
        timeframe: KPITimeframe,
        end_date: datetime
    ) -> KPIValue:
        """Calculate single KPI value"""
        try:
            # Determine period dates
            if timeframe == KPITimeframe.DAILY:
                period_start = end_date - timedelta(days=1)
            elif timeframe == KPITimeframe.WEEKLY:
                period_start = end_date - timedelta(weeks=1)
            elif timeframe == KPITimeframe.MONTHLY:
                period_start = end_date - timedelta(days=30)
            elif timeframe == KPITimeframe.QUARTERLY:
                period_start = end_date - timedelta(days=90)
            else:  # ANNUAL
                period_start = end_date - timedelta(days=365)

            # Calculate KPI value based on category
            if kpi_def.category == KPICategory.FINANCIAL:
                value = await self._calculate_financial_kpi(kpi_def, period_start, end_date)
            elif kpi_def.category == KPICategory.SALES:
                value = await self._calculate_sales_kpi(kpi_def, period_start, end_date)
            elif kpi_def.category == KPICategory.CUSTOMER_SUCCESS:
                value = await self._calculate_customer_kpi(kpi_def, period_start, end_date)
            else:
                value = await self._calculate_generic_kpi(kpi_def, period_start, end_date)

            # Get previous value for comparison
            previous_value = await self._get_previous_kpi_value(
                kpi_def.kpi_id, period_start, timeframe
            )

            # Calculate achievement and variance
            achievement_rate = (value / kpi_def.target_value * 100) if kpi_def.target_value != 0 else 0
            variance = value - kpi_def.target_value
            variance_percentage = (variance / kpi_def.target_value * 100) if kpi_def.target_value != 0 else 0

            # Determine status
            if achievement_rate >= 100:
                status = KPIStatus.EXCELLENT
            elif achievement_rate >= 80:
                status = KPIStatus.GOOD
            elif achievement_rate >= 60:
                status = KPIStatus.WARNING
            else:
                status = KPIStatus.CRITICAL

            # Determine trend
            if previous_value is not None:
                if value > previous_value * 1.05:
                    trend = KPITrend.IMPROVING
                elif value < previous_value * 0.95:
                    trend = KPITrend.DECLINING
                else:
                    trend = KPITrend.STABLE
            else:
                trend = KPITrend.STABLE

            # Assess data quality
            data_quality = await self._assess_data_quality(kpi_def)

            return KPIValue(
                kpi_id=kpi_def.kpi_id,
                value=value,
                previous_value=previous_value,
                target_value=kpi_def.target_value,
                achievement_rate=achievement_rate,
                trend=trend,
                status=status,
                variance=variance,
                variance_percentage=variance_percentage,
                confidence_level=0.9,  # Would be calculated based on data quality
                data_quality_score=data_quality,
                calculation_timestamp=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=end_date,
                metadata={
                    "calculation_method": kpi_def.calculation_method,
                    "data_sources": kpi_def.data_sources
                }
            )

        except Exception as e:
            self.logger.error(f"Error calculating single KPI {kpi_def.name}: {e}")
            # Return default KPI value
            return KPIValue(
                kpi_id=kpi_def.kpi_id,
                value=0,
                previous_value=None,
                target_value=kpi_def.target_value,
                achievement_rate=0,
                trend=KPITrend.STABLE,
                status=KPIStatus.WARNING,
                variance=-kpi_def.target_value,
                variance_percentage=-100,
                confidence_level=0.5,
                data_quality_score=50,
                calculation_timestamp=datetime.now(timezone.utc),
                period_start=datetime.now(timezone.utc) - timedelta(days=30),
                period_end=datetime.now(timezone.utc),
                metadata={"error": str(e)}
            )

    async def _calculate_financial_kpi(
        self,
        kpi_def: KPIDefinition,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate financial KPI"""
        try:
            # Use revenue intelligence engine
            if "MRR" in kpi_def.name:
                insights = await self.revenue_engine.get_revenue_insights("default_user")
                return insights.get("revenue_health", {}).get("mrr", 0)
            elif "LTV" in kpi_def.name:
                insights = await self.revenue_engine.get_revenue_insights("default_user")
                return insights.get("customer_health", {}).get("ltv_cac_ratio", 0) * 300  # Mock calculation
            elif "CAC" in kpi_def.name:
                insights = await self.revenue_engine.get_revenue_insights("default_user")
                return 300  # Mock value
            else:
                return 0

        except Exception as e:
            self.logger.error(f"Error calculating financial KPI: {e}")
            return 0

    async def _calculate_sales_kpi(
        self,
        kpi_def: KPIDefinition,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate sales KPI"""
        try:
            # Use CRM intelligence engine
            insights = await self.crm_engine.get_deal_health_insights("default_user")

            if "Pipeline" in kpi_def.name:
                return 750000  # Mock pipeline value
            elif "Win Rate" in kpi_def.name:
                return 35.0  # Mock win rate percentage
            elif "Deal Size" in kpi_def.name:
                return 35000  # Mock average deal size
            else:
                return 0

        except Exception as e:
            self.logger.error(f"Error calculating sales KPI: {e}")
            return 0

    async def _calculate_customer_kpi(
        self,
        kpi_def: KPIDefinition,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate customer KPI"""
        try:
            if "CSAT" in kpi_def.name:
                return 8.5  # Mock CSAT score
            elif "NPS" in kpi_def.name:
                return 45  # Mock NPS score
            elif "Churn" in kpi_def.name:
                return 4.2  # Mock churn rate percentage
            else:
                return 0

        except Exception as e:
            self.logger.error(f"Error calculating customer KPI: {e}")
            return 0

    async def _calculate_generic_kpi(
        self,
        kpi_def: KPIDefinition,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate generic KPI using custom method"""
        try:
            # This would implement custom calculation logic
            # For now, return a mock value based on KPI name
            return 75.0  # Mock value

        except Exception as e:
            self.logger.error(f"Error calculating generic KPI: {e}")
            return 0

    async def _get_previous_kpi_value(
        self,
        kpi_id: str,
        current_period_start: datetime,
        timeframe: KPITimeframe
    ) -> Optional[float]:
        """Get previous KPI value for comparison"""
        try:
            # This would retrieve the previous period's KPI value
            # For now, return None
            return None

        except Exception as e:
            self.logger.error(f"Error getting previous KPI value: {e}")
            return None

    async def _assess_data_quality(self, kpi_def: KPIDefinition) -> float:
        """Assess data quality for KPI calculation"""
        try:
            # Simplified data quality assessment
            quality_score = 85.0  # Mock score

            # Adjust based on data sources
            if "hubspot" in kpi_def.data_sources:
                quality_score += 5  # HubSpot is reliable

            if "internal_systems" in kpi_def.data_sources:
                quality_score -= 5  # Internal systems may vary

            return max(0, min(100, quality_score))

        except Exception as e:
            self.logger.error(f"Error assessing data quality: {e}")
            return 70.0

    async def _get_kpi_definitions(
        self,
        user_id: str,
        kpi_ids: List[str] = None
    ) -> List[KPIDefinition]:
        """Get KPI definitions"""
        try:
            # This would retrieve KPI definitions from Firebase
            # For now, return mock definitions
            definitions = []

            if not kpi_ids:
                # Get all definitions
                for category_kpis in self.kpi_configurations.values():
                    for kpi_config in category_kpis:
                        definition = KPIDefinition(
                            kpi_id=f"kpi_{uuid.uuid4().hex[:8]}",
                            name=kpi_config["name"],
                            description="",
                            category=KPICategory(kpi_config["category"]),
                            unit=kpi_config["unit"],
                            calculation_method="automated",
                            data_sources=[],
                            target_value=kpi_config["targets"]["target"],
                            minimum_acceptable=kpi_config["targets"]["minimum"],
                            stretch_target=kpi_config["targets"]["stretch"],
                            timeframe=KPITimeframe.MONTHLY,
                            owner="System",
                            reporting_frequency="monthly",
                            benchmark_value=None,
                            industry_average=None,
                            created_at=datetime.now(timezone.utc)
                        )
                        definitions.append(definition)
            else:
                # Get specific definitions
                for kpi_id in kpi_ids:
                    # Mock specific definition
                    definition = KPIDefinition(
                        kpi_id=kpi_id,
                        name="Mock KPI",
                        description="Mock KPI definition",
                        category=KPICategory.GENERIC,
                        unit="",
                        calculation_method="automated",
                        data_sources=[],
                        target_value=100,
                        minimum_acceptable=80,
                        stretch_target=120,
                        timeframe=KPITimeframe.MONTHLY,
                        owner="System",
                        reporting_frequency="monthly",
                        benchmark_value=None,
                        industry_average=None,
                        created_at=datetime.now(timezone.utc)
                    )
                    definitions.append(definition)

            return definitions

        except Exception as e:
            self.logger.error(f"Error getting KPI definitions: {e}")
            return []

    async def _store_kpi_definition(self, kpi_def: KPIDefinition, user_id: str):
        """Store KPI definition"""
        try:
            kpi_data = asdict(kpi_def)
            kpi_data["created_at"] = kpi_def.created_at.isoformat()

            await self.firebase_service.store_agent_file(
                f"kpi_system/{user_id}/definitions/{kpi_def.kpi_id}",
                json.dumps(kpi_data, indent=2, default=str)
            )

        except Exception as e:
            self.logger.error(f"Error storing KPI definition: {e}")

    async def _store_kpi_value(self, kpi_value: KPIValue, user_id: str):
        """Store KPI value"""
        try:
            value_data = asdict(kpi_value)
            value_data["calculation_timestamp"] = kpi_value.calculation_timestamp.isoformat()
            value_data["period_start"] = kpi_value.period_start.isoformat()
            value_data["period_end"] = kpi_value.period_end.isoformat()

            await self.firebase_service.store_agent_file(
                f"kpi_system/{user_id}/values/{kpi_value.kpi_id}/{kpi_value.calculation_timestamp.strftime('%Y%m%d')}",
                json.dumps(value_data, indent=2, default=str)
            )

        except Exception as e:
            self.logger.error(f"Error storing KPI value: {e}")

    async def _store_dashboard(self, dashboard: KPIDashboard, user_id: str):
        """Store dashboard configuration"""
        try:
            dashboard_data = asdict(dashboard)
            dashboard_data["created_at"] = dashboard.created_at.isoformat()
            dashboard_data["last_updated"] = dashboard.last_updated.isoformat()

            await self.firebase_service.store_agent_file(
                f"kpi_system/{user_id}/dashboards/{dashboard.dashboard_id}",
                json.dumps(dashboard_data, indent=2, default=str)
            )

        except Exception as e:
            self.logger.error(f"Error storing dashboard: {e}")

    async def _store_alert(self, alert: KPIAlert, user_id: str):
        """Store KPI alert"""
        try:
            alert_data = asdict(alert)
            alert_data["created_at"] = alert.created_at.isoformat()
            if alert.last_triggered:
                alert_data["last_triggered"] = alert.last_triggered.isoformat()

            await self.firebase_service.store_agent_file(
                f"kpi_system/{user_id}/alerts/{alert.alert_id}",
                json.dumps(alert_data, indent=2, default=str)
            )

        except Exception as e:
            self.logger.error(f"Error storing alert: {e}")

    async def _check_kpi_alerts(self, kpi_values: List[KPIValue], user_id: str):
        """Check KPI values against alert conditions"""
        try:
            # Get all alerts
            alerts = await self._get_all_alerts(user_id)

            for kpi_value in kpi_values:
                for alert in alerts:
                    if alert.kpi_id == kpi_value.kpi_id and alert.enabled:
                        # Check if alert condition is met
                        alert_triggered = await self._evaluate_alert_condition(alert, kpi_value)

                        if alert_triggered:
                            await self._trigger_alert(alert, kpi_value, user_id)

        except Exception as e:
            self.logger.error(f"Error checking KPI alerts: {e}")

    async def _evaluate_alert_condition(self, alert: KPIAlert, kpi_value: KPIValue) -> bool:
        """Evaluate if alert condition is met"""
        try:
            if alert.condition == "below_minimum":
                return kpi_value.value < alert.threshold_value
            elif alert.condition == "below_target":
                return kpi_value.value < alert.threshold_value
            elif alert.condition == "above_target":
                return kpi_value.value > alert.threshold_value
            else:
                return False

        except Exception as e:
            self.logger.error(f"Error evaluating alert condition: {e}")
            return False

    async def _trigger_alert(self, alert: KPIAlert, kpi_value: KPIValue, user_id: str):
        """Trigger KPI alert"""
        try:
            # Update last triggered time
            alert.last_triggered = datetime.now(timezone.utc)
            await self._store_alert(alert, user_id)

            # Log alert
            self.logger.warning(
                f"KPI Alert triggered: {alert.message_template}. "
                f"Value: {kpi_value.value}, Threshold: {alert.threshold_value}"
            )

            # Send notifications (would integrate with notification systems)
            # For now, just log the alert

        except Exception as e:
            self.logger.error(f"Error triggering alert: {e}")

    async def _get_all_kpi_ids(self, user_id: str) -> List[str]:
        """Get all KPI IDs for user"""
        try:
            # This would retrieve all KPI IDs from Firebase
            # For now, return mock IDs
            return [
                "kpi_mrr", "kpi_ltv", "kpi_cac", "kpi_pipeline",
                "kpi_win_rate", "kpi_deal_size", "kpi_csat",
                "kpi_nps", "kpi_churn"
            ]

        except Exception as e:
            self.logger.error(f"Error getting all KPI IDs: {e}")
            return []

    async def _get_all_kpi_definitions(self, user_id: str) -> List[KPIDefinition]:
        """Get all KPI definitions for user"""
        try:
            return await self._get_kpi_definitions(user_id, None)

        except Exception as e:
            self.logger.error(f"Error getting all KPI definitions: {e}")
            return []

    async def _get_dashboard(self, user_id: str, dashboard_id: str) -> Optional[KPIDashboard]:
        """Get dashboard configuration"""
        try:
            # This would retrieve dashboard from Firebase
            # For now, return mock dashboard
            if dashboard_id == "executive_overview":
                return KPIDashboard(
                    dashboard_id=dashboard_id,
                    name="Executive Overview",
                    description="High-level KPIs for executive leadership",
                    kpis=["kpi_mrr", "kpi_win_rate", "kpi_csat", "kpi_churn"],
                    layout_config={},
                    refresh_interval=300,
                    filters=[],
                    stakeholders=[],
                    alert_thresholds={},
                    created_at=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                )
            return None

        except Exception as e:
            self.logger.error(f"Error getting dashboard: {e}")
            return None

    async def _get_latest_kpi_value(self, user_id: str, kpi_id: str) -> Optional[KPIValue]:
        """Get latest KPI value"""
        try:
            # This would retrieve latest value from Firebase
            # For now, return mock value
            return KPIValue(
                kpi_id=kpi_id,
                value=100,
                previous_value=95,
                target_value=100,
                achievement_rate=100,
                trend=KPITrend.IMPROVING,
                status=KPIStatus.EXCELLENT,
                variance=0,
                variance_percentage=0,
                confidence_level=0.9,
                data_quality_score=90,
                calculation_timestamp=datetime.now(timezone.utc),
                period_start=datetime.now(timezone.utc) - timedelta(days=30),
                period_end=datetime.now(timezone.utc),
                metadata={}
            )

        except Exception as e:
            self.logger.error(f"Error getting latest KPI value: {e}")
            return None

    async def _calculate_dashboard_summary(self, kpi_values: List[KPIValue]) -> Dict[str, Any]:
        """Calculate dashboard summary metrics"""
        try:
            if not kpi_values:
                return {}

            total_kpis = len(kpi_values)
            critical_count = len([kpi for kpi in kpi_values if kpi.status == KPIStatus.CRITICAL])
            warning_count = len([kpi for kpi in kpi_values if kpi.status == KPIStatus.WARNING])
            good_count = len([kpi for kpi in kpi_values if kpi.status == KPIStatus.GOOD])
            excellent_count = len([kpi for kpi in kpi_values if kpi.status == KPIStatus.EXCELLENT])

            avg_achievement = statistics.mean([kpi.achievement_rate for kpi in kpi_values])

            return {
                "total_kpis": total_kpis,
                "status_distribution": {
                    "critical": critical_count,
                    "warning": warning_count,
                    "good": good_count,
                    "excellent": excellent_count
                },
                "average_achievement": round(avg_achievement, 1),
                "health_score": round((excellent_count + good_count) / total_kpis * 100, 1),
                "improving_kpis": len([kpi for kpi in kpi_values if kpi.trend == KPITrend.IMPROVING]),
                "declining_kpis": len([kpi for kpi in kpi_values if kpi.trend == KPITrend.DECLINING])
            }

        except Exception as e:
            self.logger.error(f"Error calculating dashboard summary: {e}")
            return {}

    def _calculate_slope(self, x: List[float], y: List[float]) -> float:
        """Calculate slope for linear regression"""
        try:
            if len(x) != len(y) or len(x) < 2:
                return 0

            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))

            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return 0

            slope = (n * sum_xy - sum_x * sum_y) / denominator
            return slope

        except Exception as e:
            self.logger.error(f"Error calculating slope: {e}")
            return 0

    def _calculate_r_squared(self, x: List[float], y: List[float], slope: float) -> float:
        """Calculate R-squared for trend strength"""
        try:
            if len(x) != len(y) or len(x) < 2:
                return 0

            n = len(x)
            y_mean = statistics.mean(y)

            # Calculate predicted values
            y_pred = [slope * xi for xi in x]

            # Calculate R-squared
            ss_tot = sum((yi - y_mean) ** 2 for yi in y)
            ss_res = sum((yi - y_pred[i]) ** 2 for i, yi in enumerate(y))

            if ss_tot == 0:
                return 1.0

            r_squared = 1 - (ss_res / ss_tot)
            return max(0, min(1, r_squared))

        except Exception as e:
            self.logger.error(f"Error calculating R-squared: {e}")
            return 0

    def _forecast_next_value(self, values: List[float]) -> float:
        """Simple forecast for next period"""
        try:
            if len(values) < 2:
                return values[-1] if values else 0

            # Simple linear forecast
            recent_trend = values[-1] - values[-2] if len(values) >= 2 else 0
            forecast = values[-1] + recent_trend

            return max(0, forecast)  # Ensure non-negative for most KPIs

        except Exception as e:
            self.logger.error(f"Error forecasting next value: {e}")
            return 0

    def _detect_seasonality(self, values: List[float]) -> bool:
        """Simple seasonality detection"""
        try:
            if len(values) < 12:
                return False

            # Simple check: compare first half with second half
            mid_point = len(values) // 2
            first_half_avg = statistics.mean(values[:mid_point])
            second_half_avg = statistics.mean(values[mid_point:])

            # If there's a significant pattern difference, assume seasonality
            difference = abs(first_half_avg - second_half_avg)
            avg_value = statistics.mean(values)

            return (difference / avg_value) > 0.2 if avg_value != 0 else False

        except Exception as e:
            self.logger.error(f"Error detecting seasonality: {e}")
            return False

    async def _generate_trend_insights(
        self,
        kpi_id: str,
        values: List[float],
        trend_direction: KPITrend,
        growth_rate: float,
        volatility: float
    ) -> Dict[str, List[str]]:
        """Generate insights about KPI trends using LLM"""
        try:
            context = {
                "kpi_id": kpi_id,
                "values": values,
                "trend_direction": trend_direction.value,
                "growth_rate": growth_rate,
                "volatility": volatility,
                "data_points": len(values)
            }

            system_prompt = """
            You are a business intelligence analyst providing insights about KPI trends.

            Analyze the provided KPI data and provide:
            1. Key drivers influencing the trend (3-5 factors)
            2. Specific recommendations for improvement or maintenance (3-5 actionable items)

            Focus on practical, actionable insights that would help a business leader make decisions.
            Be specific and data-driven in your recommendations.
            """

            human_prompt = f"""
            Analyze this KPI trend data and provide insights:

            KPI ID: {kpi_id}
            Trend Direction: {trend_direction.value}
            Growth Rate: {growth_rate:.2f}%
            Volatility: {volatility:.2f}%
            Data Points: {len(values)}
            Recent Values: {values[-5:]}

            Provide specific drivers and actionable recommendations.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse response (simplified)
            return {
                "drivers": ["Data quality", "Market conditions", "Operational efficiency"],
                "recommendations": ["Monitor data sources", "Investigate market factors", "Optimize processes"]
            }

        except Exception as e:
            self.logger.error(f"Error generating trend insights: {e}")
            return {"drivers": ["Unable to analyze"], "recommendations": ["Review data manually"]}

    async def _get_historical_kpi_values(
        self,
        user_id: str,
        kpi_id: str,
        days: int
    ) -> List[KPIValue]:
        """Get historical KPI values"""
        try:
            # This would retrieve historical values from Firebase
            # For now, return mock data
            mock_values = []
            for i in range(days):
                value = KPIValue(
                    kpi_id=kpi_id,
                    value=100 + (i * 2) + (i % 3 * 5),  # Some variation
                    previous_value=None,
                    target_value=100,
                    achievement_rate=100,
                    trend=KPITrend.STABLE,
                    status=KPIStatus.GOOD,
                    variance=0,
                    variance_percentage=0,
                    confidence_level=0.9,
                    data_quality_score=90,
                    calculation_timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                    period_start=datetime.now(timezone.utc) - timedelta(days=i+1),
                    period_end=datetime.now(timezone.utc) - timedelta(days=i),
                    metadata={}
                )
                mock_values.append(value)

            return mock_values

        except Exception as e:
            self.logger.error(f"Error getting historical KPI values: {e}")
            return []

    async def _validate_kpi_definition(self, kpi_def: Dict[str, Any]) -> Dict[str, Any]:
        """Validate KPI definition"""
        try:
            issues = []

            # Required fields
            required_fields = ["name", "category", "calculation_method"]
            for field in required_fields:
                if field not in kpi_def:
                    issues.append(f"Missing required field: {field}")

            # Validate category
            if "category" in kpi_def:
                try:
                    KPICategory(kpi_def["category"])
                except ValueError:
                    issues.append(f"Invalid category: {kpi_def['category']}")

            # Validate targets
            target_fields = ["target_value", "minimum_acceptable", "stretch_target"]
            for field in target_fields:
                if field in kpi_def:
                    if not isinstance(kpi_def[field], (int, float)):
                        issues.append(f"Invalid {field}: must be numeric")

            # Check logical consistency
            if all(field in kpi_def for field in target_fields):
                if kpi_def["minimum_acceptable"] > kpi_def["target_value"]:
                    issues.append("Minimum acceptable cannot be greater than target value")
                if kpi_def["target_value"] > kpi_def["stretch_target"]:
                    issues.append("Target value cannot be greater than stretch target")

            return {
                "valid": len(issues) == 0,
                "issues": issues
            }

        except Exception as e:
            self.logger.error(f"Error validating KPI definition: {e}")
            return {"valid": False, "issues": ["Validation error occurred"]}

    async def _get_all_alerts(self, user_id: str) -> List[KPIAlert]:
        """Get all KPI alerts"""
        try:
            # This would retrieve alerts from Firebase
            # For now, return empty list
            return []

        except Exception as e:
            self.logger.error(f"Error getting all alerts: {e}")
            return []