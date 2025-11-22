"""
FastAPI router modules for AutoAdmin Backend
Organized by service domain with clear separation of concerns
"""

from . import (
    health,
    monitoring,
    agents,
    ai,
    memory,
    tasks,
    webhooks,
    files,
)

__all__ = [
    "health",
    "monitoring",
    "agents",
    "ai",
    "memory",
    "tasks",
    "webhooks",
    "files",
]