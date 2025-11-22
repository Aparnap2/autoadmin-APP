"""
Unit tests for AutoAdmin agents.

Tests the CEO, Strategy, and DevOps agents functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from agents.deep_agents.base import AgentType, Task, TaskStatus, AgentState
from agents.deep_agents.ceo_agent import CEOAgent
from agents.deep_agents.strategy_agent import StrategyAgent
from agents.deep_agents.devops_agent import DevOpsAgent


@pytest.fixture
def mock_task():
    """Create a mock task."""
    return Task(
        id="test-task-123",
        type=AgentType.CEO,
        description="Test task description",
        parameters={"test": "value"},
        status=TaskStatus.PENDING,
        created_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def mock_state():
    """Create a mock agent state."""
    return {
        "messages": [],
        "current_agent": "ceo",
        "agent_task_queue": [],
        "business_context": {"test": "context"},
        "current_trends": ["AI", "Automation"],
        "finance_alerts": [],
        "marketing_queue": [],
        "repo_context": {},
        "open_prs": [],
        "pending_issues": [],
        "session_id": "test-session",
        "last_updated": "2024-01-01T00:00:00Z"
    }


class TestCEOAgent:
    """Test the CEO Agent."""

    @pytest.fixture
    def ceo_agent(self):
        """Create a CEO agent."""
        return CEOAgent()

    def test_ceo_agent_initialization(self, ceo_agent):
        """Test CEO agent initialization."""
        assert ceo_agent.agent_type == AgentType.CEO
        assert ceo_agent.name == "CEO Agent"
        assert "strategic decisions" in ceo_agent.description.lower()
        assert "Strategic planning" in ceo_agent.capabilities
        assert ceo_agent.temperature == 0.3  # Lower temperature for consistency

    def test_ceo_agent_system_prompt(self, ceo_agent, mock_state):
        """Test CEO agent system prompt generation."""
        prompt = ceo_agent.create_system_prompt(mock_state)

        assert "CEO Agent" in prompt
        assert "business context" in prompt.lower()
        assert "AI, Automation" in prompt  # From current trends

    @pytest.mark.asyncio
    async def test_ceo_agent_task_classification(self, ceo_agent):
        """Test CEO agent task classification."""
        # Test DevOps task
        task = Task(
            id="devops-task",
            type=AgentType.CEO,
            description="Implement new API endpoint",
            parameters={}
        )
        analysis = await ceo_agent._analyze_task_requirements(task, mock_state)
        required_capabilities = analysis.get("required_capabilities", [])
        assert "devops" in required_capabilities

        # Test Strategy task
        task.description = "Research market trends for AI automation"
        analysis = await ceo_agent._analyze_task_requirements(task, mock_state)
        required_capabilities = analysis.get("required_capabilities", [])
        assert "strategy" in required_capabilities

    @pytest.mark.asyncio
    async def test_ceo_agent_task_assignment(self, ceo_agent):
        """Test CEO agent task assignment."""
        # Test DevOps assignment
        task = Task(
            id="code-task",
            type=AgentType.CEO,
            description="Create a pull request for new feature",
            parameters={}
        )
        target_agent = await ceo_agent._determine_task_assignment(task, {})
        assert target_agent == AgentType.DEVOPS

        # Test Strategy assignment
        task.description = "Analyze competitive landscape"
        target_agent = await ceo_agent._determine_task_assignment(task, {})
        assert target_agent == AgentType.STRATEGY

        # Test CEO assignment
        task.description = "Review quarterly business performance"
        target_agent = await ceo_agent._determine_task_assignment(task, {})
        assert target_agent == AgentType.CEO

    @pytest.mark.asyncio
    async def test_ceo_agent_proactive_tasks(self, ceo_agent, mock_state):
        """Test CEO agent proactive task identification."""
        mock_state["current_trends"] = ["AI automation", "Remote work"]
        mock_state["open_prs"] = [
            {"number": 1, "title": "Test PR"},
            {"number": 2, "title": "Another PR"}
        ]

        tasks = await ceo_agent._identify_proactive_tasks(mock_state)

        assert len(tasks) == 2  # One for trends, one for PRs
        assert tasks[0].type == AgentType.STRATEGY
        assert tasks[1].type == AgentType.DEVOPS


class TestStrategyAgent:
    """Test the Strategy Agent."""

    @pytest.fixture
    def strategy_agent(self):
        """Create a Strategy agent."""
        mock_tavily_tools = Mock()
        return StrategyAgent(tavily_tools=mock_tavily_tools)

    def test_strategy_agent_initialization(self, strategy_agent):
        """Test Strategy agent initialization."""
        assert strategy_agent.agent_type == AgentType.STRATEGY
        assert "Strategy Agent" in strategy_agent.name
        assert "CMO/CFO" in strategy_agent.name
        assert "Market research" in strategy_agent.capabilities
        assert strategy_agent.temperature == 0.7  # Higher temperature for creativity

    def test_strategy_agent_task_classification(self, strategy_agent):
        """Test Strategy agent task classification."""
        # Test market research task
        task = Task(
            id="research-task",
            type=AgentType.STRATEGY,
            description="Research latest AI automation trends",
            parameters={}
        )
        task_type = strategy_agent._classify_strategy_task(task)
        assert task_type == "market_research"

        # Test financial analysis task
        task.description = "Analyze Q3 financial performance"
        task_type = strategy_agent._classify_strategy_task(task)
        assert task_type == "financial_analysis"

        # Test content strategy task
        task.description = "Develop content strategy for Q4"
        task_type = strategy_agent._classify_strategy_task(task)
        assert task_type == "content_strategy"

    @pytest.mark.asyncio
    async def test_strategy_agent_market_research(self, strategy_agent):
        """Test Strategy agent market research."""
        # Mock Tavily tools
        strategy_agent.tavily_tools.comprehensive_research = AsyncMock(return_value={
            'trends': [Mock(title="AI Trend", content="AI is trending")],
            'news': [Mock(title="Tech News", content="Latest tech news")],
            'analysis': [Mock(title="Market Analysis", content="Market insights")],
            'content_ideas': [Mock(title="Content Ideas", content="Blog topics")]
        })

        task = Task(
            id="research-task",
            type=AgentType.STRATEGY,
            description="Research AI automation market",
            parameters={"topic": "AI automation", "industry": "technology"}
        )

        state = {}
        result = await strategy_agent._perform_market_research(task, state)

        assert "Market Research Report" in result
        assert "AI automation" in result
        assert "Strategic Recommendations" in result

    @pytest.mark.asyncio
    async def test_strategy_agent_financial_analysis(self, strategy_agent):
        """Test Strategy agent financial analysis."""
        task = Task(
            id="finance-task",
            type=AgentType.STRATEGY,
            description="Analyze financial performance",
            parameters={"company": "Our Company", "type": "quarterly"}
        )

        state = {}
        result = await strategy_agent._perform_financial_analysis(task, state)

        assert "Financial Analysis Report" in result
        assert "Our Company" in result
        assert "Revenue Status" in result
        assert "Budget Optimization" in result

    @pytest.mark.asyncio
    async def test_strategy_agent_trend_analysis(self, strategy_agent):
        """Test Strategy agent trend analysis."""
        # Mock Tavily tools
        strategy_agent.tavily_tools.search_technology_trends = AsyncMock(return_value=[
            Mock(title="AI Trend", content="AI continues to evolve"),
            Mock(title="Automation Trend", content="Automation adoption increases")
        ])

        task = Task(
            id="trend-task",
            type=AgentType.STRATEGY,
            description="Analyze current technology trends",
            parameters={"topics": ["AI", "automation"]}
        )

        state = {}
        result = await strategy_agent._perform_trend_analysis(task, state)

        assert "Trend Analysis Report" in result
        assert "AI" in result or "automation" in result
        assert "Strategic Implications" in result


class TestDevOpsAgent:
    """Test the DevOps Agent."""

    @pytest.fixture
    def devops_agent(self):
        """Create a DevOps agent."""
        mock_github_tools = Mock()
        return DevOpsAgent(github_tools=mock_github_tools)

    def test_devops_agent_initialization(self, devops_agent):
        """Test DevOps agent initialization."""
        assert devops_agent.agent_type == AgentType.DEVOPS
        assert "DevOps Agent" in devops_agent.name
        assert "CTO" in devops_agent.name
        assert "Code generation" in devops_agent.capabilities
        assert "GitHub operations" in devops_agent.capabilities
        assert devops_agent.temperature == 0.3  # Lower temperature for precision

    def test_devops_agent_task_classification(self, devops_agent):
        """Test DevOps agent task classification."""
        # Test code generation task
        task = Task(
            id="code-task",
            type=AgentType.DEVOPS,
            description="Implement new API endpoint",
            parameters={}
        )
        task_type = devops_agent._classify_devops_task(task)
        assert task_type == "code_generation"

        # Test PR review task
        task.description = "Review pull request #123"
        task_type = devops_agent._classify_devops_task(task)
        assert task_type == "pr_review"

        # Test repository analysis task
        task.description = "Analyze repository structure"
        task_type = devops_agent._classify_devops_task(task)
        assert task_type == "repository_analysis"

    @pytest.mark.asyncio
    async def test_devops_agent_code_generation(self, devops_agent):
        """Test DevOps agent code generation."""
        # Mock GitHub tools
        devops_agent.github_tools.create_branch = AsyncMock(return_value=True)
        devops_agent.github_tools.create_file = AsyncMock(return_value=True)
        devops_agent.github_tools.create_pull_request = AsyncMock(return_value=Mock(
            number=123,
            title="Automated: Test Feature",
            url="https://github.com/test/repo/pull/123"
        ))

        task = Task(
            id="code-gen-task",
            type=AgentType.DEVOPS,
            description="Create a simple API endpoint",
            parameters={"requirements": "API endpoint for user management", "file_type": "python"}
        )

        state = {}
        result = await devops_agent._generate_code(task, state)

        assert "Code Generated and PR Created" in result
        assert "#123" in result
        assert "https://github.com/test/repo/pull/123" in result

    @pytest.mark.asyncio
    async def test_devops_agent_api_code_generation(self, devops_agent):
        """Test DevOps agent API-specific code generation."""
        code = await devops_agent._generate_api_code("User management API")

        assert "from fastapi import FastAPI" in code
        assert "@app.get" in code
        assert "@app.post" in code
        assert "class Item" in code or "class User" in code

    @pytest.mark.asyncio
    async def test_devops_agent_test_code_generation(self, devops_agent):
        """Test DevOps agent test code generation."""
        code = await devops_agent._generate_test_code("Test agent functionality")

        assert "import pytest" in code
        assert "def test_" in code
        assert "Mock" in code

    @pytest.mark.asyncio
    async def test_devops_agent_repository_analysis(self, devops_agent):
        """Test DevOps agent repository analysis."""
        # Mock GitHub tools
        mock_repo_info = Mock(
            name="test-repo",
            full_name="user/test-repo",
            description="Test repository",
            language="Python",
            stars=42,
            forks=10,
            open_issues=3,
            default_branch="main"
        )
        devops_agent.github_tools.get_repository_info = AsyncMock(return_value=mock_repo_info)

        mock_code_analysis = {
            'file_count': 150,
            'main_language': 'Python',
            'file_extensions': {'py': 80, 'js': 30, 'md': 20, 'json': 20},
            'directories': ['src/', 'tests/', 'docs/', 'config/'],
            'important_files': ['README.md', 'requirements.txt', 'setup.py']
        }
        devops_agent.github_tools.analyze_code_structure = AsyncMock(return_value=mock_code_analysis)

        devops_agent.github_tools.get_pull_requests = AsyncMock(return_value=[
            Mock(number=1, title="Fix bug", state="open"),
            Mock(number=2, title="Add feature", state="open")
        ])
        devops_agent.github_tools.get_issues = AsyncMock(return_value=[
            Mock(number=10, title="Issue title", state="open")
        ])

        task = Task(
            id="analysis-task",
            type=AgentType.DEVOPS,
            description="Analyze repository structure and health",
            parameters={"repo": "user/test-repo"}
        )

        state = {}
        result = await devops_agent._analyze_repository(task, state)

        assert "Repository Analysis" in result
        assert "test-repo" in result
        assert "150" in result  # file count
        assert "Python" in result
        assert "Health Score" in result

    @pytest.mark.asyncio
    async def test_devops_agent_deployment(self, devops_agent):
        """Test DevOps agent deployment handling."""
        task = Task(
            id="deploy-task",
            type=AgentType.DEVOPS,
            description="Deploy to production",
            parameters={"environment": "production", "service": "api"}
        )

        state = {}
        result = await devops_agent._handle_deployment(task, state)

        assert "Deployment Operation" in result
        assert "production" in result
        assert "api" in result
        assert "Pre-Deployment Checklist" in result
        assert "Deployment Steps" in result

    @pytest.mark.asyncio
    async def test_devops_agent_architecture_design(self, devops_agent):
        """Test DevOps agent architecture design."""
        task = Task(
            id="arch-task",
            type=AgentType.DEVOPS,
            description="Design architecture for new feature",
            parameters={"feature": "Real-time notifications", "scale": "large"}
        )

        state = {}
        result = await devops_agent._design_architecture(task, state)

        assert "Architecture Design" in result
        assert "Real-time notifications" in result
        assert "Proposed Architecture" in result
        assert "Frontend Layer" in result
        assert "Backend Layer" in result
        assert "Database Layer" in result
        assert "Infrastructure Layer" in result
        assert "Security Considerations" in result


class TestTask:
    """Test the Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task."""
        task = Task(
            id="test-task",
            type=AgentType.CEO,
            description="Test description",
            parameters={"key": "value"},
            status=TaskStatus.PENDING
        )

        assert task.id == "test-task"
        assert task.type == AgentType.CEO
        assert task.description == "Test description"
        assert task.parameters == {"key": "value"}
        assert task.status == TaskStatus.PENDING

    def test_task_to_dict(self):
        """Test converting Task to dictionary."""
        task = Task(
            id="test-task",
            type=AgentType.STRATEGY,
            description="Test task",
            parameters={"param": "value"},
            status=TaskStatus.IN_PROGRESS,
            assigned_by="ceo",
            result="Task completed"
        )

        task_dict = task.to_dict()

        expected = {
            'id': 'test-task',
            'type': 'strategy',
            'description': 'Test task',
            'parameters': {'param': 'value'},
            'status': 'in_progress',
            'assigned_by': 'ceo',
            'result': 'Task completed',
            'error': None,
            'created_at': None
        }

        assert task_dict == expected