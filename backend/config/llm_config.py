"""
LLM Configuration Module
Handles configuration for various LLM providers including Algion API
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class LLMConfig:
    """Configuration class for LLM providers"""

    def __init__(self):
        # Load environment variables
        load_dotenv()
        load_dotenv('.env.algion')

        # Algion/OpenAI configuration
        self.api_key = os.getenv("ALGION_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("ALGION_BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.algion.dev/v1")
        self.model = os.getenv("ALGION_MODEL") or os.getenv("LLM_MODEL", "gpt-4o")

        # Default parameters
        self.default_temperature = 0.7
        self.default_max_tokens = 2000

        # Validate configuration
        self.validate_config()

        logger.info(f"LLM Config initialized - Model: {self.model}, Base URL: {self.base_url}")

    def validate_config(self):
        """Validate the LLM configuration"""
        if not self.api_key:
            raise ValueError("LLM API key not found in environment variables")

        if not self.base_url:
            raise ValueError("LLM base URL not configured")

        if not self.model:
            raise ValueError("LLM model not specified")

    def get_openai_config(self) -> Dict[str, Any]:
        """Get configuration for OpenAI-compatible API (including Algion)"""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.default_temperature,
            "max_tokens": self.default_max_tokens
        }

    def get_langchain_config(self) -> Dict[str, Any]:
        """Get configuration for LangChain ChatOpenAI"""
        return {
            "openai_api_key": self.api_key,
            "openai_api_base": self.base_url,
            "model": self.model,
            "temperature": self.default_temperature,
            "max_tokens": self.default_max_tokens
        }

    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Get agent-specific configuration"""
        base_config = self.get_langchain_config()

        # Agent-specific adjustments
        if agent_type.lower() == "ceo":
            base_config.update({
                "temperature": 0.3,  # More deterministic for CEO decisions
                "max_tokens": 1500
            })
        elif agent_type.lower() == "strategy":
            base_config.update({
                "temperature": 0.2,  # More analytical for strategy
                "max_tokens": 2500
            })
        elif agent_type.lower() == "devops":
            base_config.update({
                "temperature": 0.1,  # Very precise for technical tasks
                "max_tokens": 2000
            })

        # Add any additional keys from environment
        base_config["tavily_api_key"] = os.getenv("TAVILY_API_KEY")

        return base_config


# Global LLM configuration instance
llm_config = LLMConfig()