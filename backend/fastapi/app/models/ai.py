"""
AI/LLM related Pydantic models for API validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from .common import BaseResponse, PaginatedResponse


class LLMProvider(str, Enum):
    """LLM provider enumeration"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    AZURE_OPENAI = "azure_openai"
    GOOGLE_AI = "google_ai"
    LOCAL = "local"


class ModelType(str, Enum):
    """Model type enumeration"""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_GENERATION = "audio_generation"


class ChatMessage(BaseModel):
    """Chat message model"""

    role: str = Field(description="Message role (system, user, assistant)")
    content: str = Field(description="Message content")
    name: Optional[str] = Field(default=None, description="Optional message name")
    function_call: Optional[Dict[str, Any]] = Field(
        default=None, description="Function call data"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Tool calls data"
    )
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator("role")
    def validate_role(cls, v):
        """Validate message role"""
        valid_roles = ["system", "user", "assistant", "function", "tool"]
        if v not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
        return v


class ModelConfig(BaseModel):
    """Model configuration model"""

    provider: LLMProvider = Field(description="LLM provider")
    model_name: str = Field(description="Model name")
    model_type: ModelType = Field(description="Model type")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens")
    top_p: Optional[float] = Field(
        default=1.0, ge=0.0, le=1.0, description="Nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None, description="Stop sequences"
    )
    stream: bool = Field(default=False, description="Enable streaming")
    response_format: Optional[Dict[str, Any]] = Field(
        default=None, description="Response format"
    )
    tools: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Available tools"
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Tool choice strategy"
    )
    custom_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Custom provider parameters"
    )


class ChatRequest(BaseModel):
    """Chat completion request model"""

    messages: List[ChatMessage] = Field(description="Chat messages")
    ai_model_config: Optional[ModelConfig] = Field(
        default=None, description="Model configuration"
    )
    user: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator("messages")
    def validate_messages(cls, v):
        """Validate that messages list is not empty"""
        if not v:
            raise ValueError("Messages list cannot be empty")
        return v


class ChatResponse(BaseResponse):
    """Chat completion response model"""

    chat_message: ChatMessage = Field(description="Assistant response message")
    model: str = Field(description="Model used")
    usage: Dict[str, int] = Field(description="Token usage information")
    finish_reason: Optional[str] = Field(
        default=None, description="Completion finish reason"
    )
    response_time_ms: float = Field(description="Response time in milliseconds")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CompletionRequest(BaseModel):
    """Text completion request model"""

    prompt: str = Field(description="Completion prompt")
    ai_model_config: Optional[ModelConfig] = Field(
        default=None, description="Model configuration"
    )
    suffix: Optional[str] = Field(default=None, description="Text suffix")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    top_p: Optional[float] = Field(
        default=1.0, ge=0.0, le=1.0, description="Nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None, description="Stop sequences"
    )
    user: Optional[str] = Field(default=None, description="User identifier")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class CompletionResponse(BaseResponse):
    """Text completion response model"""

    text: str = Field(description="Completed text")
    model: str = Field(description="Model used")
    usage: Dict[str, int] = Field(description="Token usage information")
    finish_reason: Optional[str] = Field(
        default=None, description="Completion finish reason"
    )
    response_time_ms: float = Field(description="Response time in milliseconds")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EmbeddingRequest(BaseModel):
    """Embedding generation request model"""

    input: Union[str, List[str]] = Field(description="Input text(s) to embed")
    ai_model_config: Optional[ModelConfig] = Field(
        default=None, description="Model configuration"
    )
    dimensions: Optional[int] = Field(
        default=None, ge=1, description="Embedding dimensions"
    )
    user: Optional[str] = Field(default=None, description="User identifier")
    encoding_format: str = Field(
        default="float", description="Encoding format (float, base64)"
    )

    @validator("encoding_format")
    def validate_encoding_format(cls, v):
        """Validate encoding format"""
        valid_formats = ["float", "base64"]
        if v not in valid_formats:
            raise ValueError(
                f"Invalid encoding format. Must be one of: {valid_formats}"
            )
        return v


