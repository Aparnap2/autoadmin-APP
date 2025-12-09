"""
Database models for AutoAdmin
SQLAlchemy models for PostgreSQL database
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    CEO = "ceo"
    STRATEGY = "strategy"
    DEVOPS = "devops"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentTask(Base):
    """Tasks performed by agents"""
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(100), nullable=False)  # market_analysis, tech_review, etc.

    # Task assignment
    assigned_agent = Column(String(50), nullable=False)  # ceo, strategy, devops
    task_status = Column(String(50), default=TaskStatus.PENDING)
    priority = Column(String(20), default=TaskPriority.MEDIUM)

    # Task content
    input_data = Column(JSON, nullable=True)  # Original task input
    result_data = Column(JSON, nullable=True)  # Task output/results
    error_message = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Performance metrics
    execution_time_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)

    # Task relationships
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=True)
    subtasks = relationship("AgentTask", foreign_keys=[parent_task_id], backref="parent", remote_side=[id])

    # Session tracking
    session_id = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "assigned_agent": self.assigned_agent,
            "task_status": self.task_status,
            "priority": self.priority,
            "input_data": self.input_data,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
            "tokens_used": self.tokens_used,
            "cost_estimate": self.cost_estimate,
            "parent_task_id": str(self.parent_task_id) if self.parent_task_id else None,
            "session_id": self.session_id,
            "user_id": self.user_id,
        }


class AgentSession(Base):
    """Agent interaction sessions"""
    __tablename__ = "agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)

    # Session metadata
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Session configuration
    agent_preferences = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)  # Session context/history

    # Usage metrics
    total_tasks = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "is_active": self.is_active,
            "agent_preferences": self.agent_preferences,
            "context": self.context,
            "total_tasks": self.total_tasks,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }


class AgentMemory(Base):
    """Long-term memory for agents"""
    __tablename__ = "agent_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Memory categorization
    agent_type = Column(String(50), nullable=False)  # ceo, strategy, devops
    memory_type = Column(String(50), nullable=False)  # learning, pattern, preference

    # Memory content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    memory_metadata = Column(JSON, nullable=True)

    # Memory attributes
    importance_score = Column(Float, default=1.0)  # 1.0-10.0
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)

    # Temporal data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Embeddings for semantic search
    embedding_id = Column(String(100), nullable=True)  # Reference to vector database

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "agent_type": self.agent_type,
            "memory_type": self.memory_type,
            "title": self.title,
            "content": self.content,
            "memory_metadata": self.memory_metadata,
            "importance_score": self.importance_score,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "embedding_id": self.embedding_id,
        }


class AgentMetrics(Base):
    """Performance and usage metrics for agents"""
    __tablename__ = "agent_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric identification
    agent_type = Column(String(50), nullable=False)
    metric_type = Column(String(50), nullable=False)  # performance, usage, cost
    metric_name = Column(String(100), nullable=False)

    # Metric values
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # seconds, tokens, dollars, etc.

    # Temporal data
    recorded_at = Column(DateTime, default=datetime.utcnow)
    time_period = Column(String(20), nullable=True)  # hourly, daily, weekly

    # Additional context
    context = Column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "agent_type": self.agent_type,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "time_period": self.time_period,
            "context": self.context,
        }