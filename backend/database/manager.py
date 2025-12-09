"""
Database Manager - Coordinates all database systems for AutoAdmin
Manages PostgreSQL, Redis, Qdrant, and Neo4j connections and operations
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .postgres import PostgreSQLDatabase
from .redis import RedisManager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Central database manager for AutoAdmin"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Database instances
        self.postgres: Optional[PostgreSQLDatabase] = None
        self.redis: Optional[RedisManager] = None

        # Configuration
        self.postgres_config = config.get("postgres", {})
        self.redis_config = config.get("redis", {})

        self.is_initialized = False

    async def initialize(self):
        """Initialize all database connections"""
        try:
            self.logger.info("Initializing database manager...")

            # Initialize PostgreSQL
            if self.postgres_config.get("enabled", True):
                postgres_url = self.postgres_config.get(
                    "connection_string",
                    "postgresql+asyncpg://autoadmin:autoadmin123@localhost:5433/autoadmin"
                )
                self.postgres = PostgreSQLDatabase(postgres_url)
                postgres_ok = await self.postgres.initialize()
                if postgres_ok:
                    self.logger.info("PostgreSQL initialized successfully")
                else:
                    self.logger.error("Failed to initialize PostgreSQL")

            # Initialize Redis
            if self.redis_config.get("enabled", True):
                self.redis = RedisManager(
                    host=self.redis_config.get("host", "localhost"),
                    port=self.redis_config.get("port", 6380),
                    password=self.redis_config.get("password", "redis123")
                )
                redis_ok = await self.redis.initialize()
                if redis_ok:
                    self.logger.info("Redis initialized successfully")
                else:
                    self.logger.error("Failed to initialize Redis")

            self.is_initialized = True
            self.logger.info("Database manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize database manager: {e}")
            return False

    async def close(self):
        """Close all database connections"""
        try:
            if self.postgres:
                await self.postgres.close()
                self.logger.info("PostgreSQL connection closed")

            if self.redis:
                await self.redis.close()
                self.logger.info("Redis connection closed")

            self.is_initialized = False
            self.logger.info("Database manager closed")

        except Exception as e:
            self.logger.error(f"Error closing database manager: {e}")

    # ===== UNIFIED OPERATIONS =====

    async def create_agent_task(self, task_data: Dict[str, Any]) -> Optional[str]:
        """Create a task and store in multiple databases"""
        if not self.is_initialized:
            return None

        task_id = None

        try:
            # Store in PostgreSQL for persistence
            if self.postgres:
                task = await self.postgres.create_task(task_data)
                if task:
                    task_id = str(task.id)

            # Store in Redis for fast access
            if self.redis and task_id:
                cache_key = f"task:{task_id}"
                await self.redis.set_cache(cache_key, task_data, ttl_seconds=3600)

            # Add to task queue if assigned
            if self.redis and task_id and task_data.get("task_status") == "pending":
                queue_name = f"queue:{task_data.get('assigned_agent', 'general')}"
                task_data["id"] = task_id
                await self.redis.enqueue_task(queue_name, task_data)

            # Log to metrics
            if self.redis:
                await self.redis.increment_metric("tasks_created")
                if task_data.get("assigned_agent"):
                    await self.redis.increment_metric(f"tasks_{task_data['assigned_agent']}")

            self.logger.info(f"Created agent task: {task_id}")
            return task_id

        except Exception as e:
            self.logger.error(f"Failed to create agent task: {e}")
            return None

    async def get_agent_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task from cache or database"""
        if not self.is_initialized:
            return None

        try:
            # Try Redis cache first
            if self.redis:
                cache_key = f"task:{task_id}"
                cached_task = await self.redis.get_cache(cache_key)
                if cached_task:
                    return cached_task

            # Fallback to PostgreSQL
            if self.postgres:
                task = await self.postgres.get_task(task_id)
                if task:
                    task_dict = task.to_dict()

                    # Cache for future requests
                    if self.redis:
                        cache_key = f"task:{task_id}"
                        await self.redis.set_cache(cache_key, task_dict, ttl_seconds=1800)

                    return task_dict

            return None

        except Exception as e:
            self.logger.error(f"Failed to get agent task {task_id}: {e}")
            return None

    async def create_agent_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Create agent session"""
        if not self.is_initialized:
            return False

        try:
            # Store in PostgreSQL
            postgres_ok = True
            if self.postgres:
                session = await self.postgres.create_session(session_id, user_id)
                postgres_ok = session is not None

            # Store in Redis for session management
            redis_ok = True
            if self.redis:
                redis_ok = await self.redis.create_session(session_id, user_id)

            success = postgres_ok and redis_ok
            if success:
                # Log metric
                await self.redis.increment_metric("sessions_created")
                self.logger.info(f"Created agent session: {session_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to create agent session {session_id}: {e}")
            return False

    async def get_agent_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get agent session"""
        if not self.is_initialized:
            return None

        try:
            # Try Redis first (faster)
            if self.redis:
                session = await self.redis.get_session(session_id)
                if session:
                    # Update activity
                    await self.redis.update_session_activity(session_id)
                    return session

            # Fallback to PostgreSQL
            if self.postgres:
                session = await self.postgres.get_session(session_id)
                if session:
                    session_dict = session.to_dict()

                    # Cache in Redis for future access
                    if self.redis:
                        await self.redis.create_session(session_id, session.user_id)
                        # Update activity
                        await self.redis.update_session_activity(session_id)

                    return session_dict

            return None

        except Exception as e:
            self.logger.error(f"Failed to get agent session {session_id}: {e}")
            return None

    async def store_agent_memory(self, agent_type: str, memory_data: Dict[str, Any]) -> bool:
        """Store agent memory in multiple systems"""
        if not self.is_initialized:
            return False

        try:
            # Store in PostgreSQL for persistence
            postgres_ok = True
            if self.postgres:
                memory = await self.postgres.store_memory(memory_data)
                postgres_ok = memory is not None

            # Cache in Redis for fast access
            redis_ok = True
            if self.redis:
                cache_key = f"memory:{agent_type}:{memory_data.get('title', 'unknown')}"
                await self.redis.set_cache(cache_key, memory_data, ttl_seconds=7200)  # 2 hours

            success = postgres_ok and redis_ok
            if success:
                await self.redis.increment_metric(f"memories_{agent_type}")
                self.logger.info(f"Stored {agent_type} agent memory")

            return success

        except Exception as e:
            self.logger.error(f"Failed to store agent memory: {e}")
            return False

    async def search_agent_memories(self, agent_type: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search agent memories"""
        if not self.is_initialized:
            return []

        try:
            # Try Redis search first
            if self.redis:
                # Use Redis scan for simple keyword search
                memories = await self.redis.search_memories(agent_type, query, limit)
                if memories:
                    return [memory.to_dict() for memory in memories]

            # Fallback to PostgreSQL
            if self.postgres:
                memories = await self.postgres.search_memories(agent_type, query, limit)
                return [memory.to_dict() for memory in memories]

            return []

        except Exception as e:
            self.logger.error(f"Failed to search agent memories: {e}")
            return []

    async def update_agent_state(self, agent_type: str, state: Dict[str, Any]) -> bool:
        """Update agent state in real-time"""
        if not self.is_initialized:
            return False

        try:
            # Update in Redis for real-time access
            if self.redis:
                # Add timestamp
                state["last_updated"] = datetime.utcnow().isoformat()
                success = await self.redis.set_agent_state(agent_type, state)

                if success:
                    # Update heartbeat
                    await self.redis.update_agent_heartbeat(agent_type)
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to update agent state {agent_type}: {e}")
            return False

    async def get_agent_state(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get current agent state"""
        if not self.is_initialized:
            return None

        try:
            # Get from Redis (real-time state)
            if self.redis:
                state = await self.redis.get_agent_state(agent_type)
                if state:
                    return state

            return None

        except Exception as e:
            self.logger.error(f"Failed to get agent state {agent_type}: {e}")
            return None

    async def record_agent_metric(self, agent_type: str, metric_name: str, value: float, unit: str = "") -> bool:
        """Record agent performance metric"""
        if not self.is_initialized:
            return False

        try:
            # Store in PostgreSQL
            postgres_ok = True
            if self.postgres:
                metric_data = {
                    "agent_type": agent_type,
                    "metric_type": "performance",
                    "metric_name": metric_name,
                    "value": value,
                    "unit": unit,
                    "time_period": "realtime"
                }
                metric = await self.postgres.record_metric(metric_data)
                postgres_ok = metric is not None

            # Store in Redis for real-time metrics
            redis_ok = True
            if self.redis:
                redis_metric_name = f"{agent_type}_{metric_name}"
                await self.redis.increment_metric(redis_metric_name, value)

            return postgres_ok and redis_ok

        except Exception as e:
            self.logger.error(f"Failed to record agent metric: {e}")
            return False

    async def get_agent_metrics(self, agent_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get agent metrics"""
        if not self.is_initialized:
            return []

        try:
            metrics = []

            # Get from PostgreSQL
            if self.postgres:
                postgres_metrics = await self.postgres.get_metrics(agent_type, limit=limit)
                metrics.extend([metric.to_dict() for metric in postgres_metrics])

            # Get from Redis (real-time)
            if self.redis:
                # This would need to be expanded to get specific Redis metrics
                pass

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get agent metrics: {e}")
            return []

    # ===== HEALTH AND STATUS =====

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all databases"""
        health_status = {
            "overall_status": "healthy",
            "databases": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Check PostgreSQL
            if self.postgres:
                postgres_health = await self.postgres.health_check()
                health_status["databases"]["postgres"] = postgres_health
                if postgres_health.get("status") != "healthy":
                    health_status["overall_status"] = "degraded"

            # Check Redis
            if self.redis:
                redis_health = await self.redis.health_check()
                health_status["databases"]["redis"] = redis_health
                if redis_health.get("status") != "healthy":
                    health_status["overall_status"] = "degraded"

            # Check initialization status
            health_status["initialized"] = self.is_initialized
            health_status["database_count"] = len([db for db in [self.postgres, self.redis] if db])

            return health_status

        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            health_status["overall_status"] = "unhealthy"
            health_status["error"] = str(e)
            return health_status

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        if not self.is_initialized:
            return {"error": "Database manager not initialized"}

        stats = {
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Get PostgreSQL stats
            if self.postgres:
                postgres_health = await self.postgres.health_check()
                stats["postgres"] = postgres_health.get("tables", {})

            # Get Redis stats
            if self.redis:
                redis_health = await self.redis.health_check()
                stats["redis"] = {
                    "connected_clients": redis_health.get("connected_clients"),
                    "used_memory": redis_health.get("used_memory"),
                    "uptime_seconds": redis_health.get("uptime_in_seconds"),
                }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        default_config = {
            "postgres": {
                "enabled": True,
                "connection_string": "postgresql+asyncpg://autoadmin:autoadmin123@localhost:5433/autoadmin"
            },
            "redis": {
                "enabled": True,
                "host": "localhost",
                "port": 6380,
                "password": "redis123"
            }
        }
        _db_manager = DatabaseManager(config or default_config)
        await _db_manager.initialize()
    return _db_manager


async def close_database_manager():
    """Close global database manager"""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None