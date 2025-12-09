"""
Configuration management for AutoAdmin FastAPI Backend
Uses Pydantic Settings for environment-based configuration with validation
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support
    All configuration is loaded from environment variables with sensible defaults
    """

    class Config:
        extra = "ignore"  # Allow extra fields from .env file

    # Application Settings
    APP_NAME: str = "AutoAdmin API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=True, description="Enable auto-reload for development")

    # Security Settings
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        description="Secret key for JWT token signing",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"], description="List of allowed CORS origins"
    )

    # Database Settings
    DATABASE_URL: Optional[str] = Field(
        default=None, description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(
        default=10, description="Database connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=20, description="Database connection max overflow"
    )

    # Redis Settings (for Celery and caching)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for Celery and caching",
    )
    REDIS_CACHE_TTL: int = Field(default=3600, description="Redis cache TTL in seconds")

    # Celery Settings
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )
    CELERY_TASK_SERIALIZER: str = Field(
        default="json", description="Celery task serializer"
    )
    CELERY_RESULT_SERIALIZER: str = Field(
        default="json", description="Celery result serializer"
    )

    # Firebase Settings
    FIREBASE_PROJECT_ID: str = Field(description="Firebase project ID", min_length=1)
    FIREBASE_CLIENT_EMAIL: str = Field(
        description="Firebase service account client email", min_length=1
    )
    FIREBASE_PRIVATE_KEY: str = Field(
        description="Firebase service account private key", min_length=1
    )
    FIREBASE_DATABASE_URL: Optional[str] = Field(
        default=None, description="Firebase realtime database URL"
    )
    FIREBASE_STORAGE_BUCKET: Optional[str] = Field(
        default=None, description="Firebase storage bucket name"
    )

    # OpenAI Settings
    OPENAI_API_KEY: str = Field(description="OpenAI API key", min_length=1)
    OPENAI_MODEL: str = Field(
        default="gpt-4-turbo-preview", description="Default OpenAI model"
    )
    OPENAI_MAX_TOKENS: int = Field(default=4096, description="Maximum OpenAI tokens")
    OPENAI_TEMPERATURE: float = Field(
        default=0.7, description="OpenAI temperature", ge=0.0, le=2.0
    )

    # LangGraph Settings
    LANGCHAIN_API_KEY: Optional[str] = Field(
        default=None, description="LangChain API key for tracing"
    )
    LANGCHAIN_PROJECT: str = Field(
        default="autoadmin-backend", description="LangChain project name"
    )
    LANGCHAIN_TRACING_V2: bool = Field(
        default=False, description="Enable LangChain tracing"
    )

    # Agent Settings
    MAX_CONCURRENT_AGENTS: int = Field(
        default=5, description="Maximum concurrent agents", ge=1, le=50
    )
    AGENT_TIMEOUT: int = Field(
        default=300, description="Agent timeout in seconds", ge=30
    )
    MAX_RETRIES: int = Field(
        default=3, description="Maximum retry attempts", ge=0, le=10
    )

    # File Upload Settings
    MAX_FILE_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum file upload size in bytes",
    )
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=[
            "text/plain",
            "application/pdf",
            "application/json",
            "text/csv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ],
        description="Allowed file MIME types for upload",
    )
    UPLOAD_DIR: str = Field(default="./uploads", description="File upload directory")

    # Logging Settings
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Application log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_FORMAT: str = Field(default="json", description="Log format (json, text)")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")

    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(
        default=100, description="Rate limit requests per window"
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # External Service Settings
    GITHUB_TOKEN: Optional[str] = Field(
        default=None, description="GitHub personal access token"
    )
    GITHUB_REPO: Optional[str] = Field(
        default=None, description="GitHub repository (owner/repo)"
    )
    TAVILY_API_KEY: Optional[str] = Field(
        default=None, description="Tavily search API key"
    )

    # Monitoring Settings
    ENABLE_METRICS: bool = Field(default=True, description="Enable application metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")

    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment value"""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"ENVIRONMENT must be one of: {valid_environments}")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level value"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()

    @validator("FIREBASE_PRIVATE_KEY")
    def validate_firebase_private_key(cls, v):
        """Validate and format Firebase private key"""
        if v and not v.startswith("-----BEGIN PRIVATE KEY-----"):
            # Convert escaped newlines to actual newlines
            return v.replace("\\n", "\n")
        return v

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from comma-separated string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_allowed_file_types(cls, v):
        """Parse ALLOWED_FILE_TYPES from comma-separated string or list"""
        if isinstance(v, str):
            return [file_type.strip() for file_type in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT == "development"

    class Config:
        env_file = ".env.test"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
