"""
FastAPI router modules for AutoAdmin Backend
Organized by service domain with clear separation of concerns
"""

from . import (
    health,
    monitoring,
    # agents,  # Temporarily disabled
    # ai,  # Temporarily disabled
    # memory,  # Temporarily disabled
    # tasks,  # Temporarily disabled
    # webhooks,  # Temporarily disabled
    # files,  # Temporarily disabled
    # github,  # Temporarily disabled due to circular import
    # notifications,  # Temporarily disabled
)

__all__ = [
    "health",
    "monitoring",
    # "agents",  # Temporarily disabled
    # "ai",  # Temporarily disabled
    # "memory",  # Temporarily disabled
    # "tasks",  # Temporarily disabled
    # "webhooks",  # Temporarily disabled
    # "files",  # Temporarily disabled
    # "github",  # Temporarily disabled due to circular import
    # "notifications",  # Temporarily disabled
]
