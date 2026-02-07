"""Voice caching system for common phrases."""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from diskcache import Cache

from app.config import settings

logger = logging.getLogger(__name__)


class VoiceCache:
    """LRU cache for synthesized audio with disk persistence."""

    def __init__(self) -> None:
        """Initialize voice cache."""
        self.enabled: bool = settings.cache_enabled
        self.cache_dir: Path = Path(settings.cache_dir)
        self.max_size: int = settings.cache_size_bytes
        self.ttl: int = settings.cache_ttl_seconds
        self.cache: Optional[Cache] = None

        # Statistics
        self._hits: int = 0
        self._misses: int = 0
        self._total_requests: int = 0

        if self.enabled:
            self._initialize_cache()

    def _initialize_cache(self) -> None:
        """Initialize disk cache."""
        try:
            # Create cache directory if it doesn't exist
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Initialize diskcache
            self.cache = Cache(
                directory=str(self.cache_dir),
                size_limit=self.max_size,
                eviction_policy="least-recently-used",
            )

            logger.info(
                f"Voice cache initialized at {self.cache_dir} "
                f"(max size: {self.max_size / (1024**2):.1f} MB, TTL: {self.ttl}s)"
            )

        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.enabled = False
            self.cache = None

    def _generate_cache_key(
        self,
        text: str,
        speaker_id: Optional[str] = None,
        language: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        audio_format: str = "wav",
    ) -> str:
        """
        Generate cache key from synthesis parameters.

        Args:
            text: Text to synthesize
            speaker_id: Speaker ID
            language: Language code
            speed: Speech speed
            pitch: Pitch multiplier
            audio_format: Audio format

        Returns:
            Cache key string
        """
        # Create cache key components
        key_data = {
            "text": text.strip().lower(),
            "speaker": speaker_id or "default",
            "language": language or "en",
            "speed": round(speed, 2),
            "pitch": round(pitch, 2),
            "format": audio_format,
        }

        # Convert to JSON and hash
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()

        return f"audio_{key_hash}"

    def get(
        self,
        text: str,
        speaker_id: Optional[str] = None,
        language: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        audio_format: str = "wav",
    ) -> Optional[bytes]:
        """
        Get cached audio if available.

        Args:
            text: Text to synthesize
            speaker_id: Speaker ID
            language: Language code
            speed: Speech speed
            pitch: Pitch multiplier
            audio_format: Audio format

        Returns:
            Cached audio bytes or None if not found
        """
        if not self.enabled or self.cache is None:
            return None

        self._total_requests += 1

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                text=text,
                speaker_id=speaker_id,
                language=language,
                speed=speed,
                pitch=pitch,
                audio_format=audio_format,
            )

            # Try to get from cache
            cached_data = self.cache.get(cache_key)

            if cached_data is not None:
                self._hits += 1
                logger.debug(f"Cache HIT for key: {cache_key[:16]}...")
                return cached_data

            self._misses += 1
            logger.debug(f"Cache MISS for key: {cache_key[:16]}...")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(
        self,
        audio_bytes: bytes,
        text: str,
        speaker_id: Optional[str] = None,
        language: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        audio_format: str = "wav",
    ) -> bool:
        """
        Store audio in cache.

        Args:
            audio_bytes: Audio data to cache
            text: Text that was synthesized
            speaker_id: Speaker ID used
            language: Language code used
            speed: Speech speed used
            pitch: Pitch used
            audio_format: Audio format

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled or self.cache is None:
            return False

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                text=text,
                speaker_id=speaker_id,
                language=language,
                speed=speed,
                pitch=pitch,
                audio_format=audio_format,
            )

            # Store in cache with TTL
            self.cache.set(cache_key, audio_bytes, expire=self.ttl)

            logger.debug(
                f"Cached audio for key: {cache_key[:16]}... "
                f"(size: {len(audio_bytes) / 1024:.1f} KB)"
            )

            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(
        self,
        text: str,
        speaker_id: Optional[str] = None,
        language: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        audio_format: str = "wav",
    ) -> bool:
        """
        Delete cached audio.

        Args:
            text: Text to synthesize
            speaker_id: Speaker ID
            language: Language code
            speed: Speech speed
            pitch: Pitch multiplier
            audio_format: Audio format

        Returns:
            True if deleted, False otherwise
        """
        if not self.enabled or self.cache is None:
            return False

        try:
            cache_key = self._generate_cache_key(
                text=text,
                speaker_id=speaker_id,
                language=language,
                speed=speed,
                pitch=pitch,
                audio_format=audio_format,
            )

            deleted = self.cache.delete(cache_key)
            logger.debug(f"Deleted cache key: {cache_key[:16]}... (success: {deleted})")
            return deleted

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear entire cache.

        Returns:
            True if cleared successfully
        """
        if not self.enabled or self.cache is None:
            return False

        try:
            self.cache.clear()
            logger.info("Cache cleared")

            # Reset statistics
            self._hits = 0
            self._misses = 0
            self._total_requests = 0

            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "enabled": self.enabled,
            "size": len(self.cache) if self.cache else 0,
            "size_bytes": self.cache.volume() if self.cache else 0,
            "max_size_bytes": self.max_size,
            "hit_rate": (self._hits / self._total_requests if self._total_requests > 0 else 0.0),
            "total_hits": self._hits,
            "total_misses": self._misses,
            "total_requests": self._total_requests,
            "ttl_seconds": self.ttl,
        }

        return stats

    def close(self) -> None:
        """Close cache and release resources."""
        if self.cache is not None:
            try:
                self.cache.close()
                logger.info("Cache closed")
            except Exception as e:
                logger.error(f"Error closing cache: {e}")


# Global cache instance
voice_cache = VoiceCache()
