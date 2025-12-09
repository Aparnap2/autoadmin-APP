"""
DevOps Agent - CTO agent for technical implementation and system operations
Handles system architecture, deployment, monitoring, and technical strategy
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class DevOpsAgent:
    """DevOps Agent combining CTO responsibilities"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "DevOps Agent (CTO)"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.get("model", "gpt-4"),
            temperature=config.get("temperature", 0.1),
            max_tokens=config.get("max_tokens", 2000),
            api_key=config.get("openai_api_key"),
        )

        # DevOps agent persona
        self.system_prompt = """
        You are the DevOps Agent for AutoAdmin, combining the expertise of a CTO and DevOps Engineer.

        Your core responsibilities:

        AS CTO (Chief Technology Officer):
        1. Technical architecture design and oversight
        2. Technology stack decisions and roadmap
        3. System scalability and performance optimization
        4. Technical risk assessment and mitigation
        5. Innovation and technology trends evaluation

        AS DEVOPS ENGINEER:
        1. CI/CD pipeline design and implementation
        2. Infrastructure as code (IaC) development
        3. System monitoring and observability
        4. Security implementation and compliance
        5. Automation and operational efficiency

        Technical expertise areas:
        - Cloud platforms (AWS, GCP, Azure)
        - Containerization (Docker, Kubernetes)
        - Infrastructure as Code (Terraform, CloudFormation)
        - CI/CD tools (Jenkins, GitHub Actions, GitLab CI)
        - Monitoring (Prometheus, Grafana, ELK stack)
        - Security (OWASP, SOC2, ISO27001 compliance)

        Your approach:
        - Prioritize scalability, reliability, and security
        - Use modern best practices and standards
        - Consider total cost of ownership (TCO)
        - Plan for maintainability and future growth
        - Focus on automation and operational excellence

        Always respond with:
        1. Technical analysis and architecture recommendations
        2. Implementation plan with specific technologies
        3. Security and compliance considerations
        4. Performance and scalability projections
        5. Operational requirements and monitoring strategy
        """

        # Technical templates and patterns
        self.architecture_patterns = {
            "microservices": {
                "description": "Microservices architecture with container orchestration",
                "technologies": ["Docker", "Kubernetes", "Istio", "gRPC"],
                "pros": ["Scalability", "Fault tolerance", "Independent deployment"],
                "cons": ["Complexity", "Network overhead", "Operational overhead"]
            },
            "serverless": {
                "description": "Serverless architecture with function-as-a-service",
                "technologies": ["AWS Lambda", "Azure Functions", "API Gateway"],
                "pros": ["Cost efficiency", "Auto-scaling", "No server management"],
                "cons": ["Cold starts", "Vendor lock-in", "Execution limits"]
            },
            "monolith": {
                "description": "Monolithic application architecture",
                "technologies": ["Node.js", "Python", "Java", "Load balancers"],
                "pros": ["Simplicity", "Performance", "Easier debugging"],
                "cons": ["Scalability limits", "Deployment complexity", "Technology constraints"]
            }
        }

        self.logger.info("DevOps Agent initialized")

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a DevOps/technical task"""
        try:
            messages = task_input.get("messages", [])
            ceo_guidance = task_input.get("ceo_guidance", {})
            task_analysis = task_input.get("task_analysis", {})

            # Determine task type
            task_type = self._classify_devops_task(messages)

            # Gather technical requirements
            tech_requirements = self._extract_technical_requirements(messages, task_type)

            # Build DevOps prompt
            prompt = self._build_devops_prompt(messages, ceo_guidance, task_analysis, tech_requirements)

            # Get DevOps response
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            # Parse and structure the response
            devops_result = self._parse_devops_response(response.content, task_type)

            # Generate implementation details
            implementation_plan = await self._generate_implementation_plan(devops_result, task_type)

            return {
                "agent": "devops",
                "task_type": task_type,
                "analysis": devops_result,
                "implementation_plan": implementation_plan,
                "technical_requirements": tech_requirements,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error processing DevOps task: {e}")
            return {
                "agent": "devops",
                "error": str(e),
                "task_type": "unknown",
                "analysis": {},
            }

    def _classify_devops_task(self, messages: List) -> str:
        """Classify the type of DevOps task"""
        if not messages:
            return "general_technical"

        content = messages[-1].content.lower()

        # Architecture-related keywords
        architecture_keywords = [
            "architecture", "design", "system", "scalability", "infrastructure",
            "cloud", "deployment", "microservices", "serverless"
        ]

        # Security-related keywords
        security_keywords = [
            "security", "auth", "encryption", "compliance", "audit",
            "vulnerability", "firewall", "access control"
        ]

        # Performance-related keywords
        performance_keywords = [
            "performance", "optimization", "monitoring", "metrics",
            "logging", "observability", "latency", "throughput"
        ]

        # CI/CD related keywords
        cicd_keywords = [
            "deploy", "pipeline", "cicd", "automation", "testing",
            "build", "release", "continuous"
        ]

        architecture_score = sum(1 for keyword in architecture_keywords if keyword in content)
        security_score = sum(1 for keyword in security_keywords if keyword in content)
        performance_score = sum(1 for keyword in performance_keywords if keyword in content)
        cicd_score = sum(1 for keyword in cicd_keywords if keyword in content)

        scores = {
            "architecture": architecture_score,
            "security": security_score,
            "performance": performance_score,
            "cicd": cicd_score
        }

        # Return the highest scoring category
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "general_technical"

    def _extract_technical_requirements(self, messages: List, task_type: str) -> Dict[str, Any]:
        """Extract technical requirements from the task"""
        requirements = {
            "scalability": "medium",
            "availability": "high",
            "security_level": "standard",
            "budget_constraints": "medium",
            "timeline": "standard",
            "team_size": "small",
            "existing_stack": [],
            "integration_requirements": [],
        }

        if not messages:
            return requirements

        content = messages[-1].content.lower()

        # Extract requirements based on keywords
        if any(word in content for word in ["highly scalable", "massive scale", "millions of users"]):
            requirements["scalability"] = "high"

        if any(word in content for word in ["99.9%", "high availability", "zero downtime"]):
            requirements["availability"] = "critical"

        if any(word in content for word in ["hipaa", "sox", "pci", "gdpr", "compliance"]):
            requirements["security_level"] = "enterprise"

        if any(word in content for word in ["budget", "cost-effective", "cheap", "affordable"]):
            requirements["budget_constraints"] = "tight"

        if any(word in content for word in ["urgent", "asap", "immediately", "quick"]):
            requirements["timeline"] = "aggressive"

        return requirements

    def _build_devops_prompt(self, messages: List, ceo_guidance: Dict, task_analysis: Dict, requirements: Dict) -> str:
        """Build the DevOps analysis prompt"""
        latest_message = messages[-1].content if messages else ""

        prompt = f"""
        TECHNICAL ANALYSIS AND IMPLEMENTATION PLAN

        Task: {latest_message}

        CEO Guidance: {ceo_guidance.get('full_response', 'No specific guidance provided')}

        Task Analysis: {task_analysis}

        Technical Requirements:
        - Scalability: {requirements['scalability']}
        - Availability: {requirements['availability']}
        - Security Level: {requirements['security_level']}
        - Budget Constraints: {requirements['budget_constraints']}
        - Timeline: {requirements['timeline']}
        - Team Size: {requirements['team_size']}

        As DevOps Agent (CTO), please provide:

        1. TECHNICAL ARCHITECTURE:
           - Recommended architecture pattern
           - Technology stack recommendations
           - System design and components
           - Data flow and integration points

        2. IMPLEMENTATION PLAN:
           - Development phases and milestones
           - CI/CD pipeline design
           - Infrastructure provisioning
           - Testing strategy and automation

        3. SECURITY & COMPLIANCE:
           - Security measures and best practices
           - Compliance requirements
           - Access control and authentication
           - Data protection and encryption

        4. PERFORMANCE & MONITORING:
           - Performance optimization strategies
           - Monitoring and alerting setup
           - Logging and observability
           - Capacity planning and scaling

        5. OPERATIONAL REQUIREMENTS:
           - Team skills and training needs
           - Documentation and knowledge transfer
           - Maintenance and support procedures
           - Cost analysis and optimization

        Please provide specific, actionable recommendations with technology choices and implementation details.
        """

        return prompt

    def _parse_devops_response(self, response_content: str, task_type: str) -> Dict[str, Any]:
        """Parse and structure the DevOps response"""
        analysis = {
            "architecture_recommendations": {},
            "technology_stack": [],
            "implementation_phases": [],
            "security_measures": [],
            "monitoring_strategy": {},
            "cost_analysis": {},
            "risk_assessment": [],
        }

        # Simple parsing - in production, use more sophisticated NLP
        content_lower = response_content.lower()

        # Extract technology stack mentions
        technologies = []
        tech_keywords = [
            "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
            "jenkins", "github actions", "prometheus", "grafana",
            "nodejs", "python", "java", "react", "vue", "postgresql"
        ]

        for tech in tech_keywords:
            if tech in content_lower:
                technologies.append(tech)

        analysis["technology_stack"] = technologies
        analysis["full_analysis"] = response_content
        analysis["task_type"] = task_type
        analysis["key_recommendations"] = self._extract_key_recommendations(response_content)

        return analysis

    def _extract_key_recommendations(self, content: str) -> List[str]:
        """Extract key recommendations from the response"""
        recommendations = []

        # Look for specific recommendation patterns
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # Look for recommendation indicators
            if any(keyword in line.lower() for keyword in [
                'recommend', 'suggest', 'should', 'must', 'implement',
                'use', 'deploy', 'configure', 'setup', 'adopt'
            ]):
                recommendations.append(line)

        return recommendations[:10]  # Return top 10 recommendations

    async def _generate_implementation_plan(self, devops_result: Dict, task_type: str) -> Dict[str, Any]:
        """Generate detailed implementation plan"""
        plan = {
            "phases": [],
            "dependencies": [],
            "estimated_timeline": "6-8 weeks",
            "resource_requirements": {
                "developers": 2,
                "devops_engineers": 1,
                "security_specialist": 1
            },
            "milestones": []
        }

        # Generate phases based on task type
        if task_type == "architecture":
            plan["phases"] = [
                {"phase": 1, "title": "Requirements Analysis", "duration": "1 week"},
                {"phase": 2, "title": "Architecture Design", "duration": "2 weeks"},
                {"phase": 3, "title": "Proof of Concept", "duration": "2 weeks"},
                {"phase": 4, "title": "Implementation", "duration": "3 weeks"},
                {"phase": 5, "title": "Testing & Deployment", "duration": "1 week"},
            ]
        elif task_type == "security":
            plan["phases"] = [
                {"phase": 1, "title": "Security Assessment", "duration": "1 week"},
                {"phase": 2, "title": "Security Implementation", "duration": "2 weeks"},
                {"phase": 3, "title": "Testing & Validation", "duration": "1 week"},
                {"phase": 4, "title": "Documentation & Training", "duration": "1 week"},
            ]
        else:
            plan["phases"] = [
                {"phase": 1, "title": "Planning & Design", "duration": "1-2 weeks"},
                {"phase": 2, "title": "Implementation", "duration": "3-4 weeks"},
                {"phase": 3, "title": "Testing & Optimization", "duration": "1-2 weeks"},
            ]

        return plan

    async def get_architecture_recommendation(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Get architecture recommendation based on requirements"""
        try:
            prompt = f"""
            ARCHITECTURE RECOMMENDATION REQUEST

            Requirements: {json.dumps(requirements, indent=2)}

            Based on these requirements, please recommend the most suitable architecture pattern
            from: microservices, serverless, or monolithic.

            Provide detailed reasoning for your recommendation, including:
            1. Why this pattern is最适合
            2. Specific technologies to use
            3. Implementation considerations
            4. Potential challenges and mitigation strategies
            """

            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            return {
                "recommendation": response.content,
                "requirements": requirements,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error generating architecture recommendation: {e}")
            return {"error": str(e)}

    async def get_security_audit(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security audit assessment"""
        try:
            prompt = f"""
            SECURITY AUDIT REQUEST

            System Information: {json.dumps(system_info, indent=2)}

            Please perform a security audit assessment and provide:
            1. Security vulnerabilities and risks
            2. Recommended security measures
            3. Compliance requirements
            4. Implementation priorities
            5. Monitoring and maintenance recommendations
            """

            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])

            return {
                "security_audit": response.content,
                "risk_level": "medium",  # Would be calculated based on actual analysis
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error in security audit: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Health check for DevOps agent"""
        return {
            "status": "healthy",
            "agent": "devops",
            "capabilities": [
                "technical_architecture",
                "system_design",
                "infrastructure_planning",
                "security_assessment",
                "performance_optimization",
                "cicd_implementation",
                "monitoring_setup",
                "automation"
            ],
            "architecture_patterns": list(self.architecture_patterns.keys()),
            "timestamp": datetime.now().isoformat(),
        }