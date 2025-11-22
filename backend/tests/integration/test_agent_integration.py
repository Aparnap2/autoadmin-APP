"""
Integration tests for AutoAdmin agent system.

Tests the full agent system with real interactions between components.
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
import asyncio

from agents.main import AutoAdminAgents
from agents.deep_agents.base import AgentType, Task, TaskStatus


@pytest.fixture
def mock_env_vars():
    """Mock required environment variables."""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
        "GITHUB_TOKEN": "test-github-token",
        "TAVILY_API_KEY": "test-tavily-key",
        "SESSION_ID": "test-session-123"
    }
    return env_vars


@pytest.mark.integration
class TestAutoAdminAgentsIntegration:
    """Integration tests for the full AutoAdmin system."""

    @pytest.fixture
    async def agents_system(self, mock_env_vars):
        """Create an AutoAdmin agents system for testing."""
        with patch.dict(os.environ, mock_env_vars):
            agents = AutoAdminAgents()

            # Mock all external dependencies
            with patch('agents.memory.graph_memory.create_client'), \
                 patch('agents.memory.graph_memory.OpenAIEmbeddings'), \
                 patch('agents.tools.tavily_tools.TavilyClient'), \
                 patch('agents.tools.github_tools.Github'):

                await agents.initialize()
                yield agents
                await agents.cleanup()

    @pytest.mark.asyncio
    async def test_system_initialization(self, agents_system):
        """Test full system initialization."""
        assert agents_system.orchestrator is not None
        assert agents_system.graph_memory is not None
        assert agents_system.virtual_fs is not None
        assert agents_system.tavily_tools is not None
        assert agents_system.github_tools is not None

        # Check system status
        status = await agents_system.get_system_status()
        assert status["initialized"] is True
        assert status["system_id"] == "test-session-123"
        assert "agents" in status["status"]

    @pytest.mark.asyncio
    async def test_message_processing_ceo_task(self, agents_system):
        """Test processing a message that should be handled by CEO."""
        message = "Review our quarterly business performance and provide strategic recommendations"

        # Mock the CEO agent's response
        with patch.object(agents_system.orchestrator, 'process_message') as mock_process:
            mock_process.return_value = {
                "response": "CEO Strategic Analysis: Business performance review completed with recommendations",
                "session_id": "test-session-123"
            }

            result = await agents_system.process_message(message)

            assert result["response"] is not None
            assert "CEO Strategic Analysis" in result["response"]
            assert result["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_message_processing_strategy_task(self, agents_system):
        """Test processing a message that should be handled by Strategy agent."""
        message = "Research current AI automation trends and their impact on small businesses"

        # Mock the Strategy agent's response
        with patch.object(agents_system.orchestrator, 'process_message') as mock_process:
            mock_process.return_value = {
                "response": "Strategy Agent Market Research: AI automation trends analysis completed",
                "session_id": "test-session-123"
            }

            result = await agents_system.process_message(message)

            assert result["response"] is not None
            assert "Strategy Agent" in result["response"]
            assert "Market Research" in result["response"]

    @pytest.mark.asyncio
    async def test_message_processing_devops_task(self, agents_system):
        """Test processing a message that should be handled by DevOps agent."""
        message = "Create a new API endpoint for user authentication with proper error handling"

        # Mock the DevOps agent's response
        with patch.object(agents_system.orchestrator, 'process_message') as mock_process:
            mock_process.return_value = {
                "response": "DevOps Agent Code Generation: API endpoint created and PR opened",
                "session_id": "test-session-123"
            }

            result = await agents_system.process_message(message)

            assert result["response"] is not None
            assert "DevOps Agent" in result["response"]
            assert "Code Generation" in result["response"]

    @pytest.mark.asyncio
    async def test_create_specific_task(self, agents_system):
        """Test creating a specific task for an agent."""
        # Mock the task processing
        with patch.object(agents_system, 'process_message') as mock_process:
            mock_process.return_value = {
                "response": "Task completed: Market analysis report generated",
                "session_id": "test-session-123"
            }

            result = await agents_system.create_task(
                task_type=AgentType.STRATEGY,
                description="Analyze market trends for AI automation",
                parameters={"topics": ["AI", "automation"], "depth": "comprehensive"}
            )

            assert result is not None
            assert "Task completed" in result
            assert "Market analysis" in result

    @pytest.mark.asyncio
    async def test_proactive_analysis(self, agents_system):
        """Test running proactive analysis."""
        # Mock proactive analysis
        with patch.object(agents_system, 'process_message') as mock_process:
            mock_process.return_value = {
                "response": "Daily Proactive Analysis Report: Trends monitored, insights generated",
                "session_id": "test-session-123"
            }

            result = await agents_system.run_proactive_analysis()

            assert result["response"] is not None
            assert "Proactive Analysis" in result["response"]

    @pytest.mark.asyncio
    async def test_error_handling(self, agents_system):
        """Test error handling in the agent system."""
        # Mock an error during message processing
        with patch.object(agents_system.orchestrator, 'process_message') as mock_process:
            mock_process.side_effect = Exception("Simulated error")

            result = await agents_system.process_message("Test message")

            assert result["error"] is True
            assert "Error processing message" in result["response"]

    @pytest.mark.asyncio
    async def test_agent_communication_flow(self, agents_system):
        """Test communication flow between different agents."""
        # This would test the actual LangGraph agent routing
        # For now, we'll mock the overall flow
        with patch.object(agents_system.orchestrator, 'process_message') as mock_process:
            # Simulate a multi-agent interaction
            mock_process.return_value = {
                "response": """
                CEO Analysis: This requires both market research and technical implementation.

                Strategy Agent: Market research completed, competitor analysis shows opportunities.

                DevOps Agent: Technical feasibility confirmed, implementation plan ready.

                CEO Final: Combined strategy and development plan approved for execution.
                """,
                "session_id": "test-session-123"
            }

            result = await agents_system.process_message(
                "Analyze the feasibility of implementing a real-time notification system"
            )

            assert "CEO Analysis" in result["response"]
            assert "Strategy Agent" in result["response"]
            assert "DevOps Agent" in result["response"]
            assert "CEO Final" in result["response"]

    @pytest.mark.asyncio
    async def test_memory_integration(self, agents_system):
        """Test integration of graph memory and virtual file system."""
        # Test storing and retrieving information through agents
        with patch.object(agents_system.graph_memory, 'add_node') as mock_add_node, \
             patch.object(agents_system.graph_memory, 'query_graph') as mock_query, \
             patch.object(agents_system.virtual_fs, 'write_file') as mock_write, \
             patch.object(agents_system.virtual_fs, 'read_file') as mock_read:

            # Mock memory operations
            mock_add_node.return_value = Mock(id="memory-node-123")
            mock_query.return_value = [{"content": "Stored information", "type": "node"}]
            mock_write.return_value = None
            mock_read.return_value = "Retrieved file content"

            result = await agents_system.process_message(
                "Store market analysis data and retrieve previous research"
            )

            # Verify memory systems were called
            mock_add_node.assert_called()
            mock_query.assert_called()

            assert result["response"] is not None

    @pytest.mark.asyncio
    async def test_tool_integration(self, agents_system):
        """Test integration of external tools (Tavily, GitHub)."""
        # Test using Tavily for research
        with patch.object(agents_system.tavily_tools, 'comprehensive_research') as mock_research, \
             patch.object(agents_system.github_tools, 'create_pull_request') as mock_pr:

            # Mock tool responses
            mock_research.return_value = {
                'trends': [{'title': 'AI Trend', 'content': 'AI is evolving rapidly'}],
                'analysis': [{'title': 'Market Analysis', 'content': 'Market insights'}]
            }
            mock_pr.return_value = Mock(number=456, title="Automated Research Update", url="https://github.com/test/pr/456")

            result = await agents_system.process_message(
                "Research AI trends and create a GitHub PR with the findings"
            )

            # Verify tools were called
            mock_research.assert_called()
            mock_pr.assert_called()

            assert result["response"] is not None


@pytest.mark.integration
class TestAgentWorkflowIntegration:
    """Integration tests for specific agent workflows."""

    @pytest.mark.asyncio
    async def test_market_research_workflow(self, mock_env_vars):
        """Test complete market research workflow."""
        with patch.dict(os.environ, mock_env_vars):
            agents = AutoAdminAgents()

            # Mock dependencies
            with patch('agents.memory.graph_memory.create_client'), \
                 patch('agents.memory.graph_memory.OpenAIEmbeddings'), \
                 patch('agents.tools.tavily_tools.TavilyClient'), \
                 patch('agents.tools.github_tools.Github'):

                await agents.initialize()

                # Mock Tavily research results
                agents.tavily_tools.comprehensive_research = AsyncMock(return_value={
                    'trends': [
                        Mock(title="AI Automation", content="AI automation is accelerating"),
                        Mock(title="Remote Work", content="Remote work tools evolving")
                    ],
                    'news': [
                        Mock(title="Tech News", content="Latest tech developments")
                    ],
                    'analysis': [
                        Mock(title="Market Analysis", content="Market insights and forecasts")
                    ]
                })

                # Test the workflow
                result = await agents.create_task(
                    task_type=AgentType.STRATEGY,
                    description="Research AI automation market trends for Q4 planning",
                    parameters={"industry": "technology", "depth": "comprehensive"}
                )

                assert "Market Research Report" in result
                assert "AI Automation" in result
                assert "Strategic Recommendations" in result

                await agents.cleanup()

    @pytest.mark.asyncio
    async def test_code_generation_workflow(self, mock_env_vars):
        """Test complete code generation workflow."""
        with patch.dict(os.environ, mock_env_vars):
            agents = AutoAdminAgents()

            # Mock dependencies
            with patch('agents.memory.graph_memory.create_client'), \
                 patch('agents.memory.graph_memory.OpenAIEmbeddings'), \
                 patch('agents.tools.tavily_tools.TavilyClient'), \
                 patch('agents.tools.github_tools.Github'):

                await agents.initialize()

                # Mock GitHub operations
                agents.github_tools.create_branch = AsyncMock(return_value=True)
                agents.github_tools.create_file = AsyncMock(return_value=True)
                agents.github_tools.create_pull_request = AsyncMock(return_value=Mock(
                    number=789,
                    title="Automated: API Implementation",
                    url="https://github.com/test/pr/789"
                ))

                # Test the workflow
                result = await agents.create_task(
                    task_type=AgentType.DEVOPS,
                    description="Create a RESTful API for user management",
                    parameters={
                        "requirements": "CRUD operations for users",
                        "file_type": "python",
                        "repo": "test-repo"
                    }
                )

                assert "Code Generated and PR Created" in result
                assert "#789" in result
                assert "https://github.com/test/pr/789" in result

                await agents.cleanup()

    @pytest.mark.asyncio
    async def test_daily_briefing_workflow(self, mock_env_vars):
        """Test daily morning briefing workflow."""
        with patch.dict(os.environ, mock_env_vars):
            agents = AutoAdminAgents()

            # Mock dependencies
            with patch('agents.memory.graph_memory.create_client'), \
                 patch('agents.memory.graph_memory.OpenAIEmbeddings'), \
                 patch('agents.tools.tavily_tools.TavilyClient'), \
                 patch('agents.tools.github_tools.Github'):

                await agents.initialize()

                # Mock proactive analysis
                with patch.object(agents, 'process_message') as mock_process:
                    mock_process.return_value = {
                        "response": """
                        🌅 **Good Morning, Boss.**

                        💰 **Finance:** All financial systems operational
                        📈 **Marketing:** 3 content campaigns in progress
                        🔧 **Development:** 2 PRs ready for review
                        🔥 **Trends:** AI automation and remote work tools trending

                        **What should we execute today?**
                        """,
                        "session_id": "test-session-123"
                    }

                    result = await agents.run_proactive_analysis()

                    assert "Good Morning, Boss" in result["response"]
                    assert "Finance" in result["response"]
                    assert "Marketing" in result["response"]
                    assert "Development" in result["response"]
                    assert "Trends" in result["response"]

                await agents.cleanup()