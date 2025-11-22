"""
Pydantic models for AutoAdmin FastAPI Backend
Comprehensive data models for API validation and serialization
"""

from .agent import (
    AgentType,
    AgentStatus,
    AgentCapabilities,
    AgentConfig,
    AgentRequest,
    AgentResponse,
    AgentTask,
    AgentTaskRequest,
    AgentTaskResponse,
    AgentStatusResponse,
    AgentListResponse
)

from .ai import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    VectorSearchRequest,
    VectorSearchResult,
    VectorSearchResponse,
    LLMProvider,
    ModelConfig,
    CompletionRequest,
    CompletionResponse
)

from .memory import (
    MemoryNode,
    MemoryEdge,
    MemoryGraph,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryCreateRequest,
    MemoryCreateResponse,
    MemoryUpdateRequest,
    MemoryUpdateResponse,
    MemoryDeleteRequest,
    MemoryDeleteResponse
)

from .task import (
    Task,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TaskPriority,
    TaskType,
    TaskListResponse,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskBulkRequest,
    TaskBulkResponse
)

from .webhook import (
    WebhookEvent,
    WebhookPayload,
    WebhookResponse,
    WebhookConfig,
    WebhookSubscription,
    GitHubEvent,
    HubSpotEvent,
    CustomEvent
)

from .file import (
    FileUploadRequest,
    FileUploadResponse,
    FileDownloadRequest,
    FileDownloadResponse,
    FileMetadata,
    FileListResponse,
    FileDeleteRequest,
    FileDeleteResponse
)

from .common import (
    BaseResponse,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
    PaginatedResponse,
    SortOrder,
    DateRange
)

__all__ = [
    # Agent models
    "AgentType",
    "AgentStatus",
    "AgentCapabilities",
    "AgentConfig",
    "AgentRequest",
    "AgentResponse",
    "AgentTask",
    "AgentTaskRequest",
    "AgentTaskResponse",
    "AgentStatusResponse",
    "AgentListResponse",

    # AI/LLM models
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "VectorSearchRequest",
    "VectorSearchResult",
    "VectorSearchResponse",
    "LLMProvider",
    "ModelConfig",
    "CompletionRequest",
    "CompletionResponse",

    # Memory models
    "MemoryNode",
    "MemoryEdge",
    "MemoryGraph",
    "MemoryQueryRequest",
    "MemoryQueryResponse",
    "MemoryCreateRequest",
    "MemoryCreateResponse",
    "MemoryUpdateRequest",
    "MemoryUpdateResponse",
    "MemoryDeleteRequest",
    "MemoryDeleteResponse",

    # Task models
    "Task",
    "TaskRequest",
    "TaskResponse",
    "TaskStatus",
    "TaskPriority",
    "TaskType",
    "TaskListResponse",
    "TaskCreateRequest",
    "TaskUpdateRequest",
    "TaskBulkRequest",
    "TaskBulkResponse",

    # Webhook models
    "WebhookEvent",
    "WebhookPayload",
    "WebhookResponse",
    "WebhookConfig",
    "WebhookSubscription",
    "GitHubEvent",
    "HubSpotEvent",
    "CustomEvent",

    # File models
    "FileUploadRequest",
    "FileUploadResponse",
    "FileDownloadRequest",
    "FileDownloadResponse",
    "FileMetadata",
    "FileListResponse",
    "FileDeleteRequest",
    "FileDeleteResponse",

    # Common models
    "BaseResponse",
    "ErrorResponse",
    "HealthResponse",
    "MetricsResponse",
    "PaginatedResponse",
    "SortOrder",
    "DateRange",
]