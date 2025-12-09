"""
Intelligent Task Delegation System
Context-aware task evaluation, intelligent routing, and business impact assessment
for automated task delegation to specialized agents.
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

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base_agent import BaseAgent, AgentType, TaskType, TaskStatus, TaskDelegation
from services.firebase_service import get_firebase_service
from services.agent_orchestrator_http import get_http_agent_orchestrator


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BusinessImpact(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskPriority(str, Enum):
    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"
    CRITICAL = "critical"


class DelegationStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    BEST_FIT = "best_fit"
    SPECIALIZED = "specialized"
    HYBRID = "hybrid"


@dataclass
class TaskEvaluation:
    """Task evaluation with business impact assessment"""
    task_id: str
    title: str
    description: str
    complexity: TaskComplexity
    business_impact: BusinessImpact
    priority_score: float  # 0-100
    business_value: float  # Estimated business value
    urgency_level: TaskPriority
    dependencies: List[str]
    required_skills: List[str]
    estimated_duration: float  # hours
    resource_requirements: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    success_criteria: List[str]


@dataclass
class AgentCapability:
    """Agent capability assessment"""
    agent_id: str
    agent_type: AgentType
    current_load: float  # 0-1
    max_capacity: int
    specialties: List[str]
    performance_score: float  # 0-1
    success_rate: float  # 0-1
    average_completion_time: float  # hours
    availability: bool
    cost_per_hour: float
    skills_match: float  # 0-1


@dataclass
class DelegationDecision:
    """Intelligent delegation decision"""
    task_id: str
    recommended_agent: str
    confidence_score: float  # 0-1
    reasoning: str
    alternative_agents: List[Dict[str, Any]]
    expected_completion_time: float
    estimated_cost: float
    risk_factors: List[str]
    mitigation_strategies: List[str]
    delegation_strategy: DelegationStrategy
    created_at: datetime


@dataclass
class TaskEscalation:
    """Task escalation for critical issues"""
    escalation_id: str
    task_id: str
    original_agent: str
    escalation_reason: str
    escalation_level: str  # level_1, level_2, level_3
    escalation_criteria: List[str]
    notified_stakeholders: List[str]
    escalation_time: datetime
    resolution_status: str
    resolution_time: Optional[datetime]


class IntelligentTaskDelegator:
    """Advanced intelligent task delegation system"""

    def __init__(self, openai_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.firebase_service = get_firebase_service()
        self.agent_orchestrator = get_http_agent_orchestrator()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            max_tokens=2000,
            openai_api_key=openai_api_key
        )

        # Business rules configuration
        self.business_rules = {
            "priority_weights": {
                "business_impact": 0.4,
                "urgency": 0.3,
                "complexity": 0.2,
                "dependencies": 0.1
            },
            "impact_thresholds": {
                "revenue_impact": 10000,  # $10k
                "customer_impact": 100,   # 100 customers
                "time_critical": 24,      # 24 hours
                "strategic_importance": 0.8  # 0-1 scale
            },
            "escalation_rules": {
                "failure_rate_threshold": 0.2,  # 20% failure rate
                "timeout_threshold": 2.0,        # 2x estimated time
                "priority_escalation": TaskPriority.HIGH
            }
        }

        # Agent performance cache
        self._agent_capabilities_cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 300  # 5 minutes

    async def evaluate_and_delegate_task(
        self,
        task_data: Dict[str, Any],
        user_id: str,
        force_delegate: bool = False
    ) -> DelegationDecision:
        """Evaluate task and make intelligent delegation decision"""
        try:
            self.logger.info(f"Evaluating task for delegation: {task_data.get('title', 'Unknown')}")

            # Step 1: Evaluate task characteristics and business impact
            task_evaluation = await self._evaluate_task(task_data, user_id)

            # Step 2: Get current agent capabilities
            agent_capabilities = await self._get_agent_capabilities()

            # Step 3: Apply business rules for prioritization
            prioritized_task = await self._apply_business_rules(task_evaluation)

            # Step 4: Make intelligent delegation decision
            delegation_decision = await self._make_delegation_decision(
                prioritized_task, agent_capabilities
            )

            # Step 5: Validate decision and check for escalation needs
            validated_decision = await self._validate_delegation_decision(
                delegation_decision, prioritized_task
            )

            # Step 6: Execute delegation if approved
            if force_delegate or validated_decision.confidence_score > 0.7:
                await self._execute_delegation(validated_decision, user_id)
            else:
                self.logger.warning(
                    f"Low confidence delegation ({validated_decision.confidence_score:.2f}) "
                    f"for task {task_data.get('title')}. Manual review required."
                )

            # Store decision for analytics
            await self._store_delegation_decision(validated_decision, user_id)

            return validated_decision

        except Exception as e:
            self.logger.error(f"Error in evaluate_and_delegate_task: {e}")
            raise

    async def _evaluate_task(self, task_data: Dict[str, Any], user_id: str) -> TaskEvaluation:
        """Evaluate task characteristics and business impact"""
        try:
            task_id = task_data.get("id", f"task_{uuid.uuid4().hex[:8]}")
            title = task_data.get("title", "")
            description = task_data.get("description", "")

            # Analyze task complexity using LLM
            complexity_analysis = await self._analyze_task_complexity(
                title, description, task_data
            )

            # Assess business impact
            business_impact = await self._assess_business_impact(task_data, user_id)

            # Calculate priority score
            priority_score = await self._calculate_priority_score(
                complexity_analysis, business_impact, task_data
            )

            # Determine urgency level
            urgency_level = await self._determine_urgency_level(task_data, business_impact)

            # Extract dependencies
            dependencies = await self._extract_dependencies(task_data)

            # Identify required skills
            required_skills = await self._identify_required_skills(task_data, complexity_analysis)

            # Estimate duration
            estimated_duration = await self._estimate_task_duration(
                complexity_analysis, task_data
            )

            # Assess resource requirements
            resource_requirements = await self._assess_resource_requirements(
                task_data, complexity_analysis
            )

            # Conduct risk assessment
            risk_assessment = await self._conduct_risk_assessment(task_data, business_impact)

            # Define success criteria
            success_criteria = await self._define_success_criteria(task_data, business_impact)

            return TaskEvaluation(
                task_id=task_id,
                title=title,
                description=description,
                complexity=TaskComplexity(complexity_analysis["complexity"]),
                business_impact=BusinessImpact(business_impact["impact_level"]),
                priority_score=priority_score,
                business_value=business_impact["estimated_value"],
                urgency_level=urgency_level,
                dependencies=dependencies,
                required_skills=required_skills,
                estimated_duration=estimated_duration,
                resource_requirements=resource_requirements,
                risk_assessment=risk_assessment,
                success_criteria=success_criteria
            )

        except Exception as e:
            self.logger.error(f"Error evaluating task: {e}")
            # Return default evaluation
            return TaskEvaluation(
                task_id=task_data.get("id", "unknown"),
                title=task_data.get("title", "Unknown"),
                description=task_data.get("description", ""),
                complexity=TaskComplexity.MEDIUM,
                business_impact=BusinessImpact.MEDIUM,
                priority_score=50.0,
                business_value=0.0,
                urgency_level=TaskPriority.MEDIUM,
                dependencies=[],
                required_skills=[],
                estimated_duration=4.0,
                resource_requirements={},
                risk_assessment={"risk_level": "medium", "risks": []},
                success_criteria=[]
            )

    async def _analyze_task_complexity(
        self,
        title: str,
        description: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze task complexity using LLM and heuristics"""
        try:
            # Use LLM for sophisticated complexity analysis
            context = {
                "title": title,
                "description": description,
                "task_type": task_data.get("type", ""),
                "category": task_data.get("category", ""),
                "estimated_duration": task_data.get("expectedDuration", 0),
                "complexity": task_data.get("complexity", 5)
            }

            system_prompt = """
            You are an expert project manager and system architect analyzing task complexity.

            Analyze the provided task and determine:
            1. Complexity level (low, medium, high, critical)
            2. Key complexity factors (technical difficulty, coordination required, uncertainty)
            3. Required expertise level (junior, intermediate, senior, expert)
            4. Estimated accuracy of duration estimate (high, medium, low)
            5. Primary challenges and risks

            Consider factors like:
            - Technical complexity and innovation required
            - Number of systems/components involved
            - Coordination with other teams/agents
            - Uncertainty and ambiguity
            - Impact on other systems

            Provide specific, actionable analysis.
            """

            human_prompt = f"""
            Analyze the complexity of this task:

            Task: {title}
            Description: {description}
            Type: {task_data.get('type', 'Unknown')}
            Category: {task_data.get('category', 'Unknown')}
            Estimated Duration: {task_data.get('expectedDuration', 'Unknown')} minutes

            Provide detailed complexity analysis with specific factors and recommendations.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            response = await self.llm.ainvoke(messages)

            # Parse response to extract structured data
            complexity_level = "medium"  # default
            complexity_factors = []
            expertise_level = "intermediate"
            duration_accuracy = "medium"
            challenges = []

            response_text = response.content.lower()

            # Extract complexity level
            if "critical" in response_text or "very high" in response_text:
                complexity_level = "critical"
            elif "high" in response_text:
                complexity_level = "high"
            elif "medium" in response_text:
                complexity_level = "medium"
            elif "low" in response_text or "simple" in response_text:
                complexity_level = "low"

            # Extract key factors
            if "technical" in response_text:
                complexity_factors.append("technical_complexity")
            if "coordination" in response_text or "multiple" in response_text:
                complexity_factors.append("coordination_required")
            if "uncertainty" in response_text or "ambiguous" in response_text:
                complexity_factors.append("high_uncertainty")
            if "integration" in response_text:
                complexity_factors.append("system_integration")

            # Extract expertise level
            if "expert" in response_text or "senior" in response_text:
                expertise_level = "expert"
            elif "intermediate" in response_text:
                expertise_level = "intermediate"
            elif "junior" in response_text:
                expertise_level = "junior"

            return {
                "complexity": complexity_level,
                "factors": complexity_factors,
                "expertise_level": expertise_level,
                "duration_accuracy": duration_accuracy,
                "challenges": challenges,
                "analysis_text": response.content
            }

        except Exception as e:
            self.logger.error(f"Error analyzing task complexity: {e}")
            # Fallback to heuristic analysis
            return self._heuristic_complexity_analysis(title, description, task_data)

    def _heuristic_complexity_analysis(
        self,
        title: str,
        description: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback heuristic complexity analysis"""
        complexity_score = 0
        factors = []

        # Title length and complexity
        if len(title) > 100:
            complexity_score += 1
            factors.append("complex_scope")

        # Description analysis
        desc_words = len(description.split())
        if desc_words > 200:
            complexity_score += 2
            factors.append("detailed_requirements")
        elif desc_words > 100:
            complexity_score += 1
            factors.append("moderate_requirements")

        # Task type analysis
        task_type = task_data.get("type", "").lower()
        if "integration" in task_type or "api" in task_type:
            complexity_score += 2
            factors.append("technical_integration")
        elif "analysis" in task_type or "research" in task_type:
            complexity_score += 1
            factors.append("analysis_required")

        # Duration estimate
        duration = task_data.get("expectedDuration", 0)
        if duration > 480:  # 8 hours
            complexity_score += 2
            factors.append("long_duration")
        elif duration > 240:  # 4 hours
            complexity_score += 1
            factors.append("moderate_duration")

        # Determine complexity level
        if complexity_score >= 5:
            complexity_level = "critical"
        elif complexity_score >= 3:
            complexity_level = "high"
        elif complexity_score >= 1:
            complexity_level = "medium"
        else:
            complexity_level = "low"

        expertise_level = (
            "expert" if complexity_score >= 5 else
            "senior" if complexity_score >= 3 else
            "intermediate" if complexity_score >= 1 else
            "junior"
        )

        return {
            "complexity": complexity_level,
            "factors": factors,
            "expertise_level": expertise_level,
            "duration_accuracy": "medium",
            "challenges": [],
            "analysis_text": f"Heuristic analysis: complexity_score={complexity_score}"
        }

    async def _assess_business_impact(self, task_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Assess business impact of task"""
        try:
            impact_score = 0
            impact_factors = []
            estimated_value = 0

            # Revenue impact
            revenue_keywords = ["revenue", "sales", "pricing", "monetization", "billing"]
            if any(keyword in str(task_data).lower() for keyword in revenue_keywords):
                impact_score += 3
                impact_factors.append("revenue_impact")
                estimated_value += self.business_rules["impact_thresholds"]["revenue_impact"]

            # Customer impact
            customer_keywords = ["customer", "user", "client", "support", "experience"]
            if any(keyword in str(task_data).lower() for keyword in customer_keywords):
                impact_score += 2
                impact_factors.append("customer_impact")

            # Strategic importance
            strategic_keywords = ["strategy", "roadmap", "planning", "architecture", "vision"]
            if any(keyword in str(task_data).lower() for keyword in strategic_keywords):
                impact_score += 3
                impact_factors.append("strategic_importance")
                estimated_value += 5000

            # Time criticality
            deadline = task_data.get("deadline")
            if deadline:
                deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                hours_to_deadline = (deadline_date - datetime.now(timezone.utc)).total_seconds() / 3600

                if hours_to_deadline < self.business_rules["impact_thresholds"]["time_critical"]:
                    impact_score += 2
                    impact_factors.append("time_critical")

            # Priority level from task data
            priority = task_data.get("priority", "").lower()
            if priority in ["critical", "urgent", "highest"]:
                impact_score += 2
                impact_factors.append("high_priority")

            # Determine impact level
            if impact_score >= 6:
                impact_level = "critical"
            elif impact_score >= 4:
                impact_level = "high"
            elif impact_score >= 2:
                impact_level = "medium"
            elif impact_score >= 1:
                impact_level = "low"
            else:
                impact_level = "none"

            return {
                "impact_score": impact_score,
                "impact_level": impact_level,
                "factors": impact_factors,
                "estimated_value": estimated_value,
                "assessment_time": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error assessing business impact: {e}")
            return {
                "impact_score": 2,
                "impact_level": "medium",
                "factors": ["default_assessment"],
                "estimated_value": 1000
            }

    async def _calculate_priority_score(
        self,
        complexity_analysis: Dict[str, Any],
        business_impact: Dict[str, Any],
        task_data: Dict[str, Any]
    ) -> float:
        """Calculate overall priority score"""
        try:
            weights = self.business_rules["priority_weights"]

            # Business impact component (0-100)
            impact_level = business_impact.get("impact_level", "medium")
            impact_score_map = {
                "critical": 100,
                "high": 80,
                "medium": 60,
                "low": 40,
                "none": 20
            }
            business_impact_score = impact_score_map.get(impact_level, 60)

            # Urgency component (0-100)
            urgency_score = 50  # default
            deadline = task_data.get("deadline")
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    hours_to_deadline = (deadline_date - datetime.now(timezone.utc)).total_seconds() / 3600

                    if hours_to_deadline < 24:
                        urgency_score = 100
                    elif hours_to_deadline < 72:
                        urgency_score = 80
                    elif hours_to_deadline < 168:  # 1 week
                        urgency_score = 60
                except:
                    pass

            # Complexity component (0-100, higher complexity = lower urgency for automation)
            complexity_level = complexity_analysis.get("complexity", "medium")
            complexity_score_map = {
                "critical": 20,  # High complexity, needs careful planning
                "high": 40,
                "medium": 60,
                "low": 80
            }
            complexity_score = complexity_score_map.get(complexity_level, 60)

            # Dependencies component (0-100)
            dependencies = task_data.get("dependencies", [])
            dependency_score = max(0, 100 - (len(dependencies) * 10))

            # Calculate weighted score
            priority_score = (
                business_impact_score * weights["business_impact"] +
                urgency_score * weights["urgency"] +
                complexity_score * weights["complexity"] +
                dependency_score * weights["dependencies"]
            )

            return round(priority_score, 1)

        except Exception as e:
            self.logger.error(f"Error calculating priority score: {e}")
            return 50.0

    async def _determine_urgency_level(
        self,
        task_data: Dict[str, Any],
        business_impact: Dict[str, Any]
    ) -> TaskPriority:
        """Determine task urgency level"""
        try:
            priority_score = business_impact.get("impact_score", 2)

            # Check for explicit deadline
            deadline = task_data.get("deadline")
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    hours_to_deadline = (deadline_date - datetime.now(timezone.utc)).total_seconds() / 3600

                    if hours_to_deadline < 4:
                        return TaskPriority.CRITICAL
                    elif hours_to_deadline < 24:
                        return TaskPriority.HIGHEST
                    elif hours_to_deadline < 72:
                        return TaskPriority.HIGH
                except:
                    pass

            # Determine based on business impact
            if priority_score >= 6:
                return TaskPriority.HIGH
            elif priority_score >= 4:
                return TaskPriority.MEDIUM
            elif priority_score >= 2:
                return TaskPriority.LOW
            else:
                return TaskPriority.LOWEST

        except Exception as e:
            self.logger.error(f"Error determining urgency level: {e}")
            return TaskPriority.MEDIUM

    async def _extract_dependencies(self, task_data: Dict[str, Any]) -> List[str]:
        """Extract task dependencies"""
        try:
            dependencies = []

            # Explicit dependencies
            if "dependencies" in task_data:
                dependencies.extend(task_data["dependencies"])

            # Prerequisites
            if "prerequisites" in task_data:
                dependencies.extend(task_data["prerequisites"])

            # Extract from description using NLP
            description = task_data.get("description", "")
            dependency_patterns = [
                r"(?:requires|needs|depends on)\s+([^,.]+)",
                r"(?:after|once|when)\s+([^,.]+)",
                r"(?:blocked by|waiting for)\s+([^,.]+)"
            ]

            for pattern in dependency_patterns:
                matches = re.findall(pattern, description.lower())
                dependencies.extend(matches)

            # Clean and deduplicate
            dependencies = list(set(dep.strip() for dep in dependencies if len(dep.strip()) > 3))

            return dependencies

        except Exception as e:
            self.logger.error(f"Error extracting dependencies: {e}")
            return []

    async def _identify_required_skills(
        self,
        task_data: Dict[str, Any],
        complexity_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify required skills for task completion"""
        try:
            skills = []

            # Extract from task type and category
            task_type = task_data.get("type", "").lower()
            category = task_data.get("category", "").lower()

            # Technical skills
            if any(keyword in task_type or keyword in category for keyword in
                   ["development", "coding", "programming", "software"]):
                skills.extend(["software_development", "programming"])

            # Data analysis
            if any(keyword in task_type or keyword in category for keyword in
                   ["analysis", "data", "analytics", "research"]):
                skills.extend(["data_analysis", "research"])

            # Communication
            if any(keyword in task_type or keyword in category for keyword in
                   ["communication", "writing", "content", "documentation"]):
                skills.extend(["communication", "writing"])

            # Business skills
            if any(keyword in task_type or keyword in category for keyword in
                   ["business", "strategy", "planning", "marketing", "sales"]):
                skills.extend(["business_strategy", "market_analysis"])

            # Extract from description
            description = task_data.get("description", "").lower()

            # Language/framework specific
            tech_keywords = {
                "python": "python",
                "javascript": "javascript", "js": "javascript",
                "react": "react", "vue": "vue", "angular": "angular",
                "api": "api_development", "database": "database",
                "machine learning": "machine_learning", "ai": "artificial_intelligence",
                "docker": "docker", "kubernetes": "kubernetes"
            }

            for keyword, skill in tech_keywords.items():
                if keyword in description:
                    skills.append(skill)

            # Based on expertise level
            expertise_level = complexity_analysis.get("expertise_level", "intermediate")
            if expertise_level in ["senior", "expert"]:
                skills.append("advanced_problem_solving")

            # Remove duplicates
            skills = list(set(skills))

            return skills

        except Exception as e:
            self.logger.error(f"Error identifying required skills: {e}")
            return []

    async def _estimate_task_duration(
        self,
        complexity_analysis: Dict[str, Any],
        task_data: Dict[str, Any]
    ) -> float:
        """Estimate task duration in hours"""
        try:
            # Use provided estimate if available
            if "expectedDuration" in task_data:
                provided_minutes = task_data["expectedDuration"]
                if provided_minutes > 0:
                    return provided_minutes / 60  # Convert to hours

            # Base duration by complexity
            complexity = complexity_analysis.get("complexity", "medium")
            base_durations = {
                "low": 1,      # 1 hour
                "medium": 4,   # 4 hours
                "high": 12,    # 12 hours
                "critical": 24  # 24 hours
            }

            base_duration = base_durations.get(complexity, 4)

            # Adjust based on factors
            factors = complexity_analysis.get("factors", [])

            # Technical complexity multiplier
            if "technical_complexity" in factors:
                base_duration *= 1.5

            # Coordination required
            if "coordination_required" in factors:
                base_duration *= 1.3

            # High uncertainty
            if "high_uncertainty" in factors:
                base_duration *= 1.4

            # System integration
            if "system_integration" in factors:
                base_duration *= 1.6

            # Check for explicit time requirements in description
            description = task_data.get("description", "").lower()
            time_patterns = [
                r"(\d+)\s*hours?",
                r"(\d+)\s*days?",
                r"(\d+)\s*weeks?"
            ]

            for pattern in time_patterns:
                match = re.search(pattern, description)
                if match:
                    value = int(match.group(1))
                    if "hour" in pattern:
                        base_duration = max(base_duration, value)
                    elif "day" in pattern:
                        base_duration = max(base_duration, value * 8)
                    elif "week" in pattern:
                        base_duration = max(base_duration, value * 40)

            return round(base_duration, 1)

        except Exception as e:
            self.logger.error(f"Error estimating task duration: {e}")
            return 4.0

    async def _assess_resource_requirements(
        self,
        task_data: Dict[str, Any],
        complexity_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess resource requirements for task"""
        try:
            requirements = {
                "computational_resources": "low",
                "memory_requirements": "low",
                "network_bandwidth": "low",
                "storage_requirements": "low",
                "external_apis": [],
                "specialized_tools": [],
                "human_intervention": False
            }

            # Analyze description for resource hints
            description = task_data.get("description", "").lower()

            # Computational requirements
            if any(keyword in description for keyword in
                   ["machine learning", "ai", "model training", "computationally intensive"]):
                requirements["computational_resources"] = "high"
            elif any(keyword in description for keyword in
                     ["processing", "analysis", "calculation"]):
                requirements["computational_resources"] = "medium"

            # Memory requirements
            if any(keyword in description for keyword in
                   ["large dataset", "big data", "memory intensive"]):
                requirements["memory_requirements"] = "high"
            elif any(keyword in description for keyword in
                     ["data processing", "analysis"]):
                requirements["memory_requirements"] = "medium"

            # External APIs
            api_patterns = [
                r"(\w+)\s+api",
                r"integrate\s+with\s+(\w+)",
                r"connect\s+to\s+(\w+)"
            ]

            for pattern in api_patterns:
                matches = re.findall(pattern, description)
                requirements["external_apis"].extend(matches)

            # Specialized tools
            tools_keywords = {
                "docker": "docker",
                "kubernetes": "kubernetes",
                "aws": "aws",
                "azure": "azure",
                "gcp": "gcp",
                "database": "database_management",
                "git": "git",
                "ci/cd": "cicd_pipeline"
            }

            for keyword, tool in tools_keywords.items():
                if keyword in description:
                    requirements["specialized_tools"].append(tool)

            # Human intervention
            if any(keyword in description for keyword in
                   ["manual", "human", "approval", "review", "decision"]):
                requirements["human_intervention"] = True

            # Remove duplicates
            requirements["external_apis"] = list(set(requirements["external_apis"]))
            requirements["specialized_tools"] = list(set(requirements["specialized_tools"]))

            return requirements

        except Exception as e:
            self.logger.error(f"Error assessing resource requirements: {e}")
            return {"error": str(e)}

    async def _conduct_risk_assessment(
        self,
        task_data: Dict[str, Any],
        business_impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Conduct risk assessment for task"""
        try:
            risk_assessment = {
                "risk_level": "medium",
                "risk_score": 5,  # 1-10 scale
                "risks": [],
                "mitigation_strategies": [],
                "contingency_plans": []
            }

            # Base risk from business impact
            impact_score = business_impact.get("impact_score", 2)
            if impact_score >= 6:
                risk_assessment["risk_level"] = "high"
                risk_assessment["risk_score"] = 8
            elif impact_score >= 4:
                risk_assessment["risk_level"] = "medium"
                risk_assessment["risk_score"] = 6
            elif impact_score >= 2:
                risk_assessment["risk_level"] = "low"
                risk_assessment["risk_score"] = 4

            # Analyze task description for risk indicators
            description = task_data.get("description", "").lower()

            # Technical risks
            if any(keyword in description for keyword in
                   ["experimental", "prototype", "new", "untested", "beta"]):
                risk_assessment["risks"].append("technical_uncertainty")
                risk_assessment["risk_score"] = min(10, risk_assessment["risk_score"] + 1)

            # Integration risks
            if any(keyword in description for keyword in
                   ["integration", "api", "external system"]):
                risk_assessment["risks"].append("integration_complexity")
                risk_assessment["risk_score"] = min(10, risk_assessment["risk_score"] + 1)

            # Timeline risks
            if "tight deadline" in description or "urgent" in description:
                risk_assessment["risks"].append("timeline_pressure")
                risk_assessment["risk_score"] = min(10, risk_assessment["risk_score"] + 1)

            # Dependency risks
            if len(task_data.get("dependencies", [])) > 3:
                risk_assessment["risks"].append("dependency_chain_complexity")
                risk_assessment["risk_score"] = min(10, risk_assessment["risk_score"] + 1)

            # Generate mitigation strategies
            if "technical_uncertainty" in risk_assessment["risks"]:
                risk_assessment["mitigation_strategies"].append("conduct technical proof of concept")
                risk_assessment["mitigation_strategies"].append("consult technical experts")

            if "integration_complexity" in risk_assessment["risks"]:
                risk_assessment["mitigation_strategies"].append("early integration testing")
                risk_assessment["mitigation_strategies"].append("fallback integration plan")

            if "timeline_pressure" in risk_assessment["risks"]:
                risk_assessment["mitigation_strategies"].append("parallel task execution")
                risk_assessment["mitigation_strategies"].append("resource allocation increase")

            # Generate contingency plans
            if risk_assessment["risk_score"] >= 7:
                risk_assessment["contingency_plans"].append("alternative approach preparation")
                risk_assessment["contingency_plans"].append("additional resource allocation")

            return risk_assessment

        except Exception as e:
            self.logger.error(f"Error conducting risk assessment: {e}")
            return {"risk_level": "unknown", "error": str(e)}

    async def _define_success_criteria(
        self,
        task_data: Dict[str, Any],
        business_impact: Dict[str, Any]
    ) -> List[str]:
        """Define success criteria for task"""
        try:
            criteria = []

            # Basic completion criteria
            criteria.append("Task completed according to specifications")
            criteria.append("Quality standards met or exceeded")

            # Business impact criteria
            impact_factors = business_impact.get("factors", [])

            if "revenue_impact" in impact_factors:
                criteria.append("Revenue targets achieved or exceeded")

            if "customer_impact" in impact_factors:
                criteria.append("Customer satisfaction improvements realized")

            if "strategic_importance" in impact_factors:
                criteria.append("Strategic objectives advanced")

            # Quality criteria
            criteria.append("No critical defects or issues")
            criteria.append("Performance requirements met")

            # Timeline criteria
            deadline = task_data.get("deadline")
            if deadline:
                criteria.append("Completed within deadline requirements")

            # Extract from description
            description = task_data.get("description", "").lower()

            # Look for explicit success criteria
            success_patterns = [
                r"(?:success|successful|achieve|accomplish)\s+(?:when|if|once)\s+([^,.]+)",
                r"(?:goal|objective|target)\s+(?:is|are)\s+([^,.]+)",
                r"(?:deliverable|output|result)\s+(?:should|must)\s+([^,.]+)"
            ]

            for pattern in success_patterns:
                matches = re.findall(pattern, description)
                for match in matches:
                    criteria.append(f"Achieve: {match.strip()}")

            # Remove duplicates and limit
            criteria = list(set(criteria))

            return criteria[:6]  # Top 6 criteria

        except Exception as e:
            self.logger.error(f"Error defining success criteria: {e}")
            return ["Task completed successfully"]

    async def _get_agent_capabilities(self) -> List[AgentCapability]:
        """Get current capabilities of all agents"""
        try:
            # Check cache first
            cache_key = "agent_capabilities"
            if (cache_key in self._agent_capabilities_cache and
                cache_key in self._cache_timestamp and
                (datetime.now() - self._cache_timestamp[cache_key]).seconds < self._cache_ttl):
                return self._agent_capabilities_cache[cache_key]

            # Get agent orchestrator status
            orchestrator_status = await self.agent_orchestrator.get_status()

            capabilities = []

            # Process each agent
            for agent_data in orchestrator_status.get("agents", []):
                capability = AgentCapability(
                    agent_id=agent_data.get("agent_id", ""),
                    agent_type=AgentType(agent_data.get("type", "general")),
                    current_load=agent_data.get("load", 0.0),
                    max_capacity=agent_data.get("max_tasks", 5),
                    specialties=agent_data.get("capabilities", []),
                    performance_score=agent_data.get("performance", 0.8),
                    success_rate=agent_data.get("success_rate", 0.9),
                    average_completion_time=agent_data.get("avg_completion_time", 4.0),
                    availability=agent_data.get("available", True),
                    cost_per_hour=agent_data.get("cost_per_hour", 50.0),
                    skills_match=0.0  # Will be calculated per task
                )
                capabilities.append(capability)

            # Cache the results
            self._agent_capabilities_cache[cache_key] = capabilities
            self._cache_timestamp[cache_key] = datetime.now()

            return capabilities

        except Exception as e:
            self.logger.error(f"Error getting agent capabilities: {e}")
            return []

    async def _apply_business_rules(self, task_evaluation: TaskEvaluation) -> TaskEvaluation:
        """Apply business rules to adjust task evaluation"""
        try:
            # Adjust priority based on business impact
            if task_evaluation.business_impact == BusinessImpact.CRITICAL:
                task_evaluation.priority_score = min(100, task_evaluation.priority_score + 20)
                task_evaluation.urgency_level = TaskPriority.CRITICAL
            elif task_evaluation.business_impact == BusinessImpact.HIGH:
                task_evaluation.priority_score = min(100, task_evaluation.priority_score + 10)

            # Adjust for dependencies
            if len(task_evaluation.dependencies) > 3:
                task_evaluation.complexity = TaskComplexity.HIGH
                task_evaluation.priority_score = max(0, task_evaluation.priority_score - 10)

            # Adjust for resource requirements
            if task_evaluation.resource_requirements.get("human_intervention", False):
                task_evaluation.priority_score = max(0, task_evaluation.priority_score - 5)
                task_evaluation.estimated_duration *= 1.2

            # Risk adjustment
            risk_score = task_evaluation.risk_assessment.get("risk_score", 5)
            if risk_score >= 8:
                task_evaluation.complexity = TaskComplexity.CRITICAL
                task_evaluation.estimated_duration *= 1.5

            return task_evaluation

        except Exception as e:
            self.logger.error(f"Error applying business rules: {e}")
            return task_evaluation

    async def _make_delegation_decision(
        self,
        task_evaluation: TaskEvaluation,
        agent_capabilities: List[AgentCapability]
    ) -> DelegationDecision:
        """Make intelligent delegation decision"""
        try:
            # Calculate skills match for each agent
            for capability in agent_capabilities:
                capability.skills_match = self._calculate_skills_match(
                    task_evaluation.required_skills, capability.specialties
                )

            # Filter available agents
            available_agents = [
                cap for cap in agent_capabilities
                if cap.availability and cap.current_load < 0.9
            ]

            if not available_agents:
                raise Exception("No available agents for delegation")

            # Rank agents based on multiple factors
            ranked_agents = await self._rank_agents_for_task(task_evaluation, available_agents)

            # Select best agent
            best_agent = ranked_agents[0]

            # Calculate confidence score
            confidence_score = self._calculate_delegation_confidence(
                task_evaluation, best_agent
            )

            # Generate reasoning
            reasoning = self._generate_delegation_reasoning(
                task_evaluation, best_agent, ranked_agents
            )

            # Get alternative agents
            alternative_agents = [
                {
                    "agent_id": agent.agent_id,
                    "agent_type": agent.agent_type.value,
                    "confidence": self._calculate_delegation_confidence(task_evaluation, agent),
                    "reasoning": f"Skills match: {agent.skills_match:.2f}, Load: {agent.current_load:.2f}"
                }
                for agent in ranked_agents[1:3]  # Top 2 alternatives
            ]

            # Estimate completion time and cost
            expected_completion = task_evaluation.estimated_duration * (1 + best_agent.current_load)
            estimated_cost = expected_completion * best_agent.cost_per_hour

            # Identify risk factors
            risk_factors = self._identify_delegation_risks(task_evaluation, best_agent)

            # Generate mitigation strategies
            mitigation_strategies = self._generate_mitigation_strategies(risk_factors)

            # Determine delegation strategy
            delegation_strategy = self._determine_delegation_strategy(
                task_evaluation, best_agent, ranked_agents
            )

            return DelegationDecision(
                task_id=task_evaluation.task_id,
                recommended_agent=best_agent.agent_id,
                confidence_score=confidence_score,
                reasoning=reasoning,
                alternative_agents=alternative_agents,
                expected_completion_time=expected_completion,
                estimated_cost=estimated_cost,
                risk_factors=risk_factors,
                mitigation_strategies=mitigation_strategies,
                delegation_strategy=delegation_strategy,
                created_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            self.logger.error(f"Error making delegation decision: {e}")
            raise

    def _calculate_skills_match(self, required_skills: List[str], agent_skills: List[str]) -> float:
        """Calculate skills match score between required skills and agent capabilities"""
        try:
            if not required_skills:
                return 0.8  # No specific skills required

            if not agent_skills:
                return 0.3  # Agent has no specific skills

            # Calculate overlap
            required_lower = [skill.lower() for skill in required_skills]
            agent_lower = [skill.lower() for skill in agent_skills]

            matches = sum(1 for skill in required_lower if skill in agent_lower)

            # Partial matches for similar skills
            partial_matches = 0
            for req_skill in required_lower:
                for agent_skill in agent_lower:
                    if req_skill in agent_skill or agent_skill in req_skill:
                        partial_matches += 0.5
                        break

            total_matches = matches + partial_matches
            match_score = min(1.0, total_matches / len(required_skills))

            return match_score

        except Exception as e:
            self.logger.error(f"Error calculating skills match: {e}")
            return 0.5

    async def _rank_agents_for_task(
        self,
        task_evaluation: TaskEvaluation,
        agent_capabilities: List[AgentCapability]
    ) -> List[AgentCapability]:
        """Rank agents for specific task based on multiple factors"""
        try:
            ranked_agents = []

            for capability in agent_capabilities:
                # Calculate composite score
                score = 0.0

                # Skills match (40% weight)
                score += capability.skills_match * 0.4

                # Performance score (20% weight)
                score += capability.performance_score * 0.2

                # Availability/Load (20% weight)
                load_score = 1.0 - capability.current_load
                score += load_score * 0.2

                # Success rate (10% weight)
                score += capability.success_rate * 0.1

                # Cost efficiency (10% weight) - lower cost is better
                max_cost = max(cap.cost_per_hour for cap in agent_capabilities)
                cost_efficiency = 1.0 - (capability.cost_per_hour / max_cost)
                score += cost_efficiency * 0.1

                # Adjust for expertise level match
                expertise_requirement = {
                    TaskComplexity.LOW: 1,
                    TaskComplexity.MEDIUM: 2,
                    TaskComplexity.HIGH: 3,
                    TaskComplexity.CRITICAL: 4
                }

                required_expertise = expertise_requirement.get(task_evaluation.complexity, 2)

                # Simple expertise scoring based on performance and success rate
                agent_expertise = (capability.performance_score + capability.success_rate) / 2 * 4

                if agent_expertise >= required_expertise:
                    score += 0.2  # Bonus for meeting expertise requirement
                else:
                    score -= 0.3  # Penalty for not meeting expertise requirement

                # Store the score
                capability.delegation_score = score
                ranked_agents.append(capability)

            # Sort by score (highest first)
            ranked_agents.sort(key=lambda x: x.delegation_score, reverse=True)

            return ranked_agents

        except Exception as e:
            self.logger.error(f"Error ranking agents: {e}")
            return agent_capabilities

    def _calculate_delegation_confidence(
        self,
        task_evaluation: TaskEvaluation,
        agent_capability: AgentCapability
    ) -> float:
        """Calculate confidence score for delegation decision"""
        try:
            confidence = 0.5  # Base confidence

            # Skills match
            confidence += agent_capability.skills_match * 0.3

            # Agent performance
            confidence += agent_capability.performance_score * 0.2

            # Success rate
            confidence += (agent_capability.success_rate - 0.5) * 0.2

            # Task complexity vs agent expertise
            if task_evaluation.complexity in [TaskComplexity.LOW, TaskComplexity.MEDIUM]:
                confidence += 0.1
            elif task_evaluation.complexity == TaskComplexity.CRITICAL:
                confidence -= 0.1

            # Risk adjustment
            risk_score = task_evaluation.risk_assessment.get("risk_score", 5)
            risk_adjustment = (10 - risk_score) / 20  # 0 to 0.25
            confidence += risk_adjustment

            return min(1.0, max(0.0, confidence))

        except Exception as e:
            self.logger.error(f"Error calculating delegation confidence: {e}")
            return 0.5

    def _generate_delegation_reasoning(
        self,
        task_evaluation: TaskEvaluation,
        best_agent: AgentCapability,
        ranked_agents: List[AgentCapability]
    ) -> str:
        """Generate reasoning for delegation decision"""
        try:
            reasoning_parts = []

            # Skills match reasoning
            if best_agent.skills_match > 0.7:
                reasoning_parts.append(f"Excellent skills match ({best_agent.skills_match:.1%})")
            elif best_agent.skills_match > 0.5:
                reasoning_parts.append(f"Good skills match ({best_agent.skills_match:.1%})")
            else:
                reasoning_parts.append(f"Moderate skills match ({best_agent.skills_match:.1%})")

            # Performance reasoning
            if best_agent.performance_score > 0.8:
                reasoning_parts.append("Strong historical performance")
            elif best_agent.performance_score > 0.6:
                reasoning_parts.append("Good performance record")

            # Availability reasoning
            if best_agent.current_load < 0.3:
                reasoning_parts.append("High availability")
            elif best_agent.current_load < 0.7:
                reasoning_parts.append("Moderate availability")
            else:
                reasoning_parts.append("Limited availability but best fit")

            # Complexity match
            if task_evaluation.complexity == TaskComplexity.HIGH and best_agent.performance_score > 0.7:
                reasoning_parts.append("Suitable for complex tasks")

            # Ranking advantage
            if len(ranked_agents) > 1:
                second_best = ranked_agents[1]
                score_diff = best_agent.delegation_score - second_best.delegation_score
                if score_diff > 0.2:
                    reasoning_parts.append(f"Significantly better than next best agent")

            return "; ".join(reasoning_parts)

        except Exception as e:
            self.logger.error(f"Error generating delegation reasoning: {e}")
            return "Best available agent based on overall fit assessment"

    def _identify_delegation_risks(
        self,
        task_evaluation: TaskEvaluation,
        agent_capability: AgentCapability
    ) -> List[str]:
        """Identify potential risks for delegation"""
        try:
            risks = []

            # Low skills match
            if agent_capability.skills_match < 0.5:
                risks.append("Insufficient skills match for task requirements")

            # High agent load
            if agent_capability.current_load > 0.8:
                risks.append("Agent operating near maximum capacity")

            # Low success rate
            if agent_capability.success_rate < 0.8:
                risks.append("Below-average success rate for similar tasks")

            # High task complexity
            if task_evaluation.complexity == TaskComplexity.CRITICAL:
                risks.append("Critical complexity requires careful monitoring")

            # Task dependencies
            if len(task_evaluation.dependencies) > 3:
                risks.append("Multiple dependencies may delay completion")

            # Human intervention required
            if task_evaluation.resource_requirements.get("human_intervention", False):
                risks.append("Requires human intervention may cause delays")

            # Integration complexity
            if "system_integration" in task_evaluation.risk_assessment.get("risks", []):
                risks.append("Complex integration requirements")

            return risks

        except Exception as e:
            self.logger.error(f"Error identifying delegation risks: {e}")
            return ["Unable to fully assess delegation risks"]

    def _generate_mitigation_strategies(self, risks: List[str]) -> List[str]:
        """Generate mitigation strategies for identified risks"""
        try:
            strategies = []

            for risk in risks:
                if "skills" in risk.lower():
                    strategies.append("Provide additional training or resources")
                    strategies.append("Monitor progress closely and offer support")

                elif "capacity" in risk.lower():
                    strategies.append("Set clear expectations for timeline")
                    strategies.append("Prepare backup resources if needed")

                elif "success rate" in risk.lower():
                    strategies.append("Implement frequent progress check-ins")
                    strategies.append("Prepare alternative approaches")

                elif "complexity" in risk.lower():
                    strategies.append("Break down into smaller sub-tasks")
                    strategies.append("Allocate additional review time")

                elif "dependencies" in risk.lower():
                    strategies.append("Proactively manage dependencies")
                    strategies.append("Regular status updates with dependent teams")

                elif "human" in risk.lower():
                    strategies.append("Schedule human resources in advance")
                    strategies.append("Build buffer time for reviews")

            # Remove duplicates
            strategies = list(set(strategies))

            return strategies[:4]  # Top 4 strategies

        except Exception as e:
            self.logger.error(f"Error generating mitigation strategies: {e}")
            return ["Monitor task progress closely"]

    def _determine_delegation_strategy(
        self,
        task_evaluation: TaskEvaluation,
        best_agent: AgentCapability,
        ranked_agents: List[AgentCapability]
    ) -> DelegationStrategy:
        """Determine optimal delegation strategy"""
        try:
            # High complexity, high business impact -> Specialized
            if (task_evaluation.complexity in [TaskComplexity.HIGH, TaskComplexity.CRITICAL] and
                task_evaluation.business_impact in [BusinessImpact.HIGH, BusinessImpact.CRITICAL]):
                return DelegationStrategy.SPECIALIZED

            # Low load across agents -> Least loaded
            avg_load = sum(cap.current_load for cap in ranked_agents) / len(ranked_agents)
            if avg_load < 0.5:
                return DelegationStrategy.LEAST_LOADED

            # Good skills match with multiple agents -> Best fit
            if (len([cap for cap in ranked_agents if cap.skills_match > 0.7]) >= 2 and
                best_agent.skills_match > 0.8):
                return DelegationStrategy.BEST_FIT

            # Balanced approach -> Hybrid
            return DelegationStrategy.HYBRID

        except Exception as e:
            self.logger.error(f"Error determining delegation strategy: {e}")
            return DelegationStrategy.HYBRID

    async def _validate_delegation_decision(
        self,
        delegation_decision: DelegationDecision,
        task_evaluation: TaskEvaluation
    ) -> DelegationDecision:
        """Validate delegation decision and check for escalation needs"""
        try:
            # Check if confidence is too low
            if delegation_decision.confidence_score < 0.5:
                self.logger.warning(
                    f"Low confidence delegation decision: {delegation_decision.confidence_score:.2f}"
                )
                # Add recommendation for human review
                delegation_decision.risk_factors.append("Low confidence - requires human review")

            # Check for escalation criteria
            escalation_needs = await self._check_escalation_criteria(
                delegation_decision, task_evaluation
            )

            if escalation_needs:
                escalation = await self._create_task_escalation(
                    delegation_decision, task_evaluation, escalation_needs
                )
                # Store escalation for tracking
                await self._store_task_escalation(escalation)

            # Adjust confidence based on validation
            if delegation_decision.confidence_score < 0.7:
                delegation_decision.mitigation_strategies.append(
                    "Schedule human review and approval"
                )

            return delegation_decision

        except Exception as e:
            self.logger.error(f"Error validating delegation decision: {e}")
            return delegation_decision

    async def _check_escalation_criteria(
        self,
        delegation_decision: DelegationDecision,
        task_evaluation: TaskEvaluation
    ) -> List[str]:
        """Check if task escalation is needed"""
        try:
            escalation_criteria = []

            # High business impact with low confidence
            if (task_evaluation.business_impact in [BusinessImpact.HIGH, BusinessImpact.CRITICAL] and
                delegation_decision.confidence_score < 0.7):
                escalation_criteria.append("High impact, low confidence")

            # Critical complexity with insufficient skills match
            if (task_evaluation.complexity == TaskComplexity.CRITICAL and
                delegation_decision.risk_factors):
                for risk in delegation_decision.risk_factors:
                    if "skills" in risk.lower():
                        escalation_criteria.append("Critical complexity, insufficient skills")
                        break

            # High risk score
            risk_score = task_evaluation.risk_assessment.get("risk_score", 0)
            if risk_score >= 8:
                escalation_criteria.append("High task risk score")

            # Estimated cost is very high
            if delegation_decision.estimated_cost > 5000:  # $5000 threshold
                escalation_criteria.append("High estimated cost")

            # Multiple critical risk factors
            critical_risks = [
                risk for risk in delegation_decision.risk_factors
                if any(keyword in risk.lower() for keyword in ["critical", "high", "severe"])
            ]
            if len(critical_risks) >= 2:
                escalation_criteria.append("Multiple critical risk factors")

            return escalation_criteria

        except Exception as e:
            self.logger.error(f"Error checking escalation criteria: {e}")
            return []

    async def _create_task_escalation(
        self,
        delegation_decision: DelegationDecision,
        task_evaluation: TaskEvaluation,
        escalation_reasons: List[str]
    ) -> TaskEscalation:
        """Create task escalation record"""
        try:
            escalation = TaskEscalation(
                escalation_id=f"escalation_{uuid.uuid4().hex[:8]}",
                task_id=task_evaluation.task_id,
                original_agent=delegation_decision.recommended_agent,
                escalation_reason="; ".join(escalation_reasons),
                escalation_level="level_1",  # Default escalation level
                escalation_criteria=escalation_reasons,
                notified_stakeholders=["task_manager", "operations_team"],
                escalation_time=datetime.now(timezone.utc),
                resolution_status="pending",
                resolution_time=None
            )

            return escalation

        except Exception as e:
            self.logger.error(f"Error creating task escalation: {e}")
            raise

    async def _execute_delegation(self, delegation_decision: DelegationDecision, user_id: str):
        """Execute the task delegation"""
        try:
            # Create task delegation object
            task_delegation = TaskDelegation(
                id=delegation_decision.task_id,
                type="delegated_task",
                category=TaskType.GENERAL,  # Would be determined from task analysis
                priority=delegation_decision.risk_factors,  # Convert to priority enum
                title=f"Delegated Task {delegation_decision.task_id}",
                description=f"Task delegated to agent {delegation_decision.recommended_agent}",
                parameters={
                    "delegation_reasoning": delegation_decision.reasoning,
                    "mitigation_strategies": delegation_decision.mitigation_strategies,
                    "confidence_score": delegation_decision.confidence_score
                },
                expectedDuration=int(delegation_decision.expected_completion_time * 60),  # Convert to minutes
                complexity=5,  # Default complexity
                resourceRequirements=delegation_decision.risk_factors,
                assignedTo=delegation_decision.recommended_agent,
                status=TaskStatus.PENDING,
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
                metadata={
                    "delegation_strategy": delegation_decision.delegation_strategy.value,
                    "estimated_cost": delegation_decision.estimated_cost,
                    "alternative_agents": delegation_decision.alternative_agents
                }
            )

            # Submit task through agent orchestrator
            await self.agent_orchestrator.delegate_task(task_delegation, user_id)

            self.logger.info(
                f"Successfully delegated task {delegation_decision.task_id} to agent {delegation_decision.recommended_agent}"
            )

        except Exception as e:
            self.logger.error(f"Error executing delegation: {e}")
            raise

    async def _store_delegation_decision(self, decision: DelegationDecision, user_id: str):
        """Store delegation decision for analytics"""
        try:
            decision_data = asdict(decision)

            # Convert datetime objects to ISO format
            decision_data["created_at"] = decision.created_at.isoformat()

            await self.firebase_service.store_agent_file(
                f"task_delegation/{user_id}/{decision.task_id}",
                json.dumps(decision_data, indent=2, default=str)
            )

            self.logger.info(f"Stored delegation decision for task {decision.task_id}")

        except Exception as e:
            self.logger.error(f"Error storing delegation decision: {e}")

    async def _store_task_escalation(self, escalation: TaskEscalation):
        """Store task escalation record"""
        try:
            escalation_data = asdict(escalation)

            # Convert datetime objects
            escalation_data["escalation_time"] = escalation.escalation_time.isoformat()
            if escalation.resolution_time:
                escalation_data["resolution_time"] = escalation.resolution_time.isoformat()

            await self.firebase_service.store_agent_file(
                f"task_escalations/{escalation.task_id}/{escalation.escalation_id}",
                json.dumps(escalation_data, indent=2, default=str)
            )

            self.logger.info(f"Stored task escalation {escalation.escalation_id}")

        except Exception as e:
            self.logger.error(f"Error storing task escalation: {e}")

    async def get_delegation_analytics(
        self,
        user_id: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get delegation analytics and insights"""
        try:
            # Get delegation history
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)

            # Analytics calculations
            analytics = {
                "total_delegations": 0,
                "successful_delegations": 0,
                "average_confidence": 0.0,
                "most_used_agent": None,
                "average_completion_time": 0.0,
                "escalation_rate": 0.0,
                "cost_savings": 0.0,
                "efficiency_improvements": []
            }

            return analytics

        except Exception as e:
            self.logger.error(f"Error getting delegation analytics: {e}")
            return {"error": str(e)}