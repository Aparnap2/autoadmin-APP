"""
Business Intelligence Module
Comprehensive business intelligence and analytics module for AutoAdmin.

This module provides:
- Morning briefing generation with executive summaries
- Revenue intelligence and forecasting
- Intelligent task delegation
- Competitive intelligence monitoring
- CRM intelligence and deal health scoring
- Strategic planning and OKR tracking
- KPI calculation and monitoring
- Alert management system
- Real-time streaming integration
"""

__version__ = "1.0.0"
__author__ = "AutoAdmin Team"

# Import main classes for easy access
from .morning_briefing import MorningBriefingGenerator
from .revenue_intelligence import RevenueIntelligenceEngine
from .task_delegator import IntelligentTaskDelegator
from .competitive_intelligence import CompetitiveIntelligenceEngine
from .crm_intelligence import CRMIntelligenceEngine
from .strategic_planner import StrategicPlannerEngine
from .kpi_calculator import KPIEngine
from .alert_system import AlertManagementSystem
from .streaming_integration import BIDataStreamManager, StreamingEvent, StreamingEventType

__all__ = [
    "MorningBriefingGenerator",
    "RevenueIntelligenceEngine",
    "IntelligentTaskDelegator",
    "CompetitiveIntelligenceEngine",
    "CRMIntelligenceEngine",
    "StrategicPlannerEngine",
    "KPIEngine",
    "AlertManagementSystem",
    "BIDataStreamManager",
    "StreamingEvent",
    "StreamingEventType"
]

# Module metadata
MODULE_INFO = {
    "name": "Business Intelligence",
    "version": __version__,
    "description": "Comprehensive business intelligence and analytics module",
    "components": [
        "Morning Briefing Generator",
        "Revenue Intelligence Engine",
        "Intelligent Task Delegator",
        "Competitive Intelligence Engine",
        "CRM Intelligence Engine",
        "Strategic Planner Engine",
        "KPI Calculation Engine",
        "Alert Management System",
        "Real-time Streaming Integration"
    ],
    "features": [
        "Executive dashboard integration",
        "Real-time streaming with SSE",
        "Advanced analytics and forecasting",
        "Intelligent task delegation",
        "KPI monitoring and alerting",
        "Competitive intelligence",
        "CRM integration and deal scoring",
        "Strategic planning and OKR tracking"
    ]
}

def get_module_info():
    """Get module information"""
    return MODULE_INFO

def get_available_components():
    """Get list of available components"""
    return __all__

def create_business_intelligence_suite():
    """Create a complete business intelligence suite with all components"""
    return {
        "morning_briefing": MorningBriefingGenerator(),
        "revenue_intelligence": RevenueIntelligenceEngine(),
        "task_delegator": IntelligentTaskDelegator(),
        "competitive_intelligence": CompetitiveIntelligenceEngine(),
        "crm_intelligence": CRMIntelligenceEngine(),
        "strategic_planner": StrategicPlannerEngine(),
        "kpi_engine": KPIEngine(),
        "alert_system": AlertManagementSystem(),
        "streaming_manager": BIDataStreamManager()
    }