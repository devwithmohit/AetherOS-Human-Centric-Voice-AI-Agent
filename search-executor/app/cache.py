"""Redis cache for search results with TTL support."""

from typing import Optional, List, Dict, Any
import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import asdict
import redis.asyncio as aioredis


class SearchCache:
    """Redis-based cache for search results."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_seconds: int = 86400,  # 24 hours
        key_prefix: str = "search:",
        max_cache_size_mb: int = 100,
    ):
        """Initialize search cache.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Cache TTL in seconds
            key_prefix: Prefix for cache keys
            max_cache_size_mb: Max cache size in MB
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.max_cache_size_mb = max_cache_size_mb

        # Redis client (lazy initialization)
        self._redis: Optional[aioredis.Redis] = None

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "evictions": 0,
            "errors": 0,
        }

    async def _get_redis(self) -> aioredis.Redis:
        """Get or initialize Redis connection."""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    async def get(self, query: str, **filters) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results.

        Args:
            query: Search query
            **filters: Additional search filters

        Returns:
            Cached results or None if not found
        """
        try:
            redis = await self._get_redis()
            cache_key = self._generate_key(query, filters)

            # Get from cache
            cached_data = await redis.get(cache_key)

            if cached_data:
                self.stats["hits"] += 1
                data = json.loads(cached_data)
                return data.get("results", [])

            self.stats["misses"] += 1
            return None

        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache get error: {e}")
            return None

    async def set(self, query: str, results: List[Any], **filters) -> bool:
        """Cache search results.

        Args:
            query: Search query
            results: Search results to cache
            **filters: Additional search filters

        Returns:
            True if cached successfully
        """
        try:
            redis = await self._get_redis()
            cache_key = self._generate_key(query, filters)

            # Convert results to dictionaries
            serializable_results = []
            for result in results:
                if hasattr(result, "to_dict"):
                    serializable_results.append(result.to_dict())
                elif isinstance(result, dict):
                    serializable_results.append(result)
                else:
                    serializable_results.append(asdict(result))

            # Create cache entry
            cache_entry = {
                "query": query,
                "filters": filters,
                "results": serializable_results,
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": self.ttl_seconds,
            }

            # Store in Redis with TTL
            await redis.setex(cache_key, self.ttl_seconds, json.dumps(cache_entry))

            self.stats["writes"] += 1
            return True

        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache set error: {e}")
            return False

    async def delete(self, query: str, **filters) -> bool:
        """Delete cached results.

        Args:
            query: Search query
            **filters: Additional search filters

        Returns:
            True if deleted
        """
        try:
            redis = await self._get_redis()
            cache_key = self._generate_key(query, filters)

            deleted = await redis.delete(cache_key)
            return deleted > 0

        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache delete error: {e}")
            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries.

        Args:
            pattern: Key pattern to match (e.g., "search:*weather*")

        Returns:
            Number of keys deleted
        """
        try:
            redis = await self._get_redis()

            if pattern:
                # Match specific pattern
                search_pattern = f"{self.key_prefix}{pattern}"
            else:
                # Match all search keys
                search_pattern = f"{self.key_prefix}*"

            # Find matching keys
            keys = []
            async for key in redis.scan_iter(match=search_pattern):
                keys.append(key)

            # Delete keys
            if keys:
                deleted = await redis.delete(*keys)
                self.stats["evictions"] += deleted
                return deleted

            return 0

        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache clear error: {e}")
            return 0

    async def get_info(self) -> Dict[str, Any]:
        """Get cache information.

        Returns:
            Cache statistics and info
        """
        try:
            redis = await self._get_redis()

            # Get Redis info
            info = await redis.info("memory")

            # Count cache keys
            key_count = 0
            async for _ in redis.scan_iter(match=f"{self.key_prefix}*"):
                key_count += 1

            return {
                "key_count": key_count,
                "memory_used_mb": info.get("used_memory", 0) / (1024 * 1024),
                "max_memory_mb": self.max_cache_size_mb,
                "ttl_seconds": self.ttl_seconds,
                "stats": self.stats.copy(),
            }

        except Exception as e:
            self.stats["errors"] += 1
            return {"error": str(e)}

    def _generate_key(self, query: str, filters: Dict[str, Any]) -> str:
        """Generate cache key from query and filters.

        Args:
            query: Search query
            filters: Search filters

        Returns:
            Cache key string
        """
        # Create key components
        components = [query.lower().strip()]

        # Add sorted filters
        for key in sorted(filters.keys()):
            components.append(f"{key}:{filters[key]}")

        # Hash the combined key
        key_string = "|".join(components)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"{self.key_prefix}{key_hash}"

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Statistics dictionary
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 3),
        }


class MockSearchCache(SearchCache):
    """Mock cache for testing without Redis."""

    def __init__(self, **kwargs):
        """Initialize mock cache."""
        super().__init__(redis_url="redis://mock", **kwargs)
        self._cache: Dict[str, Any] = {}

    async def _get_redis(self):
        """Return None (mock)."""
        return None

    async def get(self, query: str, **filters) -> Optional[List[Dict[str, Any]]]:
        """Get from in-memory cache."""
        try:
            cache_key = self._generate_key(query, filters)

            if cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check TTL
                cached_at = datetime.fromisoformat(entry["cached_at"])
                age_seconds = (datetime.utcnow() - cached_at).total_seconds()

                if age_seconds < self.ttl_seconds:
                    self.stats["hits"] += 1
                    return entry["results"]
                else:
                    # Expired
                    del self._cache[cache_key]

            self.stats["misses"] += 1
            return None

        except Exception as e:
            self.stats["errors"] += 1
            return None

    async def set(self, query: str, results: List[Any], **filters) -> bool:
        """Store in in-memory cache."""
        try:
            cache_key = self._generate_key(query, filters)

            # Convert results
            serializable_results = []
            for result in results:
                if hasattr(result, "to_dict"):
                    serializable_results.append(result.to_dict())
                elif isinstance(result, dict):
                    serializable_results.append(result)
                else:
                    serializable_results.append(asdict(result))

            self._cache[cache_key] = {
                "query": query,
                "filters": filters,
                "results": serializable_results,
                "cached_at": datetime.utcnow().isoformat(),
            }

            self.stats["writes"] += 1
            return True

        except Exception as e:
            self.stats["errors"] += 1
            return False

    async def delete(self, query: str, **filters) -> bool:
        """Delete from in-memory cache."""
        cache_key = self._generate_key(query, filters)
        if cache_key in self._cache:
            del self._cache[cache_key]
            return True
        return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear in-memory cache."""
        count = len(self._cache)
        self._cache.clear()
        self.stats["evictions"] += count
        return count

    async def get_info(self) -> Dict[str, Any]:
        """Get mock cache info."""
        return {
            "key_count": len(self._cache),
            "memory_used_mb": 0,
            "max_memory_mb": self.max_cache_size_mb,
            "ttl_seconds": self.ttl_seconds,
            "stats": self.stats.copy(),
        }
