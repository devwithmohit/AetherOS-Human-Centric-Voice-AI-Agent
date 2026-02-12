"""
Redis-based Rate Limiter

Implements sliding window rate limiting using Redis for distributed systems.
"""

import time
from typing import Dict, Tuple
import structlog
from redis.asyncio import Redis, ConnectionPool

from app.config import settings

logger = structlog.get_logger()


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""

    def __init__(
        self,
        redis_url: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis: Redis = None
        self.pool: ConnectionPool = None

    async def initialize(self):
        """Initialize Redis connection pool."""
        try:
            self.pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            self.redis = Redis(connection_pool=self.pool)

            # Test connection
            await self.redis.ping()

            logger.info(
                "rate_limiter_initialized",
                redis_url=self.redis_url,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
            )

        except Exception as e:
            logger.error("rate_limiter_init_failed", error=str(e))
            raise

    async def close(self):
        """Close Redis connections."""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()

        logger.info("rate_limiter_closed")

    async def check_rate_limit(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if client is within rate limit.

        Uses sliding window algorithm with Redis sorted sets.

        Args:
            client_id: Unique client identifier

        Returns:
            Tuple of (is_allowed, limit_info)
            limit_info contains: limit, remaining, reset_at
        """
        now = time.time()
        window_start = now - self.window_seconds
        key = f"rate_limit:{client_id}"

        try:
            # Use Redis transaction for atomic operations
            pipe = self.redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request with timestamp as score
            pipe.zadd(key, {str(now): now})

            # Set expiration on the key
            pipe.expire(key, self.window_seconds)

            # Execute pipeline
            results = await pipe.execute()

            # Get current count (before adding new request)
            current_count = results[1]

            # Calculate remaining requests
            remaining = max(0, self.max_requests - current_count - 1)

            # Calculate reset time
            reset_at = int(now + self.window_seconds)

            # Check if limit exceeded
            is_allowed = current_count < self.max_requests

            limit_info = {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset_at": reset_at,
                "current": current_count + 1,
            }

            if not is_allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    client_id=client_id,
                    current=current_count,
                    limit=self.max_requests,
                )

            return is_allowed, limit_info

        except Exception as e:
            logger.error(
                "rate_limit_check_failed",
                client_id=client_id,
                error=str(e),
            )
            # Fail open - allow request if Redis is down
            return True, {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "reset_at": int(now + self.window_seconds),
                "current": 0,
            }

    async def reset_limit(self, client_id: str):
        """
        Reset rate limit for a client.

        Args:
            client_id: Client identifier
        """
        key = f"rate_limit:{client_id}"
        try:
            await self.redis.delete(key)
            logger.info("rate_limit_reset", client_id=client_id)
        except Exception as e:
            logger.error("rate_limit_reset_failed", client_id=client_id, error=str(e))

    async def get_limit_info(self, client_id: str) -> Dict[str, int]:
        """
        Get current rate limit info for a client.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary with limit information
        """
        now = time.time()
        window_start = now - self.window_seconds
        key = f"rate_limit:{client_id}"

        try:
            # Count requests in current window
            count = await self.redis.zcount(key, window_start, now)

            remaining = max(0, self.max_requests - count)
            reset_at = int(now + self.window_seconds)

            return {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset_at": reset_at,
                "current": count,
            }

        except Exception as e:
            logger.error("get_limit_info_failed", client_id=client_id, error=str(e))
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "reset_at": int(now + self.window_seconds),
                "current": 0,
            }

    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error("rate_limiter_health_check_failed", error=str(e))
            return False
