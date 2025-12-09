"""
PostgreSQL database connection and operations for AutoAdmin
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete

from .models import Base, AgentTask, AgentSession, AgentMemory, AgentMetrics

logger = logging.getLogger(__name__)


class PostgreSQLDatabase:
    """PostgreSQL database manager for AutoAdmin"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.session_factory = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.connection_string,
                echo=False,  # Set to True for SQL logging
                pool_size=20,
                max_overflow=0,
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self.logger.info("PostgreSQL database initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL database: {e}")
            return False

    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("PostgreSQL database connection closed")

    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        return self.session_factory()

    # ===== TASK MANAGEMENT =====

    async def create_task(self, task_data: Dict[str, Any]) -> Optional[AgentTask]:
        """Create a new agent task"""
        try:
            async with self.get_session() as session:
                task = AgentTask(
                    title=task_data.get("title"),
                    description=task_data.get("description"),
                    task_type=task_data.get("task_type"),
                    assigned_agent=task_data.get("assigned_agent"),
                    task_status=task_data.get("task_status", "pending"),
                    priority=task_data.get("priority", "medium"),
                    input_data=task_data.get("input_data"),
                    session_id=task_data.get("session_id"),
                    user_id=task_data.get("user_id"),
                    parent_task_id=task_data.get("parent_task_id"),
                )

                session.add(task)
                await session.commit()
                await session.refresh(task)

                self.logger.info(f"Created task {task.id} for agent {task.assigned_agent}")
                return task

        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            return None

    async def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get a task by ID"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(AgentTask).where(AgentTask.id == task_id)
                )
                return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task"""
        try:
            async with self.get_session() as session:
                stmt = (
                    update(AgentTask)
                    .where(AgentTask.id == task_id)
                    .values(**updates)
                    .returning(AgentTask)
                )

                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount == 0:
                    self.logger.warning(f"Task {task_id} not found")
                    return False

                self.logger.info(f"Updated task {task_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            return False

    async def get_tasks_by_session(self, session_id: str, limit: int = 50) -> List[AgentTask]:
        """Get tasks for a specific session"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(AgentTask)
                    .where(AgentTask.session_id == session_id)
                    .order_by(AgentTask.created_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"Failed to get tasks for session {session_id}: {e}")
            return []

    async def get_tasks_by_agent(self, agent_type: str, status: Optional[str] = None) -> List[AgentTask]:
        """Get tasks for a specific agent"""
        try:
            async with self.get_session() as session:
                query = select(AgentTask).where(AgentTask.assigned_agent == agent_type)

                if status:
                    query = query.where(AgentTask.task_status == status)

                query = query.order_by(AgentTask.created_at.desc())

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"Failed to get tasks for agent {agent_type}: {e}")
            return []

    # ===== SESSION MANAGEMENT =====

    async def create_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[AgentSession]:
        """Create a new agent session"""
        try:
            async with self.get_session() as session:
                agent_session = AgentSession(
                    session_id=session_id,
                    user_id=user_id,
                    agent_preferences={},
                    context={}
                )

                session.add(agent_session)
                await session.commit()
                await session.refresh(agent_session)

                self.logger.info(f"Created session {session_id}")
                return agent_session

        except Exception as e:
            self.logger.error(f"Failed to create session {session_id}: {e}")
            return None

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get a session by ID"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(AgentSession).where(AgentSession.session_id == session_id)
                )
                return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        try:
            return await self.update_session(session_id, {"last_activity": datetime.utcnow()})

        except Exception as e:
            self.logger.error(f"Failed to update session activity {session_id}: {e}")
            return False

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            async with self.get_session() as session:
                stmt = (
                    update(AgentSession)
                    .where(AgentSession.session_id == session_id)
                    .values(**updates)
                    .returning(AgentSession)
                )

                result = await session.execute(stmt)
                await session.commit()

                return result.rowcount > 0

        except Exception as e:
            self.logger.error(f"Failed to update session {session_id}: {e}")
            return False

    # ===== MEMORY MANAGEMENT =====

    async def store_memory(self, memory_data: Dict[str, Any]) -> Optional[AgentMemory]:
        """Store agent memory"""
        try:
            async with self.get_session() as session:
                memory = AgentMemory(
                    agent_type=memory_data.get("agent_type"),
                    memory_type=memory_data.get("memory_type"),
                    title=memory_data.get("title"),
                    content=memory_data.get("content"),
                    memory_metadata=memory_data.get("metadata", {}),
                    importance_score=memory_data.get("importance_score", 1.0),
                    embedding_id=memory_data.get("embedding_id"),
                )

                session.add(memory)
                await session.commit()
                await session.refresh(memory)

                self.logger.info(f"Stored memory {memory.id} for agent {memory.agent_type}")
                return memory

        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            return None

    async def get_memories(self, agent_type: str, memory_type: Optional[str] = None, limit: int = 50) -> List[AgentMemory]:
        """Get memories for an agent"""
        try:
            async with self.get_session() as session:
                query = select(AgentMemory).where(AgentMemory.agent_type == agent_type)

                if memory_type:
                    query = query.where(AgentMemory.memory_type == memory_type)

                query = query.order_by(AgentMemory.importance_score.desc()).limit(limit)

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"Failed to get memories for agent {agent_type}: {e}")
            return []

    async def search_memories(self, agent_type: str, search_term: str, limit: int = 20) -> List[AgentMemory]:
        """Search memories by content"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(AgentMemory)
                    .where(
                        AgentMemory.agent_type == agent_type,
                        AgentMemory.content.ilike(f"%{search_term}%")
                    )
                    .order_by(AgentMemory.importance_score.desc())
                    .limit(limit)
                )
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"Failed to search memories for agent {agent_type}: {e}")
            return []

    # ===== METRICS =====

    async def record_metric(self, metric_data: Dict[str, Any]) -> Optional[AgentMetrics]:
        """Record agent metric"""
        try:
            async with self.get_session() as session:
                metric = AgentMetrics(
                    agent_type=metric_data.get("agent_type"),
                    metric_type=metric_data.get("metric_type"),
                    metric_name=metric_data.get("metric_name"),
                    value=metric_data.get("value"),
                    unit=metric_data.get("unit"),
                    time_period=metric_data.get("time_period"),
                    context=metric_data.get("context", {}),
                )

                session.add(metric)
                await session.commit()
                await session.refresh(metric)

                return metric

        except Exception as e:
            self.logger.error(f"Failed to record metric: {e}")
            return None

    async def get_metrics(self, agent_type: str, metric_type: Optional[str] = None, limit: int = 100) -> List[AgentMetrics]:
        """Get metrics for an agent"""
        try:
            async with self.get_session() as session:
                query = select(AgentMetrics).where(AgentMetrics.agent_type == agent_type)

                if metric_type:
                    query = query.where(AgentMetrics.metric_type == metric_type)

                query = query.order_by(AgentMetrics.recorded_at.desc()).limit(limit)

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"Failed to get metrics for agent {agent_type}: {e}")
            return []

    # ===== HEALTH CHECK =====

    async def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            async with self.get_session() as session:
                # Simple query to test connection
                await session.execute(select(1))

                # Get table counts
                task_count = await session.scalar(select(AgentTask).count())
                session_count = await session.scalar(select(AgentSession).count())
                memory_count = await session.scalar(select(AgentMemory).count())

                return {
                    "status": "healthy",
                    "connection": "ok",
                    "tables": {
                        "tasks": task_count,
                        "sessions": session_count,
                        "memories": memory_count,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global database instance
_db_instance: Optional[PostgreSQLDatabase] = None


async def get_database() -> PostgreSQLDatabase:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        # Use Docker PostgreSQL on port 5433
        connection_string = "postgresql+asyncpg://autoadmin:autoadmin123@localhost:5433/autoadmin"
        _db_instance = PostgreSQLDatabase(connection_string)
        await _db_instance.initialize()
    return _db_instance


async def close_database():
    """Close global database instance"""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None