class EmbeddingResponse(BaseResponse):
    """Embedding generation response model"""

    embeddings: List[List[float]] = Field(description="Generated embeddings")
    model: str = Field(description="Model used")
    usage: Dict[str, int] = Field(description="Token usage information")
    dimensions: int = Field(description="Embedding dimensions")
    response_time_ms: float = Field(description="Response time in milliseconds")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class VectorSearchRequest(BaseModel):
    """Vector similarity search request model"""

    query: str = Field(description="Search query text")
    query_embedding: Optional[List[float]] = Field(
        default=None, description="Pre-computed query embedding"
    )
    collection: str = Field(default="default", description="Collection to search in")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum results to return"
    )
    threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Similarity threshold"
    )
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    include_metadata: bool = Field(
        default=True, description="Include metadata in results"
    )
    ai_model_config: Optional[ModelConfig] = Field(
        default=None, description="Model configuration for embedding generation"
    )

    @validator("query_embedding")
    def validate_query_embedding(cls, v, values):
        """Validate query embedding dimensions"""
        if v is not None and len(v) == 0:
            raise ValueError("Query embedding cannot be empty")
        return v


class VectorSearchResult(BaseModel):
    """Vector search result model"""

    id: str = Field(description="Document ID")
    content: str = Field(description="Document content")
    similarity: float = Field(ge=0.0, le=1.0, description="Similarity score")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    embedding: Optional[List[float]] = Field(
        default=None, description="Document embedding"
    )


class VectorSearchResponse(BaseResponse):
    """Vector search response model"""

    results: List[VectorSearchResult] = Field(description="Search results")
    total: int = Field(description="Total number of results")
    query_time_ms: float = Field(description="Query time in milliseconds")
    collection: str = Field(description="Searched collection")
    query_embedding_generated: bool = Field(
        description="Whether query embedding was generated"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelStatus(BaseModel):
    """Model status model"""

    provider: LLMProvider = Field(description="LLM provider")
    model_name: str = Field(description="Model name")
    status: str = Field(description="Model status (available, unavailable, error)")
    last_checked: datetime = Field(
        default_factory=datetime.utcnow, description="Last status check"
    )
    response_time_ms: Optional[float] = Field(
        default=None, description="Average response time"
    )
    error_rate: float = Field(default=0.0, description="Error rate (0-1)")
    rate_limit_remaining: Optional[int] = Field(
        default=None, description="Rate limit remaining"
    )
    cost_per_token: Optional[float] = Field(default=None, description="Cost per token")
    capabilities: List[str] = Field(
        default_factory=list, description="Model capabilities"
    )


class ModelListResponse(PaginatedResponse[ModelStatus]):
    """Paginated model list response"""

    pass


class AIUsageMetrics(BaseModel):
    """AI usage metrics model"""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )
    provider: LLMProvider = Field(description="LLM provider")
    model: str = Field(description="Model used")
    total_requests: int = Field(ge=0, description="Total requests")
    total_tokens: int = Field(ge=0, description="Total tokens used")
    total_cost: float = Field(ge=0, description="Total cost")
    average_response_time: float = Field(ge=0, description="Average response time")
    error_rate: float = Field(ge=0.0, le=1.0, description="Error rate")
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate")


class AISettings(BaseModel):
    """AI service settings model"""

    default_provider: LLMProvider = Field(description="Default LLM provider")
    default_model: str = Field(description="Default model name")
    max_tokens_per_request: int = Field(
        default=4096, ge=1, description="Max tokens per request"
    )
    max_requests_per_minute: int = Field(
        default=60, ge=1, description="Max requests per minute"
    )
    cost_limit_per_hour: float = Field(
        default=10.0, ge=0, description="Cost limit per hour"
    )
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(
        default=3600, ge=0, description="Cache TTL in seconds"
    )
    fallback_providers: List[LLMProvider] = Field(
        default_factory=list, description="Fallback providers"
    )
    custom_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Custom settings"
    )
