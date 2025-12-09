"""
Redis integration for AutoAdmin
Handles caching, session storage, and real-time data
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis manager for AutoAdmin"""

    def __init__(self, host: str = "localhost", port: int = 6379, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password
        self.redis_client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Redis connection closed")

    # ===== SESSION MANAGEMENT =====

    async def create_session(self, session_id: str, user_id: Optional[str] = None, ttl_hours: int = 24) -> bool:
        """Create a new session"""
        try:
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "is_active": True
            }

            await self.redis_client.setex(
                f"session:{session_id}",
                ttl_hours * 3600,
                json.dumps(session_data)
            )

            # Add to active sessions set
            await self.redis_client.sadd("active_sessions", session_id)

            self.logger.info(f"Created session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create session {session_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            session_data = await self.redis_client.get(f"session:{session_id}")
            if session_data:
                return json.loads(session_data)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity"""
        try:
            session_data = await self.get_session(session_id)
            if session_data:
                session_data["last_activity"] = datetime.utcnow().isoformat()
                await self.redis_client.set(
                    f"session:{session_id}",
                    json.dumps(session_data),
                    ex=86400  # 24 hours TTL
                )
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to update session activity {session_id}: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            await self.redis_client.delete(f"session:{session_id}")
            await self.redis_client.srem("active_sessions", session_id)
            self.logger.info(f"Deleted session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    # ===== AGENT STATE MANAGEMENT =====

    async def set_agent_state(self, agent_type: str, state: Dict[str, Any]) -> bool:
        """Set agent state"""
        try:
            await self.redis_client.hset(
                f"agent_state:{agent_type}",
                mapping={k: json.dumps(v) if not isinstance(v, str) else v for k, v in state.items()}
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to set agent state {agent_type}: {e}")
            return False

    async def get_agent_state(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get agent state"""
        try:
            state_data = await self.redis_client.hgetall(f"agent_state:{agent_type}")
            if state_data:
                # Parse JSON values
                return {k: json.loads(v) if self._is_json(v) else v for k, v in state_data.items()}
            return None

        except Exception as e:
            self.logger.error(f"Failed to get agent state {agent_type}: {e}")
            return None

    async def update_agent_heartbeat(self, agent_type: str) -> bool:
        """Update agent heartbeat"""
        try:
            await self.redis_client.hset(
                f"agent_state:{agent_type}",
                mapping={
                    "last_heartbeat": datetime.utcnow().isoformat(),
                    "status": "active"
                }
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to update agent heartbeat {agent_type}: {e}")
            return False

    # ===== TASK QUEUES =====

    async def enqueue_task(self, queue_name: str, task_data: Dict[str, Any]) -> bool:
        """Add task to queue"""
        try:
            task_json = json.dumps(task_data)
            await self.redis_client.lpush(f"queue:{queue_name}", task_json)
            self.logger.info(f"Enqueued task to {queue_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to enqueue task to {queue_name}: {e}")
            return False

    async def dequeue_task(self, queue_name: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get task from queue (blocking)"""
        try:
            result = await self.redis_client.brpop(f"queue:{queue_name}", timeout)
            if result:
                _, task_json = result
                return json.loads(task_json)
            return None

        except Exception as e:
            self.logger.error(f"Failed to dequeue task from {queue_name}: {e}")
            return None

    async def get_queue_length(self, queue_name: str) -> int:
        """Get queue length"""
        try:
            return await self.redis_client.llen(f"queue:{queue_name}")

        except Exception as e:
            self.logger.error(f"Failed to get queue length {queue_name}: {e}")
            return 0

    # ===== CACHING =====

    async def set_cache(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set cache value"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self.redis_client.setex(f"cache:{key}", ttl_seconds, value)
            return True

        except Exception as e:
            self.logger.error(f"Failed to set cache {key}: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        try:
            value = await self.redis_client.get(f"cache:{key}")
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None

        except Exception as e:
            self.logger.error(f"Failed to get cache {key}: {e}")
            return None

    async def delete_cache(self, key: str) -> bool:
        """Delete cache value"""
        try:
            await self.redis_client.delete(f"cache:{key}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete cache {key}: {e}")
            return False

    # ===== RATE LIMITING =====

    async def check_rate_limit(self, identifier: str, limit: int, window_seconds: int) -> bool:
        """Check if identifier is within rate limit"""
        try:
            key = f"rate_limit:{identifier}"
            current = await self.redis_client.incr(key)

            if current == 1:
                # Set expiration on first request
                await self.redis_client.expire(key, window_seconds)

            return current <= limit

        except Exception as e:
            self.logger.error(f"Failed to check rate limit {identifier}: {e}")
            return True  # Allow if rate limiting fails

    # ===== REAL-TIME EVENTS =====

    async def publish_event(self, channel: str, event_data: Dict[str, Any]) -> bool:
        """Publish event to channel"""
        try:
            await self.redis_client.publish(channel, json.dumps(event_data))
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish event to {channel}: {e}")
            return False

    async def subscribe_to_channel(self, channel: str):
        """Subscribe to channel (returns pubsub object)"""
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            return pubsub

        except Exception as e:
            self.logger.error(f"Failed to subscribe to {channel}: {e}")
            return None

    # ===== METRICS =====

    async def increment_metric(self, metric_name: str, value: float = 1.0) -> bool:
        """Increment metric"""
        try:
            key = f"metric:{metric_name}"
            await self.redis_client.incrbyfloat(key, value)
            # Set expiration to 24 hours if this is a new key
            if await self.redis_client.ttl(key) == -1:
                await self.redis_client.expire(key, 86400)
            return True

        except Exception as e:
            self.logger.error(f"Failed to increment metric {metric_name}: {e}")
            return False

    async def get_metric(self, metric_name: str) -> Optional[float]:
        """Get metric value"""
        try:
            value = await self.redis_client.get(f"metric:{metric_name}")
            return float(value) if value else None

        except Exception as e:
            self.logger.error(f"Failed to get metric {metric_name}: {e}")
            return None

    # ===== HEALTH CHECK =====

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.redis_client:
                return {"status": "disconnected", "error": "Not initialized"}

            # Test connection
            await self.redis_client.ping()

            # Get basic info
            info = await self.redis_client.info()

            return {
                "status": "healthy",
                "connection": "ok",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _is_json(self, string: str) -> bool:
        """Check if string is JSON"""
        try:
            json.loads(string)
            return True
        except json.JSONDecodeError:
            return False


# Global Redis instance
_redis_instance: Optional[RedisManager] = None


async def get_redis() -> RedisManager:
    """Get global Redis instance"""
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = RedisManager(
            host="localhost",
            port=6380,
            password="redis123"
        )
        await _redis_instance.initialize()
    return _redis_instance


async def close_redis():
    """Close global Redis instance"""
    global _redis_instance
    if _redis_instance:
        await _redis_instance.close()
        _redis_instance = None