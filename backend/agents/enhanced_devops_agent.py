"""
Enhanced DevOps Agent - Improved DevOps agent with proper LLM integration
Handles technical implementation, system architecture, and deployment
"""

from typing import Dict, Any, List
import logging

from agents.enhanced_base_agent import EnhancedBaseAgent


class EnhancedDevOpsAgent(EnhancedBaseAgent):
    """Enhanced DevOps Agent combining CTO and DevOps responsibilities with proper LLM integration"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="devops",
            agent_type="devops"
        )
        self.logger.info("Enhanced DevOps Agent initialized with LLM integration")

    def get_system_prompt(self) -> str:
        """Return the system prompt for the DevOps agent"""
        return """You are the DevOps Agent for AutoAdmin, combining the expertise of a CTO (Chief Technology Officer) and Senior DevOps Engineer.

DUAL ROLE RESPONSIBILITIES:

AS CTO (Chief Technology Officer):
1. Technology Strategy - Define technical vision and architecture
2. System Design - Design scalable and maintainable systems
3. Technology Stack Selection - Choose appropriate technologies
4. Innovation Leadership - Identify and evaluate new technologies
5. Technical Team Leadership - Guide technical decisions and best practices

AS DEVOPS ENGINEER:
1. Infrastructure Management - Design and maintain infrastructure
2. CI/CD Pipeline - Build and optimize deployment pipelines
3. Monitoring & Observability - Implement comprehensive monitoring
4. Security & Compliance - Ensure system security and compliance
5. Performance Optimization - Optimize system performance and reliability

TECHNICAL APPROACH:
- Prioritize scalability, reliability, and maintainability
- Implement infrastructure as code and automation
- Follow DevOps best practices and SRE principles
- Ensure security is built into every layer
- Focus on observability and data-driven decisions

WHEN RESPONDING:
1. Provide technical architecture and design recommendations
2. Include specific implementation details and code examples when relevant
3. Consider scalability, performance, and security implications
4. Suggest appropriate tools and technologies
5. Provide step-by-step implementation guidance
6. Include monitoring and maintenance considerations

CURRENT TIMESTAMP: {timestamp}

