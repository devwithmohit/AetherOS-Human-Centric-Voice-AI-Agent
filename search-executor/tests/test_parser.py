"""Test suite for ResultParser."""

import pytest
from app.parser import ResultParser, ParsedContent


def test_parse_single_result():
    """Test parsing a single search result."""
    parser = ResultParser()

    parsed = parser.parse_result(
        title="Python Tutorial for Beginners",
        url="https://python.org/tutorial",
        snippet="Learn Python programming from scratch",
        query="python tutorial",
        position=1,
    )

    assert isinstance(parsed, ParsedContent)
    assert parsed.title == "Python Tutorial for Beginners"
    assert parsed.url == "https://python.org/tutorial"
    assert parsed.domain == "python.org"
    assert parsed.relevance_score > 0


def test_relevance_calculation():
    """Test relevance score calculation."""
    parser = ResultParser(calculate_relevance=True)

    # High relevance (query matches title and snippet)
    high = parser.parse_result(
        title="Python Tutorial",
        url="https://example.com",
        snippet="Python tutorial for beginners",
        query="python tutorial",
        position=1,
    )

    # Low relevance (no matches)
    low = parser.parse_result(
        title="JavaScript Guide",
        url="https://example.com",
        snippet="Learn JavaScript programming",
        query="python tutorial",
        position=10,
    )

    assert high.relevance_score > low.relevance_score
    assert high.relevance_score > 0.5
    assert low.relevance_score < 0.3


def test_content_type_detection():
    """Test content type detection from URL."""
    parser = ResultParser()

    # Webpage
    web = parser.parse_result(
        title="Test",
        url="https://example.com/page",
        snippet="test",
        query="test",
        position=1,
    )
    assert web.content_type == "webpage"

    # PDF
    pdf = parser.parse_result(
        title="Document",
        url="https://example.com/doc.pdf",
        snippet="test",
        query="test",
        position=1,
    )
    assert pdf.content_type == "pdf"

    # Image
    img = parser.parse_result(
        title="Image",
        url="https://example.com/photo.jpg",
        snippet="test",
        query="test",
        position=1,
    )
    assert img.content_type == "image"

    # Video
    video = parser.parse_result(
        title="Video",
        url="https://youtube.com/watch?v=123",
        snippet="test",
        query="test",
        position=1,
    )
    assert video.content_type == "video"


def test_parse_results_batch():
    """Test batch parsing of multiple results."""
    parser = ResultParser()

    results = [
        {
            "title": "Result 1",
            "url": "https://example.com/1",
            "snippet": "First result",
            "position": 1,
        },
        {
            "title": "Result 2",
            "url": "https://example.com/2",
            "snippet": "Second result",
            "position": 2,
        },
        {
            "title": "Result 3",
            "url": "https://example.com/3",
            "snippet": "Third result",
            "position": 3,
        },
    ]

    parsed = parser.parse_results_batch(results, query="test")

    assert len(parsed) == 3
    assert all(isinstance(r, ParsedContent) for r in parsed)
    assert parsed[0].position == 1
    assert parsed[2].position == 3


def test_filter_by_relevance():
    """Test filtering results by minimum relevance."""
    parser = ResultParser(calculate_relevance=True)

    results = [
        parser.parse_result(
            "Python Tutorial",
            "https://python.org",
            "Python programming tutorial",
            "python",
            1,
        ),
        parser.parse_result(
            "Java Guide", "https://java.com", "Java programming guide", "python", 2
        ),
        parser.parse_result(
            "Python Examples",
            "https://examples.com",
            "Python code examples",
            "python",
            3,
        ),
    ]

    filtered = parser.filter_results(results, min_relevance=0.5)

    assert len(filtered) <= len(results)
    assert all(r.relevance_score >= 0.5 for r in filtered)


def test_filter_by_content_type():
    """Test filtering by content type."""
    parser = ResultParser()

    results = [
        parser.parse_result("Page", "https://example.com/page", "test", "test", 1),
        parser.parse_result("PDF", "https://example.com/doc.pdf", "test", "test", 2),
        parser.parse_result("Image", "https://example.com/img.jpg", "test", "test", 3),
    ]

    # Only webpages
    webpages = parser.filter_results(results, content_types=["webpage"])
    assert len(webpages) == 1
    assert webpages[0].content_type == "webpage"

    # PDFs and images
    docs = parser.filter_results(results, content_types=["pdf", "image"])
    assert len(docs) == 2


def test_filter_by_domain():
    """Test domain whitelist/blacklist filtering."""
    parser = ResultParser()

    results = [
        parser.parse_result("Python", "https://python.org/page", "test", "test", 1),
        parser.parse_result("Example", "https://example.com/page", "test", "test", 2),
        parser.parse_result("Test", "https://test.com/page", "test", "test", 3),
    ]

    # Whitelist
    whitelisted = parser.filter_results(
        results, domain_whitelist=["python.org", "test.com"]
    )
    assert len(whitelisted) == 2
    assert all(r.domain in ["python.org", "test.com"] for r in whitelisted)

    # Blacklist
    blacklisted = parser.filter_results(results, domain_blacklist=["example.com"])
    assert len(blacklisted) == 2
    assert all(r.domain != "example.com" for r in blacklisted)


def test_rank_results():
    """Test result re-ranking."""
    parser = ResultParser(calculate_relevance=True)

    results = [
        parser.parse_result("Low", "https://low.com", "test", "query", 10),
        parser.parse_result("Medium", "https://medium.com", "query", "query", 5),
        parser.parse_result("High", "https://high.com", "query test", "query", 1),
    ]

    ranked = parser.rank_results(results)

    # Should be sorted by relevance (descending)
    for i in range(len(ranked) - 1):
        assert ranked[i].relevance_score >= ranked[i + 1].relevance_score


def test_rank_with_domain_boost():
    """Test ranking with domain boosting."""
    parser = ResultParser(calculate_relevance=True)

    results = [
        parser.parse_result("Python", "https://python.org/page", "python", "python", 1),
        parser.parse_result(
            "Example", "https://example.com/page", "python", "python", 2
        ),
    ]

    # Boost python.org
    ranked = parser.rank_results(results, boost_domains={"python.org": 2.0})

    # python.org should be first (due to boost)
    assert ranked[0].domain == "python.org"


def test_snippet_truncation():
    """Test snippet length constraints."""
    parser = ResultParser(min_snippet_length=50, max_snippet_length=100)

    # Too short (padded)
    short = parser.parse_result("Title", "https://example.com", "Short", "test", 1)
    assert len(short.snippet) >= 50

    # Too long (truncated)
    long_snippet = "x" * 200
    long = parser.parse_result("Title", "https://example.com", long_snippet, "test", 1)
    assert len(long.snippet) <= 103  # 100 + "..."


def test_metadata_extraction():
    """Test metadata extraction from results."""
    parser = ResultParser(extract_metadata=True)

    parsed = parser.parse_result(
        title="Test Article",
        url="https://example.com/2024/01/article",
        snippet="Published on January 1, 2024",
        query="test",
        position=1,
    )

    # Should have metadata
    assert parsed.metadata is not None
    assert isinstance(parsed.metadata, dict)
