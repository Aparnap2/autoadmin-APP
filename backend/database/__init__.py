"""
Database layer for AutoAdmin
Handles PostgreSQL, Redis, Qdrant (vector), and Neo4j (graph) databases
"""

from .postgres import PostgreSQLDatabase, get_database, close_database
from .redis import RedisManager, get_redis, close_redis
from .models import Base, AgentTask, AgentSession, AgentMemory, AgentMetrics
from .manager import DatabaseManager

__all__ = [
    "PostgreSQLDatabase",
    "RedisManager",
    "DatabaseManager",
    "Base",
    "AgentTask",
    "AgentSession",
    "AgentMemory",
    "AgentMetrics",
    "get_database",
    "close_database",
    "get_redis",
    "close_redis",
]