Remember: You are responsible for the technical foundation of all systems. Your recommendations must be practical, scalable, and aligned with industry best practices."""

    def get_capabilities(self) -> List[str]:
        """Return list of DevOps agent capabilities"""
        return [
            "system_architecture",
            "infrastructure_design",
            "ci_cd_pipeline",
            "deployment_strategy",
            "monitoring_observability",
            "security_compliance",
            "performance_optimization",
            "cloud_services",
            "containerization",
            "automation"
        ]

    async def process_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a DevOps-specific task with enhanced capabilities"""
        self.logger.info(f"[DevOps] Processing task: {task_input.get('message', '')[:100]}...")

        # Determine task type
        task_type = self._classify_devops_task(task_input.get("message", ""))

        # Add DevOps-specific context
        devops_context = {
            **task_input,
            "task_type": task_type,
            "role": "cto_devops",
            "technical_scope": "implementation"
        }

        # Process using enhanced base agent
        response = await super().process_task(devops_context)

        # Add DevOps-specific metadata
        if response.get("success"):
            response["metadata"].update({
                "technical_domain": task_type,
                "technologies_mentioned": self._extract_technologies(response.get("response", "")),
                "implementation_complexity": self._assess_complexity(response.get("response", "")),
                "security_considerations": self._extract_security_points(response.get("response", ""))
            })

        return response

    def _classify_devops_task(self, message: str) -> str:
        """Classify the type of DevOps task"""
        message_lower = message.lower()

        # Architecture keywords
        arch_keywords = [
            "architecture", "design", "system", "structure", "pattern",
            "scalable", "microservices", "monolith", "distributed"
        ]

        # Infrastructure keywords
        infra_keywords = [
            "infrastructure", "cloud", "aws", "azure", "gcp", "serverless",
            "kubernetes", "docker", "container", "vm", "networking"
        ]

        # CI/CD keywords
        cicd_keywords = [
            "deploy", "deployment", "pipeline", "ci/cd", "continuous",
            "integration", "delivery", "release", "build", "automate"
        ]

        # Monitoring keywords
        monitor_keywords = [
            "monitor", "observability", "logging", "metrics", "alert",
            "dashboard", "prometheus", "grafana", "elk", "splunk"
        ]

        # Security keywords
        security_keywords = [
            "security", "authentication", "authorization", "encryption",
            "vulnerability", "compliance", "audit", "penetration", "ssl"
        ]

        keyword_sets = [
            (arch_keywords, "architecture"),
            (infra_keywords, "infrastructure"),
            (cicd_keywords, "cicd"),
            (monitor_keywords, "monitoring"),
            (security_keywords, "security")
        ]

        scores = [(sum(1 for kw in keywords if kw in message_lower), task_type)
                  for keywords, task_type in keyword_sets]

        # Return the task type with the highest score
        if scores:
            best_score, best_type = max(scores)
            if best_score > 0:
                return best_type

        return "general_technical"

    def _extract_technologies(self, response: str) -> List[str]:
        """Extract technology mentions from response"""
        technologies = []
        response_lower = response.lower()

        # Common technology keywords
        tech_keywords = [
            "aws", "azure", "gcp", "kubernetes", "docker", "jenkins",
            "gitlab", "github", "terraform", "ansible", "prometheus",
            "grafana", "elasticsearch", "kibana", "fluentd", "nginx",
            "apache", "node.js", "python", "java", "react", "angular",
            "vue", "postgresql", "mysql", "mongodb", "redis", "rabbitmq",
            "kafka", "microservices", "serverless", "lambda", "ecs",
            "eks", "aks", "gke", "vpc", "cdn", "load balancer"
        ]

        for tech in tech_keywords:
            if tech in response_lower:
                technologies.append(tech)

        return list(set(technologies))  # Remove duplicates

    def _assess_complexity(self, response: str) -> str:
        """Assess implementation complexity from response"""
        response_lower = response.lower()

        complexity_indicators = {
            "simple": ["simple", "basic", "straightforward", "easy", "quick"],
            "moderate": ["moderate", "medium", "standard", "typical"],
            "complex": ["complex", "advanced", "challenging", "sophisticated"],
            "very_complex": ["very complex", "highly complex", "enterprise", "large scale"]
        }

        for complexity, indicators in complexity_indicators.items():
            if any(indicator in response_lower for indicator in indicators):
                return complexity

        # Default based on response length and detail
        if len(response) > 2000:
            return "complex"
        elif len(response) > 1000:
            return "moderate"
        else:
            return "simple"

    def _extract_security_points(self, response: str) -> List[str]:
        """Extract security considerations from response"""
        security_points = []
        response_lower = response.lower()
        lines = response.split('\n')

        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in [
                "security", "authentication", "authorization", "encryption",
                "ssl", "tls", "firewall", "vpn", "iam", "rbac", "audit"
            ]):
                # Clean up the point
                point = line.strip()
                if point.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    point = point[1:].strip()
                if point and len(point) > 10:
                    security_points.append(point)

        return security_points[:5]  # Return max 5 points

    async def design_system_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design system architecture based on requirements"""
        self.logger.info("[DevOps] Designing system architecture")

        arch_prompt = f"""Design a comprehensive system architecture for the following requirements:

{requirements}

