"""Short-term memory store using Redis."""

from typing import Optional, Any, List
import json
import logging
from datetime import timedelta
import redis.asyncio as aioredis
from redis.asyncio import Redis
from app.config import settings

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Redis-based short-term memory for active conversations."""

    def __init__(self) -> None:
        """Initialize Redis connection."""
        self.redis: Optional[Redis] = None
        self.default_ttl = settings.short_term_ttl

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.max_connections,
            )
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Running without cache.")
            self.redis = None  # Run without Redis

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "stm",
    ) -> bool:
        """Store value in short-term memory.

        Args:
            key: Storage key
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds (None for default)
            namespace: Key namespace prefix

        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            serialized = json.dumps(value)
            expire_time = ttl if ttl is not None else self.default_ttl

            await self.redis.set(full_key, serialized, ex=expire_time)
            logger.debug(f"Set key {full_key} with TTL {expire_time}s")
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    async def get(self, key: str, namespace: str = "stm") -> Optional[Any]:
        """Retrieve value from short-term memory.

        Args:
            key: Storage key
            namespace: Key namespace prefix

        Returns:
            Stored value or None if not found
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            value = await self.redis.get(full_key)

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    async def delete(self, key: str, namespace: str = "stm") -> bool:
        """Delete value from short-term memory.

        Args:
            key: Storage key
            namespace: Key namespace prefix

        Returns:
            True if deleted, False otherwise
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            result = await self.redis.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    async def exists(self, key: str, namespace: str = "stm") -> bool:
        """Check if key exists in short-term memory.

        Args:
            key: Storage key
            namespace: Key namespace prefix

        Returns:
            True if exists, False otherwise
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            return await self.redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False

    async def get_ttl(self, key: str, namespace: str = "stm") -> Optional[int]:
        """Get remaining TTL for a key.

        Args:
            key: Storage key
            namespace: Key namespace prefix

        Returns:
            Remaining seconds or None if key doesn't exist
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            ttl = await self.redis.ttl(full_key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return None

    async def set_conversation_context(
        self, session_id: str, context: dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Store conversation context.

        Args:
            session_id: Session identifier
            context: Conversation context data
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        return await self.set(session_id, context, ttl=ttl, namespace="conversation")

    async def get_conversation_context(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve conversation context.

        Args:
            session_id: Session identifier

        Returns:
            Conversation context or None
        """
        return await self.get(session_id, namespace="conversation")

    async def append_to_list(
        self, key: str, value: Any, max_length: int = 100, namespace: str = "stm"
    ) -> bool:
        """Append value to a list in Redis.

        Args:
            key: List key
            value: Value to append
            max_length: Maximum list length (oldest items removed)
            namespace: Key namespace prefix

        Returns:
            True if successful
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            serialized = json.dumps(value)

            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            pipe.rpush(full_key, serialized)
            pipe.ltrim(full_key, -max_length, -1)
            await pipe.execute()

            return True
        except Exception as e:
            logger.error(f"Failed to append to list {key}: {e}")
            return False

    async def get_list(
        self, key: str, start: int = 0, end: int = -1, namespace: str = "stm"
    ) -> List[Any]:
        """Retrieve list from Redis.

        Args:
            key: List key
            start: Start index
            end: End index (-1 for all)
            namespace: Key namespace prefix

        Returns:
            List of values
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            full_key = f"{namespace}:{key}"
            values = await self.redis.lrange(full_key, start, end)
            return [json.loads(v) for v in values]
        except Exception as e:
            logger.error(f"Failed to get list {key}: {e}")
            return []

    async def flush_namespace(self, namespace: str) -> int:
        """Delete all keys in a namespace.

        Args:
            namespace: Namespace to flush

        Returns:
            Number of keys deleted
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")

        try:
            pattern = f"{namespace}:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to flush namespace {namespace}: {e}")
            return 0


# Global instance
short_term_memory = ShortTermMemory()
