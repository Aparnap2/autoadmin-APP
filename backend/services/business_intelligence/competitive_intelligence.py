"""
Competitive Intelligence Monitoring System
Automated competitor monitoring, market positioning assessment, feature gap analysis,
and strategic opportunity identification for competitive advantage.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
import re
from decimal import Decimal

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from services.firebase_service import get_firebase_service
from tools.web_search import WebSearchTool
from tools.competitor_analysis import CompetitorAnalysisTool


class CompetitorSize(str, Enum):
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class MarketPosition(str, Enum):
    LEADER = "leader"
    CHALLENGER = "challenger"
    FOLLOWER = "follower"
    NICHE = "niche"


class CompetitiveThreat(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OpportunityType(str, Enum):
    MARKET_EXPANSION = "market_expansion"
    PRODUCT_DIFFERENTIATION = "product_differentiation"
    PRICING_ADVANTAGE = "pricing_advantage"
    FEATURE_INNOVATION = "feature_innovation"
    CUSTOMER_SEGMENT = "customer_segment"
    TECHNOLOGY_LEAP = "technology_leap"


@dataclass
class CompetitorProfile:
    """Comprehensive competitor profile"""
    competitor_id: str
    name: str
    website: str
    size: CompetitorSize
    founded_year: int
    funding_stage: str
    total_funding: float
    employee_count: int
    headquarters: str
    target_markets: List[str]
    key_products: List[str]
    unique_value_proposition: str
    strengths: List[str]
    weaknesses: List[str]
    recent_developments: List[str]
    social_media_presence: Dict[str, str]
    contact_info: Dict[str, str]
    last_updated: datetime


@dataclass
class ProductComparison:
    """Product feature comparison with competitors"""
    product_id: str
    feature_name: str
    our_capability: str
    competitor_capabilities: Dict[str, str]  # competitor_id -> capability
    feature_importance: float  # 0-1 scale
    market_standard: str
    innovation_level: str  # cutting_edge, advanced, standard, basic, missing
    competitive_advantage: str  # leader, equal, follower, lagging
    development_priority: str  # high, medium, low
    gap_analysis: str
    recommendation: str


@dataclass
class MarketPositioning:
    """Market positioning analysis"""
    market_segment: str
    total_market_size: float  # USD
    our_market_share: float
    competitor_market_shares: Dict[str, float]  # competitor_id -> share
    positioning_map: Dict[str, Tuple[float, float]]  # company -> (price, quality)
    price_positioning: str  # premium, value, budget
    quality_positioning: str  # luxury, premium, standard, budget
    customer_segments: List[str]
    differentiation_factors: List[str]
    competitive_moats: List[str]
    positioning_strategy: str


@dataclass
class CompetitiveThreat:
    """Identified competitive threat"""
    threat_id: str
    threat_type: str
    source_competitor: str
    threat_level: CompetitiveThreat
    description: str
    timeline: str
    potential_impact: str
    affected_markets: List[str]
    warning_indicators: List[str]
    monitoring_keywords: List[str]
    recommended_actions: List[str]
    contingency_plans: List[str]
    created_at: datetime
    last_assessed: datetime


@dataclass
class StrategicOpportunity:
    """Identified strategic opportunity"""
    opportunity_id: str
    title: str
    opportunity_type: OpportunityType
    description: str
    market_size: float
    confidence_score: float  # 0-1
    time_to_market: str
    required_investment: float
    expected_roi: float
    competitive_landscape: Dict[str, str]
    success_factors: List[str]
    risks: List[str]
    first_mover_advantage: bool
    implementation_roadmap: List[str]
    kpis: List[str]
    created_at: datetime


@dataclass
class TrendAnalysis:
    """Market and industry trend analysis"""
    trend_id: str
    trend_name: str
    category: str  # technology, market, customer, regulatory
    trend_direction: str  # emerging, growing, mature, declining
    impact_level: str  # low, medium, high, transformative
    time_horizon: str  # short_term, medium_term, long_term
    description: str
    supporting_data: List[str]
    affected_companies: List[str]
    opportunity_areas: List[str]
    risk_areas: List[str]
    confidence_score: float
    last_updated: datetime


class CompetitiveIntelligenceEngine:
    """Advanced competitive intelligence monitoring and analysis engine"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.web_search = WebSearchTool()
        self.competitor_analysis = CompetitorAnalysisTool()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=3000,
            openai_api_key=openai_api_key
        )

        # Monitoring configuration
        self.monitoring_config = {
            "search_keywords": [
                "competitor analysis", "market research", "industry trends",
                "product comparison", "pricing analysis", "customer reviews"
            ],
            "monitoring_frequency": 3600,  # 1 hour
            "competitor_sources": [
                "company_website", "press_releases", "social_media",
                "product_reviews", "industry_reports", "news_articles"
            ],
            "alert_thresholds": {
                "price_change": 10,  # 10% price change
                "feature_launch": True,  # Any new feature
                "funding_round": True,  # Any funding activity
                "market_entry": True  # New market entry
            }
        }

        # Analysis cache
        self._analysis_cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 1800  # 30 minutes

    async def initialize_competitive_monitoring(
        self,
        user_id: str,
        competitor_list: List[str],
        monitoring_level: str = "standard"
    ) -> Dict[str, Any]:
        """Initialize competitive intelligence monitoring"""
        try:
            self.logger.info(f"Initializing competitive monitoring for {len(competitor_list)} competitors")

            # Validate and process competitor list
            validated_competitors = await self._validate_competitor_list(competitor_list)

            # Create competitor profiles
            competitor_profiles = []
            for competitor in validated_competitors:
                profile = await self._create_competitor_profile(competitor)
                competitor_profiles.append(profile)

            # Establish monitoring baselines
            baselines = await self._establish_monitoring_baselines(competitor_profiles)

            # Set up monitoring alerts
            alert_configuration = await self._configure_monitoring_alerts(
                competitor_profiles, monitoring_level
            )

            # Store initial monitoring setup
            monitoring_setup = {
                "user_id": user_id,
                "competitors": [asdict(profile) for profile in competitor_profiles],
                "baselines": baselines,
                "alert_configuration": alert_configuration,
                "monitoring_level": monitoring_level,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            await self.firebase_service.store_agent_file(
                f"competitive_intelligence/{user_id}/monitoring_setup",
                json.dumps(monitoring_setup, indent=2, default=str)
            )

            # Start background monitoring
            asyncio.create_task(self._background_monitoring_loop(user_id, competitor_profiles))

            return {
                "success": True,
                "competitors_monitored": len(competitor_profiles),
                "monitoring_level": monitoring_level,
                "alert_count": len(alert_configuration.get("alerts", [])),
                "next_scan": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error initializing competitive monitoring: {e}")
            raise

    async def generate_competitive_analysis(
        self,
        user_id: str,
        analysis_type: str = "comprehensive",
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive competitive analysis"""
        try:
            self.logger.info(f"Generating competitive analysis: {analysis_type}")

            # Get current competitor data
            competitor_profiles = await self._get_monitored_competitors(user_id)

            if not competitor_profiles:
                return {"error": "No competitors being monitored"}

            # Generate different analysis components
            analysis_components = {}

            # Market positioning analysis
            if analysis_type in ["comprehensive", "positioning"]:
                analysis_components["market_positioning"] = await self._analyze_market_positioning(
                    competitor_profiles
                )

            # Product feature comparison
            if analysis_type in ["comprehensive", "features"]:
                analysis_components["product_comparison"] = await self._analyze_product_features(
                    competitor_profiles
                )

            # Pricing analysis
            if analysis_type in ["comprehensive", "pricing"]:
                analysis_components["pricing_analysis"] = await self._analyze_pricing_competitive(
                    competitor_profiles
                )

            # Threat assessment
            if analysis_type in ["comprehensive", "threats"]:
                analysis_components["threat_assessment"] = await self._assess_competitive_threats(
                    competitor_profiles
                )

            # Opportunity identification
            if analysis_type in ["comprehensive", "opportunities"]:
                analysis_components["opportunity_analysis"] = await self._identify_strategic_opportunities(
                    competitor_profiles
                )

            # Trend analysis
            if analysis_type in ["comprehensive", "trends"]:
                analysis_components["trend_analysis"] = await self._analyze_market_trends(
                    competitor_profiles
                )

            # Generate strategic recommendations
            strategic_recommendations = await self._generate_strategic_recommendations(
                analysis_components, focus_areas
            )

            # Compile comprehensive analysis
            competitive_analysis = {
                "analysis_id": f"competitive_analysis_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
                "analysis_type": analysis_type,
                "focus_areas": focus_areas or [],
                "competitors_analyzed": len(competitor_profiles),
                "analysis_components": analysis_components,
                "strategic_recommendations": strategic_recommendations,
                "executive_summary": await self._generate_executive_summary(analysis_components),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_quality": await self._assess_analysis_quality(analysis_components)
            }

            # Store analysis
            await self._store_competitive_analysis(competitive_analysis, user_id)

            return competitive_analysis

        except Exception as e:
            self.logger.error(f"Error generating competitive analysis: {e}")
            raise

    async def _validate_competitor_list(self, competitor_list: List[str]) -> List[Dict[str, str]]:
        """Validate and enrich competitor list"""
        try:
            validated_competitors = []

            for competitor in competitor_list:
                # Search for competitor information
                search_results = await self.web_search.search(f"{competitor} company information")

                if search_results:
                    # Extract basic information
                    competitor_info = {
                        "name": competitor,
                        "website": self._extract_website(search_results),
                        "description": self._extract_description(search_results)
                    }
                    validated_competitors.append(competitor_info)
                else:
                    # Add with minimal information
                    competitor_info = {
                        "name": competitor,
                        "website": "",
                        "description": "Competitor company"
                    }
                    validated_competitors.append(competitor_info)

            return validated_competitors

        except Exception as e:
            self.logger.error(f"Error validating competitor list: {e}")
            return [{"name": comp, "website": "", "description": ""} for comp in competitor_list]

    def _extract_website(self, search_results: List[Dict[str, Any]]) -> str:
        """Extract website from search results"""
        try:
            for result in search_results:
                url = result.get("url", "")
                if url and not any(exclude in url for exclude in ["linkedin", "crunchbase", "twitter"]):
                    return url
            return ""
        except:
            return ""

    def _extract_description(self, search_results: List[Dict[str, Any]]) -> str:
        """Extract company description from search results"""
        try:
            for result in search_results:
                description = result.get("description", "")
                if description and len(description) > 50:
                    return description[:200]  # Truncate if too long
            return ""
        except:
            return ""

    async def _create_competitor_profile(self, competitor_info: Dict[str, str]) -> CompetitorProfile:
        """Create comprehensive competitor profile"""
        try:
            name = competitor_info["name"]
            website = competitor_info.get("website", "")

            # Gather detailed information using web search and analysis
            detailed_info = await self._gather_competitor_details(name, website)

            return CompetitorProfile(
                competitor_id=f"comp_{uuid.uuid4().hex[:8]}",
                name=name,
                website=website,
                size=CompetitorSize(detailed_info.get("size", "medium")),
                founded_year=detailed_info.get("founded_year", 2015),
                funding_stage=detailed_info.get("funding_stage", "unknown"),
                total_funding=detailed_info.get("total_funding", 0),
                employee_count=detailed_info.get("employee_count", 50),
                headquarters=detailed_info.get("headquarters", "Unknown"),
                target_markets=detailed_info.get("target_markets", []),
                key_products=detailed_info.get("key_products", []),
                unique_value_proposition=detailed_info.get("value_proposition", ""),
                strengths=detailed_info.get("strengths", []),
                weaknesses=detailed_info.get("weaknesses", []),
                recent_developments=detailed_info.get("recent_developments", []),
                social_media_presence=detailed_info.get("social_media", {}),
                contact_info=detailed_info.get("contact_info", {}),
                last_updated=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error creating competitor profile for {competitor_info.get('name', 'Unknown')}: {e}")
            # Return basic profile
            return CompetitorProfile(
                competitor_id=f"comp_{uuid.uuid4().hex[:8]}",
                name=competitor_info.get("name", "Unknown"),
                website=competitor_info.get("website", ""),
                size=CompetitorSize.MEDIUM,
                founded_year=2015,
                funding_stage="unknown",
                total_funding=0,
                employee_count=50,
                headquarters="Unknown",
                target_markets=[],
                key_products=[],
                unique_value_proposition="",
                strengths=[],
                weaknesses=[],
                recent_developments=[],
                social_media_presence={},
                contact_info={},
                last_updated=datetime.now(timezone.utc)
            )

    async def _gather_competitor_details(self, name: str, website: str) -> Dict[str, Any]:
        """Gather detailed competitor information"""
        try:
            details = {
                "size": "medium",
                "founded_year": 2015,
                "funding_stage": "unknown",
                "total_funding": 0,
                "employee_count": 50,
                "headquarters": "Unknown",
                "target_markets": [],
                "key_products": [],
                "value_proposition": "",
                "strengths": [],
                "weaknesses": [],
                "recent_developments": [],
                "social_media": {},
                "contact_info": {}
            }

            # Use web search to gather information
            search_queries = [
                f"{name} company profile funding",
                f"{name} products services",
                f"{name} competitors market",
                f"{name} recent news developments"
            ]

            all_results = []
            for query in search_queries:
                results = await self.web_search.search(query)
                all_results.extend(results)

            # Use LLM to extract structured information
            if all_results:
                structured_info = await self._extract_structured_competitor_info(name, all_results)
                details.update(structured_info)

            # Enhance with website-specific information if available
            if website:
                website_info = await self._analyze_competitor_website(website)
                details.update(website_info)

            return details

        except Exception as e:
            self.logger.error(f"Error gathering competitor details for {name}: {e}")
            return {}

    async def _extract_structured_competitor_info(
        self,
        competitor_name: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract structured competitor information using LLM"""
        try:
            # Combine search results for analysis
            combined_text = "\n".join([
                f"Title: {result.get('title', '')}\n"
                f"Description: {result.get('description', '')}\n"
                for result in search_results[:10]  # Limit to top 10 results
            ])

            system_prompt = """
            You are a business intelligence analyst extracting structured information about a competitor company.

            Analyze the provided search results and extract the following information:
            1. Company size (startup, small, medium, large, enterprise)
            2. Founded year
            3. Funding stage (seed, series A, series B, etc.)
            4. Total funding amount (if mentioned)
            5. Employee count (if mentioned)
            6. Headquarters location
            7. Target markets/industries
            8. Key products and services
            9. Unique value proposition
            10. Company strengths
            11. Company weaknesses
            12. Recent developments/news

            Be specific and factual. If information is not available, indicate as "unknown" or omit the field.
            """

            human_prompt = f"""
            Extract structured information about {competitor_name} from these search results:

            {combined_text}

            Provide the information in a structured format that can be easily parsed.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse the response to extract structured data
            # This is a simplified parser - in production, you'd want more sophisticated parsing
            response_text = response.content.lower()

            extracted_info = {}

            # Extract size
            size_keywords = ["startup", "small", "medium", "large", "enterprise"]
            for keyword in size_keywords:
                if keyword in response_text:
                    extracted_info["size"] = keyword
                    break

            # Extract founded year
            year_match = re.search(r'founded\s*(?:in)?\s*(\d{4})', response_text)
            if year_match:
                extracted_info["founded_year"] = int(year_match.group(1))

            # Extract funding stage
            funding_keywords = ["seed", "series a", "series b", "series c", "ipo", "public"]
            for keyword in funding_keywords:
                if keyword in response_text:
                    extracted_info["funding_stage"] = keyword
                    break

            # Extract employee count
            employee_match = re.search(r'(\d+)\s*(?:employees?|staff)', response_text)
            if employee_match:
                extracted_info["employee_count"] = int(employee_match.group(1))

            # Extract headquarters
            location_match = re.search(r'(?:headquartered|based|located)\s+(?:in\s+)?([^.]+)', response_text)
            if location_match:
                extracted_info["headquarters"] = location_match.group(1).strip().title()

            return extracted_info

        except Exception as e:
            self.logger.error(f"Error extracting structured competitor info: {e}")
            return {}

    async def _analyze_competitor_website(self, website: str) -> Dict[str, Any]:
        """Analyze competitor website for additional insights"""
        try:
            # This would use web scraping tools to analyze the website
            # For now, return mock data
            return {
                "products": ["Product A", "Product B"],
                "pricing": {"basic": "$99", "pro": "$299", "enterprise": "Custom"}
            }

        except Exception as e:
            self.logger.error(f"Error analyzing competitor website {website}: {e}")
            return {}

    async def _establish_monitoring_baselines(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> Dict[str, Any]:
        """Establish baselines for monitoring"""
        try:
            baselines = {
                "pricing_baselines": {},
                "feature_baselines": {},
                "market_positioning_baselines": {},
                "social_media_baselines": {},
                "established_at": datetime.now(timezone.utc).isoformat()
            }

            for profile in competitor_profiles:
                # Pricing baselines would be gathered from pricing pages
                baselines["pricing_baselines"][profile.competitor_id] = {
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                    "prices": {}  # Would contain actual pricing data
                }

                # Feature baselines
                baselines["feature_baselines"][profile.competitor_id] = {
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                    "features": profile.key_products
                }

                # Social media baselines
                baselines["social_media_baselines"][profile.competitor_id] = {
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                    "followers": {},  # Would contain follower counts
                    "recent_posts": []
                }

            return baselines

        except Exception as e:
            self.logger.error(f"Error establishing monitoring baselines: {e}")
            return {"error": str(e)}

    async def _configure_monitoring_alerts(
        self,
        competitor_profiles: List[CompetitorProfile],
        monitoring_level: str
    ) -> Dict[str, Any]:
        """Configure monitoring alerts"""
        try:
            alert_config = {
                "monitoring_level": monitoring_level,
                "alert_frequency": "daily" if monitoring_level == "intensive" else "weekly",
                "alerts": []
            }

            # Configure alerts for each competitor
            for profile in competitor_profiles:
                competitor_alerts = {
                    "competitor_id": profile.competitor_id,
                    "competitor_name": profile.name,
                    "alert_types": []
                }

                # Standard alerts for all monitoring levels
                competitor_alerts["alert_types"].extend([
                    "new_product_launch",
                    "pricing_changes",
                    "funding_announcements",
                    "executive_hires",
                    "major_partnerships"
                ])

                # Additional alerts for intensive monitoring
                if monitoring_level == "intensive":
                    competitor_alerts["alert_types"].extend([
                        "website_updates",
                        "social_media_activity",
                        "customer_reviews",
                        "job_postings",
                        "patent_filings"
                    ])

                alert_config["alerts"].append(competitor_alerts)

            return alert_config

        except Exception as e:
            self.logger.error(f"Error configuring monitoring alerts: {e}")
            return {}

    async def _background_monitoring_loop(
        self,
        user_id: str,
        competitor_profiles: List[CompetitorProfile]
    ):
        """Background monitoring loop"""
        try:
            while True:
                self.logger.info("Running competitive intelligence monitoring scan")

                # Monitor each competitor for changes
                for profile in competitor_profiles:
                    await self._monitor_competitor_changes(user_id, profile)

                # Sleep until next scan
                await asyncio.sleep(self.monitoring_config["monitoring_frequency"])

        except Exception as e:
            self.logger.error(f"Error in background monitoring loop: {e}")

    async def _monitor_competitor_changes(self, user_id: str, profile: CompetitorProfile):
        """Monitor individual competitor for changes"""
        try:
            # Check for website changes
            website_changes = await self._check_website_changes(profile)

            # Check for news and announcements
            news_changes = await self._check_competitor_news(profile)

            # Check for social media activity
            social_changes = await self._check_social_media_activity(profile)

            # If changes detected, create alerts
            if website_changes or news_changes or social_changes:
                await self._create_competitive_alert(user_id, profile, {
                    "website_changes": website_changes,
                    "news_changes": news_changes,
                    "social_changes": social_changes
                })

        except Exception as e:
            self.logger.error(f"Error monitoring competitor {profile.name}: {e}")

    async def _check_website_changes(self, profile: CompetitorProfile) -> List[str]:
        """Check for website changes"""
        try:
            # This would compare current website content with stored baseline
            # For now, return empty list
            return []

        except Exception as e:
            self.logger.error(f"Error checking website changes for {profile.name}: {e}")
            return []

    async def _check_competitor_news(self, profile: CompetitorProfile) -> List[str]:
        """Check for competitor news and announcements"""
        try:
            # Search for recent news
            news_query = f"{profile.name} recent news announcements"
            search_results = await self.web_search.search(news_query)

            # Filter for recent news (last 24 hours)
            recent_news = []
            for result in search_results:
                # Check if news is recent (simplified check)
                recent_news.append(result.get("title", ""))

            return recent_news[:3]  # Return top 3 recent news items

        except Exception as e:
            self.logger.error(f"Error checking competitor news for {profile.name}: {e}")
            return []

    async def _check_social_media_activity(self, profile: CompetitorProfile) -> List[str]:
        """Check for significant social media activity"""
        try:
            # This would integrate with social media APIs
            # For now, return empty list
            return []

        except Exception as e:
            self.logger.error(f"Error checking social media activity for {profile.name}: {e}")
            return []

    async def _create_competitive_alert(
        self,
        user_id: str,
        profile: CompetitorProfile,
        changes: Dict[str, List[str]]
    ) -> None:
        """Create competitive intelligence alert"""
        try:
            alert = {
                "alert_id": f"alert_{uuid.uuid4().hex[:8]}",
                "competitor_id": profile.competitor_id,
                "competitor_name": profile.name,
                "alert_type": "competitor_activity",
                "severity": "medium",
                "changes": changes,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "reviewed": False
            }

            # Store alert
            await self.firebase_service.store_agent_file(
                f"competitive_intelligence/{user_id}/alerts/{alert['alert_id']}",
                json.dumps(alert, indent=2, default=str)
            )

            self.logger.info(f"Created competitive alert for {profile.name}")

        except Exception as e:
            self.logger.error(f"Error creating competitive alert: {e}")

    async def _get_monitored_competitors(self, user_id: str) -> List[CompetitorProfile]:
        """Get list of monitored competitors"""
        try:
            # Retrieve monitoring setup from Firebase
            setup_data = await self.firebase_service.get_agent_file(
                f"competitive_intelligence/{user_id}/monitoring_setup"
            )

            if not setup_data:
                return []

            # Parse competitor profiles
            competitors = []
            for comp_data in setup_data.get("competitors", []):
                try:
                    profile = CompetitorProfile(
                        competitor_id=comp_data["competitor_id"],
                        name=comp_data["name"],
                        website=comp_data["website"],
                        size=CompetitorSize(comp_data["size"]),
                        founded_year=comp_data["founded_year"],
                        funding_stage=comp_data["funding_stage"],
                        total_funding=comp_data["total_funding"],
                        employee_count=comp_data["employee_count"],
                        headquarters=comp_data["headquarters"],
                        target_markets=comp_data["target_markets"],
                        key_products=comp_data["key_products"],
                        unique_value_proposition=comp_data["unique_value_proposition"],
                        strengths=comp_data["strengths"],
                        weaknesses=comp_data["weaknesses"],
                        recent_developments=comp_data["recent_developments"],
                        social_media_presence=comp_data["social_media_presence"],
                        contact_info=comp_data["contact_info"],
                        last_updated=datetime.fromisoformat(comp_data["last_updated"])
                    )
                    competitors.append(profile)
                except Exception as e:
                    self.logger.error(f"Error parsing competitor profile: {e}")

            return competitors

        except Exception as e:
            self.logger.error(f"Error getting monitored competitors: {e}")
            return []

    async def _analyze_market_positioning(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> Dict[str, Any]:
        """Analyze market positioning"""
        try:
            positioning_analysis = {
                "market_segments": {},
                "positioning_maps": {},
                "price_positioning": {},
                "quality_positioning": {},
                "competitive_landscape": {}
            }

            # Group competitors by market segments
            market_segments = {}
            for profile in competitor_profiles:
                for market in profile.target_markets:
                    if market not in market_segments:
                        market_segments[market] = []
                    market_segments[market].append(profile)

            # Analyze each market segment
            for segment, competitors in market_segments.items():
                positioning_analysis["market_segments"][segment] = {
                    "competitor_count": len(competitors),
                    "competitors": [
                        {
                            "name": comp.name,
                            "size": comp.size.value,
                            "market_position": "unknown"  # Would be calculated based on market share
                        }
                        for comp in competitors
                    ]
                }

            # Create positioning maps (price vs quality)
            positioning_analysis["positioning_maps"]["price_quality"] = await self._create_positioning_map(
                competitor_profiles, "price", "quality"
            )

            return positioning_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing market positioning: {e}")
            return {}

    async def _create_positioning_map(
        self,
        competitors: List[CompetitorProfile],
        x_axis: str,
        y_axis: str
    ) -> Dict[str, Any]:
        """Create positioning map"""
        try:
            # This would analyze competitor positioning on two dimensions
            # For now, return mock data
            return {
                "axis_labels": {"x": x_axis, "y": y_axis},
                "quadrants": {
                    "top_right": "Premium",
                    "top_left": "Quality-focused",
                    "bottom_right": "Value",
                    "bottom_left": "Budget"
                },
                "competitor_positions": {
                    "comp_1": {"x": 0.7, "y": 0.8},
                    "comp_2": {"x": 0.3, "y": 0.6},
                    "us": {"x": 0.5, "y": 0.7}
                }
            }

        except Exception as e:
            self.logger.error(f"Error creating positioning map: {e}")
            return {}

    async def _analyze_product_features(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> List[ProductComparison]:
        """Analyze product features compared to competitors"""
        try:
            # This would involve detailed feature analysis
            # For now, return mock data
            feature_comparisons = []

            # Sample feature comparison
            comparison = ProductComparison(
                product_id="core_platform",
                feature_name="AI-powered Automation",
                our_capability="Advanced machine learning algorithms",
                competitor_capabilities={
                    "comp_1": "Basic automation rules",
                    "comp_2": "No automation capabilities"
                },
                feature_importance=0.9,
                market_standard="Basic automation",
                innovation_level="cutting_edge",
                competitive_advantage="leader",
                development_priority="high",
                gap_analysis="We have significant advantage in AI capabilities",
                recommendation="Continue to invest and market this advantage"
            )
            feature_comparisons.append(comparison)

            return feature_comparisons

        except Exception as e:
            self.logger.error(f"Error analyzing product features: {e}")
            return []

    async def _analyze_pricing_competitive(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> Dict[str, Any]:
        """Analyze competitive pricing"""
        try:
            pricing_analysis = {
                "market_average": 250.0,
                "price_range": {"min": 99.0, "max": 999.0},
                "our_positioning": "mid_range",
                "competitor_pricing": {},
                "pricing_recommendations": []
            }

            # Analyze competitor pricing
            for profile in competitor_profiles:
                # This would gather actual pricing data
                pricing_analysis["competitor_pricing"][profile.competitor_id] = {
                    "name": profile.name,
                    "pricing_tier": "mid_range",
                    "average_price": 299.0,
                    "pricing_model": "tiered"
                }

            return pricing_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing competitive pricing: {e}")
            return {}

    async def _assess_competitive_threats(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> List[CompetitiveThreat]:
        """Assess competitive threats"""
        try:
            threats = []

            for profile in competitor_profiles:
                # Analyze potential threats from each competitor
                if profile.size in [CompetitorSize.LARGE, CompetitorSize.ENTERPRISE]:
                    threat = CompetitiveThreat(
                        threat_id=f"threat_{uuid.uuid4().hex[:8]}",
                        threat_type="market_dominance",
                        source_competitor=profile.name,
                        threat_level=CompetitiveThreat.HIGH,
                        description=f"Large competitor {profile.name} could dominate market",
                        timeline="medium_term",
                        potential_impact="Market share loss, pricing pressure",
                        affected_markets=profile.target_markets,
                        warning_indicators=["Price cuts", "Marketing campaigns", "Product launches"],
                        monitoring_keywords=[profile.name, "pricing", "launch"],
                        recommended_actions=["Monitor pricing", "Differentiate value proposition", "Focus on niche"],
                        contingency_plans=["Alternative positioning", "Price matching strategy"],
                        created_at=datetime.now(timezone.utc),
                        last_assessed=datetime.now(timezone.utc)
                    )
                    threats.append(threat)

            return threats

        except Exception as e:
            self.logger.error(f"Error assessing competitive threats: {e}")
            return []

    async def _identify_strategic_opportunities(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> List[StrategicOpportunity]:
        """Identify strategic opportunities"""
        try:
            opportunities = []

            # Analyze market gaps
            market_gaps = await self._identify_market_gaps(competitor_profiles)

            for gap in market_gaps:
                opportunity = StrategicOpportunity(
                    opportunity_id=f"opp_{uuid.uuid4().hex[:8]}",
                    title=f"Market Opportunity: {gap['name']}",
                    opportunity_type=OpportunityType.MARKET_EXPANSION,
                    description=gap["description"],
                    market_size=gap["market_size"],
                    confidence_score=gap["confidence"],
                    time_to_market="6 months",
                    required_investment=gap["investment_required"],
                    expected_roi=gap["expected_roi"],
                    competitive_landscape=gap["competitive_landscape"],
                    success_factors=gap["success_factors"],
                    risks=gap["risks"],
                    first_mover_advantage=gap["first_mover_advantage"],
                    implementation_roadmap=gap["implementation_steps"],
                    kpis=gap["kpis"],
                    created_at=datetime.now(timezone.utc)
                )
                opportunities.append(opportunity)

            return opportunities

        except Exception as e:
            self.logger.error(f"Error identifying strategic opportunities: {e}")
            return []

    async def _identify_market_gaps(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> List[Dict[str, Any]]:
        """Identify gaps in the market"""
        try:
            # This would analyze market segments and competitor offerings
            # For now, return sample market gap
            return [
                {
                    "name": "AI-powered Small Business Automation",
                    "description": "Competitors focus on enterprise market, small business segment underserved",
                    "market_size": 50000000,  # $50M
                    "confidence": 0.8,
                    "investment_required": 250000,  # $250k
                    "expected_roi": 3.5,
                    "competitive_landscape": {"threat_level": "low", "barriers": "moderate"},
                    "success_factors": ["Simplified UI", "Affordable pricing", "Quick setup"],
                    "risks": ["Market size validation", "Customer acquisition cost"],
                    "first_mover_advantage": True,
                    "implementation_steps": ["Market research", "MVP development", "Beta testing"],
                    "kpis": ["Customer acquisition", "Revenue growth", "Market share"]
                }
            ]

        except Exception as e:
            self.logger.error(f"Error identifying market gaps: {e}")
            return []

    async def _analyze_market_trends(
        self,
        competitor_profiles: List[CompetitorProfile]
    ) -> List[TrendAnalysis]:
        """Analyze market and industry trends"""
        try:
            trends = []

            # Search for industry trends
            trend_search = await self.web_search.search("SaaS industry trends 2024")

            if trend_search:
                # Use LLM to analyze trends
                trend_analysis = await self._analyze_industry_trends_with_llm(trend_search)

                for trend in trend_analysis:
                    trend_obj = TrendAnalysis(
                        trend_id=f"trend_{uuid.uuid4().hex[:8]}",
                        trend_name=trend["name"],
                        category=trend["category"],
                        trend_direction=trend["direction"],
                        impact_level=trend["impact"],
                        time_horizon=trend["time_horizon"],
                        description=trend["description"],
                        supporting_data=trend["data"],
                        affected_companies=[comp.name for comp in competitor_profiles],
                        opportunity_areas=trend["opportunities"],
                        risk_areas=trend["risks"],
                        confidence_score=trend["confidence"],
                        last_updated=datetime.now(timezone.utc)
                    )
                    trends.append(trend_obj)

            return trends

        except Exception as e:
            self.logger.error(f"Error analyzing market trends: {e}")
            return []

    async def _analyze_industry_trends_with_llm(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze industry trends using LLM"""
        try:
            # Combine search results
            combined_text = "\n".join([
                f"Title: {result.get('title', '')}\n"
                f"Description: {result.get('description', '')}\n"
                for result in search_results[:10]
            ])

            system_prompt = """
            You are a market research analyst identifying industry trends from search results.

            Analyze the provided information and identify key trends in the SaaS/tech industry.
            For each trend, provide:
            1. Trend name
            2. Category (technology, market, customer, regulatory)
            3. Direction (emerging, growing, mature, declining)
            4. Impact level (low, medium, high, transformative)
            5. Time horizon (short_term, medium_term, long_term)
            6. Description
            7. Supporting data points
            8. Opportunity areas
            9. Risk areas
            10. Confidence score (0-1)

            Focus on actionable trends that businesses should be aware of.
            """

            human_prompt = f"""
            Analyze these industry search results and identify key trends:

            {combined_text}

            Provide specific, actionable trend analysis with confidence scores.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse response (simplified)
            # In production, you'd want more sophisticated parsing
            return [
                {
                    "name": "AI Integration in SaaS",
                    "category": "technology",
                    "direction": "growing",
                    "impact": "transformative",
                    "time_horizon": "medium_term",
                    "description": "Increasing integration of AI capabilities across SaaS products",
                    "data": ["AI adoption rates", "Product announcements"],
                    "opportunities": ["AI-powered features", "Automation"],
                    "risks": ["Implementation complexity", "Competition"],
                    "confidence": 0.9
                }
            ]

        except Exception as e:
            self.logger.error(f"Error analyzing industry trends with LLM: {e}")
            return []

    async def _generate_strategic_recommendations(
        self,
        analysis_components: Dict[str, Any],
        focus_areas: List[str] = None
    ) -> List[str]:
        """Generate strategic recommendations based on analysis"""
        try:
            recommendations = []

            # Analyze positioning for recommendations
            if "market_positioning" in analysis_components:
                positioning = analysis_components["market_positioning"]
                recommendations.extend(await self._generate_positioning_recommendations(positioning))

            # Analyze feature comparisons for recommendations
            if "product_comparison" in analysis_components:
                features = analysis_components["product_comparison"]
                recommendations.extend(await self._generate_feature_recommendations(features))

            # Analyze threats for recommendations
            if "threat_assessment" in analysis_components:
                threats = analysis_components["threat_assessment"]
                recommendations.extend(await self._generate_threat_recommendations(threats))

            # Analyze opportunities for recommendations
            if "opportunity_analysis" in analysis_components:
                opportunities = analysis_components["opportunity_analysis"]
                recommendations.extend(await self._generate_opportunity_recommendations(opportunities))

            # Filter by focus areas if specified
            if focus_areas:
                filtered_recommendations = []
                for rec in recommendations:
                    if any(area in rec.lower() for area in focus_areas):
                        filtered_recommendations.append(rec)
                recommendations = filtered_recommendations

            return recommendations[:10]  # Top 10 recommendations

        except Exception as e:
            self.logger.error(f"Error generating strategic recommendations: {e}")
            return ["Review competitive analysis and develop targeted strategies"]

    async def _generate_positioning_recommendations(self, positioning: Dict[str, Any]) -> List[str]:
        """Generate positioning-based recommendations"""
        try:
            recommendations = []

            # Check market positioning
            market_segments = positioning.get("market_segments", {})
            for segment, data in market_segments.items():
                competitor_count = data.get("competitor_count", 0)
                if competitor_count > 5:
                    recommendations.append(f"Differentiate strongly in {segment} market due to high competition")
                elif competitor_count < 2:
                    recommendations.append(f"Consider expansion in {segment} market with low competition")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating positioning recommendations: {e}")
            return []

    async def _generate_feature_recommendations(self, features: List) -> List[str]:
        """Generate feature-based recommendations"""
        try:
            recommendations = []

            for feature in features:
                if hasattr(feature, 'competitive_advantage'):
                    if feature.competitive_advantage == "leader":
                        recommendations.append(f"Market and expand {feature.feature_name} advantage")
                    elif feature.competitive_advantage == "lagging":
                        recommendations.append(f"Prioritize development of {feature.feature_name}")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating feature recommendations: {e}")
            return []

    async def _generate_threat_recommendations(self, threats: List) -> List[str]:
        """Generate threat-based recommendations"""
        try:
            recommendations = []

            for threat in threats:
                if hasattr(threat, 'threat_level'):
                    if threat.threat_level == CompetitiveThreat.CRITICAL:
                        recommendations.append(f"Immediate action required for {threat.source_competitor} threat")
                    elif threat.threat_level == CompetitiveThreat.HIGH:
                        recommendations.append(f"Develop contingency plans for {threat.source_competitor}")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating threat recommendations: {e}")
            return []

    async def _generate_opportunity_recommendations(self, opportunities: List) -> List[str]:
        """Generate opportunity-based recommendations"""
        try:
            recommendations = []

            for opportunity in opportunities:
                if hasattr(opportunity, 'confidence_score') and opportunity.confidence_score > 0.7:
                    recommendations.append(f"Pursue {opportunity.title} with high confidence")

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating opportunity recommendations: {e}")
            return []

    async def _generate_executive_summary(
        self,
        analysis_components: Dict[str, Any]
    ) -> str:
        """Generate executive summary of competitive analysis"""
        try:
            # Prepare context for LLM
            context = {
                "analysis_components": analysis_components,
                "date": datetime.now().strftime("%Y-%m-%d")
            }

            system_prompt = """
            You are a strategic business analyst creating an executive summary of competitive intelligence.

            Create a concise, impactful executive summary that:
            1. Highlights key competitive insights
            2. Identifies critical threats and opportunities
            3. Provides strategic recommendations
            4. Maintains a professional, strategic tone
            5. Is 200-300 words maximum

            Focus on actionable insights that leadership can use for strategic decision-making.
            """

            human_prompt = f"""
            Generate an executive summary based on this competitive analysis:

            {json.dumps(context, indent=2)}

            Focus on the most critical insights and strategic implications.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            return response.content.strip()

        except Exception as e:
            self.logger.error(f"Error generating executive summary: {e}")
            return "Executive summary generation failed. Please review the detailed analysis."

    async def _assess_analysis_quality(self, analysis_components: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality of competitive analysis"""
        try:
            quality_metrics = {
                "completeness": 0.0,
                "data_freshness": 0.0,
                "confidence_score": 0.0,
                "data_sources": 0
            }

            # Assess completeness
            expected_components = [
                "market_positioning", "product_comparison", "pricing_analysis",
                "threat_assessment", "opportunity_analysis", "trend_analysis"
            ]
            actual_components = len(analysis_components)
            quality_metrics["completeness"] = actual_components / len(expected_components)

            # Assess data freshness (mock calculation)
            quality_metrics["data_freshness"] = 0.9

            # Calculate overall confidence
            quality_metrics["confidence_score"] = (
                quality_metrics["completeness"] * 0.4 +
                quality_metrics["data_freshness"] * 0.6
            )

            quality_metrics["data_sources"] = 5  # Mock data source count

            return quality_metrics

        except Exception as e:
            self.logger.error(f"Error assessing analysis quality: {e}")
            return {"error": str(e)}

    async def _store_competitive_analysis(self, analysis: Dict[str, Any], user_id: str):
        """Store competitive analysis in Firebase"""
        try:
            await self.firebase_service.store_agent_file(
                f"competitive_intelligence/{user_id}/analysis/{analysis['analysis_id']}",
                json.dumps(analysis, indent=2, default=str)
            )

            self.logger.info(f"Stored competitive analysis {analysis['analysis_id']}")

        except Exception as e:
            self.logger.error(f"Error storing competitive analysis: {e}")

    async def get_competitive_alerts(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get competitive intelligence alerts"""
        try:
            # Retrieve alerts from Firebase
            alerts = await self.firebase_service.get_agent_files_by_prefix(
                f"competitive_intelligence/{user_id}/alerts/"
            )

            # Parse alerts
            parsed_alerts = []
            for alert_file in alerts:
                try:
                    alert_data = json.loads(alert_file.get("content", "{}"))
                    if not unread_only or not alert_data.get("reviewed", False):
                        parsed_alerts.append(alert_data)
                except:
                    continue

            # Sort by creation date (newest first)
            parsed_alerts.sort(
                key=lambda x: datetime.fromisoformat(x.get("created_at", "1970-01-01")),
                reverse=True
            )

            return {
                "alerts": parsed_alerts[:limit],
                "total_count": len(parsed_alerts),
                "unread_count": len([a for a in parsed_alerts if not a.get("reviewed", False)])
            }

        except Exception as e:
            self.logger.error(f"Error getting competitive alerts: {e}")
            return {"alerts": [], "error": str(e)}