Include:
1. High-level architecture diagram description
2. Component breakdown and responsibilities
3. Data flow and communication patterns
4. Technology stack recommendations
5. Scalability considerations
6. Security measures
7. Deployment strategy"""

        response = await self.process_message(arch_prompt, {
            "analysis_type": "architecture_design",
            "requirements": requirements
        })

        return {
            "requirements": requirements,
            "architecture_design": response.content,
            "success": response.success,
            "timestamp": response.timestamp,
            "metadata": response.metadata
        }

    async def create_deployment_pipeline(self, project_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a CI/CD deployment pipeline"""
        self.logger.info("[DevOps] Creating deployment pipeline")

        pipeline_prompt = f"""Design a complete CI/CD deployment pipeline for:

{project_info}

Include:
1. Pipeline stages and workflows
2. Build and test automation
3. Deployment strategy (blue-green, canary, rolling)
4. Environment management
5. Rollback procedures
6. Monitoring and alerting
7. Specific tool recommendations (GitHub Actions, Jenkins, GitLab CI, etc.)"""

        response = await self.process_message(pipeline_prompt, {
            "analysis_type": "deployment_pipeline",
            "project_info": project_info
        })

        # Extract pipeline stages
        pipeline_stages = self._extract_pipeline_stages(response.content)

        return {
            "project_info": project_info,
            "pipeline_design": response.content,
            "pipeline_stages": pipeline_stages,
            "success": response.success,
            "timestamp": response.timestamp,
            "metadata": response.metadata
        }

    def _extract_pipeline_stages(self, response: str) -> List[str]:
        """Extract pipeline stages from response"""
        stages = []
        response_lower = response.lower()
        lines = response.split('\n')

        stage_keywords = [
            "build", "test", "lint", "security scan", "deploy", "monitor",
            "validate", "package", "release", "rollback", "notify"
        ]

        for line in lines:
            line_lower = line.lower()
            for keyword in stage_keywords:
                if keyword in line_lower and any(indicator in line for indicator in [':', '-', '•', 'stage']):
                    stage = line.strip()
                    if stage.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                        stage = stage[1:].strip()
                    if stage and len(stage) > 5:
                        stages.append(stage)
                    break

        return stages[:10]  # Return max 10 stages

    async def security_review(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security review of a system"""
        self.logger.info("[DevOps] Performing security review")

        security_prompt = f"""Perform a comprehensive security review for:

{system_info}

Include:
1. Security vulnerabilities and risks
2. Authentication and authorization recommendations
3. Data protection measures
4. Network security considerations
5. Compliance requirements
6. Security monitoring and logging
7. Best practices implementation"""

        response = await self.process_message(security_prompt_prompt, {
            "analysis_type": "security_review",
            "system_info": system_info
        })

        # Extract security recommendations
        recommendations = self._extract_security_recommendations(response.content)

        return {
            "system_info": system_info,
            "security_review": response.content,
            "recommendations": recommendations,
            "success": response.success,
            "timestamp": response.timestamp,
            "metadata": response.metadata
        }

    def _extract_security_recommendations(self, response: str) -> List[Dict[str, str]]:
        """Extract structured security recommendations"""
        recommendations = []
        lines = response.split('\n')
        current_rec = {}

        for line in lines:
            line_lower = line.lower()
            line_stripped = line.strip()

            # Look for recommendation indicators
            if any(keyword in line_lower for keyword in [
                "recommend", "should", "must", "implement", "use", "enable"
            ]):
                if current_rec:
                    recommendations.append(current_rec)

                current_rec = {
                    "recommendation": line_stripped,
                    "category": self._categorize_recommendation(line_stripped),
                    "priority": self._assess_priority(line_stripped)
                }

        # Don't forget the last recommendation
        if current_rec:
            recommendations.append(current_rec)

        return recommendations[:10]  # Return max 10 recommendations

    def _categorize_recommendation(self, recommendation: str) -> str:
        """Categorize a security recommendation"""
        rec_lower = recommendation.lower()

        categories = {
            "authentication": ["auth", "login", "password", "mfa", "2fa"],
            "encryption": ["encrypt", "tls", "ssl", "certificate", "key"],
            "network": ["network", "firewall", "vpn", "port", "protocol"],
            "data": ["data", "backup", "retention", "privacy", "pii"],
            "monitoring": ["monitor", "log", "audit", "alert", "detect"]
        }

        for category, keywords in categories.items():
            if any(keyword in rec_lower for keyword in keywords):
                return category

        return "general"

    def _assess_priority(self, recommendation: str) -> str:
        """Assess priority of a recommendation"""
        rec_lower = recommendation.lower()

        if any(word in rec_lower for word in ["critical", "urgent", "immediate", "must"]):
            return "high"
        elif any(word in rec_lower for word in ["important", "should", "recommend"]):
            return "medium"
        else:
            return "low"