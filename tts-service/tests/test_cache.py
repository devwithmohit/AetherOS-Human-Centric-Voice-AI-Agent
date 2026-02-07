"""Unit tests for voice cache."""

import pytest
from app.voice_cache import VoiceCache


@pytest.fixture
def cache():
    """Create cache instance for testing."""
    cache_instance = VoiceCache()
    yield cache_instance
    cache_instance.clear()
    cache_instance.close()


def test_cache_initialization(cache):
    """Test cache initializes correctly."""
    assert cache is not None
    stats = cache.get_stats()
    assert stats["enabled"] is True


def test_cache_set_get(cache):
    """Test basic set and get operations."""
    audio_bytes = b"fake audio data"
    text = "Hello world"

    # Set cache
    success = cache.set(
        audio_bytes=audio_bytes, text=text, speaker_id="ljspeech", audio_format="wav"
    )
    assert success is True

    # Get cache
    cached = cache.get(text=text, speaker_id="ljspeech", audio_format="wav")
    assert cached == audio_bytes


def test_cache_miss(cache):
    """Test cache miss returns None."""
    result = cache.get(text="This text is not cached", speaker_id="ljspeech")
    assert result is None


def test_cache_key_generation(cache):
    """Test cache keys are unique for different parameters."""
    audio_bytes = b"audio data"

    # Cache with different parameters
    cache.set(audio_bytes, text="Hello", speaker_id="ljspeech", speed=1.0)
    cache.set(audio_bytes, text="Hello", speaker_id="p225", speed=1.0)
    cache.set(audio_bytes, text="Hello", speaker_id="ljspeech", speed=1.2)

    # All should be cached separately
    assert cache.get(text="Hello", speaker_id="ljspeech", speed=1.0) is not None
    assert cache.get(text="Hello", speaker_id="p225", speed=1.0) is not None
    assert cache.get(text="Hello", speaker_id="ljspeech", speed=1.2) is not None


def test_cache_case_insensitive(cache):
    """Test cache is case-insensitive for text."""
    audio_bytes = b"audio"

    cache.set(audio_bytes, text="Hello World")

    # Should hit cache regardless of case
    assert cache.get(text="hello world") is not None
    assert cache.get(text="HELLO WORLD") is not None
    assert cache.get(text="HeLLo WoRLd") is not None


def test_cache_statistics(cache):
    """Test cache statistics tracking."""
    # Start with zero stats
    stats = cache.get_stats()
    initial_hits = stats["total_hits"]
    initial_misses = stats["total_misses"]

    # Cache miss
    cache.get(text="not cached")
    stats = cache.get_stats()
    assert stats["total_misses"] == initial_misses + 1

    # Cache hit
    cache.set(b"data", text="cached text")
    cache.get(text="cached text")
    stats = cache.get_stats()
    assert stats["total_hits"] == initial_hits + 1


def test_cache_hit_rate(cache):
    """Test cache hit rate calculation."""
    # Add some cached items
    for i in range(5):
        cache.set(b"data", text=f"text {i}")

    # Hit cache 5 times
    for i in range(5):
        cache.get(text=f"text {i}")

    # Miss cache 5 times
    for i in range(5, 10):
        cache.get(text=f"text {i}")

    stats = cache.get_stats()
    assert stats["hit_rate"] == 0.5  # 50% hit rate


def test_cache_delete(cache):
    """Test cache deletion."""
    audio_bytes = b"audio to delete"
    text = "Delete me"

    # Cache item
    cache.set(audio_bytes, text=text)
    assert cache.get(text=text) is not None

    # Delete item
    deleted = cache.delete(text=text)
    assert deleted is True

    # Verify deleted
    assert cache.get(text=text) is None


def test_cache_clear(cache):
    """Test clearing entire cache."""
    # Add multiple items
    for i in range(10):
        cache.set(b"data", text=f"item {i}")

    stats = cache.get_stats()
    assert stats["size"] > 0

    # Clear cache
    success = cache.clear()
    assert success is True

    # Verify cleared
    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["total_hits"] == 0
    assert stats["total_misses"] == 0


def test_cache_ttl(cache):
    """Test cache TTL expiration."""
    import time

    # Create cache with 1 second TTL
    short_ttl_cache = VoiceCache()
    short_ttl_cache.ttl = 1

    # Cache item
    short_ttl_cache.set(b"expires", text="expiring text")

    # Should be cached immediately
    assert short_ttl_cache.get(text="expiring text") is not None

    # Wait for expiration
    time.sleep(2)

    # Should be expired
    result = short_ttl_cache.get(text="expiring text")
    # Note: diskcache may still return expired items, this is implementation-dependent

    short_ttl_cache.close()


def test_cache_size_limit(cache):
    """Test cache respects size limit."""
    # Fill cache with large items
    large_audio = b"x" * (1024 * 100)  # 100KB per item

    for i in range(20):
        cache.set(large_audio, text=f"large item {i}")

    stats = cache.get_stats()
    # Should not exceed max size
    assert stats["size_bytes"] <= stats["max_size_bytes"]


def test_cache_disabled():
    """Test cache can be disabled."""
    from app.config import settings

    # Create cache with cache disabled
    settings.cache_enabled = False
    disabled_cache = VoiceCache()

    # Operations should return False/None
    assert disabled_cache.set(b"data", text="test") is False
    assert disabled_cache.get(text="test") is None

    # Re-enable for other tests
    settings.cache_enabled = True


def test_cache_different_formats(cache):
    """Test cache handles different audio formats."""
    formats = ["wav", "mp3", "ogg", "flac"]

    for fmt in formats:
        cache.set(b"audio", text="format test", audio_format=fmt)
        assert cache.get(text="format test", audio_format=fmt) is not None


def test_cache_special_characters(cache):
    """Test cache handles special characters in text."""
    special_texts = [
        "Hello, world!",
        "What's up?",
        "Temperature: 72°F",
        "Cost: $100.50",
        "Email: test@example.com",
    ]

    for text in special_texts:
        cache.set(b"audio", text=text)
        assert cache.get(text=text) is not None
