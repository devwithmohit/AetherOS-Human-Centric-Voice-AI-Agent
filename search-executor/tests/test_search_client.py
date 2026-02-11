"""Test suite for SearchClient."""

import pytest
import asyncio
from app.search_client import SearchClient, MockSearchClient, SearchResult, SearchError


@pytest.mark.asyncio
async def test_mock_client_search():
    """Test mock search client."""
    client = MockSearchClient()

    results = await client.search("Python tutorials")

    assert len(results) == 5
    assert all(isinstance(r, SearchResult) for r in results)
    assert results[0].position == 1
    assert "python tutorials" in results[0].title.lower()


@pytest.mark.asyncio
async def test_mock_client_num_results():
    """Test mock client respects num_results."""
    client = MockSearchClient()

    results = await client.search("test", num_results=3)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_mock_client_different_queries():
    """Test mock client with different queries."""
    client = MockSearchClient()

    results1 = await client.search("Python")
    results2 = await client.search("JavaScript")

    assert len(results1) == 5
    assert len(results2) == 5
    assert results1[0].snippet != results2[0].snippet


@pytest.mark.asyncio
async def test_search_result_to_dict():
    """Test SearchResult serialization."""
    result = SearchResult(
        title="Test Title",
        url="https://example.com",
        snippet="Test snippet",
        position=1,
        source="google",
        timestamp="2024-01-01T00:00:00Z",
    )

    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["title"] == "Test Title"
    assert data["url"] == "https://example.com"
    assert data["position"] == 1


@pytest.mark.asyncio
async def test_client_stats():
    """Test client statistics tracking."""
    client = MockSearchClient()

    # Perform searches
    await client.search("test1")
    await client.search("test2")
    await client.search("test3")

    stats = client.get_stats()

    assert stats["total_searches"] == 3
    assert stats["api_calls"] == 3
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_search_sync_wrapper():
    """Test synchronous search wrapper."""
    client = MockSearchClient()

    results = client.search_sync("Python", num_results=5)

    assert len(results) == 5
    assert all(isinstance(r, SearchResult) for r in results)


def test_search_result_dataclass():
    """Test SearchResult dataclass properties."""
    result = SearchResult(
        title="Test",
        url="https://test.com",
        snippet="Test snippet",
        position=1,
        source="google",
        timestamp="2024-01-01T00:00:00Z",
    )

    assert result.title == "Test"
    assert result.url == "https://test.com"
    assert result.position == 1
    assert result.source == "google"


@pytest.mark.asyncio
async def test_mock_client_safe_search():
    """Test mock client with safe search."""
    client = MockSearchClient()

    results = await client.search("test", safe_search=True)

    assert len(results) == 5


@pytest.mark.asyncio
async def test_mock_client_location_filter():
    """Test mock client with location filter."""
    client = MockSearchClient()

    results = await client.search("test", location="United States")

    assert len(results) == 5


@pytest.mark.asyncio
async def test_mock_client_language_filter():
    """Test mock client with language filter."""
    client = MockSearchClient()

    results = await client.search("test", language="en")

    assert len(results) == 5
