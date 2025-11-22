"""
Pytest configuration and shared fixtures for the AutoAdmin Backend.

This module provides common test fixtures and configuration for all test modules.
"""

import os
import pytest
from unittest.mock import Mock
from typing import Generator, Dict, Any

from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def load_test_env() -> None:
    """Load test environment variables."""
    # Load test environment variables from .env.test if it exists
    # Otherwise, use the example environment
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env.test")
    if not os.path.exists(env_file):
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env.example")

    if os.path.exists(env_file):
        load_dotenv(env_file)


@pytest.fixture
def mock_openai_client() -> Mock:
    """Create a mock OpenAI client."""
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Test response"))]
    )
    return mock_client


@pytest.fixture
def mock_supabase_client() -> Mock:
    """Create a mock Supabase client."""
    mock_client = Mock()
    mock_client.table.return_value = Mock()
    mock_client.auth.return_value = Mock()
    return mock_client


@pytest.fixture
def mock_github_client() -> Mock:
    """Create a mock GitHub client."""
    mock_client = Mock()
    mock_client.get_user.return_value = Mock()
    mock_client.get_repo.return_value = Mock()
    return mock_client


@pytest.fixture
def test_agent_config() -> Dict[str, Any]:
    """Provide test configuration for agents."""
    return {
        "name": "test_agent",
        "model": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_retries": 3,
        "timeout": 30,
    }


@pytest.fixture
def sample_user_input() -> str:
    """Provide sample user input for testing."""
    return "Create a simple Python script that reads data from a CSV file."


@pytest.fixture
def mock_tavily_client() -> Mock:
    """Create a mock Tavily search client."""
    mock_client = Mock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content",
            }
        ]
    }
    return mock_client