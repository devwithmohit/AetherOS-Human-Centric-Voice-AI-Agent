"""SerpAPI client for web search queries.

This module provides a wrapper around SerpAPI for performing web searches
with rate limiting, error handling, and result parsing.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import httpx
import asyncio
from pathlib import Path


class SearchError(Exception):
    """Raised when search operation fails."""

    pass


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str
    position: int
    source: str = "organic"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        elif isinstance(self.timestamp, str):
            # Convert string timestamp to datetime if needed
            try:
                self.timestamp = datetime.fromisoformat(
                    self.timestamp.replace("Z", "+00:00")
                )
            except:
                self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "position": self.position,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
            if isinstance(self.timestamp, datetime)
            else self.timestamp,
        }


class SearchClient:
    """SerpAPI client for web searches."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        engine: str = "google",
        cache_ttl: int = 86400,  # 24 hours
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize search client.

        Args:
            api_key: SerpAPI key (or env var SERPAPI_KEY)
            engine: Search engine (google, bing, duckduckgo)
            cache_ttl: Cache TTL in seconds
            timeout: Request timeout in seconds
            max_retries: Max retry attempts
        """
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        self.engine = engine
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.max_retries = max_retries

        # Rate limiting
        self.requests_per_second = 5
        self.last_request_time = 0
        self._rate_limit_lock = asyncio.Lock()

        # API endpoints
        self.base_url = "https://serpapi.com/search"

        # Statistics
        self.stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "errors": 0,
        }

    async def search(
        self,
        query: str,
        num_results: int = 10,
        location: Optional[str] = None,
        language: str = "en",
        safe_search: bool = True,
        **kwargs,
    ) -> List[SearchResult]:
        """Perform web search.

        Args:
            query: Search query
            num_results: Number of results to return
            location: Geographic location for results
            language: Language code
            safe_search: Enable safe search
            **kwargs: Additional search parameters

        Returns:
            List of SearchResult objects

        Raises:
            SearchError: If search fails
        """
        if not query or not query.strip():
            raise SearchError("Search query cannot be empty")

        self.stats["total_searches"] += 1

        # Build request parameters
        params = {
            "q": query.strip(),
            "num": min(num_results, 100),  # Max 100 results
            "api_key": self.api_key,
            "engine": self.engine,
            "hl": language,
        }

        if location:
            params["location"] = location

        if safe_search:
            params["safe"] = "active"

        # Add custom parameters
        params.update(kwargs)

        # Apply rate limiting
        await self._apply_rate_limit()

        # Make API request
        try:
            results = await self._make_request(params)
            self.stats["api_calls"] += 1
            return results

        except Exception as e:
            self.stats["errors"] += 1
            raise SearchError(f"Search failed: {e}")

    async def _make_request(self, params: Dict[str, Any]) -> List[SearchResult]:
        """Make HTTP request to SerpAPI.

        Args:
            params: Request parameters

        Returns:
            List of SearchResult objects
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()

                    data = response.json()
                    return self._parse_results(data)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Rate limited, wait and retry
                        wait_time = 2**attempt  # Exponential backoff
                        await asyncio.sleep(wait_time)
                        continue
                    elif e.response.status_code == 401:
                        raise SearchError("Invalid API key")
                    else:
                        raise SearchError(f"HTTP error: {e.response.status_code}")

                except httpx.TimeoutException:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    raise SearchError("Request timeout")

                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    raise SearchError(f"Request failed: {e}")

        raise SearchError("Max retries exceeded")

    def _parse_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse SerpAPI response.

        Args:
            data: API response data

        Returns:
            List of SearchResult objects
        """
        results = []

        # Parse organic results
        organic_results = data.get("organic_results", [])

        for idx, result in enumerate(organic_results):
            try:
                search_result = SearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    position=result.get("position", idx + 1),
                    source="organic",
                )
                results.append(search_result)

            except Exception as e:
                print(f"Warning: Failed to parse result {idx}: {e}")
                continue

        # Parse featured snippet if present
        featured_snippet = data.get("answer_box", {})
        if featured_snippet:
            try:
                snippet_result = SearchResult(
                    title=featured_snippet.get("title", "Featured Snippet"),
                    url=featured_snippet.get("link", ""),
                    snippet=featured_snippet.get("snippet", ""),
                    position=0,
                    source="featured",
                )
                results.insert(0, snippet_result)
            except Exception:
                pass

        return results

    async def _apply_rate_limit(self):
        """Apply rate limiting to prevent API abuse."""
        async with self._rate_limit_lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.requests_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self.last_request_time = asyncio.get_event_loop().time()

    def get_stats(self) -> Dict[str, int]:
        """Get client statistics.

        Returns:
            Dictionary with usage statistics
        """
        return self.stats.copy()

    # Synchronous wrapper for compatibility
    def search_sync(self, query: str, **kwargs) -> List[SearchResult]:
        """Synchronous search wrapper.

        Args:
            query: Search query
            **kwargs: Additional parameters

        Returns:
            List of SearchResult objects
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop in a thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.search(query, **kwargs))
                    return future.result()
            else:
                return loop.run_until_complete(self.search(query, **kwargs))
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(self.search(query, **kwargs))


class MockSearchClient(SearchClient):
    """Mock search client for testing without API key."""

    def __init__(self, **kwargs):
        """Initialize mock client."""
        super().__init__(api_key="mock_key", **kwargs)

    async def _make_request(self, params: Dict[str, Any]) -> List[SearchResult]:
        """Return mock results."""
        query = params.get("q", "")
        num_results = params.get("num", 10)

        # Generate mock results
        results = []
        for i in range(min(num_results, 5)):
            results.append(
                SearchResult(
                    title=f"Mock Result {i + 1} for: {query}",
                    url=f"https://example.com/result{i + 1}",
                    snippet=f"This is a mock snippet for result {i + 1} about {query}. "
                    f"It contains relevant information and appears in position {i + 1}.",
                    position=i + 1,
                    source="organic",
                )
            )

        return results
