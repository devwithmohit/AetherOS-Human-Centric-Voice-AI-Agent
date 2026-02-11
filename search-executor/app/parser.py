"""Result parser for extracting structured data from search results."""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import re
from urllib.parse import urlparse


@dataclass
class ParsedContent:
    """Parsed and structured search result content."""

    # Basic fields
    title: str
    url: str
    domain: str
    snippet: str
    position: int = 0

    # Extracted content
    main_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Classification
    content_type: str = "webpage"  # webpage, pdf, image, video
    relevance_score: float = 0.0

    # Temporal
    published_date: Optional[datetime] = None
    parsed_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Extract domain from URL."""
        if not self.domain and self.url:
            try:
                parsed = urlparse(self.url)
                self.domain = parsed.netloc
            except Exception:
                self.domain = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "domain": self.domain,
            "snippet": self.snippet,
            "position": self.position,
            "main_text": self.main_text,
            "metadata": self.metadata,
            "content_type": self.content_type,
            "relevance_score": self.relevance_score,
            "published_date": self.published_date.isoformat()
            if self.published_date
            else None,
            "parsed_at": self.parsed_at.isoformat(),
        }


class ResultParser:
    """Parser for search results and web content."""

    def __init__(
        self,
        extract_metadata: bool = True,
        calculate_relevance: bool = True,
        min_snippet_length: int = 50,
        max_snippet_length: int = 300,
    ):
        """Initialize parser.

        Args:
            extract_metadata: Extract metadata from results
            calculate_relevance: Calculate relevance scores
            min_snippet_length: Minimum snippet length
            max_snippet_length: Maximum snippet length
        """
        self.extract_metadata = extract_metadata
        self.calculate_relevance = calculate_relevance
        self.min_snippet_length = min_snippet_length
        self.max_snippet_length = max_snippet_length

        # Common file extensions
        self.file_extensions = {
            "pdf": "pdf",
            "doc": "document",
            "docx": "document",
            "xls": "spreadsheet",
            "xlsx": "spreadsheet",
            "ppt": "presentation",
            "pptx": "presentation",
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gif": "image",
            "mp4": "video",
            "avi": "video",
            "mov": "video",
        }

    def parse_result(
        self,
        title: str,
        url: str,
        snippet: str,
        query: Optional[str] = None,
        position: int = 0,
        **kwargs,
    ) -> ParsedContent:
        """Parse a single search result.

        Args:
            title: Result title
            url: Result URL
            snippet: Result snippet/description
            query: Original search query (for relevance)
            position: Result position in search
            **kwargs: Additional metadata

        Returns:
            ParsedContent object
        """
        # Clean and normalize fields
        title = self._clean_text(title)
        snippet = self._clean_snippet(snippet)

        # Detect content type
        content_type = self._detect_content_type(url)

        # Calculate relevance score
        relevance_score = 0.0
        if self.calculate_relevance and query:
            relevance_score = self._calculate_relevance(title, snippet, query, position)

        # Extract metadata
        metadata = {}
        if self.extract_metadata:
            metadata = self._extract_metadata(title, snippet, url, **kwargs)

        # Create parsed content
        parsed = ParsedContent(
            title=title,
            url=url,
            domain="",  # Will be extracted in __post_init__
            snippet=snippet,
            position=position,
            content_type=content_type,
            relevance_score=relevance_score,
            metadata=metadata,
        )

        return parsed

    def parse_results_batch(
        self,
        results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> List[ParsedContent]:
        """Parse multiple search results.

        Args:
            results: List of result dictionaries
            query: Original search query

        Returns:
            List of ParsedContent objects
        """
        parsed_results = []

        for idx, result in enumerate(results):
            try:
                # Extract known parameters
                title = result.get("title", "")
                url = result.get("url", "")
                snippet = result.get("snippet", "")
                position = result.get("position", idx + 1)

                # Get additional metadata (exclude already extracted)
                extra_kwargs = {k: v for k, v in result.items()
                               if k not in ["title", "url", "snippet", "position", "query"]}

                parsed = self.parse_result(
                    title=title,
                    url=url,
                    snippet=snippet,
                    query=query,
                    position=position,
                    **extra_kwargs,
                )
                parsed_results.append(parsed)

            except Exception as e:
                print(f"Warning: Failed to parse result {idx}: {e}")
                continue

        return parsed_results

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove HTML entities
        text = re.sub(r"&[a-z]+;", "", text)

        # Strip and return
        return text.strip()

    def _clean_snippet(self, snippet: str) -> str:
        """Clean and truncate snippet.

        Args:
            snippet: Raw snippet

        Returns:
            Cleaned snippet
        """
        snippet = self._clean_text(snippet)

        # Truncate if too long
        if len(snippet) > self.max_snippet_length:
            snippet = snippet[: self.max_snippet_length - 3] + "..."

        # Ensure minimum length
        if len(snippet) < self.min_snippet_length:
            snippet = snippet.ljust(self.min_snippet_length, " ")

        return snippet

    def _detect_content_type(self, url: str) -> str:
        """Detect content type from URL.

        Args:
            url: Resource URL

        Returns:
            Content type string
        """
        url_lower = url.lower()

        # Check file extensions
        for ext, content_type in self.file_extensions.items():
            if url_lower.endswith(f".{ext}"):
                return content_type

        # Check URL patterns
        if any(x in url_lower for x in ["youtube.com", "vimeo.com", "video"]):
            return "video"

        if any(x in url_lower for x in ["image", ".jpg", ".png", ".gif"]):
            return "image"

        return "webpage"

    def _calculate_relevance(
        self,
        title: str,
        snippet: str,
        query: str,
        position: int,
    ) -> float:
        """Calculate relevance score.

        Args:
            title: Result title
            snippet: Result snippet
            query: Search query
            position: Result position

        Returns:
            Relevance score (0.0 - 1.0)
        """
        score = 0.0

        # Normalize query
        query_terms = query.lower().split()
        title_lower = title.lower()
        snippet_lower = snippet.lower()

        # Title matches (40% weight)
        title_matches = sum(1 for term in query_terms if term in title_lower)
        title_score = title_matches / max(len(query_terms), 1)
        score += title_score * 0.4

        # Snippet matches (30% weight)
        snippet_matches = sum(1 for term in query_terms if term in snippet_lower)
        snippet_score = snippet_matches / max(len(query_terms), 1)
        score += snippet_score * 0.3

        # Position score (30% weight) - higher positions = better
        position_score = max(0, 1.0 - (position - 1) * 0.1)
        score += position_score * 0.3

        return min(score, 1.0)

    def _extract_metadata(
        self, title: str, snippet: str, url: str, **kwargs
    ) -> Dict[str, Any]:
        """Extract metadata from result.

        Args:
            title: Result title
            snippet: Result snippet
            url: Result URL
            **kwargs: Additional fields

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Extract from kwargs
        for key in ["source", "timestamp", "language", "location"]:
            if key in kwargs:
                metadata[key] = kwargs[key]

        # Extract dates from snippet
        date_patterns = [
            r"\b(\d{1,2}[\s/-]\w+[\s/-]\d{2,4})\b",  # 15 Jan 2024
            r"\b(\d{4}-\d{2}-\d{2})\b",  # 2024-01-15
        ]

        for pattern in date_patterns:
            match = re.search(pattern, snippet)
            if match:
                metadata["extracted_date"] = match.group(1)
                break

        # Estimate reading time (words per minute)
        word_count = len(snippet.split())
        metadata["estimated_read_seconds"] = int(word_count / 250 * 60)

        return metadata

    def filter_results(
        self,
        results: List[ParsedContent],
        min_relevance: float = 0.0,
        content_types: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        domain_whitelist: Optional[List[str]] = None,
        domain_blacklist: Optional[List[str]] = None,
    ) -> List[ParsedContent]:
        """Filter parsed results.

        Args:
            results: List of ParsedContent objects
            min_relevance: Minimum relevance score
            content_types: Allowed content types
            domains: Allowed domains (whitelist)
            exclude_domains: Blocked domains (blacklist)
            domain_whitelist: Alias for domains (whitelist)
            domain_blacklist: Alias for exclude_domains (blacklist)

        Returns:
            Filtered list of results
        """
        # Support both parameter names
        if domain_whitelist:
            domains = domain_whitelist
        if domain_blacklist:
            exclude_domains = domain_blacklist
        filtered = []

        for result in results:
            # Check relevance
            if result.relevance_score < min_relevance:
                continue

            # Check content type
            if content_types and result.content_type not in content_types:
                continue

            # Check domain whitelist
            if domains and result.domain not in domains:
                continue

            # Check domain blacklist
            if exclude_domains and result.domain in exclude_domains:
                continue

            filtered.append(result)

        return filtered

    def rank_results(
        self,
        results: List[ParsedContent],
        boost_recent: bool = True,
        boost_domains: Optional[Dict[str, float]] = None,
    ) -> List[ParsedContent]:
        """Re-rank results based on additional criteria.

        Args:
            results: List of ParsedContent objects
            boost_recent: Boost recent content
            boost_domains: Domain boost factors

        Returns:
            Re-ranked list of results
        """
        scored_results = []

        for result in results:
            score = result.relevance_score

            # Boost trusted domains
            if boost_domains and result.domain in boost_domains:
                score *= boost_domains[result.domain]

            # Boost recent content
            if boost_recent and result.published_date:
                days_old = (datetime.utcnow() - result.published_date).days
                if days_old < 7:
                    score *= 1.2
                elif days_old < 30:
                    score *= 1.1

            scored_results.append((score, result))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        return [result for _, result in scored_results]
