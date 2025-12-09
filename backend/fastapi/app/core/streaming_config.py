"""
Streaming Configuration for AutoAdmin Backend
Configures HTTP-only communication without WebSocket dependencies
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class StreamingConfig(BaseSettings):
    """
    Configuration for HTTP-only streaming (no WebSockets)
    Replaces WebSocket functionality with HTTP-based alternatives
    """

    # General streaming settings
    enable_websockets: bool = Field(default=False, env="ENABLE_WEBSOCKETS")
    enable_http_streaming: bool = Field(default=True, env="ENABLE_HTTP_STREAMING")
    enable_long_polling: bool = Field(default=True, env="ENABLE_LONG_POLLING")
    enable_server_sent_events: bool = Field(default=True, env="ENABLE_SSE")

    # Connection management
    max_concurrent_connections: int = Field(default=1000, env="MAX_CONCURRENT_CONNECTIONS")
    connection_timeout: int = Field(default=300, env="CONNECTION_TIMEOUT")  # 5 minutes
    ping_interval: int = Field(default=30, env="PING_INTERVAL")  # 30 seconds

    # Long polling settings
    max_poll_timeout: int = Field(default=60, env="MAX_POLL_TIMEOUT")  # 60 seconds
    poll_cleanup_interval: int = Field(default=300, env="POLL_CLEANUP_INTERVAL")  # 5 minutes
    max_pending_events: int = Field(default=10000, env="MAX_PENDING_EVENTS")

    # Event management
    event_history_size: int = Field(default=100, env="EVENT_HISTORY_SIZE")
    event_ttl: int = Field(default=3600, env="EVENT_TTL")  # 1 hour
    max_event_size: int = Field(default=1024 * 1024, env="MAX_EVENT_SIZE")  # 1MB

    # Performance settings
    enable_connection_tracking: bool = Field(default=True, env="ENABLE_CONNECTION_TRACKING")
    enable_health_monitoring: bool = Field(default=True, env="ENABLE_HEALTH_MONITORING")
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")

    # Fallback settings
    enable_offline_mode: bool = Field(default=True, env="ENABLE_OFFLINE_MODE")
    fallback_to_polling: bool = Field(default=True, env="FALLBACK_TO_POLLING")
    enable_circuit_breaker: bool = Field(default=True, env="ENABLE_CIRCUIT_BREAKER")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_configuration()
        self._log_configuration()

    def _validate_configuration(self):
        """Validate streaming configuration"""

        # Ensure WebSockets are disabled
        if self.enable_websockets:
            logger.warning("⚠️  WebSockets are enabled but not recommended for production")
            logger.warning("  Consider setting ENABLE_WEBSOCKETS=false for HTTP-only communication")
        else:
            logger.info("✅ WebSockets disabled - using HTTP-only communication")

        # Validate HTTP streaming settings
        if not self.enable_http_streaming and not self.enable_long_polling:
            raise ValueError("At least one of HTTP streaming or long polling must be enabled")

        # Validate connection limits
        if self.max_concurrent_connections < 1:
            raise ValueError("MAX_CONCURRENT_CONNECTIONS must be >= 1")

        if self.connection_timeout < 30:
            logger.warning("Connection timeout < 30 seconds may cause frequent disconnections")

        # Validate polling settings
        if self.max_poll_timeout < 5:
            logger.warning("Max poll timeout < 5 seconds may not be useful")
        elif self.max_poll_timeout > 300:
            logger.warning("Max poll timeout > 300 seconds may cause server issues")

    def _log_configuration(self):
        """Log streaming configuration"""
        logger.info("🌊 HTTP Streaming Configuration:")
        logger.info(f"  HTTP Streaming: {self.enable_http_streaming}")
        logger.info(f"  Server-Sent Events: {self.enable_server_sent_events}")
        logger.info(f"  Long Polling: {self.enable_long_polling}")
        logger.info(f"  Max Connections: {self.max_concurrent_connections}")
        logger.info(f"  Connection Timeout: {self.connection_timeout}s")
        logger.info(f"  Poll Timeout: {self.max_poll_timeout}s")

    def is_websocket_replacement_enabled(self) -> bool:
        """Check if WebSocket replacement features are enabled"""
        return (self.enable_http_streaming or
                self.enable_server_sent_events or
                self.enable_long_polling)

    def get_streaming_features(self) -> Dict[str, bool]:
        """Get all streaming feature statuses"""
        return {
            "websockets": self.enable_websockets,
            "http_streaming": self.enable_http_streaming,
            "server_sent_events": self.enable_server_sent_events,
            "long_polling": self.enable_long_polling,
            "connection_tracking": self.enable_connection_tracking,
            "health_monitoring": self.enable_health_monitoring,
            "rate_limiting": self.enable_rate_limiting,
            "offline_mode": self.enable_offline_mode,
            "circuit_breaker": self.enable_circuit_breaker
        }

    def get_endpoints_configuration(self) -> Dict[str, Any]:
        """Get endpoint configuration for WebSocket replacements"""
        return {
            "streaming_endpoints": {
                "sse_connect": "/api/v1/streaming/connect",
                "sse_events": "/api/v1/streaming/events/{client_id}",
                "chat_streaming": "/api/v1/streaming/chat/stream/{agent_type}"
            } if self.enable_server_sent_events else None,
            "polling_endpoints": {
                "create_session": "/api/v1/streaming/polling/session",
                "poll_events": "/api/v1/streaming/polling/poll",
                "remove_session": "/api/v1/streaming/polling/session/{session_id}"
            } if self.enable_long_polling else None,
            "notification_endpoints": {
                "send_notification": "/api/v1/streaming/events/notify",
                "agent_status": "/api/v1/streaming/events/agent-status",
                "task_progress": "/api/v1/streaming/events/task-progress"
            },
            "monitoring_endpoints": {
                "status": "/api/v1/streaming/status",
                "health": "/api/v1/streaming/health"
            }
        }

    def get_replacement_guide(self) -> Dict[str, Any]:
        """Get WebSocket replacement guide"""
        return {
            "websocket_replacements": {
                "real_time_updates": {
                    "original": "WebSocket messages",
                    "replacement": "Server-Sent Events (SSE)",
                    "endpoint": "/api/v1/streaming/events/{client_id}",
                    "implementation": "HTTP streaming with persistent connections"
                },
                "bidirectional_communication": {
                    "original": "WebSocket send/receive",
                    "replacement": "HTTP requests + SSE responses",
                    "endpoints": {
                        "send": "POST /api/v1/streaming/events/notify",
                        "receive": "GET /api/v1/streaming/events/{client_id}"
                    },
                    "implementation": "HTTP for sending, SSE for receiving"
                },
                "connection_management": {
                    "original": "WebSocket connections",
                    "replacement": "HTTP connection tracking",
                    "endpoint": "/api/v1/streaming/connect",
                    "implementation": "Connection IDs and session management"
                },
                "real_time_chat": {
                    "original": "WebSocket chat rooms",
                    "replacement": "HTTP chat with streaming responses",
                    "endpoint": "/api/v1/streaming/chat/stream/{agent_type}",
                    "implementation": "HTTP requests with streaming responses"
                }
            },
            "performance_considerations": {
                "latency": "SSE provides low-latency updates similar to WebSockets",
                "scalability": "HTTP servers can handle more connections than WebSocket servers",
                "reliability": "HTTP connections are more reliable through firewalls/proxies",
                "fallback": "System automatically falls back to polling if streaming fails"
            },
            "configuration_options": {
                "disable_websockets": {
                    "env_var": "ENABLE_WEBSOCKETS=false",
                    "description": "Completely disable WebSocket support"
                },
                "enable_http_streaming": {
                    "env_var": "ENABLE_HTTP_STREAMING=true",
                    "description": "Enable HTTP-based streaming"
                },
                "long_polling_fallback": {
                    "env_var": "FALLBACK_TO_POLLING=true",
                    "description": "Fall back to long polling if streaming fails"
                }
            }
        }


# Create global configuration instance
streaming_config = StreamingConfig()


def get_streaming_config() -> StreamingConfig:
    """Get streaming configuration singleton"""
    return streaming_config


# Environment-specific configurations
def get_development_config() -> StreamingConfig:
    """Get development-specific streaming configuration"""
    return StreamingConfig(
        enable_websockets=False,
        enable_http_streaming=True,
        enable_long_polling=True,
        max_concurrent_connections=100,
        connection_timeout=180,  # 3 minutes
        max_poll_timeout=30,  # 30 seconds
        enable_health_monitoring=True
    )


def get_production_config() -> StreamingConfig:
    """Get production-specific streaming configuration"""
    return StreamingConfig(
        enable_websockets=False,
        enable_http_streaming=True,
        enable_long_polling=True,
        max_concurrent_connections=5000,
        connection_timeout=300,  # 5 minutes
        max_poll_timeout=60,  # 60 seconds
        enable_circuit_breaker=True,
        enable_rate_limiting=True,
        enable_health_monitoring=True
    )


def get_testing_config() -> StreamingConfig:
    """Get testing-specific streaming configuration"""
    return StreamingConfig(
        enable_websockets=False,
        enable_http_streaming=True,
        enable_long_polling=True,
        max_concurrent_connections=10,
        connection_timeout=30,  # 30 seconds
        max_poll_timeout=5,  # 5 seconds
        event_history_size=20
    )


# Export for use in other modules
__all__ = [
    'StreamingConfig',
    'get_streaming_config',
    'get_development_config',
    'get_production_config',
    'get_testing_config'
]