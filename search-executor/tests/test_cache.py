"""Test suite for SearchCache."""

import pytest
import asyncio
from app.cache import MockSearchCache
from app.search_client import SearchResult


@pytest.mark.asyncio
async def test_cache_miss():
    """Test cache miss returns None."""
    cache = MockSearchCache()

    result = await cache.get("nonexistent query")

    assert result is None
    assert cache.stats["misses"] == 1


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test setting and getting cached results."""
    cache = MockSearchCache()

    # Create test results
    results = [
        SearchResult(
            title="Result 1",
            url="https://example.com/1",
            snippet="First result",
            position=1,
            source="google",
            timestamp="2024-01-01T00:00:00Z",
        ),
        SearchResult(
            title="Result 2",
            url="https://example.com/2",
            snippet="Second result",
            position=2,
            source="google",
            timestamp="2024-01-01T00:00:00Z",
        ),
    ]

    # Cache results
    success = await cache.set("test query", results)
    assert success is True
    assert cache.stats["writes"] == 1

    # Retrieve from cache
    cached = await cache.get("test query")
    assert cached is not None
    assert len(cached) == 2
    assert cache.stats["hits"] == 1


@pytest.mark.asyncio
async def test_cache_with_filters():
    """Test cache key generation with filters."""
    cache = MockSearchCache()

    results = [
        SearchResult("Title", "https://test.com", "snippet", 1, "google", "2024")
    ]

    # Cache with filters
    await cache.set("query", results, location="US", language="en")

    # Same query + filters should hit
    cached1 = await cache.get("query", location="US", language="en")
    assert cached1 is not None

    # Different filters should miss
    cached2 = await cache.get("query", location="UK", language="en")
    assert cached2 is None


@pytest.mark.asyncio
async def test_cache_ttl():
    """Test cache TTL expiration."""
    # Short TTL for testing
    cache = MockSearchCache(ttl_seconds=1)

    results = [
        SearchResult("Title", "https://test.com", "snippet", 1, "google", "2024")
    ]

    # Cache results
    await cache.set("query", results)

    # Immediate get should hit
    cached1 = await cache.get("query")
    assert cached1 is not None

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be expired (miss)
    cached2 = await cache.get("query")
    assert cached2 is None


@pytest.mark.asyncio
async def test_cache_delete():
    """Test deleting cached results."""
    cache = MockSearchCache()

    results = [
        SearchResult("Title", "https://test.com", "snippet", 1, "google", "2024")
    ]

    # Cache and verify
    await cache.set("query", results)
    cached = await cache.get("query")
    assert cached is not None

    # Delete
    deleted = await cache.delete("query")
    assert deleted is True

    # Should be gone
    cached2 = await cache.get("query")
    assert cached2 is None


@pytest.mark.asyncio
async def test_cache_clear():
    """Test clearing all cache entries."""
    cache = MockSearchCache()

    # Cache multiple queries
    results = [
        SearchResult("Title", "https://test.com", "snippet", 1, "google", "2024")
    ]

    await cache.set("query1", results)
    await cache.set("query2", results)
    await cache.set("query3", results)

    # Clear all
    count = await cache.clear()
    assert count == 3
    assert cache.stats["evictions"] == 3

    # All should be gone
    assert await cache.get("query1") is None
    assert await cache.get("query2") is None
    assert await cache.get("query3") is None


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics tracking."""
    cache = MockSearchCache()

    results = [
        SearchResult("Title", "https://test.com", "snippet", 1, "google", "2024")
    ]

    # Perform operations
    await cache.set("q1", results)  # write
    await cache.get("q1")  # hit
    await cache.get("q2")  # miss
    await cache.get("q1")  # hit
    await cache.set("q2", results)  # write

    stats = cache.get_stats()

    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["writes"] == 2
    assert stats["total_requests"] == 3
    assert stats["hit_rate"] == round(2 / 3, 3)


@pytest.mark.asyncio
async def test_cache_info():
    """Test cache info retrieval."""
    cache = MockSearchCache()

    results = [
        SearchResult("Title", "https://test.com", "snippet", 1, "google", "2024")
    ]

    await cache.set("query", results)

    info = await cache.get_info()

    assert "key_count" in info
    assert info["key_count"] == 1
    assert info["ttl_seconds"] == cache.ttl_seconds
    assert "stats" in info


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key generation is consistent."""
    cache = MockSearchCache()

    # Same query and filters should generate same key
    key1 = cache._generate_key("test query", {"location": "US", "lang": "en"})
    key2 = cache._generate_key("test query", {"location": "US", "lang": "en"})

    assert key1 == key2

    # Different query should generate different key
    key3 = cache._generate_key("other query", {"location": "US", "lang": "en"})
    assert key1 != key3

    # Different filters should generate different key
    key4 = cache._generate_key("test query", {"location": "UK", "lang": "en"})
    assert key1 != key4


@pytest.mark.asyncio
async def test_cache_multiple_queries():
    """Test caching multiple different queries."""
    cache = MockSearchCache()

    # Cache different queries
    for i in range(5):
        results = [
            SearchResult(
                f"Result {i}",
                f"https://example.com/{i}",
                f"Snippet {i}",
                1,
                "google",
                "2024",
            )
        ]
        await cache.set(f"query {i}", results)

    # All should be retrievable
    for i in range(5):
        cached = await cache.get(f"query {i}")
        assert cached is not None
        assert len(cached) == 1
